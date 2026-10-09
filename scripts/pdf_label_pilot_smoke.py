"""Ejercita el canal local de rótulos y apaga únicamente procesos propios."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess
import time

from skopos.pdf_document_store import _canonical
from skopos.pdf_label_host import CONTRACT_ID, CONTRACT_VERSION


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'runs' / 'pdf-document-imss-pilot-v1'
POLICY_SHA256 = '21540db84c1b6b10cdbd433392caa6ed66b26d9820814c227d2d08dec948be1d'


def _run(*arguments):
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('command_failed: ' + result.stdout[-300:] + result.stderr[-300:])
    return result.stdout.strip()


def main():
    config = json.loads((PILOT / 'label-host.json').read_bytes())
    policy = json.loads((PILOT / 'label-policy.json').read_bytes())
    document = json.loads((PILOT / 'policy.json').read_bytes())
    if (config['label_policy_sha256'] != POLICY_SHA256
            or hashlib.sha256(_canonical(policy)).hexdigest() != POLICY_SHA256
            or policy['allowed_pages'] != [18, 19, 20, 21, 22]):
        raise RuntimeError('unexpected_label_policy')
    socket_path = Path(config['socket_path'])
    requests_root = Path(policy['requests_root'])
    derived_root = Path(document['derived_root'])
    delivery_root = Path(document['delivery_root'])
    manifest_path = derived_root / policy['derivation_id'] / 'manifest.json'
    manifest_before = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_before != policy['manifest_sha256']:
        raise RuntimeError('parent_manifest_changed')
    derived_before = {str(path.relative_to(derived_root))
                      for path in derived_root.rglob('*') if path.is_file()}
    delivery_before = {str(path.relative_to(delivery_root))
                       for path in delivery_root.rglob('*') if path.is_file()}
    source = {field: document[field] for field in
              ('material_id', 'source_revision', 'source_sha256',
               'custody_receipt_id', 'custody_policy_sha256')}
    prefix = 'eg-imss-label-v02-' + secrets.token_hex(4)
    summary = {'request_prefix': prefix, 'label_policy_sha256': POLICY_SHA256,
               'manifest_sha256': policy['manifest_sha256']}
    host = None
    mongo_started = False

    def start_host():
        nonlocal host
        if socket_path.exists():
            raise RuntimeError('preexisting_label_socket')
        descriptor = os.open(PILOT / 'label-host.stderr.log',
                             os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
                             0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise RuntimeError('invalid_label_log')
        os.fchmod(descriptor, 0o600)
        log = os.fdopen(descriptor, 'ab')
        try:
            host = subprocess.Popen(
                [str(ROOT / '.venv/bin/python'), '-m', 'skopos.pdf_label_host',
                 'serve', '--config', str(PILOT / 'label-host.json')],
                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=log)
        finally:
            log.close()
        for _ in range(60):
            if host.poll() is not None:
                raise RuntimeError('label_host_exited')
            if socket_path.exists():
                return
            time.sleep(0.1)
        raise RuntimeError('label_host_not_ready')

    def stop_host():
        nonlocal host
        if host is not None:
            host.terminate()
            try:
                host.wait(timeout=10)
            except subprocess.TimeoutExpired:
                host.kill()
                host.wait()
            host = None
        if socket_path.exists():
            raise RuntimeError('label_socket_remained')

    def store_request(operation, suffix, **changes):
        request = {'request_id': prefix + '-' + suffix,
                   'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION,
                   'project_id': policy['project_id'], 'operation': operation,
                   'source': source, 'label_policy_sha256': POLICY_SHA256}
        if operation == 'get_label_candidates':
            request.update({'derivation_id': policy['derivation_id'],
                            'manifest_sha256': policy['manifest_sha256'],
                            'page_number': 20, 'max_nodes': 40})
        request.update(changes)
        raw = _canonical(request)
        stem = request['request_id']
        request_ref = stem + '.request.json'
        envelope_ref = stem + '.envelope.json'
        envelope = {'request_file_ref': request_ref,
                    'request_sha256': hashlib.sha256(raw).hexdigest(),
                    'request_id': stem, 'contract_id': CONTRACT_ID,
                    'contract_version': CONTRACT_VERSION}
        for reference, payload in ((request_ref, raw),
                                   (envelope_ref, _canonical(envelope))):
            descriptor = os.open(requests_root / reference,
                                 os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
        return envelope_ref

    def send(reference, *, read_response=True):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(str(socket_path))
            connection.sendall(_canonical({'envelope_ref': reference}) + b'\n')
            if not read_response:
                return None
            with connection.makefile('rb') as stream:
                return json.loads(stream.readline(65537))

    try:
        preflight = json.loads(_run(str(ROOT / '.venv/bin/python'),
                                    'scripts/pdf_custody_pilot.py', 'preflight'))
        if preflight['status'] != 'ready_to_start':
            raise RuntimeError('pilot_not_free')
        _run(str(ROOT / '.venv/bin/python'), 'scripts/pdf_custody_pilot.py', 'start')
        mongo_started = True
        start_host()
        described = send(store_request('describe_label_capabilities', 'describe'))
        if described['status'] != 'ok':
            raise RuntimeError('describe_failed: ' + repr(described))
        summary['request_persistence'] = described['result']['request_persistence']
        summary['response_persistence'] = described['result']['response_persistence']
        pages = {}
        positive_reference = positive = None
        for number in policy['allowed_pages']:
            reference = store_request('get_label_candidates', 'page-' + str(number),
                                      page_number=number)
            response = send(reference)
            if response['status'] != 'ok':
                raise RuntimeError('page_failed: ' + repr(response))
            coverage = response['result']['coverage']
            pages[str(number)] = {'nodes': len(response['result']['nodes']),
                                  'graph_status': coverage['graph_status'],
                                  'connector_count': coverage['connector_count'],
                                  'edge_count': coverage['edge_count'],
                                  'unresolved_connector_count':
                                      coverage['unresolved_connector_count'],
                                  'missing_native_labels':
                                      coverage['missing_native_labels'],
                                  'missing_ocr_labels': coverage['missing_ocr_labels'],
                                  'response_bytes': len(_canonical(response))}
            if number == 20:
                positive_reference, positive = reference, response
        summary['pages'] = pages
        failures = {}
        for name, changes, code in (
                ('outside', {'page_number': 23}, 'page_out_of_scope'),
                ('manifest', {'manifest_sha256': '0' * 64}, 'manifest_mismatch'),
                ('policy', {'label_policy_sha256': '0' * 64}, 'label_policy_mismatch'),
                ('source', {'source': dict(source, source_sha256='0' * 64)},
                 'source_mismatch')):
            response = send(store_request('get_label_candidates', name, **changes))
            if response['error']['code'] != code:
                raise RuntimeError('negative_failed: ' + repr(response))
            failures[name] = code
        summary['negative_codes'] = failures
        send(positive_reference, read_response=False)
        if send(positive_reference) != positive:
            raise RuntimeError('lost_response_replay_changed')
        summary['lost_response_replay'] = 'same_response'
        stop_host()
        start_host()
        if send(positive_reference) != positive:
            raise RuntimeError('restart_replay_changed')
        summary['restart_replay'] = 'same_response'
        stop_host()
    finally:
        try:
            stop_host()
        finally:
            if mongo_started:
                _run(str(ROOT / '.venv/bin/python'), 'scripts/pdf_custody_pilot.py', 'stop')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        summary['mongo_port_closed'] = connection.connect_ex(('127.0.0.1', 37034)) != 0
    summary['label_socket_absent'] = not socket_path.exists()
    summary['parent_manifest_unchanged'] = (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest() == manifest_before)
    summary['derived_files_unchanged'] = derived_before == {
        str(path.relative_to(derived_root))
        for path in derived_root.rglob('*') if path.is_file()}
    summary['delivery_files_unchanged'] = delivery_before == {
        str(path.relative_to(delivery_root))
        for path in delivery_root.rglob('*') if path.is_file()}
    if not summary['mongo_port_closed'] or not summary['label_socket_absent']:
        raise RuntimeError('pilot_shutdown_unconfirmed')
    if not all(summary[key] for key in ('parent_manifest_unchanged',
                                       'derived_files_unchanged',
                                       'delivery_files_unchanged')):
        raise RuntimeError('pilot_files_changed')
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
