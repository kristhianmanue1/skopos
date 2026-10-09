"""Arranque bajo demanda del piloto PDF IMSS; no instala un servicio permanente."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from skopos.pdf_custody import (_policy_digest, _read_under, load_policy,
                                read_request)
from skopos.pdf_custody_host import HOST_SCHEMA, load_host_config


ROOT = Path(__file__).resolve().parents[1] / 'runs/pdf-custody-imss-pilot-v1'
CONTROL = ROOT / 'operator.sock'
EXPECTED_POLICY = 'a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160'
EXPECTED_RECEIPT = 'expertogobernanza:imss-2000-002-001:1:4fbed2bd3d2633aa'
MONGO_URI = 'mongodb://127.0.0.1:37034/?directConnection=true'
MONGO_SET = 'skoposPdfImssPilot'
MONGO_BIN = '/opt/homebrew/bin/mongod'


def _mode(path, expected, *, directory=False):
    details = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(details.st_mode) or details.st_uid != os.getuid()
            or stat.S_IMODE(details.st_mode) != expected):
        raise ValueError('unsafe_permissions:' + str(path))


def preflight():
    _mode(ROOT, 0o700, directory=True)
    _mode(ROOT / 'db', 0o700, directory=True)
    _mode(ROOT / 'delivery', 0o700, directory=True)
    _mode(ROOT / 'host.json', 0o600)
    _mode(ROOT / 'policy.json', 0o600)
    config = load_host_config(str(ROOT / 'host.json'))
    policy = load_policy(config['policy_path'])
    if (Path(config['policy_path']) != ROOT / 'policy.json'
            or Path(config['socket_path']) != ROOT / 'agent.sock'
            or config['mongo_uri'] !=
            'mongodb://127.0.0.1:37034/?replicaSet=skoposPdfImssPilot'
            or config['database'] != 'skopos_pdf_imss_pilot_v1'
            or _policy_digest(policy) != EXPECTED_POLICY
            or policy['project_id'] != 'expertogobernanza'
            or policy['retention_until'] != '2026-11-08T00:00:00Z'
            or policy['recovery_requirement'] != 'while_reference_available'
            or len(policy['allowed_materials']) != 1):
        raise ValueError('pilot_policy_mismatch')
    material = policy['allowed_materials'][0]
    if material['material_id'] != 'imss-2000-002-001' or material['source_revision'] != 1:
        raise ValueError('pilot_material_mismatch')
    for reference, expected in ((material['source_ref'], material['source_sha256']),
                                (material['provenance_ref'], material['provenance_sha256'])):
        raw = _read_under(policy['source_root'], reference, policy['max_bytes'])
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('source_hash_mismatch:' + reference)
    _mode(Path(policy['requests_root']), 0o700, directory=True)
    if not Path(MONGO_BIN).is_file():
        raise ValueError('mongod_unavailable')
    return config, policy


def _control(command):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(str(CONTROL))
        connection.sendall(json.dumps({'command': command}).encode() + b'\n')
        response = b''
        while not response.endswith(b'\n') and len(response) < 4096:
            block = connection.recv(4096)
            if not block:
                raise ValueError('control_disconnected')
            response += block
    return json.loads(response)


def _mongo_ready():
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=500) as client:
        hello = client.admin.command('hello')
        options = client.admin.command('getCmdLineOpts')['parsed']
        if (hello.get('setName') != MONGO_SET or not hello.get('isWritablePrimary')
                or options['storage']['dbPath'] != str(ROOT / 'db')
                or options['replication']['replSet'] != MONGO_SET
                or options['net']['bindIp'] != '127.0.0.1'
                or options['net']['port'] != 37034):
            raise ValueError('mongo_identity_mismatch')


def _socket_ready(path):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        connection.connect(path)


def _wait_for(check, process, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError('child_exited:' + str(process.returncode))
        try:
            check()
            return
        except (OSError, PyMongoError):
            time.sleep(0.1)
    raise ValueError('startup_timeout')


def _stop_child(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            raise ValueError('child_stop_timeout:' + str(process.pid)) from None


def _record_counts(config):
    with MongoClient(config['mongo_uri'], serverSelectionTimeoutMS=1000) as client:
        database = client[config['database']]
        material = 'expertogobernanza:imss-2000-002-001'
        return (database.pdf_custody_revisions_v1.count_documents(
                    {'_id': material + ':1'}),
                database.pdf_custody_heads_v1.count_documents({'_id': material}))


def serve():
    config, _ = preflight()
    if CONTROL.exists() or Path(config['socket_path']).exists():
        raise ValueError('socket_already_exists')
    mongo = host = None
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as control:
        control.bind(str(CONTROL))
        os.chmod(CONTROL, 0o600)
        socket_inode = CONTROL.stat().st_ino
        control.listen(2)
        control.settimeout(1)
        prior = signal.getsignal(signal.SIGTERM)

        def terminate(_number, _frame):
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, terminate)
        try:
            with (ROOT / 'mongo.stdout.log').open('ab') as mongo_log, \
                    (ROOT / 'host.stdout.log').open('ab') as host_log:
                os.fchmod(mongo_log.fileno(), 0o600)
                os.fchmod(host_log.fileno(), 0o600)
                mongo = subprocess.Popen([
                    MONGO_BIN, '--dbpath', str(ROOT / 'db'), '--port', '37034',
                    '--bind_ip', '127.0.0.1', '--replSet', MONGO_SET,
                    '--logpath', str(ROOT / 'mongo.log'), '--logappend'],
                    stdin=subprocess.DEVNULL, stdout=mongo_log, stderr=mongo_log)
                _wait_for(_mongo_ready, mongo)
                host = subprocess.Popen([
                    sys.executable, '-m', 'skopos', 'custody-host', 'serve',
                    '--config', str(ROOT / 'host.json')], stdin=subprocess.DEVNULL,
                    stdout=host_log, stderr=host_log, cwd=str(ROOT.parents[1]))
                _wait_for(lambda: _socket_ready(config['socket_path']), host)
                while True:
                    if mongo.poll() is not None or host.poll() is not None:
                        raise ValueError('child_exited_during_service')
                    try:
                        connection, _ = control.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        connection.settimeout(2)
                        request = connection.recv(512)
                        try:
                            command = json.loads(request).get('command')
                        except (ValueError, TypeError):
                            command = None
                        response = {'status': 'ready' if command == 'status' else
                                    'stopping' if command == 'stop' else 'invalid_command',
                                    'policy_sha256': EXPECTED_POLICY}
                        connection.sendall(json.dumps(response).encode() + b'\n')
                        if command == 'stop':
                            break
        finally:
            signal.signal(signal.SIGTERM, prior)
            try:
                _stop_child(host)
            finally:
                try:
                    _stop_child(mongo)
                finally:
                    try:
                        if CONTROL.stat().st_ino == socket_inode:
                            CONTROL.unlink()
                    except FileNotFoundError:
                        pass


def _request_raw(socket_path, call):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(socket_path)
        connection.sendall(json.dumps(call).encode() + b'\n')
        raw = b''
        while not raw.endswith(b'\n') and len(raw) < 65536:
            block = connection.recv(65536)
            if not block:
                raise ValueError('host_disconnected')
            raw += block
    return json.loads(raw)


def _request(config, policy, reference, operation):
    envelope = json.loads(_read_under(policy['requests_root'], reference, 65536))
    request = read_request(policy, envelope, contract_version='v0.2')
    if request.get('operation') != operation:
        raise ValueError('unexpected_operation:' + reference)
    response = _request_raw(config['socket_path'], {'envelope_ref': reference})
    if response.get('schema') != HOST_SCHEMA or response.get('status') != 'ok':
        raise ValueError('smoke_request_failed:' + json.dumps(response))
    return request, response['result']


def smoke(args):
    config, policy = preflight()
    if _control('status')['status'] != 'ready':
        raise ValueError('pilot_not_ready')
    _mongo_ready()
    before = _record_counts(config)
    if before != (1, 1):
        raise ValueError('unexpected_record_counts:' + str(before))
    _, capabilities = _request(config, policy, args.capabilities_ref, 'describe_capabilities')
    if capabilities['policy']['policy_sha256'] != EXPECTED_POLICY:
        raise ValueError('capabilities_policy_mismatch')
    _, receipt = _request(config, policy, args.receipt_ref, 'receipt')
    if receipt['receipt_id'] != EXPECTED_RECEIPT:
        raise ValueError('receipt_mismatch')
    fetch_request, _ = _request_preview(policy, args.fetch_ref)
    output_ref = fetch_request['output_ref']
    if '/' in output_ref or output_ref in ('.', '..'):
        raise ValueError('unsafe_output_ref')
    output = Path(policy['delivery_root']) / output_ref
    if output.exists() or output.is_symlink():
        raise ValueError('output_already_exists')
    try:
        _, fetched = _request(config, policy, args.fetch_ref, 'fetch_original')
        if (fetched['bytes_ref'] != output_ref
                or fetched['source_sha256'] != receipt['source_sha256']
                or fetched['source_revision'] != 1):
            raise ValueError('fetch_mismatch')
        _mode(output, 0o600)
        raw = _read_under(policy['delivery_root'], output_ref, policy['max_bytes'])
        if (len(raw) != fetched['byte_length']
                or hashlib.sha256(raw).hexdigest() != receipt['source_sha256']
                or raw != _read_under(policy['source_root'],
                                      policy['allowed_materials'][0]['source_ref'],
                                      policy['max_bytes'])):
            raise ValueError('fetched_bytes_mismatch')
    finally:
        if output.is_file() and not output.is_symlink():
            candidate = _read_under(policy['delivery_root'], output_ref,
                                    policy['max_bytes'])
            if hashlib.sha256(candidate).hexdigest() == receipt['source_sha256']:
                output.unlink()
    after = _record_counts(config)
    if after != before:
        raise ValueError('record_counts_changed:' + str(after))
    return {'status': 'verified', 'receipt_id': EXPECTED_RECEIPT,
            'source_sha256': receipt['source_sha256'], 'bytes': fetched['byte_length'],
            'output_removed': not output.exists(), 'record_counts': after}


def _request_preview(policy, reference):
    envelope = json.loads(_read_under(policy['requests_root'], reference, 65536))
    request = read_request(policy, envelope, contract_version='v0.2')
    if request.get('operation') != 'fetch_original':
        raise ValueError('unexpected_operation:' + reference)
    return request, envelope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('preflight', 'start', 'status', 'stop', 'serve'):
        sub.add_parser(name)
    smoke_parser = sub.add_parser('smoke')
    for name in ('capabilities-ref', 'receipt-ref', 'fetch-ref'):
        smoke_parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'preflight':
            preflight()
            result = {'status': 'ready_to_start', 'policy_sha256': EXPECTED_POLICY}
        elif args.command == 'serve':
            serve()
            result = {'status': 'stopped'}
        elif args.command == 'start':
            preflight()
            if CONTROL.exists():
                raise ValueError('control_socket_already_exists')
            started = time.monotonic()
            with (ROOT / 'operator.stdout.log').open('ab') as log:
                os.fchmod(log.fileno(), 0o600)
                process = subprocess.Popen([sys.executable, __file__, 'serve'],
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=log, start_new_session=True)
            try:
                _wait_for(lambda: _control('status'), process)
            except (OSError, ValueError, PyMongoError):
                _stop_child(process)
                raise
            result = {'status': 'ready', 'startup_seconds': round(time.monotonic() - started, 3),
                      'policy_sha256': EXPECTED_POLICY}
        elif args.command == 'status':
            result = _control('status')
            if result['status'] == 'ready':
                _mongo_ready()
                config, _ = preflight()
                _socket_ready(config['socket_path'])
        elif args.command == 'stop':
            _control('stop')
            deadline = time.monotonic() + 20
            while CONTROL.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            if CONTROL.exists() or (ROOT / 'agent.sock').exists():
                raise ValueError('stop_not_confirmed')
            result = {'status': 'stopped', 'policy_sha256': EXPECTED_POLICY}
        else:
            result = smoke(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, PyMongoError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
