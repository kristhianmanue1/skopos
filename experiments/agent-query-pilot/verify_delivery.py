"""Comprueba correlación de entregas con el hook de llamada de OpenCode."""
import hashlib
import json
from pathlib import Path
import sys


def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def verify(run_dir):
    run_dir = Path(run_dir)
    deliveries = _jsonl(run_dir / 'deliveries.jsonl')
    calls = _jsonl(run_dir / 'call-trace.jsonl')
    events = _jsonl(run_dir / 'events.jsonl')
    session_ids = {event['sessionID'] for event in events if 'sessionID' in event}
    errors = []
    if len(session_ids) != 1:
        errors.append('session_count')
    if not calls:
        errors.append('no_model_call')
    primary_starts = [event for event in events if event.get('type') == 'step_start']
    primary_finishes = [event for event in events if event.get('type') == 'step_finish']
    accepted_calls = [call for call in calls if call.get('violation') is None]
    if len(primary_starts) != len(accepted_calls) or len(primary_finishes) != len(accepted_calls):
        errors.append('main_call_trace_count_mismatch')
    if len(calls) > 8:
        errors.append('model_call_budget_exceeded')
    seen = set()
    for delivery in deliveries:
        pair = (delivery['request_id'], delivery['invocation_id'])
        if pair in seen:
            errors.append('duplicate_delivery')
        seen.add(pair)
        digest = hashlib.sha256(delivery['payload'].encode()).hexdigest()
        if digest != delivery['context_sha256']:
            errors.append('context_digest_mismatch')
        if len(delivery['payload'].encode()) != delivery['delivered_bytes']:
            errors.append('delivery_size_mismatch')
        if delivery.get('session_id') is not None and delivery['session_id'] not in session_ids:
            errors.append('foreign_session')
    trace_by_pair = {}
    cumulative = 0
    accepted_cumulative = 0
    for index, call in enumerate(calls, 1):
        if call['call_index'] != index:
            errors.append('call_order')
        matches = call['matched_deliveries']
        expected_bytes = 0
        for match in matches:
            item = next((candidate for candidate in deliveries
                         if candidate['request_id'] == match['request_id']
                         and candidate['invocation_id'] == match['invocation_id']
                         and candidate['context_sha256'] == match['context_sha256']
                         and candidate['session_id'] == match['session_id']), None)
            if item is None:
                errors.append('stale_ack')
                continue
            kind = match.get('representation')
            if kind == 'raw':
                effective = item['payload']
            elif kind == 'json_escaped':
                effective = json.dumps(item['payload'], ensure_ascii=False)[1:-1]
            else:
                errors.append('unknown_representation')
                continue
            if hashlib.sha256(effective.encode()).hexdigest() != match.get('effective_sha256'):
                errors.append('effective_digest_mismatch')
            if len(effective.encode()) != match.get('effective_bytes'):
                errors.append('effective_size_mismatch')
            expected_bytes += len(effective.encode())
        cumulative += expected_bytes
        if call['delivered_bytes'] != expected_bytes or call['cumulative_bytes'] != cumulative:
            errors.append('call_byte_mismatch')
        if call['violation'] is not None:
            errors.append(call['violation'])
        else:
            accepted_cumulative += expected_bytes
        for match in matches:
            pair = (match['request_id'], match['invocation_id'])
            if pair not in seen:
                errors.append('stale_ack')
            if call['violation'] is None:
                trace_by_pair.setdefault(pair, []).append(index)
    if accepted_cumulative > 128 * 1024:
        errors.append('context_budget_exceeded')
    for item in deliveries:
        pair = (item['request_id'], item['invocation_id'])
        if not trace_by_pair.get(pair):
            errors.append('not_incorporated:' + item['request_id'])
    return {'status': 'pass' if not errors else 'fail', 'errors': sorted(set(errors)),
            'calls': len(calls), 'deliveries': len(deliveries),
            'incorporated_deliveries': len(trace_by_pair),
            'cumulative_delivered_bytes': accepted_cumulative,
            'attempted_context_bytes': cumulative,
            'session_ids': sorted(session_ids)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: verify_delivery.py RUN_DIR')
    result = verify(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
