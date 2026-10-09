"""Host local de candidatos visuales versionados, sin adjudicar organigramas."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socketserver
import stat

from pymongo.errors import PyMongoError

from skopos.pdf_custody import CustodyError, _digest, _identifier, _read_under
from skopos.pdf_document_store import (DocumentError, PdfDocumentStore, _canonical,
                                       _file_sha256, load_document_policy)
from skopos.pdf_graph_review import build_manifest
from skopos.pdf_label_host import (LabelGateway, load_label_config,
                                   load_label_policy)


SCHEMA = 'skopos/pdf-graph-review-host/v0.3-experimental'
CONTRACT_ID = 'expertogobernanza/skopos-graph-review'
CONTRACT_VERSION = 'v0.3-experimental'
ROOT = Path(__file__).resolve().parents[2]
HOST_SCRIPT = Path(__file__).resolve()
BUILDER_SCRIPT = HOST_SCRIPT.with_name('pdf_graph_review.py')
REVIEW_PATH = ROOT / 'docs/evidencia/pdf-imss-visual-self-review-2026-10-08.json'
MANIFEST_PATH = ROOT / 'docs/evidencia/pdf-imss-graph-review-v0.3-experimental.json'
MAX_REQUEST = 64 * 1024
MAX_RESPONSE = 64 * 1024


def _private_json(path, maximum, code):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise DocumentError(code)
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise DocumentError(code)
        value = json.loads(raw)
    except (OSError, ValueError, UnicodeError):
        raise DocumentError(code) from None
    if not isinstance(value, dict):
        raise DocumentError(code)
    return value, raw


def load_config(path):
    if not isinstance(path, str) or not os.path.isabs(path):
        raise DocumentError('graph_config_unavailable')
    config, _ = _private_json(path, 4096, 'graph_config_unavailable')
    required = {'schema', 'label_host_config_path', 'manifest_path',
                'manifest_sha256', 'review_sha256', 'builder_sha256',
                'host_sha256', 'socket_path'}
    if set(config) != required or config['schema'] != SCHEMA:
        raise DocumentError('graph_config_unavailable')
    if any(not isinstance(config[field], str) or not os.path.isabs(config[field])
           for field in ('label_host_config_path', 'manifest_path', 'socket_path')):
        raise DocumentError('graph_config_unavailable')
    for field in ('manifest_sha256', 'review_sha256', 'builder_sha256', 'host_sha256'):
        _digest(config[field])
    label_config = load_label_config(config['label_host_config_path'])
    pilot = Path(label_config['socket_path']).parent
    if (Path(path) != pilot / 'graph-review-host.json'
            or Path(config['socket_path']) != pilot / 'graph-review.sock'
            or Path(config['manifest_path']) != MANIFEST_PATH
            or Path(config['label_host_config_path']) != pilot / 'label-host.json'
            or _file_sha256(HOST_SCRIPT) != config['host_sha256']
            or _file_sha256(BUILDER_SCRIPT) != config['builder_sha256']):
        raise DocumentError('graph_config_unavailable')
    return config


def _read_request(root, call):
    if not isinstance(call, dict) or set(call) != {'envelope_ref'}:
        raise DocumentError('invalid_request')
    try:
        envelope = json.loads(_read_under(root, call['envelope_ref'], MAX_REQUEST))
        if set(envelope) != {'request_file_ref', 'request_sha256', 'request_id',
                             'contract_id', 'contract_version'}:
            raise DocumentError('invalid_request')
        raw = _read_under(root, envelope['request_file_ref'], MAX_REQUEST)
        if hashlib.sha256(raw).hexdigest() != _digest(envelope['request_sha256']):
            raise DocumentError('request_hash_mismatch')
        request = json.loads(raw)
    except (DocumentError, CustodyError):
        raise
    except (UnicodeError, ValueError, TypeError):
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


class GraphReviewGateway:
    def __init__(self, config):
        self.config = config
        self.config_sha256 = hashlib.sha256(_canonical(config)).hexdigest()
        self.label = LabelGateway(load_label_config(config['label_host_config_path']))
        self.document_policy = self.label.document_policy
        self.label_policy = self.label.policy
        self._load_manifest()

    def close(self):
        self.label.close()

    def _load_manifest(self):
        review, review_raw = _private_json(REVIEW_PATH, 256 * 1024,
                                            'review_unavailable')
        graph, graph_raw = _private_json(MANIFEST_PATH, 256 * 1024,
                                         'graph_manifest_unavailable')
        if (hashlib.sha256(review_raw).hexdigest() != self.config['review_sha256']
                or hashlib.sha256(graph_raw).hexdigest() !=
                self.config['manifest_sha256']):
            raise DocumentError('graph_integrity_failed', 'retrieval')
        store = PdfDocumentStore(
            self.label.client[self.label.document_config['database']],
            self.document_policy)
        parent, parent_raw = store._manifest(self.label_policy['derivation_id'])
        if hashlib.sha256(parent_raw).hexdigest() != self.label_policy['manifest_sha256']:
            raise DocumentError('parent_integrity_failed', 'retrieval')
        try:
            expected = build_manifest(parent, self.label_policy['manifest_sha256'],
                                      review, self.config['review_sha256'])
        except (ValueError, KeyError, TypeError):
            raise DocumentError('graph_projection_mismatch', 'retrieval') from None
        if graph != expected:
            raise DocumentError('graph_projection_mismatch', 'retrieval')
        self.manifest = graph

    def handle(self, call):
        request = {}
        try:
            if load_config(str(Path(self.config['socket_path']).with_name(
                    'graph-review-host.json'))) != self.config:
                raise DocumentError('graph_config_changed')
            current = load_document_policy(self.label.document_config['policy_path'])
            if current != self.document_policy:
                raise DocumentError('document_policy_mismatch')
            if load_label_policy(self.label.config, current) != self.label_policy:
                raise DocumentError('label_policy_mismatch')
            request = _read_request(self.label_policy['requests_root'], call)
            if request.get('project_id') != 'expertogobernanza':
                raise DocumentError('project_mismatch')
            if request.get('graph_config_sha256') != self.config_sha256:
                raise DocumentError('graph_config_mismatch')
            self._load_manifest()
            store = PdfDocumentStore(self.label.client[
                self.label.document_config['database']], self.document_policy)
            store._source(request.get('source'))
            operation = request.get('operation')
            if operation == 'describe_graph_review':
                if set(request) != {'request_id', 'contract_id', 'contract_version',
                                    'project_id', 'operation', 'source',
                                    'graph_config_sha256', '_request_sha256'}:
                    raise DocumentError('invalid_request')
                result = {'derivation_id': self.manifest['derivation_id'],
                          'manifest_sha256': self.config['manifest_sha256'],
                          'parent_derivation_id': self.manifest['parent_derivation_id'],
                          'parent_manifest_sha256': self.manifest['parent_manifest_sha256'],
                          'source': self.manifest['source'],
                          'allowed_pages': [18, 19, 20, 21, 22],
                          'retention_until': self.label_policy['retention_until'],
                          'request_persistence': 'existing_requests_root',
                          'response_persistence': 'none',
                          'fidelity_status': 'unreviewed_partial'}
            elif operation in ('get_graph_review_page', 'fetch_graph_review_item'):
                result = self._retrieve(store, request, operation)
            else:
                raise DocumentError('unsupported_operation')
            response = {'status': 'ok', 'result': result, 'error': None}
        except (DocumentError, CustodyError) as error:
            stage = getattr(error, 'stage', 'validation')
            response = {'status': 'invalid_input' if stage == 'validation' else
                        'execution_failed', 'result': None,
                        'error': {'code': error.code, 'stage': stage}}
        except (PyMongoError, OSError):
            response = {'status': 'execution_failed', 'result': None,
                        'error': {'code': 'store_unavailable', 'stage': 'execution'}}
        except (KeyError, TypeError, AttributeError, ValueError):
            response = {'status': 'invalid_input', 'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        response.update({'schema': SCHEMA, 'contract_id': CONTRACT_ID,
                         'contract_version': CONTRACT_VERSION,
                         'request_id': request.get('request_id'),
                         'request_sha256': request.get('_request_sha256')})
        return response

    def _retrieve(self, store, request, operation):
        common = {'request_id', 'contract_id', 'contract_version', 'project_id',
                  'operation', 'source', 'graph_config_sha256', 'derivation_id',
                  'manifest_sha256', '_request_sha256'}
        additional = {'page_number'} if operation == 'get_graph_review_page' else {'item_id'}
        if set(request) != common | additional:
            raise DocumentError('invalid_request')
        if (request['derivation_id'] != self.manifest['derivation_id']
                or request['manifest_sha256'] != self.config['manifest_sha256']):
            raise DocumentError('graph_identity_mismatch')
        if operation == 'get_graph_review_page':
            number = request['page_number']
            if type(number) is not int or number not in (18, 19, 20, 21, 22):
                raise DocumentError('page_out_of_scope')
            page = next(item for item in self.manifest['pages']
                        if item['page_number'] == number)
            self._render(store, page)
            return {'page': page, 'source': self.manifest['source'],
                    'derivation_id': self.manifest['derivation_id'],
                    'manifest_sha256': self.config['manifest_sha256'],
                    'fidelity_status': 'unreviewed_partial'}
        item_id = _digest(request['item_id'])
        for page in self.manifest['pages']:
            for modality, items in (('visual_graph_node', page['nodes']),
                                    ('visual_graph_edge', page['edges'])):
                for item in items:
                    if item['item_id'] == item_id:
                        self._render(store, page)
                        return {'item': item, 'modality': modality,
                                'page_number': page['page_number'],
                                'render_sha256': page['render_sha256'],
                                'source': self.manifest['source'],
                                'derivation_id': self.manifest['derivation_id'],
                                'manifest_sha256': self.config['manifest_sha256'],
                                'fidelity_status': 'unreviewed_partial'}
        raise DocumentError('evidence_unavailable', 'retrieval')

    def _render(self, store, page):
        parent, _ = store._manifest(self.label_policy['derivation_id'])
        original = next(item for item in parent['pages']
                        if item['page_number'] == page['page_number'])
        render = original['render']
        raw = _read_under(store.policy['derived_root'],
                          self.label_policy['derivation_id'] + '/' + render['file_ref'],
                          store.policy['max_output_bytes'], stage='retrieval')
        if (hashlib.sha256(raw).hexdigest() != render['sha256']
                or render['sha256'] != page['render_sha256']):
            raise DocumentError('render_integrity_failed', 'retrieval')


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(2)
            raw = self.rfile.readline(4097)
            if len(raw) > 4096:
                raise ValueError('call_too_large')
            response = self.server.gateway.handle(json.loads(raw))
        except (OSError, ValueError, UnicodeError):
            response = {'schema': SCHEMA, 'status': 'invalid_input', 'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        raw = _canonical(response) + b'\n'
        if len(raw) > MAX_RESPONSE:
            raw = _canonical({'schema': SCHEMA, 'status': 'execution_failed',
                              'contract_id': CONTRACT_ID,
                              'contract_version': CONTRACT_VERSION,
                              'request_id': response.get('request_id'),
                              'request_sha256': response.get('request_sha256'),
                              'result': None,
                              'error': {'code': 'response_limit_exceeded',
                                        'stage': 'execution'}}) + b'\n'
        try:
            self.wfile.write(raw)
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('serve', choices=['serve'])
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    gateway = GraphReviewGateway(config)
    bound = None
    try:
        with socketserver.UnixStreamServer(config['socket_path'], _Handler) as server:
            details = os.lstat(config['socket_path'])
            bound = (details.st_dev, details.st_ino)
            server.gateway = gateway
            os.chmod(config['socket_path'], 0o600)
            previous = signal.getsignal(signal.SIGTERM)

            def stop(_number, _frame):
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, stop)
            try:
                server.serve_forever(poll_interval=0.1)
            finally:
                signal.signal(signal.SIGTERM, previous)
    finally:
        gateway.close()
        try:
            details = os.lstat(config['socket_path'])
            if bound == (details.st_dev, details.st_ino):
                os.unlink(config['socket_path'])
        except FileNotFoundError:
            pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
