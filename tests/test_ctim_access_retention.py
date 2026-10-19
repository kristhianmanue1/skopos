"""Retención de pares servidos: escritura canónica, colisión y revalidación."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from skopos.ctim_access_retention import (
    load_served_pair, retain_served_pair)
from skopos.ctim_source_access import (
    AccessError, _canonical, _sha, load_access_policy)


def pair(name='imss-p15'):
    request = {'request_id': name, 'operation': 'read_pdf_page',
               'source_id': 'imss-procedure-2900-003-001-2021',
               'page_number': 15}
    response = {'schema': 'skopos/ctim-source-access/v0.2', 'status': 'ok',
                'request_id': name, 'result': {'page_number': 15}, 'error': None}
    return request, response


class ServedPairRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'served'

    def test_retains_canonical_pair_with_hashes(self):
        request, response = pair()
        record = retain_served_pair(self.directory, request, response)
        self.assertEqual(record['request_sha256'], _sha(_canonical(request)))
        self.assertEqual(record['response_sha256'], _sha(_canonical(response)))
        raw = Path(record['path']).read_bytes()
        stored = json.loads(raw)
        self.assertEqual(stored['schema'], 'skopos/ctim-served-pair/v0.1')
        self.assertEqual(stored['request'], request)

    def test_collision_fails_closed_without_overwrite(self):
        request, response = pair()
        retain_served_pair(self.directory, request, response)
        with self.assertRaises(AccessError) as caught:
            retain_served_pair(self.directory, *pair())
        self.assertEqual(caught.exception.code, 'retention_collision')

    def test_invalid_identity_is_refused(self):
        with self.assertRaises(AccessError) as caught:
            retain_served_pair(self.directory, {'request_id': 'x y'}, {})
        self.assertEqual(caught.exception.code, 'retention_invalid_pair')

    def test_load_revalidates_and_detects_drift(self):
        request, response = pair()
        record = retain_served_pair(self.directory, request, response)
        reloaded = load_served_pair(self.directory, 'imss-p15')
        self.assertEqual(reloaded['response'], response)
        path = Path(record['path'])
        tampered = json.loads(path.read_bytes())
        tampered['response']['status'] = 'tampered'
        path.write_bytes(_canonical(tampered) + b'\n')
        with self.assertRaises(AccessError) as caught:
            load_served_pair(self.directory, 'imss-p15')
        self.assertEqual(caught.exception.code, 'retention_pair_drift')

    def test_missing_pair_fails_closed(self):
        with self.assertRaises(AccessError) as caught:
            load_served_pair(self.directory, 'absent')
        self.assertEqual(caught.exception.code, 'retention_pair_not_found')

    def test_policy_accepts_optional_served_retention_dir(self):
        root = Path(self.temp.name)
        inventory = {'schema': 'expertogobernanza/source-inventory/v1',
                     'sources': [{'id': 'source-a', 'media_type': 'text/html',
                                  'sha256': 'b' * 64, 'bytes': 4}]}
        inventory_path = root / 'inventory.json'
        inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        policy = {'schema': 'skopos/ctim-source-access-policy/v0.2',
                  'inventory_root': str(root), 'inventory_ref': 'inventory.json',
                  'inventory_sha256': _sha(inventory_path.read_bytes()),
                  'mongo_uri': 'mongodb://127.0.0.1:37034/?replicaSet=x',
                  'database': 'skopos_test', 'socket_path': str(root / 'a.sock'),
                  'sources': [{'source_id': 'source-a',
                               'custody_policy_path': str(root / 'custody.json'),
                               'derivative_path': str(root / 'derivative.txt'),
                               'derivative_sha256': 'c' * 64}],
                  'served_retention_dir': str(root / 'served')}
        path = root / 'policy.json'
        path.write_text(json.dumps(policy), encoding='utf-8')
        try:
            loaded, _, _ = load_access_policy(path)
        except AccessError as error:
            if error.code == 'policy_unavailable':
                raise AssertionError('clave opcional rechazada') from None
            raise
        self.assertEqual(loaded['served_retention_dir'], str(root / 'served'))
        del policy['served_retention_dir']
        path.write_text(json.dumps(policy), encoding='utf-8')
        loaded, _, _ = load_access_policy(path)
        self.assertNotIn('served_retention_dir', loaded)
        policy['served_retention_dir'] = 'relative/path'
        path.write_text(json.dumps(policy), encoding='utf-8')
        with self.assertRaises(AccessError):
            load_access_policy(path)


if __name__ == '__main__':
    unittest.main()
