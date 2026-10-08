"""Ejecuta una vez cada slot congelado; nunca reintenta un intento incierto."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from run_one import run


HERE = Path(__file__).resolve().parent
CRITICAL = {'stale_ack', 'foreign_session', 'context_digest_mismatch',
            'main_call_trace_count_mismatch', 'call_byte_mismatch',
            'effective_digest_mismatch'}


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_frozen(freeze, corpus, config_home):
    for name, digest in freeze['code_hashes'].items():
        assert _sha(HERE / name) == digest, 'code_changed:' + name
    for name, digest in freeze['corpus_hashes'].items():
        assert _sha(corpus / name) == digest, 'corpus_changed:' + name
    assert _sha(config_home / 'opencode/opencode.json') == freeze['code_hashes']['opencode/config.json']
    assert _sha(config_home / 'opencode/plugins/trace.js') == freeze['code_hashes']['opencode/trace.js']
    assert _sha(config_home / 'opencode/tools/evidence.js') == freeze['code_hashes']['opencode/evidence.js']
    for item in freeze['source_files']:
        path = Path(item['path'])
        if item['status'] == 'present':
            assert _sha(path) == item['sha256'], 'source_changed:' + str(path)
        else:
            assert not path.exists(), 'unavailable_source_restored:' + str(path)
            assert _sha(path.with_suffix('.held')) == item['sha256'], 'held_source_changed'


def _append(path, record):
    with path.open('a') as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
        stream.flush()


def series(freeze_path, output_root, corpus, lab, config_home, workspace):
    freeze = json.loads(freeze_path.read_text())
    _check_frozen(freeze, corpus, config_home)
    output_root.mkdir(exist_ok=True)
    progress = output_root / 'progress.jsonl'
    if progress.exists():
        raise ValueError('series_already_started_no_automatic_resume')
    for slot in freeze['slots']:
        _check_frozen(freeze, corpus, config_home)
        name = '%03d-%s-%s-%s' % (slot['slot'], slot['task_id'],
                                   slot['variant_id'], slot['condition'])
        target = output_root / name
        _append(progress, {'slot': slot['slot'], 'event': 'started', 'at': _utc(),
                           'target': name})
        try:
            summary = run(slot['condition'], slot['task_id'], slot['variant_id'],
                          target, corpus, lab, config_home, workspace)
        except Exception as error:
            _append(progress, {'slot': slot['slot'], 'event': 'failed', 'at': _utc(),
                               'error_type': type(error).__name__, 'error': str(error)[:180]})
            print(json.dumps({'slot': slot['slot'], 'status': 'failed',
                              'error_type': type(error).__name__}), flush=True)
            raise
        status = ('completed' if summary['returncode'] == 0 and not summary['timed_out']
                  and summary['receipt']['status'] == 'pass' and summary['answer'].strip()
                  else 'failed')
        _append(progress, {'slot': slot['slot'], 'event': status, 'at': _utc(),
                           'run_id': summary['run_id'], 'elapsed_ms': summary['elapsed_ms'],
                           'receipt': summary['receipt']['status'],
                           'model_calls': summary['model_calls']})
        print(json.dumps({'slot': slot['slot'], 'status': status,
                          'condition': slot['condition'], 'task_id': slot['task_id'],
                          'variant_id': slot['variant_id'],
                          'elapsed_ms': summary['elapsed_ms']}), flush=True)
        if CRITICAL.intersection(summary['receipt'].get('errors', [])):
            raise RuntimeError('critical_receipt_failure_at_slot_%d' % slot['slot'])


def main():
    if len(sys.argv) != 7:
        raise SystemExit('usage: run_series.py FREEZE OUTPUT_ROOT CORPUS LAB CONFIG_HOME WORKSPACE')
    series(*(Path(value) for value in sys.argv[1:]))


if __name__ == '__main__':
    main()
