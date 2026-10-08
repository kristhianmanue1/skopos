"""Derivados PDF separados de la custodia inmutable del original v0.2."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from skopos.pdf_custody import (_deliver, _digest, _identifier, _policy_digest,
                                _read_under, _root_fd, _verified_document,
                                load_policy)
from skopos.pdf_document_extract import (SCRIPT, DocumentExtractionError,
                                         extract_pages)


POLICY_SCHEMA = 'skopos/pdf-document-policy/v0.1'
CONTRACT_ID = 'expertogobernanza/skopos-document-derivatives'
CONTRACT_VERSION = 'v0.1'
MAX_POLICY_BYTES = 16 * 1024
MAX_RECEIPT_BYTES = 4096
GRAPH_SCRIPT = Path(__file__).resolve().with_name('pdf_visual_graph.py')
EXTRACT_SCRIPT = Path(__file__).resolve().with_name('pdf_document_extract.py')
STORE_SCRIPT = Path(__file__).resolve()


class DocumentError(ValueError):
    def __init__(self, code, stage='validation'):
        self.code, self.stage = code, stage
        super().__init__(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_document_policy(path):
    path = Path(path)
    if not path.is_absolute():
        raise DocumentError('policy_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise DocumentError('policy_unavailable')
            raw = source.read(MAX_POLICY_BYTES + 1)
    except OSError:
        raise DocumentError('policy_unavailable') from None
    if len(raw) > MAX_POLICY_BYTES:
        raise DocumentError('policy_unavailable')
    try:
        policy = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DocumentError('policy_unavailable') from None
    required = {
        'schema', 'policy_id', 'policy_version', 'project_id', 'owner',
        'custody_policy_path', 'custody_policy_sha256', 'custody_receipt_id',
        'material_id', 'source_revision', 'source_sha256', 'provenance_sha256',
        'requests_root', 'derived_root', 'delivery_root', 'cache_root',
        'retention_until', 'retention_basis', 'retention_action',
        'max_page', 'ocr_pages', 'graph_pages', 'allowed_modalities',
        'max_pages', 'max_ocr_pages', 'max_render_pixels', 'max_seconds',
        'max_output_bytes', 'render_scale_to', 'allow_network',
        'swift_path', 'renderer_path', 'engine_script_sha256',
        'graph_engine_sha256', 'extract_engine_sha256',
        'store_engine_sha256',
    }
    if (not isinstance(policy, dict) or set(policy) != required
            or policy['schema'] != POLICY_SCHEMA
            or policy['project_id'] != 'expertogobernanza'
            or policy['owner'] != 'expertogobernanza'
            or policy['allow_network'] is not False
            or policy['retention_action'] != 'block_then_explicit_retirement'):
        raise DocumentError('policy_unavailable')
    for field in ('requests_root', 'derived_root', 'delivery_root', 'cache_root'):
        descriptor = _root_fd(policy[field])
        os.close(descriptor)
    for field in ('policy_id', 'policy_version', 'retention_basis'):
        if not isinstance(policy[field], str) or not policy[field]:
            raise DocumentError('policy_unavailable')
    for field in ('material_id', 'project_id'):
        _identifier(policy[field])
    for field in ('source_sha256', 'provenance_sha256',
                  'custody_policy_sha256', 'engine_script_sha256',
                  'graph_engine_sha256', 'extract_engine_sha256',
                  'store_engine_sha256'):
        _digest(policy[field])
    if (policy['source_revision'] != 1 or policy['max_page'] != 188
            or policy['max_pages'] != 188 or policy['max_ocr_pages'] != 6
            or policy['ocr_pages'] != [1, 18, 19, 20, 21, 22]
            or policy['graph_pages'] != [18, 19, 20, 21, 22]
            or policy['allowed_modalities'] != ['native_text', 'selective_ocr',
                                                'visual_graph']
            or policy['max_render_pixels'] != 4_452_000
            or policy['max_seconds'] != 120
            or policy['max_output_bytes'] != 10_000_000
            or policy['render_scale_to'] != 2400):
        raise DocumentError('policy_unavailable')
    if not all(isinstance(policy[field], str) and os.path.isabs(policy[field])
               for field in ('custody_policy_path', 'swift_path', 'renderer_path')):
        raise DocumentError('policy_unavailable')
    if (_file_sha256(SCRIPT) != policy['engine_script_sha256']
            or _file_sha256(GRAPH_SCRIPT) != policy['graph_engine_sha256']
            or _file_sha256(EXTRACT_SCRIPT) != policy['extract_engine_sha256']
            or _file_sha256(STORE_SCRIPT) != policy['store_engine_sha256']):
        raise DocumentError('engine_mismatch')
    try:
        expires = datetime.fromisoformat(policy['retention_until'].replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise DocumentError('retention_policy_missing') from None
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise DocumentError('retention_policy_missing')
    custody = load_policy(policy['custody_policy_path'])
    if (_policy_digest(custody) != policy['custody_policy_sha256']
            or expires > datetime.fromisoformat(custody['retention_until'].replace('Z', '+00:00'))
            or custody['project_id'] != policy['project_id']
            or len(custody['allowed_materials']) != 1):
        raise DocumentError('custody_policy_mismatch')
    allowed = custody['allowed_materials'][0]
    if (allowed['material_id'] != policy['material_id']
            or allowed['source_revision'] != policy['source_revision']
            or allowed['source_sha256'] != policy['source_sha256']
            or allowed['provenance_sha256'] != policy['provenance_sha256']):
        raise DocumentError('custody_policy_mismatch')
    return policy


def _atomic_json(path, value):
    raw = _canonical(value)
    temporary = path.with_name('.' + path.name + '.' + os.urandom(8).hex())
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    try:
        with os.fdopen(descriptor, 'wb') as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return _sha256(raw)


def _write_digest(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as target:
        target.write((value + '\n').encode())
        target.flush()
        os.fsync(target.fileno())


class PdfDocumentStore:
    def __init__(self, database, policy):
        self.database, self.policy = database, policy
        self.custody = load_policy(policy['custody_policy_path'])
        self.policy_sha256 = _sha256(_canonical(policy))

    def _source(self, supplied):
        policy = self.policy
        expected = {
            'material_id': policy['material_id'],
            'source_revision': policy['source_revision'],
            'source_sha256': policy['source_sha256'],
            'custody_receipt_id': policy['custody_receipt_id'],
            'custody_policy_sha256': policy['custody_policy_sha256'],
        }
        if supplied != expected:
            raise DocumentError('source_mismatch')
        key = ':'.join((policy['project_id'], policy['material_id'],
                        str(policy['source_revision'])))
        document = self.database.pdf_custody_revisions_v1.find_one({'_id': key})
        if document is None:
            raise DocumentError('custody_receipt_missing')
        try:
            _verified_document(document, key)
        except ValueError:
            raise DocumentError('custody_integrity_failed') from None
        actual_receipt = key + ':' + document['request_sha256'][:16]
        provenance_record = document.get('provenance')
        if (actual_receipt != policy['custody_receipt_id']
                or document['source_sha256'] != policy['source_sha256']
                or document['policy_sha256'] != policy['custody_policy_sha256']
                or not isinstance(provenance_record, dict)
                or provenance_record.get('record_sha256') != policy['provenance_sha256']):
            raise DocumentError('custody_receipt_mismatch')
        allowed = self.custody['allowed_materials'][0]
        raw = _read_under(self.custody['source_root'], allowed['source_ref'],
                          self.custody['max_bytes'], stage='retrieval')
        provenance = _read_under(self.custody['source_root'], allowed['provenance_ref'],
                                 256 * 1024, stage='retrieval')
        if (_sha256(raw) != policy['source_sha256']
                or _sha256(provenance) != policy['provenance_sha256']):
            raise DocumentError('source_hash_mismatch', 'retrieval')
        return raw

    def _limits(self, request):
        policy = self.policy
        pages, modalities, limits = (request.get('pages'), request.get('modalities'),
                                     request.get('limits'))
        if (not isinstance(pages, list) or not pages or len(pages) > policy['max_pages']
                or any(type(n) is not int or n < 1 or n > policy['max_page'] for n in pages)
                or len(set(n for n in pages if type(n) is int)) != len(pages)
                or pages != sorted(pages)
                or not isinstance(modalities, list) or not modalities
                or any(not isinstance(mode, str) for mode in modalities)
                or len(set(modalities)) != len(modalities)
                or 'native_text' not in modalities
                or any(mode not in policy['allowed_modalities'] for mode in modalities)
                or not isinstance(limits, dict)
                or set(limits) != {'max_pages', 'max_render_pixels', 'max_seconds',
                                  'max_output_bytes', 'allow_network'}
                or limits['allow_network'] is not False):
            raise DocumentError('invalid_limits')
        for field in ('max_pages', 'max_render_pixels', 'max_seconds', 'max_output_bytes'):
            if (type(limits[field]) is not int or limits[field] < 1
                    or limits[field] > policy[field]):
                raise DocumentError('limit_exceeded')
        if len(pages) > limits['max_pages']:
            raise DocumentError('limit_exceeded')
        ocr_pages = request.get('ocr_pages', [])
        if (not isinstance(ocr_pages, list)
                or any(type(n) is not int for n in ocr_pages)
                or ocr_pages != sorted(set(ocr_pages))
                or any(type(n) is not int or n not in pages
                       or n not in policy['ocr_pages'] for n in ocr_pages)
                or len(ocr_pages) > policy['max_ocr_pages']
                or (ocr_pages and 'selective_ocr' not in modalities)
                or ('selective_ocr' in modalities and not ocr_pages)):
            raise DocumentError('invalid_ocr_pages')
        graph_pages = request.get('graph_pages', [])
        if (not isinstance(graph_pages, list)
                or any(type(n) is not int for n in graph_pages)
                or graph_pages != sorted(set(graph_pages))
                or any(n not in pages or n not in policy['graph_pages']
                       for n in graph_pages)
                or (graph_pages and 'visual_graph' not in modalities)
                or ('visual_graph' in modalities and not graph_pages)):
            raise DocumentError('invalid_graph_pages')
        return pages, modalities, ocr_pages, graph_pages, limits

    def _manifest(self, derivation_id):
        reference = derivation_id + '/manifest.json'
        try:
            raw = _read_under(self.policy['derived_root'], reference,
                              self.policy['max_output_bytes'], stage='retrieval')
            digest = _read_under(self.policy['derived_root'],
                                 derivation_id + '/manifest.sha256', 128,
                                 stage='retrieval').decode().strip()
            manifest = json.loads(raw)
        except (ValueError, UnicodeError):
            raise DocumentError('derivative_unavailable', 'retrieval') from None
        if (not isinstance(manifest, dict)
                or digest != _sha256(raw)
                or manifest.get('derivation_id') != derivation_id
                or manifest.get('schema') != 'skopos/pdf-document-manifest/v0.1'
                or manifest.get('policy_sha256') != self.policy_sha256
                or manifest.get('parent') != {
                    'material_id': self.policy['material_id'],
                    'source_revision': self.policy['source_revision'],
                    'source_sha256': self.policy['source_sha256'],
                    'custody_receipt_id': self.policy['custody_receipt_id'],
                    'custody_policy_sha256': self.policy['custody_policy_sha256'],
                }):
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        return manifest, raw

    def _receipt(self, request_id):
        _identifier(request_id)
        reference = 'requests/' + request_id + '.json'
        path = Path(self.policy['derived_root']) / reference
        try:
            path.lstat()
        except FileNotFoundError:
            return None
        try:
            raw = _read_under(self.policy['derived_root'], reference,
                              MAX_RECEIPT_BYTES, stage='retrieval')
            receipt = json.loads(raw)
        except (ValueError, UnicodeError):
            raise DocumentError('receipt_integrity_failed', 'retrieval') from None
        if not isinstance(receipt, dict) or receipt.get('request_id') != request_id:
            raise DocumentError('receipt_integrity_failed', 'retrieval')
        return receipt

    def derive(self, request):
        source_bytes = self._source(request.get('source'))
        pages, modalities, ocr_pages, graph_pages, limits = self._limits(request)
        request_id, request_sha256 = request['request_id'], request['_request_sha256']
        existing_receipt = self._receipt(request_id)
        if existing_receipt is not None:
            if existing_receipt['request_sha256'] != request_sha256:
                raise DocumentError('request_conflict')
            manifest, raw = self._manifest(existing_receipt['derivation_id'])
            if _sha256(raw) != existing_receipt['manifest_sha256']:
                raise DocumentError('manifest_integrity_failed', 'retrieval')
            return dict(existing_receipt, derivation_status='duplicate')
        job = {
            'source': request['source'], 'pages': pages,
            'modalities': modalities, 'ocr_pages': ocr_pages,
            'graph_pages': graph_pages,
            'limits': limits, 'policy_sha256': self.policy_sha256,
            'engine_script_sha256': self.policy['engine_script_sha256'],
            'graph_engine_sha256': self.policy['graph_engine_sha256'],
            'extract_engine_sha256': self.policy['extract_engine_sha256'],
            'store_engine_sha256': self.policy['store_engine_sha256'],
            'renderer_path': self.policy['renderer_path'],
            'render_scale_to': self.policy['render_scale_to'],
        }
        derivation_id = _sha256(_canonical(job))
        final = Path(self.policy['derived_root']) / derivation_id
        if final.exists():
            manifest, raw = self._manifest(derivation_id)
            if (manifest.get('parent') != request['source']
                    or manifest.get('policy_sha256') != self.policy_sha256
                    or [p.get('page_number') for p in manifest.get('pages', [])] != pages):
                raise DocumentError('manifest_integrity_failed', 'retrieval')
            manifest_sha256 = _sha256(raw)
            status = 'duplicate'
        else:
            temporary = Path(tempfile.mkdtemp(prefix='.skopos-derive-',
                                              dir=self.policy['derived_root']))
            os.chmod(temporary, 0o700)
            try:
                input_path = temporary / 'input.pdf'
                descriptor = os.open(input_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                     0o600)
                with os.fdopen(descriptor, 'wb') as target:
                    target.write(source_bytes)
                    target.flush()
                    os.fsync(target.fileno())
                result, renders = extract_pages(
                    input_path, pages, ocr_pages, graph_pages, temporary / 'renders',
                    render_scale_to=self.policy['render_scale_to'],
                    max_render_pixels=min(limits['max_render_pixels'],
                                          self.policy['max_render_pixels']),
                    max_seconds=min(limits['max_seconds'], self.policy['max_seconds']),
                    max_output_bytes=min(limits['max_output_bytes'],
                                         self.policy['max_output_bytes']),
                    renderer=self.policy['renderer_path'],
                    swift=self.policy['swift_path'],
                    cache_root=self.policy['cache_root'])
                if result['page_count'] != self.policy['max_page']:
                    raise DocumentError('page_count_mismatch', 'derivation')
                self._source(request['source'])
                for page in result['pages']:
                    for mode, key in (('native_text', 'native_text'),
                                      ('selective_ocr', 'ocr_text')):
                        for index, item in enumerate(page[key]['lines']):
                            item['item_id'] = _sha256(_canonical({
                                'derivation_id': derivation_id,
                                'page_number': page['page_number'],
                                'modality': mode, 'index': index,
                                'text': item['text'], 'bbox': item['bbox'],
                            }))
                    for node in page['visual_graph']['nodes']:
                        indices = node.pop('ocr_line_indices')
                        node['ocr_line_refs'] = [
                            page['ocr_text']['lines'][index]['item_id']
                            for index in indices]
                        node['item_id'] = _sha256(_canonical({
                            'derivation_id': derivation_id,
                            'page_number': page['page_number'],
                            'modality': 'visual_graph_node',
                            'node_id': node['node_id'], 'bbox': node['bbox'],
                            'label': node['label'],
                        }))
                manifest = {
                    'schema': 'skopos/pdf-document-manifest/v0.1',
                    'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION,
                    'derivation_id': derivation_id, 'parent': request['source'],
                    'policy_id': self.policy['policy_id'],
                    'policy_version': self.policy['policy_version'],
                    'policy_sha256': self.policy_sha256,
                    'engine_schema': result['schema'],
                    'fidelity_status': 'unreviewed',
                    'page_count': result['page_count'], 'pages': result['pages'],
                    'artifacts': renders,
                    'limits': limits,
                }
                manifest_sha256 = _atomic_json(temporary / 'manifest.json', manifest)
                _write_digest(temporary / 'manifest.sha256', manifest_sha256)
                input_path.unlink()
                total_bytes = ((temporary / 'manifest.json').stat().st_size
                               + (temporary / 'manifest.sha256').stat().st_size
                               + sum(item['byte_length'] for item in renders.values()))
                if total_bytes > limits['max_output_bytes']:
                    raise DocumentError('limit_exceeded', 'derivation')
                os.rename(temporary, final)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            status = 'created'
        summary = {
            'requested_pages': len(pages),
            'native_extracted': sum(p['native_text']['status'] == 'extracted'
                                    for p in manifest['pages']),
            'native_no_text': sum(p['native_text']['status'] == 'no_text'
                                  for p in manifest['pages']),
            'ocr_extracted': sum(p['ocr_text']['status'] == 'extracted'
                                 for p in manifest['pages']),
            'visual_graph': ('partial' if any(p['visual_graph']['status'] == 'partial'
                                             for p in manifest['pages']) else 'not_run'),
        }
        receipt = {
            'request_id': request_id, 'request_sha256': request_sha256,
            'derivation_id': derivation_id, 'manifest_ref': derivation_id + '/manifest.json',
            'manifest_sha256': manifest_sha256, 'page_summary': summary,
        }
        _atomic_json(Path(self.policy['derived_root']) / 'requests' /
                     (request_id + '.json'), receipt)
        return dict(receipt, derivation_status=status)

    def derivation_receipt(self, request):
        self._source(request.get('source'))
        receipt = self._receipt(request.get('derivation_request_id'))
        if receipt is None:
            return {'derivation_status': 'not_found'}
        if receipt['request_sha256'] != request.get('derivation_request_sha256'):
            raise DocumentError('request_conflict')
        manifest, raw = self._manifest(receipt['derivation_id'])
        if _sha256(raw) != receipt['manifest_sha256']:
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        return dict(receipt, derivation_status='duplicate')

    def fetch(self, request):
        self._source(request.get('source'))
        derivation_id = _digest(request.get('derivation_id'))
        manifest, manifest_raw = self._manifest(derivation_id)
        if _sha256(manifest_raw) != _digest(request.get('manifest_sha256')):
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        artifact_id = request.get('artifact_id')
        if artifact_id == 'manifest':
            raw = manifest_raw
            expected = request['manifest_sha256']
        else:
            artifact = next((a for a in manifest['artifacts'].values()
                             if a['artifact_id'] == artifact_id), None)
            if artifact is None:
                raise DocumentError('artifact_unavailable', 'retrieval')
            raw = _read_under(self.policy['derived_root'],
                              derivation_id + '/' + artifact['file_ref'],
                              self.policy['max_output_bytes'], stage='retrieval')
            expected = artifact['sha256']
        if _sha256(raw) != expected or request.get('artifact_sha256') != expected:
            raise DocumentError('artifact_integrity_failed', 'retrieval')
        output_ref = request.get('output_ref')
        _deliver(self.policy['delivery_root'], output_ref, raw)
        return {'artifact_id': artifact_id, 'derivation_id': derivation_id,
                'bytes_ref': output_ref, 'byte_length': len(raw), 'sha256': expected}

    def evidence(self, request):
        self._source(request.get('source'))
        derivation_id = _digest(request.get('derivation_id'))
        manifest, raw = self._manifest(derivation_id)
        if _sha256(raw) != _digest(request.get('manifest_sha256')):
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        item_id = _digest(request.get('item_id'))
        for page in manifest['pages']:
            for item in page['visual_graph']['nodes']:
                if item['item_id'] == item_id:
                    return {'item': item, 'page_number': page['page_number'],
                            'modality': 'visual_graph_node',
                            'render_sha256': (page['render'] or {}).get('sha256'),
                            'parent': manifest['parent'],
                            'fidelity_status': 'unreviewed'}
            for modality in ('native_text', 'ocr_text'):
                for item in page[modality]['lines']:
                    if item['item_id'] == item_id:
                        return {'item': item, 'page_number': page['page_number'],
                                'modality': modality,
                                'render_sha256': (page['render'] or {}).get('sha256'),
                                'parent': manifest['parent'],
                                'fidelity_status': 'unreviewed'}
        raise DocumentError('evidence_unavailable', 'retrieval')

    def search(self, request):
        self._source(request.get('source'))
        derivation_id = _digest(request.get('derivation_id'))
        manifest, raw = self._manifest(derivation_id)
        if _sha256(raw) != _digest(request.get('manifest_sha256')):
            raise DocumentError('manifest_integrity_failed', 'retrieval')
        term, limit = request.get('term'), request.get('limit')
        if (not isinstance(term, str) or not 1 <= len(term) <= 128
                or type(limit) is not int or not 1 <= limit <= 20):
            raise DocumentError('invalid_query')
        matches = []
        coverage = {'page_statuses': [
                        {'page_number': page['page_number'],
                         'native_text': page['native_text']['status'],
                         'ocr_text': page['ocr_text']['status']}
                        for page in manifest['pages']],
                    'modalities_scanned': ['native_text', 'ocr_text'],
                    'exclusions': ['visual_graph_labels', 'unrendered_image_text',
                                   'semantic_matches'],
                    'fidelity_status': 'unreviewed'}
        for page in manifest['pages']:
            for modality in ('native_text', 'ocr_text'):
                for item in page[modality]['lines']:
                    if term.casefold() in item['text'].casefold():
                        matches.append({'item_id': item['item_id'],
                                        'parent': manifest['parent'],
                                        'derivation_id': derivation_id,
                                        'manifest_sha256': request['manifest_sha256'],
                                        'page_number': page['page_number'],
                                        'modality': modality, 'bbox': item['bbox'],
                                        'text': item['text'],
                                        'search_method': 'literal_scan_v0.1',
                                        'fidelity_status': 'unreviewed'})
                        if len(matches) >= limit:
                            return {'match_status': 'matched', 'candidates': matches,
                                    'search_method': 'literal_scan_v0.1',
                                    'coverage': coverage}
        return {'match_status': 'matched' if matches else 'no_match',
                'candidates': matches, 'search_method': 'literal_scan_v0.1',
                'coverage': coverage}
