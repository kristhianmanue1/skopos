"""Métricas mecánicas de T4; no adjudica semántica ni autoridad."""
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import sys


HASH = re.compile(r'\b[0-9a-f]{64}\b')


def _evidence_hashes(value):
    if isinstance(value, dict):
        found = {item for key, item in value.items()
                 if 'sha256' in key and isinstance(item, str) and HASH.fullmatch(item)}
        for item in value.values():
            found.update(_evidence_hashes(item))
        return found
    if isinstance(value, list):
        found = set()
        for item in value:
            found.update(_evidence_hashes(item))
        return found
    return set()


def _jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []


def analyze(root, corpus):
    oracle = {(item['task_id'], item['variant_id']): item
              for item in json.loads((corpus / 'oracle.json').read_text())}
    freeze = json.loads((root / 'freeze-final.json').read_text())
    rows = []
    for slot in freeze['slots']:
        dirname = '%03d-%s-%s-%s' % (slot['slot'], slot['task_id'],
                                      slot['variant_id'], slot['condition'])
        directory = root / dirname
        summary_path = directory / 'summary.json'
        if not summary_path.exists():
            rows.append({**slot, 'status': 'not_completed', 'directory': dirname})
            continue
        summary = json.loads(summary_path.read_text())
        events = _jsonl(directory / 'events.jsonl')
        final_messages = [item['part']['messageID'] for item in events
                          if item.get('type') == 'step_finish'
                          and item.get('part', {}).get('reason') == 'stop']
        final_message_id = final_messages[-1] if final_messages else None
        answer = '\n'.join(item['part']['text'] for item in events
                           if item.get('type') == 'text'
                           and item.get('part', {}).get('messageID') == final_message_id)
        expected = oracle[(slot['task_id'], slot['variant_id'])]
        all_hashes = set(HASH.findall(answer))
        supported = set()
        supported_evidence_hashes = set()
        requests = _jsonl(directory / 'requests.jsonl')
        calls = _jsonl(directory / 'call-trace.jsonl')
        steps = [item['part'] for item in events if item.get('type') == 'step_finish']
        tool_events = [item['part'] for item in events if item.get('type') == 'tool_use']
        transport_hashes = {item['response_sha256'] for item in requests}
        transport_hashes.update(item['context_sha256'] for item in
                                _jsonl(directory / 'deliveries.jsonl'))
        cited_source_hashes = all_hashes - transport_hashes
        for request in requests:
            if request['result_status'] != 'produced' or not request['result']:
                continue
            result = request['result']
            supported_evidence_hashes.update(_evidence_hashes(result))
            for item in result.get('results', [result]):
                if isinstance(item, dict) and item.get('source_sha256'):
                    supported.add(item['source_sha256'])
        expected_value = expected['expected']
        if isinstance(expected_value, dict):
            literal_found = all(str(value).casefold() in answer.casefold()
                                for value in expected_value.values())
        elif expected_value in ('conflict_unresolved', 'insufficient_evidence',
                                'source_unavailable', 'excluded_by_result_limit'):
            literal_found = None
        else:
            literal_found = str(expected_value).casefold() in answer.casefold()
        status = ('completed' if summary['returncode'] == 0 and not summary['timed_out']
                  and summary['receipt']['status'] == 'pass' and answer.strip()
                  else 'failed')
        rows.append({**slot, 'status': status, 'directory': dirname,
                     'run_id': summary['run_id'], 'elapsed_ms': summary['elapsed_ms'],
                     'model_calls': summary['model_calls'],
                     'input_tokens_client_reported': sum(item.get('tokens', {}).get('input', 0)
                                                          for item in steps),
                     'output_tokens_client_reported': sum(item.get('tokens', {}).get('output', 0)
                                                           for item in steps),
                     'cost_client_reported': sum(item.get('cost', 0) or 0 for item in steps),
                     'searches': sum(item['operation'] == 'search' for item in requests),
                     'fetches': sum(item['operation'] == 'fetch' for item in requests),
                     'search_attempts': sum(item.get('tool') == 'evidence_search'
                                            for item in tool_events) + int(slot['condition'] == 'C'),
                     'fetch_attempts': sum(item.get('tool') == 'evidence_fetch'
                                           for item in tool_events),
                     'tool_errors': sum(item.get('state', {}).get('status') == 'error'
                                        for item in tool_events),
                     'deliveries': summary['receipt'].get('deliveries', 0),
                     'incorporated_deliveries': summary['receipt'].get('incorporated_deliveries', 0),
                     'call_delivery_occurrences': sum(len(item['matched_deliveries']) for item in calls),
                     'cumulative_context_bytes': summary['receipt'].get('cumulative_delivered_bytes', 0),
                     'receipt_status': summary['receipt']['status'],
                     'receipt_errors': summary['receipt'].get('errors', []),
                     'final_message_id': final_message_id,
                     'expected_literal_found': literal_found,
                     'cited_source_hashes': sorted(cited_source_hashes),
                     'unsupported_cited_hashes': sorted(cited_source_hashes - supported_evidence_hashes),
                     'expected_source_hashes_found': sorted(
                         item['source_sha256'] for item in expected['admissible_sources']
                         if item['source_sha256'] in cited_source_hashes),
                     'answer': answer})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['condition']].append(row)
    metrics = {'planned': 108, 'completed': sum(row['status'] == 'completed' for row in rows),
               'failed': sum(row['status'] == 'failed' for row in rows),
               'not_completed': sum(row['status'] == 'not_completed' for row in rows),
               'conditions': {}}
    for condition, items in sorted(grouped.items()):
        durations = [item['elapsed_ms'] for item in items if item['status'] == 'completed']
        metrics['conditions'][condition] = {
            'completed': len(durations),
            'failed': sum(item['status'] == 'failed' for item in items),
            'not_completed': sum(item['status'] == 'not_completed' for item in items),
            'latency_median_ms': statistics.median(durations) if durations else None,
            'latency_max_ms': max(durations) if durations else None,
            'incorporated_deliveries': sum(item.get('incorporated_deliveries', 0) for item in items),
            'deliveries': sum(item.get('deliveries', 0) for item in items),
            'call_delivery_occurrences': sum(item.get('call_delivery_occurrences', 0) for item in items),
            'model_calls': sum(item.get('model_calls', 0) for item in items),
            'tool_errors': sum(item.get('tool_errors', 0) for item in items),
            'input_tokens_client_reported': sum(item.get('input_tokens_client_reported', 0)
                                                for item in items),
            'output_tokens_client_reported': sum(item.get('output_tokens_client_reported', 0)
                                                 for item in items),
            'cost_client_reported': sum(item.get('cost_client_reported', 0)
                                        for item in items),
            'unsupported_citation_runs': sum(bool(item.get('unsupported_cited_hashes')) for item in items),
        }
    return rows, metrics


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: analyze_series.py SERIES_ROOT CORPUS_DIR')
    root, corpus = map(Path, sys.argv[1:])
    rows, metrics = analyze(root, corpus)
    (root / 'mechanical-evaluations.jsonl').write_text(''.join(
        json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    (root / 'mechanical-metrics.json').write_text(json.dumps(metrics, ensure_ascii=False,
                                                          indent=2) + '\n')
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == '__main__':
    main()
