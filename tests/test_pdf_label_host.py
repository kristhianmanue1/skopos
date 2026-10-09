"""Canal de candidatos: integridad, alcance y recuperación determinista."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from skopos.pdf_document_store import DocumentError, _canonical
from skopos.pdf_label_host import (CONTRACT_ID, CONTRACT_VERSION, LabelGateway,
                                   LABEL_HOST_SCRIPT, LABEL_PROJECTION_SCRIPT,
                                   POLICY_SCHEMA, _request, load_label_policy)


class FakeStore:
    def __init__(self, manifest, raw, source, root):
        self.manifest, self.raw, self.source = manifest, raw, source
        self.policy = {'derived_root': str(root), 'max_output_bytes': 10000}

    def _source(self, value):
        if value != self.source:
            raise DocumentError('source_mismatch')

    def _manifest(self, _derivation_id):
        return self.manifest, self.raw


class LabelHostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = {'material_id': 'sample', 'source_revision': 1,
                       'source_sha256': 'a' * 64,
                       'custody_receipt_id': 'sample:1:receipt',
                       'custody_policy_sha256': 'b' * 64}
        self.render_bytes = b'fixture-png-bytes'
        render_dir = self.root / ('c' * 64) / 'renders'
        render_dir.mkdir(parents=True)
        (render_dir / 'page-020.png').write_bytes(self.render_bytes)
        self.render_sha = hashlib.sha256(self.render_bytes).hexdigest()
        self.manifest = {
            'schema': 'skopos/pdf-document-manifest/v0.1',
            'derivation_id': 'c' * 64, 'policy_sha256': 'd' * 64,
            'parent': self.source, 'pages': [{
                'page_number': 20, 'render': {'sha256': self.render_sha,
                                             'file_ref': 'renders/page-020.png'},
                'native_text': {'status': 'extracted', 'lines': [
                    {'item_id': 'f' * 64, 'bbox': [0.2, 0.2, 0.4, 0.3],
                     'text': 'COORDINACIÓN DE'}]},
                'ocr_text': {'status': 'extracted', 'lines': []},
                'visual_graph': {'status': 'partial', 'nodes': [
                    {'node_id': 'n1', 'item_id': '1' * 64,
                     'bbox': [0.1, 0.1, 0.5, 0.5]}], 'edges': [],
                    'connectors': [], 'unknown': [],
                    'direction_rule': 'unknown_without_visible_arrowhead'},
            }]}
        self.raw = _canonical(self.manifest)
        self.manifest_sha = hashlib.sha256(self.raw).hexdigest()
        self.gateway = LabelGateway.__new__(LabelGateway)
        self.gateway.policy = {'allowed_pages': [18, 19, 20, 21, 22],
                               'max_nodes_per_response': 40,
                               'derivation_id': 'c' * 64,
                               'manifest_sha256': self.manifest_sha,
                               'source_sha256': 'a' * 64}
        self.gateway.config = {'label_policy_sha256': '2' * 64}
        self.store = FakeStore(self.manifest, self.raw, self.source, self.root)
        self.request = {'request_id': 'sample-label-20',
                        'contract_id': CONTRACT_ID,
                        'contract_version': CONTRACT_VERSION,
                        'project_id': 'sample',
                        'operation': 'get_label_candidates',
                        'source': self.source,
                        'label_policy_sha256': '2' * 64,
                        'derivation_id': 'c' * 64,
                        'manifest_sha256': self.manifest_sha,
                        'page_number': 20, 'max_nodes': 40,
                        '_request_sha256': '3' * 64}

    def test_native_and_empty_ocr_remain_distinct(self):
        result = self.gateway._candidates(self.store, self.request)
        node = result['nodes'][0]
        self.assertEqual('1' * 64, node['parent_item_id'])
        self.assertEqual('COORDINACIÓN DE', node['label_candidates'][0]['text'])
        self.assertEqual(['f' * 64], node['label_candidates'][0]['line_item_ids'])
        self.assertEqual('', node['label_candidates'][1]['text'])
        self.assertEqual('no_lines', node['label_candidates'][1]['status'])
        self.assertEqual('unreviewed', result['fidelity_status'])
        self.assertEqual(self.render_sha, result['render_sha256'])
        self.assertEqual('unreviewed_partial',
                         result['coverage']['topology_completeness'])

    def test_page_source_manifest_and_limit_fail_closed(self):
        for field, value, code in (
                ('page_number', 23, 'page_out_of_scope'),
                ('manifest_sha256', '4' * 64, 'manifest_mismatch'),
                ('label_policy_sha256', '4' * 64, 'label_policy_mismatch'),
                ('source', {}, 'source_mismatch'),
                ('max_nodes', 0, 'limit_exceeded')):
            changed = dict(self.request, **{field: value})
            with self.subTest(field=field), self.assertRaises(DocumentError) as error:
                self.gateway._candidates(self.store, changed)
            self.assertEqual(code, error.exception.code)
        self.store.raw = b'{}'
        with self.assertRaises(DocumentError) as error:
            self.gateway._candidates(self.store, self.request)
        self.assertEqual('manifest_integrity_failed', error.exception.code)
        self.store.raw = self.raw
        (self.root / ('c' * 64) / 'renders' / 'page-020.png').write_bytes(b'changed')
        with self.assertRaises(DocumentError) as error:
            self.gateway._candidates(self.store, self.request)
        self.assertEqual('render_integrity_failed', error.exception.code)

    def test_request_envelope_and_replay(self):
        request = {key: value for key, value in self.request.items()
                   if key != '_request_sha256'}
        raw = _canonical(request)
        (self.root / 'request.json').write_bytes(raw)
        envelope = {'request_file_ref': 'request.json',
                    'request_sha256': hashlib.sha256(raw).hexdigest(),
                    'request_id': request['request_id'],
                    'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION}
        (self.root / 'envelope.json').write_bytes(_canonical(envelope))
        first = _request({'requests_root': str(self.root)},
                         {'envelope_ref': 'envelope.json'})
        second = _request({'requests_root': str(self.root)},
                          {'envelope_ref': 'envelope.json'})
        self.assertEqual(first, second)
        envelope['request_sha256'] = '0' * 64
        (self.root / 'envelope.json').write_bytes(_canonical(envelope))
        with self.assertRaises(DocumentError) as error:
            _request({'requests_root': str(self.root)},
                     {'envelope_ref': 'envelope.json'})
        self.assertEqual('request_hash_mismatch', error.exception.code)

    def test_policy_pin_and_expiration_inherit_parent(self):
        parent = {'project_id': 'sample', 'source_sha256': 'a' * 64,
                  'requests_root': str(self.root),
                  'retention_until': '2026-11-08T00:00:00Z',
                  'retention_action': 'block_then_explicit_retirement'}
        policy = {'schema': POLICY_SCHEMA, 'policy_id': 'sample-labels',
                  'policy_version': 'v0.2', 'project_id': 'sample',
                  'document_policy_sha256': hashlib.sha256(_canonical(parent)).hexdigest(),
                  'source_sha256': 'a' * 64, 'derivation_id': 'c' * 64,
                  'manifest_sha256': self.manifest_sha,
                  'allowed_pages': [18, 19, 20, 21, 22],
                  'max_pages_per_request': 1, 'max_nodes_per_response': 40,
                  'retention_until': parent['retention_until'],
                  'request_retention_action': parent['retention_action'],
                  'requests_root': str(self.root), 'allow_network': False,
                  'response_persistence': False,
                  'label_host_sha256': hashlib.sha256(
                      LABEL_HOST_SCRIPT.read_bytes()).hexdigest(),
                  'label_projection_sha256': hashlib.sha256(
                      LABEL_PROJECTION_SCRIPT.read_bytes()).hexdigest()}
        path = self.root / 'label-policy.json'
        path.write_bytes(_canonical(policy))
        config = {'label_policy_path': str(path),
                  'label_policy_sha256': hashlib.sha256(_canonical(policy)).hexdigest()}
        self.assertEqual(policy, load_label_policy(config, parent))
        policy['retention_until'] = '2026-12-08T00:00:00Z'
        path.write_bytes(_canonical(policy))
        with self.assertRaises(DocumentError) as error:
            load_label_policy(config, parent)
        self.assertEqual('retention_policy_missing', error.exception.code)
        policy['retention_until'] = parent['retention_until']
        policy['policy_id'] = 'tampered-labels'
        path.write_bytes(_canonical(policy))
        with self.assertRaises(DocumentError) as error:
            load_label_policy(config, parent)
        self.assertEqual('label_policy_mismatch', error.exception.code)
        policy['policy_id'] = 'sample-labels'
        policy['label_projection_sha256'] = '0' * 64
        path.write_bytes(_canonical(policy))
        with self.assertRaises(DocumentError) as error:
            load_label_policy(config, parent)
        self.assertEqual('label_engine_mismatch', error.exception.code)


if __name__ == '__main__':
    unittest.main()
