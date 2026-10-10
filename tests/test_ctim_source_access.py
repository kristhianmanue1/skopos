"""Controles del contrato de consulta CTIM, sin Mongo ni originales privados."""

import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from skopos.ctim_source_access import (AccessError, AccessGateway, _canonical,
                                      load_access_policy)


class GatewayContractTests(unittest.TestCase):
    def setUp(self):
        self.gateway = object.__new__(AccessGateway)
        self.gateway.policy_file_sha256 = 'a' * 64
        self.gateway.entries = {'source-a': {}, 'source-b': {}}
        self.gateway.inventory = {
            'source-a': {'media_type': 'application/pdf', 'sha256': 'b' * 64,
                         'bytes': 4, 'pages': 1},
            'source-b': {'media_type': 'text/html', 'sha256': 'c' * 64,
                         'bytes': 4, 'pages': None}}
        self.gateway._current = lambda: None
        line = {'item_id': 'd' * 64, 'text': 'CTIM en PDF', 'bbox': [0, 0, 1, 1]}
        page = {'page_number': 1, 'page_width_points': 612.0,
                'page_height_points': 792.0, 'page_rotation': 0,
                'native_text': {'status': 'extracted', 'lines': [line]},
                'ocr_text': {'status': 'not_requested', 'lines': []}}
        item = {'item_id': 'e' * 64, 'text': 'CTIM en HTML',
                'start_byte': 0, 'end_byte': 4, 'raw_sha256': 'f' * 64}
        self.values = {'source-a': (None, {'pages': [page]}, 4),
                       'source-b': ({'items': [item]}, 4)}
        def source(source_id):
            if source_id not in self.values:
                raise AccessError('source_not_allowed')
            return self.values[source_id]
        self.gateway._source = source

    def test_inventory_search_and_fetch_keep_identity_and_coverage(self):
        found = self.gateway.handle({'request_id': 'one',
                                     'operation': 'find_literal',
                                     'term': 'CTIM', 'limit': 2})
        self.assertEqual(found['status'], 'ok')
        self.assertEqual(found['schema'], 'skopos/ctim-source-access/v0.1')
        result = found['result']
        self.assertEqual(len(result['coverage']), 2)
        self.assertEqual([item['source_id'] for item in result['candidates']],
                         ['source-a', 'source-b'])
        self.assertFalse(result['result_limit'])
        fetched = self.gateway.handle({'request_id': 'two',
                                       'operation': 'fetch_fragment',
                                       'source_id': 'source-b',
                                       'item_id': 'e' * 64})
        self.assertEqual(fetched['status'], 'ok')
        self.assertEqual(fetched['result']['start_byte'], 0)

    def test_fails_closed_on_unknown_identity_and_changed_policy(self):
        response = self.gateway.handle({'request_id': 'three',
                                        'operation': 'fetch_fragment',
                                        'source_id': 'outside-root',
                                        'item_id': 'e' * 64})
        self.assertEqual(response['error']['code'], 'source_not_allowed')
        self.assertIsNone(response['result'])
        self.gateway._current = lambda: (_ for _ in ()).throw(
            ValueError('policy_mismatch'))
        response = self.gateway.handle({'request_id': 'four',
                                        'operation': 'list_sources'})
        self.assertNotEqual(response['status'], 'ok')
        self.assertIsNone(response['result'])

    def test_rejects_extra_request_fields(self):
        response = self.gateway.handle({'request_id': 'five',
                                        'operation': 'list_sources',
                                        'source_root': '/tmp'})
        self.assertEqual(response['error']['code'], 'invalid_request')

    def test_read_pdf_page_keeps_manifest_lines_and_original_identity(self):
        response = self.gateway.handle({'request_id': 'page-one',
                                        'operation': 'read_pdf_page',
                                        'source_id': 'source-a', 'page_number': 1})
        self.assertEqual(response['schema'], 'skopos/ctim-source-access/v0.2')
        self.assertEqual(response['status'], 'ok')
        page = response['result']
        self.assertEqual(page['source_sha256'], 'b' * 64)
        self.assertEqual(page['page_number'], 1)
        self.assertEqual(page['native_text']['lines'][0]['item_id'], 'd' * 64)
        self.assertEqual(page['native_text']['lines'][0]['bbox'], [0, 0, 1, 1])
        self.assertEqual(page['ocr_text']['status'], 'not_requested')
        self.assertEqual(page['fidelity_status'], 'unreviewed')
        self.assertEqual(page['coverage'][0]['derived_pages'], 1)

    def test_read_pdf_page_rejects_non_pdf_outside_page_and_bad_types(self):
        for source_id, number, code in (
                ('outside-root', 1, 'source_not_allowed'),
                ('source-b', 1, 'unsupported_format'),
                ('source-a', 0, 'invalid_page'),
                ('source-a', 2, 'invalid_page'),
                ('source-a', True, 'invalid_page'),
                ('source-a', 1.0, 'invalid_page')):
            with self.subTest(source_id=source_id, number=number):
                response = self.gateway.handle({
                    'request_id': 'reject', 'operation': 'read_pdf_page',
                    'source_id': source_id, 'page_number': number})
                self.assertEqual(response['error']['code'], code)
                self.assertIsNone(response['result'])

    def test_read_pdf_page_fails_closed_on_derivative_and_size(self):
        original_source = self.gateway._source
        self.gateway._source = lambda _id: (_ for _ in ()).throw(
            AccessError('coverage_mismatch', 'retrieval'))
        request = {'request_id': 'broken', 'operation': 'read_pdf_page',
                   'source_id': 'source-a', 'page_number': 1}
        broken = self.gateway.handle(request)
        self.assertEqual(broken['status'], 'execution_failed')
        self.assertEqual(broken['error']['code'], 'coverage_mismatch')
        self.gateway._source = original_source
        self.values['source-a'][1]['pages'][0]['native_text']['lines'][0][
            'text'] = 'x' * (64 * 1024)
        oversized = self.gateway.handle(request)
        self.assertEqual(oversized['error']['code'],
                         'page_response_limit_exceeded')
        self.assertIsNone(oversized['result'])
        self.assertLess(len(_canonical(oversized)) + 1, 64 * 1024)

    def test_pdf_policy_cannot_alias_another_material_identity(self):
        self.gateway.policy = {'schema': 'skopos/ctim-source-access-policy/v0.2'}
        self.gateway.entries['source-a'] = {
            'custody_policy_path': '/unused/custody.json',
            'document_policy_path': '/unused/document.json',
            'custody_material_id': 'source-a'}
        with patch('skopos.ctim_source_access.load_policy',
                   return_value={'schema': 'skopos/source-custody-policy/v0.3'}), \
                patch('skopos.ctim_source_access._file',
                      return_value=b'{"schema":"skopos/pdf-document-policy/v0.2"}'), \
                patch('skopos.ctim_source_access.load_document_policy_v02',
                      return_value={'material_id': 'source-b'}):
            with self.assertRaisesRegex(AccessError, 'source_mismatch'):
                self.gateway._pdf('source-a')


