"""Canal local de derivados PDF con política propia fijada por el host."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat
import sys

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import CustodyError, _identifier, _read_under
from skopos.pdf_document_extract import DocumentExtractionError
from skopos.pdf_document_store import (CONTRACT_ID, CONTRACT_VERSION,
                                       DocumentError, PdfDocumentStore,
                                       _canonical, load_document_policy)
from skopos.pdf_document_policy_v02 import load_document_policy_v02


HOST_SCHEMA = 'skopos/pdf-document-host/v0.1'
HOST_CONFIG_V02 = 'skopos/pdf-document-host-config/v0.2'
MAX_CALL_BYTES = 4096
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 64 * 1024


def _policy_loader(config):
    loader = (load_document_policy_v02 if config['schema'] == HOST_CONFIG_V02
              else load_document_policy)
    if loader is load_document_policy:
        return loader

    def checked(path):
        try:
            return loader(path)
        except (KeyError, TypeError):
            raise DocumentError('policy_unavailable') from None

    return checked


def load_host_config(path):
    path = Path(path)
    if not path.is_absolute():
        raise DocumentError('host_config_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise DocumentError('host_config_unavailable')
            raw = source.read(MAX_CALL_BYTES + 1)
        config = json.loads(raw)
    except (OSError, UnicodeError, ValueError):
        raise DocumentError('host_config_unavailable') from None
    if (len(raw) > MAX_CALL_BYTES or not isinstance(config, dict)
            or set(config) != {'schema', 'policy_path', 'mongo_uri',
                               'database', 'socket_path'}
            or config['schema'] not in (HOST_SCHEMA, HOST_CONFIG_V02)):
        raise DocumentError('host_config_unavailable')
    for field in ('policy_path', 'socket_path'):
        if not isinstance(config[field], str) or not os.path.isabs(config[field]):
            raise DocumentError('host_config_unavailable')
    if (not isinstance(config['mongo_uri'], str)
            or not config['mongo_uri'].startswith('mongodb://127.0.0.1:')
            or not isinstance(config['database'], str) or not config['database']):
        raise DocumentError('host_config_unavailable')
    return config


def _json(raw, maximum):
    if not raw or len(raw) > maximum:
        raise DocumentError('invalid_json')
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DocumentError('invalid_json') from None
    if not isinstance(value, dict):
        raise DocumentError('invalid_json')
    return value


def _read_request(policy, envelope):
    required = {'request_file_ref', 'request_sha256', 'request_id',
                'contract_id', 'contract_version'}
    if not isinstance(envelope, dict) or set(envelope) != required:
        raise DocumentError('invalid_request')
    raw = _read_under(policy['requests_root'], envelope['request_file_ref'],
                      MAX_REQUEST_BYTES)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != envelope['request_sha256']:
        raise DocumentError('request_hash_mismatch')
    request = _json(raw, MAX_REQUEST_BYTES)
    for field in ('request_id', 'contract_id', 'contract_version'):
        if request.get(field) != envelope[field]:
            raise DocumentError('request_mismatch')
    if (request.get('contract_id') != CONTRACT_ID
            or request.get('contract_version') != CONTRACT_VERSION):
        raise DocumentError('unsupported_contract')
    _identifier(request.get('request_id'))
    if not isinstance(request.get('operation'), str):
        raise DocumentError('invalid_request')
    request['_request_sha256'] = actual
    return request


class DocumentGateway:
    def __init__(self, config, client=None):
        self.config = config
        self._load_policy = _policy_loader(config)
        self.policy = self._load_policy(config['policy_path'])
        self.policy_sha256 = hashlib.sha256(_canonical(self.policy)).hexdigest()
        self.client = (client if client is not None else pymongo.MongoClient(
            config['mongo_uri'], serverSelectionTimeoutMS=2000))
        self.owns_client = client is None

    def close(self):
        if self.owns_client:
            self.client.close()

    def handle(self, call):
        request = {}
        try:
            if not isinstance(call, dict) or set(call) != {'envelope_ref'}:
                raise DocumentError('invalid_request')
            envelope = _json(_read_under(self.policy['requests_root'],
                                         call['envelope_ref'], MAX_REQUEST_BYTES),
                             MAX_REQUEST_BYTES)
            request = _read_request(self.policy, envelope)
            current = self._load_policy(self.config['policy_path'])
            if hashlib.sha256(_canonical(current)).hexdigest() != self.policy_sha256:
                raise DocumentError('policy_mismatch')
            if request.get('project_id') != self.policy['project_id']:
                raise DocumentError('project_mismatch')
            operation = request.get('operation')
            store = PdfDocumentStore(self.client[self.config['database']], self.policy)
            if operation == 'describe_document_capabilities':
                store._source({
                    'material_id': self.policy['material_id'],
                    'source_revision': self.policy['source_revision'],
                    'source_sha256': self.policy['source_sha256'],
                    'custody_receipt_id': self.policy['custody_receipt_id'],
                    'custody_policy_sha256': self.policy['custody_policy_sha256'],
                })
                result = {
                    'policy': {'id': self.policy['policy_id'],
                               'version': self.policy['policy_version'],
                               'policy_sha256': self.policy_sha256,
                               'retention_until': self.policy['retention_until']},
                    'capabilities': {'native_text': 'partial',
                                     'selective_ocr': 'partial',
                                     'visual_graph': 'partial',
                                     'text_search': 'partial'},
                    'engine': {'platform': sys.platform,
                               'native': 'macos/PDFKit',
                               'ocr': 'macos/Vision/es-ES',
                               'renderer': 'poppler/pdftoppm'},
                    'limits': {'max_pages': self.policy['max_pages'],
                               'max_ocr_pages': self.policy['max_ocr_pages'],
                               'max_render_pixels': self.policy['max_render_pixels'],
                               'max_seconds': self.policy['max_seconds'],
                               'max_output_bytes': self.policy['max_output_bytes']},
                }
            elif operation == 'derive_document':
                result = store.derive(request)
            elif operation == 'derivation_receipt':
                result = store.derivation_receipt(request)
            elif operation == 'fetch_derivative':
                result = store.fetch(request)
            elif operation == 'fetch_evidence':
                result = store.evidence(request)
            elif operation == 'search_document':
                result = store.search(request)
            else:
                raise DocumentError('unsupported_operation')
            response = {'status': 'ok', 'result': result, 'error': None}
        except (DocumentError, DocumentExtractionError, CustodyError) as error:
            code = error.code
            stage = getattr(error, 'stage', 'derivation')
            response = {'status': 'execution_failed' if stage != 'validation' else
                        'invalid_input', 'result': None,
                        'error': {'code': code, 'stage': stage}}
        except (PyMongoError, OSError):
            response = {'status': 'execution_failed', 'result': None,
                        'error': {'code': 'store_unavailable', 'stage': 'execution'}}
        except (KeyError, TypeError, AttributeError):
            response = {'status': 'invalid_input', 'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        response.update({'schema': HOST_SCHEMA, 'contract_id': CONTRACT_ID,
                         'contract_version': CONTRACT_VERSION,
                         'request_id': request.get('request_id'),
                         'request_sha256': request.get('_request_sha256')})
        return response


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(2.0)
            call = _json(self.rfile.readline(MAX_CALL_BYTES + 1), MAX_CALL_BYTES)
            response = self.server.gateway.handle(call)
        except (DocumentError, OSError) as error:
            response = {'schema': HOST_SCHEMA, 'status': 'invalid_input',
                        'error': {'code': error.code if isinstance(error, DocumentError)
                                  else 'invalid_request', 'stage': 'validation'},
                        'result': None}
        raw = _canonical(response) + b'\n'
        if len(raw) > MAX_RESPONSE_BYTES:
            raw = _canonical({'schema': HOST_SCHEMA, 'status': 'execution_failed',
                              'error': {'code': 'response_limit_exceeded',
                                        'stage': 'execution'}, 'result': None}) + b'\n'
        try:
            self.wfile.write(raw)
        except OSError:
            pass


def document_host_command(argv=None):
    parser = argparse.ArgumentParser(prog='skopos document-host')
    sub = parser.add_subparsers(dest='mode', required=True)
    server_parser = sub.add_parser('serve')
    server_parser.add_argument('--config', required=True)
    client_parser = sub.add_parser('request')
    client_parser.add_argument('--socket', required=True)
    client_parser.add_argument('--envelope-ref', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'request':
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(130)
                connection.connect(args.socket)
                connection.sendall(_canonical({'envelope_ref': args.envelope_ref}) + b'\n')
                with connection.makefile('rb') as stream:
                    response = _json(stream.readline(MAX_RESPONSE_BYTES + 1),
                                     MAX_RESPONSE_BYTES)
        except (OSError, DocumentError):
            response = {'schema': HOST_SCHEMA, 'status': 'execution_failed',
                        'error': {'code': 'host_unavailable', 'stage': 'transport'},
                        'result': None}
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response.get('status') == 'ok' else 1
    config = load_host_config(args.config)
    gateway = DocumentGateway(config)
    try:
        with socketserver.UnixStreamServer(config['socket_path'], _Handler) as server:
            server.gateway = gateway
            os.chmod(config['socket_path'], 0o600)
            socket_details = os.lstat(config['socket_path'])
            previous_handler = signal.getsignal(signal.SIGTERM)

            def terminate(_number, _frame):
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, terminate)
            try:
                server.serve_forever()
            finally:
                signal.signal(signal.SIGTERM, previous_handler)
                try:
                    current = os.lstat(config['socket_path'])
                    if (stat.S_ISSOCK(current.st_mode)
                            and (current.st_dev, current.st_ino) ==
                            (socket_details.st_dev, socket_details.st_ino)):
                        os.unlink(config['socket_path'])
                except FileNotFoundError:
                    pass
    finally:
        gateway.close()
    return 0
