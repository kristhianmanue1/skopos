"""Consulta literal acotada de siete originales CTIM bajo políticas existentes."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

import pymongo

from skopos.pdf_custody import (SOURCE_POLICY_SCHEMA, SOURCE_SCHEMA,
                               PdfCustodyStore, _policy_digest,
                               _read_under, _verified_document, load_policy)
from skopos.pdf_document_policy_v02 import load_document_policy_v02
from skopos.pdf_document_store import PdfDocumentStore, load_document_policy
from skopos.source_document_store import SourceDocumentStore


SCHEMA = 'skopos/ctim-source-access/v0.1'
PAGE_SCHEMA = 'skopos/ctim-source-access/v0.2'
POLICY_SCHEMA = 'skopos/ctim-source-access-policy/v0.1'
EXTENSIBLE_POLICY_SCHEMA = 'skopos/ctim-source-access-policy/v0.2'
HEX = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
MAX_POLICY_BYTES = 32 * 1024
MAX_PAGE_RESPONSE_BYTES = 64 * 1024


class AccessError(ValueError):
    def __init__(self, code, stage='validation'):
        self.code, self.stage = code, stage
        super().__init__(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode()


def _file(path, maximum):
    if not isinstance(path, str) or not os.path.isabs(path):
        raise AccessError('policy_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            details = os.fstat(stream.fileno())
            if not stat.S_ISREG(details.st_mode) or details.st_size > maximum:
                raise AccessError('policy_unavailable')
            raw = stream.read(maximum + 1)
    except OSError:
        raise AccessError('policy_unavailable') from None
    if not raw or len(raw) > maximum:
        raise AccessError('policy_unavailable')
    return raw


def load_access_policy(path):
    raw = _file(str(path), MAX_POLICY_BYTES)
    try:
        policy = json.loads(raw)
    except (UnicodeError, ValueError):
        raise AccessError('policy_unavailable') from None
    required = {'schema', 'inventory_root', 'inventory_ref', 'inventory_sha256',
                'mongo_uri', 'database', 'socket_path', 'sources'}
    if (not isinstance(policy, dict) or set(policy) != required
            or policy['schema'] not in (POLICY_SCHEMA, EXTENSIBLE_POLICY_SCHEMA)
            or not isinstance(policy['sources'], list)
            or (len(policy['sources']) != 7 if policy['schema'] == POLICY_SCHEMA
                else len(policy['sources']) < 1)
            or not isinstance(policy['mongo_uri'], str)
            or not policy['mongo_uri'].startswith('mongodb://127.0.0.1:37034/')
            or not isinstance(policy['database'], str) or not policy['database']
            or not isinstance(policy['socket_path'], str)
            or not os.path.isabs(policy['socket_path'])
            or not isinstance(policy['inventory_sha256'], str)
            or not HEX.fullmatch(policy['inventory_sha256'])):
        raise AccessError('policy_unavailable')
    inventory_raw = _read_under(policy['inventory_root'], policy['inventory_ref'],
                                MAX_POLICY_BYTES)
    if _sha(inventory_raw) != policy['inventory_sha256']:
        raise AccessError('inventory_mismatch')
    try:
        inventory = json.loads(inventory_raw)
    except (UnicodeError, ValueError):
        raise AccessError('inventory_mismatch') from None
    if (not isinstance(inventory, dict)
            or inventory.get('schema') != 'expertogobernanza/source-inventory/v1'
            or not isinstance(inventory.get('sources'), list)
            or len(inventory['sources']) != len(policy['sources'])):
        raise AccessError('inventory_mismatch')
    if any(not isinstance(item, dict) or not isinstance(item.get('id'), str)
           or item.get('media_type') not in ('application/pdf', 'text/html')
           or not isinstance(item.get('sha256'), str)
           or HEX.fullmatch(item['sha256']) is None
           or type(item.get('bytes')) is not int
           or item['bytes'] < 1 for item in inventory['sources']):
        raise AccessError('inventory_mismatch')
    indexed = {item['id']: item for item in inventory['sources']}
    if len(indexed) != len(inventory['sources']):
        raise AccessError('inventory_mismatch')
    seen = set()
    for entry in policy['sources']:
        if not isinstance(entry, dict) or entry.get('source_id') not in indexed:
            raise AccessError('policy_unavailable')
        source_id = entry['source_id']
        if source_id in seen or ID.fullmatch(source_id) is None:
            raise AccessError('policy_unavailable')
        seen.add(source_id)
        source = indexed[source_id]
        common = {'source_id', 'custody_policy_path'}
        expected = (common | {'document_policy_path', 'derivation_id',
                              'manifest_sha256'} if source['media_type'] == 'application/pdf'
                    else common | {'derivative_path', 'derivative_sha256'})
        if (policy['schema'] == EXTENSIBLE_POLICY_SCHEMA
                and source['media_type'] == 'application/pdf'):
            expected.add('custody_material_id')
        if set(entry) != expected:
            raise AccessError('policy_unavailable')
        for field in expected - {'source_id'}:
            if not isinstance(entry[field], str):
                raise AccessError('policy_unavailable')
            if field.endswith('_path') and not os.path.isabs(entry[field]):
                raise AccessError('policy_unavailable')
            if field.endswith('_sha256') and HEX.fullmatch(entry[field]) is None:
                raise AccessError('policy_unavailable')
        if source['media_type'] == 'application/pdf' and HEX.fullmatch(
                entry['derivation_id']) is None:
            raise AccessError('policy_unavailable')
        if ('custody_material_id' in entry and ID.fullmatch(
                entry['custody_material_id']) is None):
            raise AccessError('policy_unavailable')
    if seen != set(indexed):
        raise AccessError('policy_unavailable')
    return policy, indexed, _sha(raw)


class AccessGateway:
    """El agente sólo envía operaciones e identidades, nunca raíces ni políticas."""

    def __init__(self, policy_path, client=None):
        self.policy_path = str(policy_path)
        self.policy, self.inventory, self.policy_file_sha256 = load_access_policy(
            self.policy_path)
        self.entries = {entry['source_id']: entry for entry in self.policy['sources']}
        self.client = client if client is not None else pymongo.MongoClient(
            self.policy['mongo_uri'], serverSelectionTimeoutMS=2000)
        self.owns_client = client is None

    def close(self):
        if self.owns_client:
            self.client.close()

    def _current(self):
        _, _, digest = load_access_policy(self.policy_path)
        if digest != self.policy_file_sha256:
            raise AccessError('policy_mismatch')

    def _pdf(self, source_id):
        entry, source = self.entries[source_id], self.inventory[source_id]
        custody = load_policy(entry['custody_policy_path'])
        raw = _file(entry['document_policy_path'], MAX_POLICY_BYTES)
        try:
            schema = json.loads(raw)['schema']
        except (UnicodeError, ValueError, KeyError, TypeError):
            raise AccessError('policy_unavailable') from None
        loader = (load_document_policy_v02 if schema == 'skopos/pdf-document-policy/v0.2'
                  else load_document_policy)
        policy = loader(entry['document_policy_path'])
        if (self.policy['schema'] == EXTENSIBLE_POLICY_SCHEMA
                and policy['material_id'] != entry['custody_material_id']):
            raise AccessError('source_mismatch')
        if (policy['custody_policy_path'] != entry['custody_policy_path']
                or policy['source_sha256'] != source['sha256']
                or policy['max_page'] != source['pages']
                or source['media_type'] != 'application/pdf'):
            raise AccessError('source_mismatch')
        store_type = (SourceDocumentStore if custody['schema'] == SOURCE_POLICY_SCHEMA
                      else PdfDocumentStore)
        store = store_type(self.client[self.policy['database']], policy)
        parent = {'material_id': policy['material_id'],
                  'source_revision': policy['source_revision'],
                  'source_sha256': policy['source_sha256'],
                  'custody_receipt_id': policy['custody_receipt_id'],
                  'custody_policy_sha256': policy['custody_policy_sha256']}
        original = store._source(parent)
        if len(original) != source['bytes'] or _sha(original) != source['sha256']:
            raise AccessError('source_mismatch', 'retrieval')
        manifest, manifest_raw = store._manifest(entry['derivation_id'])
        if (_sha(manifest_raw) != entry['manifest_sha256']
                or manifest['page_count'] != source['pages']
                or [page['page_number'] for page in manifest['pages']] !=
                   list(range(1, source['pages'] + 1))):
            raise AccessError('coverage_mismatch', 'retrieval')
        return store, manifest, len(original) + len(manifest_raw)

    def _html(self, source_id):
        entry, source = self.entries[source_id], self.inventory[source_id]
        policy = load_policy(entry['custody_policy_path'])
        allowed = policy['allowed_materials']
        if (policy['schema'] != SOURCE_POLICY_SCHEMA or len(allowed) != 1
                or allowed[0]['material_id'] != source_id
                or allowed[0]['media_type'] != 'text/html'
                or allowed[0]['source_sha256'] != source['sha256']):
            raise AccessError('source_mismatch')
        store = PdfCustodyStore(self.client[self.policy['database']], policy)
        key = ':'.join((policy['project_id'], source_id,
                        str(allowed[0]['source_revision'])))
        document = store.revisions.find_one({'_id': key})
        if document is None:
            raise AccessError('custody_receipt_missing', 'retrieval')
        _verified_document(document, key, SOURCE_SCHEMA)
        if (document.get('policy_sha256') != _policy_digest(policy)
                or document.get('source_sha256') != source['sha256']
                or document.get('source_ref') != allowed[0]['source_ref']
                or not isinstance(document.get('provenance'), dict)
                or document['provenance'].get('record_ref') != allowed[0]['provenance_ref']
                or document['provenance'].get('record_sha256') !=
                   allowed[0]['provenance_sha256']):
            raise AccessError('custody_receipt_mismatch', 'retrieval')
        original = _read_under(policy['source_root'], allowed[0]['source_ref'],
                               policy['max_bytes'], stage='retrieval')
        provenance = _read_under(policy['provenance_root'],
                                 allowed[0]['provenance_ref'], 256 * 1024,
                                 stage='retrieval')
        if (len(original) != source['bytes'] or _sha(original) != source['sha256']
                or _sha(provenance) != allowed[0]['provenance_sha256']):
            raise AccessError('source_hash_mismatch', 'retrieval')
        path = entry['derivative_path']
        derivative_raw = _read_under(str(Path(path).parent), Path(path).name,
                                     4 * 1024 * 1024, stage='retrieval')
        if _sha(derivative_raw) != entry['derivative_sha256']:
            raise AccessError('derivative_hash_mismatch', 'retrieval')
        try:
            derivative = json.loads(derivative_raw)
        except (UnicodeError, ValueError):
            raise AccessError('derivative_unavailable', 'retrieval') from None
        if (derivative.get('schema') != 'skopos/html-text-derivative/v0.1'
                or derivative.get('source_sha256') != source['sha256']
                or derivative.get('source_bytes') != source['bytes']
                or derivative.get('fidelity_status') != 'unreviewed'
                or not isinstance(derivative.get('items'), list)):
            raise AccessError('derivative_mismatch', 'retrieval')
        for item in derivative['items']:
            start, end = item['start_byte'], item['end_byte']
            if (type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(original)
                    or _sha(original[start:end]) != item['raw_sha256']
                    or _sha(item['text'].encode()) != item['text_sha256']):
                raise AccessError('fragment_integrity_failed', 'retrieval')
        return derivative, len(original) + len(provenance) + len(derivative_raw)

    def _source(self, source_id):
        if source_id not in self.entries:
            raise AccessError('source_not_allowed')
        source = self.inventory[source_id]
        if source['media_type'] == 'application/pdf':
            return self._pdf(source_id)
        if source['media_type'] == 'text/html':
            return self._html(source_id)
        raise AccessError('unsupported_format')

    def _coverage(self, source_id, value):
        source = self.inventory[source_id]
        if source['media_type'] == 'application/pdf':
            _, manifest, _ = value
            return {'source_id': source_id, 'media_type': source['media_type'],
                    'source_sha256': source['sha256'], 'source_bytes': source['bytes'],
                    'page_count': source['pages'],
                    'derived_pages': len(manifest['pages']),
                    'native_no_text_pages': sum(page['native_text']['status'] == 'no_text'
                                                for page in manifest['pages']),
                    'ocr_extracted_pages': sum(page['ocr_text']['status'] == 'extracted'
                                               for page in manifest['pages']),
                    'scope': 'full_physical_page_set',
                    'fidelity_status': 'unreviewed'}
        derivative, _ = value
        return {'source_id': source_id, 'media_type': source['media_type'],
                'source_sha256': source['sha256'], 'source_bytes': source['bytes'],
                'segments': len(derivative['items']),
                'scope': 'parser_visible_text', 'fidelity_status': 'unreviewed',
                'css_visibility_evaluated': False}

    def _find(self, term, limit, loaded):
        normalized = term.casefold()
        candidates, total, by_source = [], 0, {}
        for source_id in self.entries:
            source = self.inventory[source_id]
            value = loaded[source_id]
            hits = []
            before = total
            if source['media_type'] == 'application/pdf':
                _, manifest, _ = value
                for page in manifest['pages']:
                    for modality in ('native_text', 'ocr_text'):
                        for item in page[modality]['lines']:
                            if normalized not in item['text'].casefold():
                                continue
                            total += 1
                            if len(hits) < limit:
                                hits.append({
                                    'source_id': source_id, 'source_sha256': source['sha256'],
                                    'media_type': source['media_type'],
                                    'page_number': page['page_number'],
                                    'item_id': item['item_id'], 'modality': modality,
                                    'bbox': item['bbox'], 'text': item['text'],
                                    'fidelity_status': 'unreviewed'})
            else:
                derivative, _ = value
                for item in derivative['items']:
                    if normalized not in item['text'].casefold():
                        continue
                    total += 1
                    if len(hits) < limit:
                        hits.append({
                            'source_id': source_id, 'source_sha256': source['sha256'],
                            'media_type': source['media_type'],
                            'start_byte': item['start_byte'],
                            'end_byte': item['end_byte'], 'item_id': item['item_id'],
                            'raw_sha256': item['raw_sha256'], 'text': item['text'],
                            'fidelity_status': 'unreviewed'})
            by_source[source_id] = {'literal_hits': total - before}
            candidates.append(hits)
        selected = []
        for index in range(limit):
            for hits in candidates:
                if index < len(hits):
                    selected.append(hits[index])
                    if len(selected) == limit:
                        break
            if len(selected) == limit:
                break
        return {'candidates': selected, 'total_literal_hits': total,
                'result_limit': total > limit,
                'search_method': 'literal_casefold_across_allowed_sources',
                'selected_source_count': len(loaded),
                'hits_by_source': by_source}

    def _fetch(self, source_id, item_id, value):
        source = self.inventory[source_id]
        if source['media_type'] == 'application/pdf':
            _, manifest, _ = value
            for page in manifest['pages']:
                for modality in ('native_text', 'ocr_text'):
                    for item in page[modality]['lines']:
                        if item['item_id'] == item_id:
                            return {'source_id': source_id,
                                    'source_sha256': source['sha256'],
                                    'page_number': page['page_number'],
                                    'modality': modality, 'item': item,
                                    'fidelity_status': 'unreviewed'}
        else:
            derivative, _ = value
            for item in derivative['items']:
                if item['item_id'] == item_id:
                    return {'source_id': source_id,
                            'source_sha256': source['sha256'],
                            'start_byte': item['start_byte'],
                            'end_byte': item['end_byte'], 'item': item,
                            'fidelity_status': 'unreviewed'}
        raise AccessError('fragment_not_found', 'retrieval')

    def _page(self, source_id, page_number, value):
        source = self.inventory[source_id]
        _, manifest, _ = value
        page = manifest['pages'][page_number - 1]
        return {'source_id': source_id, 'source_sha256': source['sha256'],
                'media_type': source['media_type'],
                'page_number': page_number, 'page_count': source['pages'],
                'page_width_points': page['page_width_points'],
                'page_height_points': page['page_height_points'],
                'page_rotation': page['page_rotation'],
                'native_text': page['native_text'], 'ocr_text': page['ocr_text'],
                'fidelity_status': 'unreviewed',
                'line_order': 'manifest_extraction_order'}

    def handle(self, request):
        started = time.monotonic()
        request_id = request.get('request_id') if isinstance(request, dict) else None
        request_sha256 = _sha(_canonical(request)) if isinstance(request, dict) else None
        try:
            if (not isinstance(request, dict)
                    or not isinstance(request_id, str)
                    or ID.fullmatch(request_id) is None):
                raise AccessError('invalid_request')
            operation = request.get('operation')
            fields = ({'request_id', 'operation'} if operation == 'list_sources'
                      else {'request_id', 'operation', 'term', 'limit'}
                      if operation == 'find_literal'
                      else {'request_id', 'operation', 'source_id', 'item_id'}
                      if operation == 'fetch_fragment'
                      else {'request_id', 'operation', 'source_id', 'page_number'}
                      if operation == 'read_pdf_page' else None)
            if fields is None or set(request) != fields:
                raise AccessError('invalid_request')
            if operation == 'find_literal' and (not isinstance(request['term'], str)
                    or not 1 <= len(request['term']) <= 128
                    or type(request['limit']) is not int
                    or not 1 <= request['limit'] <= 10):
                raise AccessError('invalid_query')
            if operation == 'fetch_fragment' and (
                    not isinstance(request['source_id'], str)
                    or not isinstance(request['item_id'], str)
                    or HEX.fullmatch(request['item_id']) is None):
                raise AccessError('invalid_request')
            if operation == 'read_pdf_page' and (
                    not isinstance(request['source_id'], str)
                    or type(request['page_number']) is not int
                    or request['page_number'] < 1):
                raise AccessError('invalid_page')
            self._current()
            source_ids = (list(self.entries) if operation not in
                          ('fetch_fragment', 'read_pdf_page')
                          else [request['source_id']])
            if operation == 'read_pdf_page':
                source_id = request['source_id']
                if source_id not in self.entries:
                    raise AccessError('source_not_allowed')
                source = self.inventory[source_id]
                if source['media_type'] != 'application/pdf':
                    raise AccessError('unsupported_format')
                if request['page_number'] > source['pages']:
                    raise AccessError('invalid_page')
            loaded = {source_id: self._source(source_id) for source_id in source_ids}
            coverage = [self._coverage(source_id, loaded[source_id])
                        for source_id in source_ids]
            if operation == 'list_sources':
                result = {'sources': coverage}
            elif operation == 'find_literal':
                result = self._find(request['term'], request['limit'], loaded)
                result['coverage'] = coverage
            elif operation == 'read_pdf_page':
                result = self._page(request['source_id'], request['page_number'],
                                    loaded[request['source_id']])
                result['coverage'] = coverage
            else:
                result = self._fetch(request['source_id'], request['item_id'],
                                     loaded[request['source_id']])
                result['coverage'] = coverage
            result['cost'] = {'elapsed_ms': round((time.monotonic() - started) * 1000),
                              'verified_input_bytes': sum(value[-1] for value in
                                                          loaded.values())}
            response = {'status': 'ok', 'result': result, 'error': None}
        except (AccessError, ValueError, KeyError, TypeError, IndexError) as error:
            code = getattr(error, 'code', 'source_unavailable')
            stage = getattr(error, 'stage', 'retrieval')
            response = {'status': 'execution_failed' if stage == 'retrieval' else
                        'invalid_input', 'result': None,
                        'error': {'code': code, 'stage': stage}}
        except (pymongo.errors.PyMongoError, OSError):
            response = {'status': 'execution_failed', 'result': None,
                        'error': {'code': 'store_unavailable', 'stage': 'execution'}}
        response.update({'schema': PAGE_SCHEMA if isinstance(request, dict) and
                         request.get('operation') == 'read_pdf_page' else SCHEMA,
                         'request_id': request_id,
                         'request_sha256': request_sha256,
                         'policy_sha256': self.policy_file_sha256})
        limit = (MAX_PAGE_RESPONSE_BYTES if isinstance(request, dict) and
                 request.get('operation') == 'read_pdf_page' else 256 * 1024)
        response_bytes = len(_canonical(response))
        if response_bytes + (1 if limit == MAX_PAGE_RESPONSE_BYTES else 0) > limit:
            response.update({'status': 'execution_failed', 'result': None,
                             'error': {'code': 'page_response_limit_exceeded' if
                                       limit == MAX_PAGE_RESPONSE_BYTES else
                                       'response_limit_exceeded',
                                       'stage': 'delivery'}})
        return response