class ExtensibleProfileTests(unittest.TestCase):
    def test_eighth_registered_pdf_is_selectable_without_opening_unknown_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [{'id': 'source-' + str(index),
                        'media_type': 'application/pdf', 'sha256': 'a' * 64,
                        'bytes': 4, 'pages': 1} for index in range(1, 9)]
            inventory = {'schema': 'expertogobernanza/source-inventory/v1',
                         'sources': sources}
            inventory_raw = _canonical(inventory)
            (root / 'inventory.json').write_bytes(inventory_raw)
            entries = [{'source_id': source['id'],
                        'custody_policy_path': str(root / 'custody.json'),
                        'custody_material_id': source['id'],
                        'document_policy_path': str(root / 'document.json'),
                        'derivation_id': 'b' * 64,
                        'manifest_sha256': 'c' * 64} for source in sources]
            policy = {'schema': 'skopos/ctim-source-access-policy/v0.2',
                      'inventory_root': str(root),
                      'inventory_ref': 'inventory.json',
                      'inventory_sha256': hashlib.sha256(inventory_raw).hexdigest(),
                      'mongo_uri': 'mongodb://127.0.0.1:37034/',
                      'database': 'synthetic',
                      'socket_path': str(root / 'access.sock'),
                      'sources': entries}
            path = root / 'policy.json'
            path.write_bytes(_canonical(policy))
            loaded, indexed, _ = load_access_policy(path)
            self.assertEqual(len(indexed), 8)
            self.assertEqual(loaded['schema'], policy['schema'])
            gateway = AccessGateway(path, client=object())
            page = {'page_number': 1, 'page_width_points': 612,
                    'page_height_points': 792, 'page_rotation': 0,
                    'native_text': {'status': 'extracted', 'lines': []},
                    'ocr_text': {'status': 'not_run', 'lines': []}}
            gateway._source = lambda _id: (None, {'pages': [page]}, 4)
            request = {'request_id': 'eighth', 'operation': 'read_pdf_page',
                       'source_id': 'source-8', 'page_number': 1}
            self.assertEqual(gateway.handle(request)['status'], 'ok')
            request['source_id'] = 'source-9'
            rejected = gateway.handle(request)
            self.assertEqual(rejected['error']['code'], 'source_not_allowed')
            self.assertIsNone(rejected['result'])
            inventory['sources'].append({'id': 'source-9',
                                         'media_type': 'application/pdf',
                                         'sha256': 'a' * 64,
                                         'bytes': 4, 'pages': 1})
            expanded_raw = _canonical(inventory)
            (root / 'inventory.json').write_bytes(expanded_raw)
            policy['inventory_sha256'] = hashlib.sha256(expanded_raw).hexdigest()
            path.write_bytes(_canonical(policy))
            with self.assertRaisesRegex(AccessError, 'inventory_mismatch'):
                load_access_policy(path)
            inventory['sources'].pop()
            (root / 'inventory.json').write_bytes(inventory_raw)
            policy['inventory_sha256'] = hashlib.sha256(inventory_raw).hexdigest()
            policy['schema'] = 'skopos/ctim-source-access-policy/v0.1'
            for entry in entries:
                entry.pop('custody_material_id')
            path.write_bytes(_canonical(policy))
            with self.assertRaisesRegex(AccessError, 'policy_unavailable'):
                load_access_policy(path)
            policy['schema'] = 'skopos/ctim-source-access-policy/v0.2'
            for entry in entries:
                entry['custody_material_id'] = entry['source_id']
            inventory['sources'][7]['media_type'] = 'conversation'
            inventory_raw = _canonical(inventory)
            (root / 'inventory.json').write_bytes(inventory_raw)
            policy['inventory_sha256'] = hashlib.sha256(inventory_raw).hexdigest()
            path.write_bytes(_canonical(policy))
            with self.assertRaisesRegex(AccessError, 'inventory_mismatch'):
                load_access_policy(path)


if __name__ == '__main__':
    unittest.main()
