"""Consulta local y acotada de candidatos de rótulo sin persistir respuestas."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import CustodyError, _digest, _identifier, _read_under
from skopos.pdf_document_host import load_host_config as load_document_host_config
from skopos.pdf_document_store import (DocumentError, PdfDocumentStore, _canonical,
                                       _file_sha256,
                                       load_document_policy)
from skopos.pdf_label_evaluation import project_labels


HOST_SCHEMA = 'skopos/pdf-label-host/v0.2-experimental'
POLICY_SCHEMA = 'skopos/pdf-label-policy/v0.2-experimental'
CONTRACT_ID = 'expertogobernanza/skopos-label-candidates'
CONTRACT_VERSION = 'v0.2-experimental'
MAX_CONFIG_BYTES = 4096
MAX_POLICY_BYTES = 4096
MAX_CALL_BYTES = 4096
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
LABEL_HOST_SCRIPT = Path(__file__).resolve()
LABEL_PROJECTION_SCRIPT = LABEL_HOST_SCRIPT.with_name('pdf_label_evaluation.py')


def _private_json(path, maximum, error_code):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise DocumentError(error_code)
            raw = source.read(maximum + 1)
        if len(raw) > maximum:
            raise DocumentError(error_code)
        value = json.loads(raw)
    except (OSError, UnicodeError, ValueError):
        raise DocumentError(error_code) from None
    if not isinstance(value, dict):
        raise DocumentError(error_code)
    return value


def load_label_config(path):
    if not isinstance(path, (str, Path)) or not os.path.isabs(path):
        raise DocumentError('label_config_unavailable')
    config = _private_json(path, MAX_CONFIG_BYTES, 'label_config_unavailable')
    if (set(config) != {'schema', 'document_host_config_path',
                        'label_policy_path', 'label_policy_sha256', 'socket_path'}
            or config['schema'] != HOST_SCHEMA
            or any(not isinstance(config[key], str) or not os.path.isabs(config[key])
                   for key in ('document_host_config_path', 'label_policy_path',
                               'socket_path'))):
        raise DocumentError('label_config_unavailable')
    _digest(config['label_policy_sha256'])
    return config


def load_label_policy(config, document_policy):
    policy = _private_json(config['label_policy_path'], MAX_POLICY_BYTES,
                           'label_policy_unavailable')
    required = {'schema', 'policy_id', 'policy_version', 'project_id',
                'document_policy_sha256', 'source_sha256', 'derivation_id',
                'manifest_sha256', 'allowed_pages', 'max_pages_per_request',
                'max_nodes_per_response', 'retention_until', 'request_retention_action',
                'requests_root', 'allow_network', 'response_persistence',
                'label_host_sha256', 'label_projection_sha256'}
    if (set(policy) != required or policy['schema'] != POLICY_SCHEMA
            or policy['project_id'] != document_policy['project_id']
            or policy['source_sha256'] != document_policy['source_sha256']
            or policy['document_policy_sha256'] !=
                hashlib.sha256(_canonical(document_policy)).hexdigest()
            or policy['allowed_pages'] != [18, 19, 20, 21, 22]
            or policy['max_pages_per_request'] != 1
            or policy['max_nodes_per_response'] != 40
            or policy['requests_root'] != document_policy['requests_root']
            or policy['request_retention_action'] !=
                document_policy['retention_action']
            or policy['allow_network'] is not False
            or policy['response_persistence'] is not False):
        raise DocumentError('label_policy_unavailable')
    for field in ('derivation_id', 'manifest_sha256', 'label_host_sha256',
                  'label_projection_sha256'):
        _digest(policy[field])
    if (_file_sha256(LABEL_HOST_SCRIPT) != policy['label_host_sha256']
            or _file_sha256(LABEL_PROJECTION_SCRIPT) !=
                policy['label_projection_sha256']):
        raise DocumentError('label_engine_mismatch')
    for field in ('policy_id', 'policy_version'):
        if not isinstance(policy[field], str) or not policy[field]:
            raise DocumentError('label_policy_unavailable')
    try:
        expires = datetime.fromisoformat(policy['retention_until'].replace('Z', '+00:00'))
        parent_expires = datetime.fromisoformat(
            document_policy['retention_until'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise DocumentError('retention_policy_missing') from None
    if (expires.tzinfo is None or expires <= datetime.now(timezone.utc)
            or expires > parent_expires):
        raise DocumentError('retention_policy_missing')
    actual = hashlib.sha256(_canonical(policy)).hexdigest()
    if actual != config['label_policy_sha256']:
        raise DocumentError('label_policy_mismatch')
    return policy


def _request(policy, call):
    if not isinstance(call, dict) or set(call) != {'envelope_ref'}:
        raise DocumentError('invalid_request')
    envelope = _private_json_under(policy['requests_root'], call['envelope_ref'])
    if set(envelope) != {'request_file_ref', 'request_sha256', 'request_id',
                         'contract_id', 'contract_version'}:
        raise DocumentError('invalid_request')
    raw = _read_under(policy['requests_root'], envelope['request_file_ref'],
                      MAX_REQUEST_BYTES)
    if hashlib.sha256(raw).hexdigest() != _digest(envelope['request_sha256']):
        raise DocumentError('request_hash_mismatch')
    try:
        request = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DocumentError('invalid_request') from None
    if not isinstance(request, dict):
        raise DocumentError('invalid_request')
    for field in ('request_id', 'contract_id', 'contract_version'):
        if request.get(field) != envelope[field]:
            raise DocumentError('request_mismatch')
    if (request.get('contract_id') != CONTRACT_ID
            or request.get('contract_version') != CONTRACT_VERSION):
        raise DocumentError('unsupported_contract')
    _identifier(request.get('request_id'))
    request['_request_sha256'] = envelope['request_sha256']
    return request


def _private_json_under(root, reference):
    raw = _read_under(root, reference, MAX_REQUEST_BYTES)
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DocumentError('invalid_request') from None
    if not isinstance(value, dict):
        raise DocumentError('invalid_request')
    return value


class LabelGateway:
    def __init__(self, config, client=None):
        self.config = config
        self.document_config = load_document_host_config(config['document_host_config_path'])
        self.document_policy = load_document_policy(self.document_config['policy_path'])
        pilot_root = Path(self.document_config['socket_path']).parent
        if (Path(config['socket_path']) != pilot_root / 'label.sock'
                or Path(config['label_policy_path']) != pilot_root / 'label-policy.json'
                or Path(self.document_policy['derived_root']).parent != pilot_root):
            raise DocumentError('label_config_unavailable')
        self.policy = load_label_policy(config, self.document_policy)
        self.client = client if client is not None else pymongo.MongoClient(
            self.document_config['mongo_uri'], serverSelectionTimeoutMS=2000)
        self.owns_client = client is None

    def close(self):
        if self.owns_client:
            self.client.close()

    def handle(self, call):
        request = {}
        try:
            current_document = load_document_policy(self.document_config['policy_path'])
            if current_document != self.document_policy:
                raise DocumentError('document_policy_mismatch')
            if load_label_policy(self.config, current_document) != self.policy:
                raise DocumentError('label_policy_mismatch')
            request = _request(self.policy, call)
            if request.get('project_id') != self.policy['project_id']:
                raise DocumentError('project_mismatch')
            store = PdfDocumentStore(self.client[self.document_config['database']],
                                     self.document_policy)
            source = request.get('source')
            if request.get('operation') == 'describe_label_capabilities':
                if set(request) != {'request_id', 'contract_id', 'contract_version',
                                    'project_id', 'operation', 'source',
                                    'label_policy_sha256', '_request_sha256'}:
                    raise DocumentError('invalid_request')
                if request['label_policy_sha256'] != self.config['label_policy_sha256']:
                    raise DocumentError('label_policy_mismatch')
                store._source(source)
                result = {'allowed_pages': self.policy['allowed_pages'],
                          'max_pages_per_request': self.policy['max_pages_per_request'],
                          'max_nodes_per_response': self.policy['max_nodes_per_response'],
                          'label_policy_sha256': self.config['label_policy_sha256'],
                          'document_policy_sha256':
                              self.policy['document_policy_sha256'],
                          'request_retention_until': self.policy['retention_until'],
                          'request_retention_action':
                              self.policy['request_retention_action'],
                          'request_persistence': 'existing_requests_root',
                          'response_persistence': 'none_by_label_host',
                          'fidelity_status': 'unreviewed'}
            elif request.get('operation') == 'get_label_candidates':
                result = self._candidates(store, request)
            else:
                raise DocumentError('unsupported_operation')
            response = {'status': 'ok', 'result': result, 'error': None}
        except (DocumentError, CustodyError) as error:
            code = error.code
            stage = getattr(error, 'stage', 'validation')
            response = {'status': 'invalid_input' if stage == 'validation'
                        else 'execution_failed', 'result': None,
                        'error': {'code': code, 'stage': stage}}
        except (PyMongoError, OSError):
            response = {'status': 'execution_failed', 'result': None,
                        'error': {'code': 'store_unavailable', 'stage': 'execution'}}
        except (KeyError, TypeError, AttributeError, ValueError):
            response = {'status': 'invalid_input', 'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        response.update({'schema': HOST_SCHEMA, 'contract_id': CONTRACT_ID,
                         'contract_version': CONTRACT_VERSION,
                         'request_id': request.get('request_id'),
                         'request_sha256': request.get('_request_sha256')})
        return response

    def _candidates(self, store, request):
        required = {'request_id', 'contract_id', 'contract_version', 'project_id',
                    'operation', 'source', 'label_policy_sha256', 'derivation_id',
                    'manifest_sha256', 'page_number', 'max_nodes', '_request_sha256'}
        if set(request) != required:
            raise DocumentError('invalid_request')
        if request['label_policy_sha256'] != self.config['label_policy_sha256']:
            raise DocumentError('label_policy_mismatch')
        number = request['page_number']
        if type(number) is not int or number not in self.policy['allowed_pages']:
            raise DocumentError('page_out_of_scope')
        maximum = request['max_nodes']
        if type(maximum) is not int or not 1 <= maximum <= self.policy['max_nodes_per_response']:
            raise DocumentError('limit_exceeded')
        if _digest(request['derivation_id']) != self.policy['derivation_id']:
            raise DocumentError('derivation_mismatch')
        if _digest(request['manifest_sha256']) != self.policy['manifest_sha256']:
            raise DocumentError('manifest_mismatch')
        store._source(request['source'])
        manifest, raw = store._manifest(self.policy['derivation_id'])
        if hashlib.sha256(raw).hexdigest() != self.policy['manifest_sha256']:
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        page = next((item for item in manifest['pages']
                     if item['page_number'] == number), None)
        if page is None:
            raise DocumentError('page_unavailable', 'retrieval')
        render = page.get('render')
        if not isinstance(render, dict):
            raise DocumentError('render_unavailable', 'retrieval')
        render_bytes = _read_under(
            store.policy['derived_root'],
            self.policy['derivation_id'] + '/' + render['file_ref'],
            store.policy['max_output_bytes'], stage='retrieval')
        if hashlib.sha256(render_bytes).hexdigest() != render['sha256']:
            raise DocumentError('render_integrity_failed', 'retrieval')
        projected = project_labels(manifest, raw)
        selected = next(item for item in projected['pages']
                        if item['page_number'] == number)
        if len(selected['nodes']) > maximum:
            raise DocumentError('limit_exceeded')
        return {'derivation_id': self.policy['derivation_id'],
                'manifest_sha256': self.policy['manifest_sha256'],
                'label_policy_sha256': self.config['label_policy_sha256'],
                'source_sha256': self.policy['source_sha256'],
                'page_number': number, 'render_sha256': selected['render_sha256'],
                'nodes': selected['nodes'], 'edges': selected['edges'],
                'unresolved_connectors': page['visual_graph']['unknown'],
                'coverage': {'graph_status': page['visual_graph']['status'],
                             'topology_completeness': 'unreviewed_partial',
                             'connector_count': len(page['visual_graph']['connectors']),
                             'edge_count': len(selected['edges']),
                             'unresolved_connector_count':
                                 len(page['visual_graph']['unknown']),
                             'native_text_status': page['native_text']['status'],
                             'ocr_text_status': page['ocr_text']['status'],
                             'node_count': len(selected['nodes']),
                             'missing_native_labels': sum(not node['label_candidates'][0]['text']
                                                          for node in selected['nodes']),
                             'missing_ocr_labels': sum(not node['label_candidates'][1]['text']
                                                       for node in selected['nodes'])},
                'fidelity_status': 'unreviewed'}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(2.0)
            raw = self.rfile.readline(MAX_CALL_BYTES + 1)
            if len(raw) > MAX_CALL_BYTES:
                raise ValueError('call_too_large')
            call = json.loads(raw)
            response = self.server.gateway.handle(call)
        except (OSError, UnicodeError, ValueError):
            response = {'schema': HOST_SCHEMA, 'status': 'invalid_input',
                        'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        raw = _canonical(response) + b'\n'
        if len(raw) > MAX_RESPONSE_BYTES:
            raw = _canonical({'schema': HOST_SCHEMA, 'status': 'execution_failed',
                              'result': None,
                              'contract_id': CONTRACT_ID,
                              'contract_version': CONTRACT_VERSION,
                              'request_id': response.get('request_id'),
                              'request_sha256': response.get('request_sha256'),
                              'error': {'code': 'response_limit_exceeded',
                                        'stage': 'execution'}}) + b'\n'
        try:
            self.wfile.write(raw)
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog='skopos.pdf_label_host')
    sub = parser.add_subparsers(dest='mode', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--config', required=True)
    request = sub.add_parser('request')
    request.add_argument('--socket', required=True)
    request.add_argument('--envelope-ref', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'request':
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(5)
                connection.connect(args.socket)
                connection.sendall(_canonical({'envelope_ref': args.envelope_ref}) + b'\n')
                response = json.loads(connection.makefile('rb').readline(MAX_RESPONSE_BYTES + 1))
        except (OSError, UnicodeError, ValueError):
            response = {'schema': HOST_SCHEMA, 'status': 'execution_failed',
                        'error': {'code': 'host_unavailable', 'stage': 'transport'},
                        'result': None}
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response.get('status') == 'ok' else 1
    config = load_label_config(args.config)
    gateway = LabelGateway(config)
    bound_identity = None
    try:
        with socketserver.UnixStreamServer(config['socket_path'], _Handler) as server:
            details = os.lstat(config['socket_path'])
            bound_identity = (details.st_dev, details.st_ino)
            server.gateway = gateway
            os.chmod(config['socket_path'], 0o600)
            previous = signal.getsignal(signal.SIGTERM)

            def terminate(_number, _frame):
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, terminate)
            try:
                server.serve_forever(poll_interval=0.1)
            finally:
                signal.signal(signal.SIGTERM, previous)
    finally:
        gateway.close()
        try:
            details = os.lstat(config['socket_path'])
            if bound_identity == (details.st_dev, details.st_ino):
                os.unlink(config['socket_path'])
        except FileNotFoundError:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
