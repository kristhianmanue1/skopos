"""Canal local candidato: el host fija política y Mongo fuera de cada solicitud."""

import argparse
import json
import os
import socket
import socketserver
from pathlib import Path
import stat

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import (HOST_POLICY_SCHEMA, MAX_REQUEST_BYTES,
                               CustodyError, PdfCustodyStore, _load_json,
                               _policy_current, _policy_digest, _read_under,
                               load_policy, read_request)
from skopos.pdf_custody_cli import _response


HOST_SCHEMA = 'skopos/pdf-custody-host/v0.1'
HOST_CONTRACT_VERSION = 'v0.2'
MAX_CALL_BYTES = 4096


def load_host_config(path):
    """Sólo el proceso lanzado por el host elige esta ruta."""
    path = Path(path)
    if not path.is_absolute():
        raise CustodyError('host_config_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise CustodyError('host_config_unavailable')
            raw = source.read(MAX_CALL_BYTES + 1)
    except OSError:
        raise CustodyError('host_config_unavailable') from None
    config = _load_json(raw, MAX_CALL_BYTES)
    required = {'schema', 'policy_path', 'mongo_uri', 'database', 'socket_path'}
    if set(config) != required or config['schema'] != HOST_SCHEMA:
        raise CustodyError('host_config_unavailable')
    for field in ('policy_path', 'socket_path'):
        if not isinstance(config[field], str) or not os.path.isabs(config[field]):
            raise CustodyError('host_config_unavailable')
    for field in ('mongo_uri', 'database'):
        if not isinstance(config[field], str) or not config[field]:
            raise CustodyError('host_config_unavailable')
    if config['mongo_uri'].startswith('mongodb+srv://'):
        raise CustodyError('host_config_unavailable')
    return config


class HostGateway:
    """El payload del agente sólo contiene envelope_ref; configuración fija."""

    def __init__(self, config, client=None):
        self.config = config
        self.policy = load_policy(config['policy_path'])
        if self.policy['schema'] != HOST_POLICY_SCHEMA:
            raise CustodyError('policy_unavailable')
        self.policy_sha256 = _policy_digest(self.policy)
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
                raise CustodyError('invalid_request')
            envelope = _load_json(_read_under(
                self.policy['requests_root'], call['envelope_ref'], MAX_REQUEST_BYTES),
                MAX_REQUEST_BYTES)
            request = read_request(self.policy, envelope,
                                   contract_version=HOST_CONTRACT_VERSION)
            request['_request_sha256'] = envelope['request_sha256']
            current_policy = load_policy(self.config['policy_path'])
            if _policy_digest(current_policy) != self.policy_sha256:
                raise CustodyError('policy_mismatch')
            _policy_current(self.policy)
            operation = request.get('operation')
            if operation == 'describe_capabilities':
                if request.get('project_id') != self.policy['project_id']:
                    raise CustodyError('policy_mismatch')
                result = {'policy': {'id': self.policy['policy_id'],
                                     'version': self.policy['policy_version'],
                                     'custody_modes': ['verified_external_reference'],
                                     'scope': ['single_object'],
                                     'seal_policy': self.policy['seal_policy'],
                                     'retention_basis': self.policy['retention_basis'],
                                     'retention_until': self.policy['retention_until'],
                                     'recovery_requirement': self.policy['recovery_requirement'],
                                     'max_bytes': self.policy['max_bytes']},
                          'operations': ['admit_original', 'fetch_original', 'receipt'],
                          'format_validation': 'pdf_header_only',
                          'binary_custody_profile': HOST_SCHEMA}
            elif operation in ('admit_original', 'fetch_original', 'receipt'):
                store = PdfCustodyStore(self.client[self.config['database']], self.policy)
                result = {'admit_original': store.admit,
                          'fetch_original': store.fetch,
                          'receipt': store.receipt}[operation](request)
            else:
                raise CustodyError('unsupported_operation')
            response = _response(request, 'ok', result=result)
        except CustodyError as error:
            status = ('execution_failed' if error.stage in
                      ('admission', 'retrieval', 'delivery') else 'invalid_input')
            response = _response(request, status,
                                 error={'code': error.code, 'stage': error.stage})
        except (PyMongoError, OSError):
            response = _response(request, 'execution_failed',
                                 error={'code': 'store_unavailable', 'stage': 'execution'})
        response['schema'] = HOST_SCHEMA
        response['producer_version'] = HOST_SCHEMA
        response['adapter_version'] = 'skopos/pdf-binary-reference/v0.1'
        return response


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(2.0)
            raw = self.rfile.readline(MAX_CALL_BYTES + 1)
            call = _load_json(raw, MAX_CALL_BYTES)
            response = self.server.gateway.handle(call)
        except (CustodyError, OSError) as error:
            code = error.code if isinstance(error, CustodyError) else 'invalid_request'
            response = {'schema': HOST_SCHEMA, 'status': 'invalid_input',
                        'error': {'code': code, 'stage': 'validation'},
                        'result': None}
        try:
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode() + b'\n')
        except OSError:
            pass


def host_command(argv=None):
    parser = argparse.ArgumentParser(prog='skopos custody-host')
    sub = parser.add_subparsers(dest='mode', required=True)
    server_parser = sub.add_parser('serve', help='Host: inicia canal con configuración fija.')
    server_parser.add_argument('--config', required=True)
    client_parser = sub.add_parser('request', help='Agente: envía sólo envelope_ref.')
    client_parser.add_argument('--socket', required=True)
    client_parser.add_argument('--envelope-ref', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'request':
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.connect(args.socket)
                connection.sendall(json.dumps({'envelope_ref': args.envelope_ref}).encode() + b'\n')
                with connection.makefile('rb') as stream:
                    raw = stream.readline(MAX_REQUEST_BYTES + 1)
            response = _load_json(raw, MAX_REQUEST_BYTES)
        except (OSError, CustodyError, UnicodeError):
            response = {'schema': HOST_SCHEMA, 'status': 'execution_failed',
                        'error': {'code': 'host_unavailable', 'stage': 'transport'},
                        'result': None}
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response.get('status') == 'ok' else 1
    config = load_host_config(args.config)
    gateway = HostGateway(config)
    try:
        with socketserver.UnixStreamServer(config['socket_path'], _Handler) as server:
            server.gateway = gateway
            os.chmod(config['socket_path'], 0o600)
            try:
                server.serve_forever()
            finally:
                os.unlink(config['socket_path'])
    finally:
        gateway.close()
    return 0
