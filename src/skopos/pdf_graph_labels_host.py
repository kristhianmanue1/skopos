"""Host local de rótulos candidatos, ligado al grafo v0.3."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socketserver

from pymongo.errors import PyMongoError

from skopos.pdf_custody import CustodyError, _digest, _identifier, _read_under
from skopos.pdf_document_store import DocumentError, PdfDocumentStore, _canonical, _file_sha256, load_document_policy
from skopos.pdf_graph_labels import build_manifest
from skopos.pdf_graph_review_host import GraphReviewGateway, load_config as load_graph_config, _private_json
from skopos.pdf_label_host import load_label_policy


SCHEMA = 'skopos/pdf-graph-labels-host/v0.4-experimental'
CONTRACT_ID = 'expertogobernanza/skopos-graph-labels'
CONTRACT_VERSION = 'v0.4-experimental'
ROOT = Path(__file__).resolve().parents[2]
HOST = Path(__file__).resolve()
BUILDER = HOST.with_name('pdf_graph_labels.py')
ANNOTATIONS = ROOT / 'docs/evidencia/pdf-imss-graph-label-annotations-v0.4-experimental.json'
MANIFEST = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.4-experimental.json'
MAX_REQUEST = 64 * 1024
MAX_RESPONSE = 64 * 1024


def load_config(path):
    if not isinstance(path, str) or not os.path.isabs(path):
        raise DocumentError('labels_config_unavailable')
    config, _ = _private_json(path, 4096, 'labels_config_unavailable')
    fields = {'schema', 'graph_config_path', 'annotation_sha256', 'manifest_sha256',
              'builder_sha256', 'host_sha256', 'socket_path'}
    if set(config) != fields or config['schema'] != SCHEMA:
        raise DocumentError('labels_config_unavailable')
    for field in ('annotation_sha256', 'manifest_sha256', 'builder_sha256', 'host_sha256'):
        _digest(config[field])
    graph = load_graph_config(config['graph_config_path'])
    pilot = Path(graph['socket_path']).parent
    if (Path(path) != pilot / 'graph-labels-host.json'
            or config['graph_config_path'] != str(pilot / 'graph-review-host.json')
            or config['socket_path'] != str(pilot / 'graph-labels.sock')
            or _file_sha256(HOST) != config['host_sha256']
            or _file_sha256(BUILDER) != config['builder_sha256']):
        raise DocumentError('labels_config_unavailable')
    return config


def read_request(root, call):
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


class GraphLabelsGateway:
    def __init__(self, config):
        self.config = config
        self.config_sha256 = hashlib.sha256(_canonical(config)).hexdigest()
        self.graph = GraphReviewGateway(load_graph_config(config['graph_config_path']))
        self._load_manifest()

    def close(self):
        self.graph.close()

    def _load_manifest(self):
        self.graph._load_manifest()
        annotations, annotation_raw = _private_json(ANNOTATIONS, 256 * 1024,
                                                       'annotations_unavailable')
        manifest, manifest_raw = _private_json(MANIFEST, 256 * 1024,
                                                 'labels_manifest_unavailable')
        if (hashlib.sha256(annotation_raw).hexdigest() != self.config['annotation_sha256']
                or hashlib.sha256(manifest_raw).hexdigest() != self.config['manifest_sha256']):
            raise DocumentError('labels_integrity_failed', 'retrieval')
        try:
            expected = build_manifest(self.graph.manifest,
                                      self.graph.config['manifest_sha256'], annotations)
        except (ValueError, TypeError, KeyError):
            raise DocumentError('labels_projection_mismatch', 'retrieval') from None
        if manifest != expected:
            raise DocumentError('labels_projection_mismatch', 'retrieval')
        self.manifest = manifest

    def handle(self, call):
        request = {}
        try:
            if load_config(self.config['socket_path'].replace('graph-labels.sock',
                                                               'graph-labels-host.json')) != self.config:
                raise DocumentError('labels_config_changed')
            current = load_document_policy(self.graph.label.document_config['policy_path'])
            if current != self.graph.document_policy:
                raise DocumentError('document_policy_mismatch')
            if load_label_policy(self.graph.label.config, current) != self.graph.label_policy:
                raise DocumentError('label_policy_mismatch')
            request = read_request(self.graph.label_policy['requests_root'], call)
            if request.get('project_id') != 'expertogobernanza':
                raise DocumentError('project_mismatch')
            if request.get('labels_config_sha256') != self.config_sha256:
                raise DocumentError('labels_config_mismatch')
            self._load_manifest()
            store = PdfDocumentStore(self.graph.label.client[
                self.graph.label.document_config['database']], self.graph.document_policy)
            store._source(request.get('source'))
            operation = request.get('operation')
            basic = {'request_id', 'contract_id', 'contract_version', 'project_id',
                     'operation', 'source', 'labels_config_sha256', '_request_sha256'}
            if operation == 'describe_graph_labels':
                if set(request) != basic:
                    raise DocumentError('invalid_request')
                result = {'derivation_id': self.manifest['derivation_id'],
                          'manifest_sha256': self.config['manifest_sha256'],
                          'parent_derivation_id': self.manifest['parent_derivation_id'],
                          'parent_manifest_sha256': self.manifest['parent_manifest_sha256'],
                          'source': self.manifest['source'],
                          'allowed_pages': [18, 19, 20, 21, 22],
                          'retention_until': self.graph.label_policy['retention_until'],
                          'fidelity_status': 'unreviewed_partial'}
            elif operation == 'get_graph_labels_page':
                if set(request) != basic | {'derivation_id', 'manifest_sha256', 'page_number'}:
                    raise DocumentError('invalid_request')
                self._identity(request)
                number = request['page_number']
                if type(number) is not int or number not in (18, 19, 20, 21, 22):
                    raise DocumentError('page_out_of_scope')
                page = next(p for p in self.manifest['pages'] if p['page_number'] == number)
                self.graph._render(store, page)
                result = {'page': page, 'source': self.manifest['source'],
                          'derivation_id': self.manifest['derivation_id'],
                          'manifest_sha256': self.config['manifest_sha256'],
                          'fidelity_status': 'unreviewed_partial'}
            elif operation == 'fetch_graph_label_item':
                if set(request) != basic | {'derivation_id', 'manifest_sha256', 'item_id'}:
                    raise DocumentError('invalid_request')
                self._identity(request)
                item_id = _digest(request['item_id'])
                result = None
                for page in self.manifest['pages']:
                    for item in page['labels']:
                        if item['item_id'] == item_id:
                            self.graph._render(store, page)
                            result = {'item': item, 'page_number': page['page_number'],
                                      'render_sha256': page['render_sha256'],
                                      'source': self.manifest['source'],
                                      'derivation_id': self.manifest['derivation_id'],
                                      'manifest_sha256': self.config['manifest_sha256'],
                                      'fidelity_status': 'unreviewed_partial'}
                if result is None:
                    raise DocumentError('evidence_unavailable', 'retrieval')
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

    def _identity(self, request):
        if (request['derivation_id'] != self.manifest['derivation_id']
                or request['manifest_sha256'] != self.config['manifest_sha256']):
            raise DocumentError('labels_identity_mismatch')


class Handler(socketserver.StreamRequestHandler):
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
                              'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION,
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
    gateway = GraphLabelsGateway(config)
    bound = None
    try:
        with socketserver.UnixStreamServer(config['socket_path'], Handler) as server:
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
