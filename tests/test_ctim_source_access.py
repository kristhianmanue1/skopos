"""Controles del contrato de consulta CTIM, sin Mongo ni originales privados."""

import unittest

from skopos.ctim_source_access import AccessError, AccessGateway


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
        page = {'page_number': 1,
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


if __name__ == '__main__':
    unittest.main()
