"""Ejecuta una vez cada slot congelado; nunca reintenta un intento incierto."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from freeze import CODE
from run_one import MODEL, run


HERE = Path(__file__).resolve().parent
CRITICAL = {'stale_ack', 'foreign_session', 'context_digest_mismatch',
            'main_call_trace_count_mismatch', 'call_byte_mismatch',
            'effective_digest_mismatch', 'messages_snapshot_missing',
            'messages_snapshot_unavailable', 'messages_digest_mismatch',
            'messages_snapshot_reference_mismatch', 'message_match_missing',
            'message_snapshot_limit_exceeded'}
PRODUCT_CODE = {'source_cli.py', 'runtime_store.py', 'runtime_views.py',
                'runtime_reader.py'}


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_hash(path, expected, code):
    if _sha(path) != expected:
        raise ValueError(code + ':' + str(path))


def _check_frozen(freeze, corpus, config_home):
    root = HERE.parents[1]
    if set(freeze['code_hashes']) != set(CODE):
        raise ValueError('code_hashes_incomplete')
    if set(freeze['product_code_hashes']) != PRODUCT_CODE:
        raise ValueError('product_code_hashes_incomplete')
    if set(freeze['corpus_hashes']) != {'manifest.json', 'tasks.json', 'oracle.json'}:
        raise ValueError('corpus_hashes_incomplete')
    if len(freeze['source_files']) != 66:
        raise ValueError('source_inventory_incomplete')
    if len({item['path'] for item in freeze['source_files']}) != 66:
        raise ValueError('source_inventory_duplicate')
    if (len(freeze['slots']) != 108
            or [slot['slot'] for slot in freeze['slots']] != list(range(1, 109))):
        raise ValueError('slot_inventory_mismatch')
    if (freeze['model_requested'] != MODEL
            or freeze['client_version'] != '1.18.35'):
        raise ValueError('requested_client_profile_mismatch')
    if freeze['schema'] == 'skopos/agent-query-freeze/v1':
        capture = freeze.get('message_capture')
        expected_bytes = {'none': 0, 'synthetic_bounded_v1': 524288}.get(capture)
        if (expected_bytes is None or
                freeze['limits'].get('message_snapshot_bytes') != expected_bytes):
            raise ValueError('message_capture_policy_mismatch')
    elif freeze['schema'] == 'skopos/agent-query-freeze/v0':
        if freeze.get('message_capture', 'none') != 'none':
            raise ValueError('message_capture_policy_mismatch')
    else:
        raise ValueError('unsupported_freeze_schema')
    for name, digest in freeze['code_hashes'].items():
        _require_hash(HERE / name, digest, 'code_changed')
    for name, digest in freeze['product_code_hashes'].items():
        _require_hash(root / 'src/skopos' / name, digest, 'product_code_changed')
    _require_hash(root / 'docs/planes/activos/piloto-consulta-agente-2026-10-07.md',
                  freeze['plan_sha256'], 'plan_changed')
    for name, digest in freeze['corpus_hashes'].items():
        _require_hash(corpus / name, digest, 'corpus_changed')
    _require_hash(config_home / 'opencode/opencode.json',
                  freeze['code_hashes']['opencode/config.json'], 'config_changed')
    _require_hash(config_home / 'opencode/plugins/trace.js',
                  freeze['code_hashes']['opencode/trace.js'], 'trace_changed')
    _require_hash(config_home / 'opencode/tools/evidence.js',
                  freeze['code_hashes']['opencode/evidence.js'], 'tool_changed')
    for item in freeze['source_files']:
        path = Path(item['path'])
        if item['status'] == 'present':
            _require_hash(path, item['sha256'], 'source_changed')
        elif item['status'] == 'unavailable_after_import':
            if path.exists():
                raise ValueError('unavailable_source_restored:' + str(path))
            _require_hash(path.with_suffix('.held'), item['sha256'], 'held_source_changed')
        else:
            raise ValueError('invalid_source_status')


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
                          target, corpus, lab, config_home, workspace,
                          message_capture=freeze.get('message_capture', 'none'))
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
