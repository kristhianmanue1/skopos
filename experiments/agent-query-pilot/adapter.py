"""Adaptador de lectura del piloto: allowlist, límites y trazas por ejecución."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import uuid


BACKEND = Path(__file__).with_name('backend.py')
MAX_STDOUT = 1024 * 1024
MAX_STDERR = 64 * 1024
MAX_CONTEXT = 128 * 1024
DEADLINE = 10


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _backend(request, config):
    env = {**os.environ, 'SKOPOS_PILOT_CONDITION': config['condition'],
           'SKOPOS_PILOT_PROJECT': config['project_id'],
           'SKOPOS_PILOT_CORPUS': config['corpus_dir'],
           'SKOPOS_PILOT_LAB': config['lab_dir']}
    process = subprocess.Popen([sys.executable, str(BACKEND)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, start_new_session=True)
    process.stdin.write(json.dumps(request, ensure_ascii=False).encode())
    process.stdin.close()
    streams = selectors.DefaultSelector()
    streams.register(process.stdout, selectors.EVENT_READ, 'stdout')
    streams.register(process.stderr, selectors.EVENT_READ, 'stderr')
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    reason = None
    started = time.monotonic()
    try:
        while streams.get_map() or process.poll() is None:
            remaining = DEADLINE - (time.monotonic() - started)
            if remaining <= 0:
                reason = 'timed_out'
                break
            for key, _ in streams.select(timeout=min(.2, remaining)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    streams.unregister(key.fileobj)
                    continue
                buffer = output[key.data]
                buffer.extend(chunk)
                maximum = MAX_STDOUT if key.data == 'stdout' else MAX_STDERR
                if len(buffer) > maximum:
                    reason = 'response_too_large'
                    break
            if reason:
                break
    finally:
        if reason and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)
        streams.close()
    return bytes(output['stdout']), bytes(output['stderr']), process.returncode, reason


def _request(value, project_id):
    if type(value) is not dict or value.get('operation') not in ('search', 'fetch'):
        raise ValueError('operation_not_allowed')
    if value['operation'] == 'search':
        if set(value) != {'operation', 'term'}:
            raise ValueError('invalid_request_fields')
        if type(value['term']) is not str or not value['term'].strip():
            raise ValueError('invalid_term')
        return {'operation': 'search', 'project_id': project_id,
                'term': value['term'], 'limit': 5}
    required = {'operation', 'source_id', 'source_revision',
                'source_sha256', 'text_id'}
    if set(value) != required:
        raise ValueError('invalid_request_fields')
    return {**value, 'project_id': project_id}


def _record(run_dir, record):
    with (run_dir / 'requests.jsonl').open('a') as stream:
        stream.write(json.dumps(record, ensure_ascii=False,
                                separators=(',', ':')) + '\n')


def _search_scope(result):
    if not isinstance(result, dict):
        return None
    excluded = result.get('excluded') or {}
    unavailable = result.get('unavailable_sources') or {}
    return {'selection': result.get('selection'),
            'result_limit': excluded.get('result_limit', 0),
            'fragment_too_large': excluded.get('fragment_too_large', 0),
            'unavailable_sources': unavailable,
            'interpretation': 'literal_observed_heads_only_no_global_absence'}


def invoke(run_dir, value):
    run_dir = Path(run_dir)
    config = json.loads((run_dir / 'config.json').read_text())
    if config['condition'] not in ('A', 'B', 'C'):
        raise ValueError('invalid_condition')
    request = _request(value, config['project_id'])
    lock_path = run_dir / 'budget.lock'
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = run_dir / 'budget.json'
        state = (json.loads(state_path.read_text()) if state_path.exists()
                 else {'searches': 0, 'fetches': 0, 'output_bytes': 0})
        counter = 'searches' if request['operation'] == 'search' else 'fetches'
        if state[counter] >= 3:
            raise ValueError('operation_budget_exceeded')
        state[counter] += 1
        state_path.write_text(json.dumps(state, sort_keys=True) + '\n')
        request_id = uuid.uuid4().hex
        start_utc = _utc()
        start_mono = time.monotonic()
        stdout, stderr, returncode, reason = _backend(request, config)
        raw_dir = run_dir / 'raw'
        raw_dir.mkdir(exist_ok=True)
        (raw_dir / (request_id + '.stdout')).write_bytes(stdout)
        (raw_dir / (request_id + '.stderr')).write_bytes(stderr)
        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        status = reason or ('failed' if returncode else 'produced')
        payload = None
        if status == 'produced':
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                status = 'invalid_json'
        record = {'schema': 'skopos/agent-query-request/v0',
                  'run_id': config['run_id'], 'task_id': config['task_id'],
                  'variant_id': config['variant_id'], 'condition': config['condition'],
                  'request_id': request_id, 'attempt_id': state[counter],
                  'client': 'opencode', 'client_version': '1.18.35',
                  'model_requested': 'zai-coding-plan/glm-5.3-flash',
                  'model_effective': None, 'model_evidence': None,
                  'operation': request['operation'], 'project_id': config['project_id'],
                  'query': request.get('term'), 'deadline_ms': DEADLINE * 1000,
                  'result_status': status, 'response_sha256': hashlib.sha256(stdout).hexdigest(),
                  'response_bytes': len(stdout), 'stderr_bytes': len(stderr),
                  'started_at': start_utc, 'finished_at': _utc(),
                  'elapsed_ms': elapsed_ms, 'returncode': returncode,
                  'raw_stdout': 'raw/' + request_id + '.stdout',
                  'raw_stderr': 'raw/' + request_id + '.stderr',
                  'result': payload,
                  'search_scope': (_search_scope(payload)
                                   if request['operation'] == 'search'
                                   and status == 'produced' else None)}
        encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode()
        if state['output_bytes'] + len(encoded) > MAX_CONTEXT:
            record['result_status'] = 'context_budget_exceeded'
            record['result'] = None
            record['search_scope'] = None
            encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode()
        state['output_bytes'] += len(encoded)
        state_path.write_text(json.dumps(state, sort_keys=True) + '\n')
        _record(run_dir, record)
        return encoded.decode()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: adapter.py RUN_DIR')
    try:
        value = json.load(sys.stdin)
        print(invoke(sys.argv[1], value))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(str(error).split(':', 1)[0], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
