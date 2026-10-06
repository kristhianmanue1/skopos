"""Almacén experimental contra Mongo temporal, con fuentes sintéticas propias."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch, MagicMock
import uuid

import pymongo
from bson.int64 import Int64
from test_runtime_verification import load, verification, views, seal
from test_runtime_envelope import envelope, reader, message, source

store_module = load('store', {'envelope': envelope, 'reader': reader,
                              'verification': verification, 'views': views})
LaboratoryStore = store_module.LaboratoryStore
TIME = '2026-10-05T00:00:00Z'


class RuntimeLaboratoryBoundaryTests(unittest.TestCase):
    def test_bson_normalization_does_not_coerce_json_types(self):
        original = {'nested': [Int64(2**40), True, 1.5, '7']}
        normalized = store_module.json_integers(original)
        self.assertIs(type(normalized['nested'][0]), int)
        self.assertIs(type(original['nested'][0]), Int64)
        self.assertIs(normalized['nested'][1], True)
        self.assertEqual(normalized['nested'][2:], [1.5, '7'])

    def test_database_and_endpoint_guards(self):
        database = MagicMock()
        database.name = 'production'
        with self.assertRaisesRegex(ValueError, '^laboratory_database_required$'):
            LaboratoryStore(database)
        database.name = 'skopos_test_guard'
        for address in [('127.0.0.1', 27017), ('remote.example', 37027)]:
            database.client.address = address
            with self.assertRaisesRegex(ValueError, '^laboratory_endpoint_required$'):
                LaboratoryStore(database)
        database.client.address = ('127.0.0.1', 37027)
        LaboratoryStore(database)


class RuntimeStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=1000)
        try:
            hello = cls.client.admin.command('hello')
            if not hello.get('setName') or cls.client.address[1] == 27017:
                raise ValueError('Instancia temporal requerida')
        except (pymongo.errors.PyMongoError, ValueError):
            cls.client.close()
            raise unittest.SkipTest('Ejecutar mediante run_isolated_tests en replica set temporal')
        cls.database = cls.client['skopos_test_runtime_' + uuid.uuid4().hex]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.database.name)
        cls.client.close()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = 'p' + uuid.uuid4().hex
        self.store = LaboratoryStore(self.database)
        self.raw = source(message(), message(1, True))
        self.path = Path(self.directory.name) / 'runtime.jsonl'
        self.path.write_bytes(self.raw)

    def import_runtime(self, **kwargs):
        args = dict(project_id=self.project, source_id='runtime', captured_at=TIME,
                    source_format='dsh-session-v0-jsonl')
        args.update(kwargs)
        return self.store.import_file(self.path, **args)

    def fetch(self, receipt, **kwargs):
        args = {k: receipt[k] for k in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        args.update(view='text_projection', text_id='event-0-block-0')
        args.update(kwargs)
        return self.store.fetch_runtime(**args)

    def test_import_replay_receipt_and_file_fetch(self):
        first = self.import_runtime()
        self.assertEqual(first['status'], 'imported')
        replay = self.import_runtime(captured_at='2026-10-06T00:00:00Z')
        self.assertEqual(replay, {**first, 'status': 'duplicate'})
        self.assertEqual(self.fetch(first)['projection']['text'], 'á終')
        identity = {k: first[k] for k in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        self.path.unlink()
        self.assertEqual(self.store.receipt(**identity), replay)
        with self.assertRaisesRegex(ValueError, '^source_unavailable$'):
            self.fetch(first)

    def test_large_json_times_survive_bson_roundtrip(self):
        events = [message(), message(1, True)]
        events[0]['time'], events[1]['time'] = 2**40, -(2**40)
        self.raw = source(*events)
        self.path.write_bytes(self.raw)
        first = self.import_runtime()
        document = self.store.revisions.find_one({'project_id': self.project})
        self.assertIs(type(document['envelope']['events'][0]['time']), Int64)
        verified = self.store._verified_envelope(document)
        verification.verify(verified, self.raw)
        self.assertEqual(self.import_runtime(), {**first, 'status': 'duplicate'})
        self.assertEqual(self.fetch(first)['projection']['text'], 'á終')
        self.assertEqual(len(self.store.search_runtime(project_id=self.project, term='á')['results']), 2)
        identity = {k: first[k] for k in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        self.assertEqual(self.store.receipt(**identity)['status'], 'duplicate')
        self.store.heads.update_one({'project_id': self.project}, {'$set': {'source_revision': Int64(1)}})
        self.store.revisions.update_one({'project_id': self.project},
                                       {'$set': {'source_revision': Int64(1), 'envelope.source_revision': Int64(1)}})
        self.assertEqual(len(self.store.search_runtime(project_id=self.project, term='á')['results']), 2)
        corrupted = deepcopy(document)
        corrupted['envelope']['events'][0]['time'] = True
        with self.assertRaises(ValueError):
            self.store._verified_envelope(corrupted)

    def test_mixed_sources_and_crossed_fetch(self):
        runtime = self.import_runtime()
        txt = Path(self.directory.name) / 'meeting.txt'
        txt.write_bytes('[0.0 - 1.0] SPEAKER_00: reunión\n'.encode())
        a = self.store.import_file(txt, project_id=self.project, source_id='txt', captured_at=TIME)
        asr = Path(self.directory.name) / 'meeting.json'
        asr.write_text(json.dumps({'segments':[{'start':0,'end':1,'text':'reunión','words':[]}]}))
        self.store.import_file(asr, project_id=self.project, source_id='asr', captured_at=TIME,
                               source_format='whisperx-json')
        found = self.store.search(project_id=self.project, term='reunión')
        self.assertEqual(len(found['results']), 2)
        self.assertEqual(found['excluded_source_kinds'], {'runtime-events': 1})
        found = self.store.search_runtime(project_id=self.project, term='á')
        self.assertEqual(len(found['results']), 2)
        self.assertEqual(found['excluded_source_kinds'], {'meeting-transcript': 2})
        with self.assertRaisesRegex(ValueError, '^source_kind_conflict$'):
            self.fetch(a)
        with self.assertRaisesRegex(ValueError, '^source_kind_conflict$'):
            self.store.fetch(**{k:runtime[k] for k in ('project_id','source_id','source_revision','source_sha256')}, segment_id='x')

    def test_revision_current_search_and_historical_fetch(self):
        first = self.import_runtime()
        next_path = Path(self.directory.name) / 'next.jsonl'
        next_path.write_bytes(source(message(content=[{'type':'text','text':'replacement'}])))
        self.store.import_file(next_path, project_id=self.project, source_id='runtime', captured_at=TIME,
                               source_format='dsh-session-v0-jsonl', source_revision=2,
                               expected_previous_sha256=first['source_sha256'])
        self.assertEqual(self.store.search_runtime(project_id=self.project, term='á')['results'], [])
        self.assertEqual(self.fetch(first)['projection']['text'], 'á終')

    def test_family_change_rejected_without_advancing_head(self):
        first = self.import_runtime()
        txt = Path(self.directory.name) / 'meeting.txt'
        txt.write_bytes(b'[0.0 - 1.0] SPEAKER_00: test\n')
        with self.assertRaisesRegex(ValueError, '^source_kind_conflict$'):
            self.store.import_file(txt, project_id=self.project, source_id='runtime', captured_at=TIME,
                                   source_revision=2, expected_previous_sha256=first['source_sha256'])
        self.assertEqual(self.store.heads.find_one({'project_id':self.project})['source_revision'], 1)
        self.assertEqual(self.store.revisions.count_documents({'project_id':self.project}), 1)

    def test_missing_modified_restored_source(self):
        first = self.import_runtime()
        for content, error in [(None, 'source_unavailable'), (self.raw+b' ', 'source_integrity_failed')]:
            if content is None:
                self.path.unlink()
            else:
                self.path.write_bytes(content)
            found = self.store.search_runtime(project_id=self.project, term='á')
            self.assertEqual(found['results'], [])
            self.assertEqual(found['unavailable_sources'], {error:1})
        self.path.write_bytes(self.raw)
        self.assertEqual(len(self.store.search_runtime(project_id=self.project, term='á')['results']), 2)
        self.fetch(first)

    def test_resealed_last_projection_rejects_entire_source(self):
        first = self.import_runtime()
        original = self.store.revisions.find_one({'project_id':self.project})
        corrupt = deepcopy(original)
        text = corrupt['envelope']['texts'][-1]
        text['text'] = 'forged'
        text['derived_text_sha256'] = verification.checksum(b'forged')
        seal(corrupt['envelope'])
        self.store.revisions.replace_one({'_id':original['_id']}, corrupt)
        found = self.store.search_runtime(project_id=self.project, term='á')
        self.assertEqual(found['results'], [])
        self.assertEqual(found['unavailable_sources'], {'runtime_derivation_mismatch':1})
        with self.assertRaisesRegex(ValueError, '^runtime_derivation_mismatch$'):
            self.fetch(first)
        self.store.revisions.replace_one({'_id':original['_id']}, original)
        self.fetch(first)

    def test_transaction_failure_rolls_back_revision(self):
        first = self.import_runtime()
        with patch.object(self.store.heads, 'replace_one', side_effect=RuntimeError('synthetic interruption')):
            with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
                self.import_runtime(source_revision=2, expected_previous_sha256=first['source_sha256'])
        self.assertEqual(self.store.revisions.count_documents({'project_id':self.project}), 1)
        self.assertEqual(self.store.heads.find_one({'project_id':self.project})['source_revision'], 1)
        self.assertEqual(self.import_runtime(source_revision=2, expected_previous_sha256=first['source_sha256'])['status'], 'imported')

    def test_concurrent_revision_candidates_one_winner(self):
        first = self.import_runtime()
        barrier = Barrier(2)
        def attempt(index):
            path = Path(self.directory.name) / ('candidate-%d.jsonl' % index)
            path.write_bytes(source(message(content=[{'type':'text','text':str(index)}])))
            barrier.wait(timeout=10)
            try:
                return self.store.import_file(path, project_id=self.project, source_id='runtime', captured_at=TIME,
                                               source_format='dsh-session-v0-jsonl', source_revision=2,
                                               expected_previous_sha256=first['source_sha256'])['status']
            except ValueError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, [1,2]))
        self.assertCountEqual(outcomes, ['imported','revision_conflict'])
        self.assertEqual(self.store.revisions.count_documents({'project_id':self.project}), 2)

    def test_bson_budget_rejects_before_writing(self):
        with patch.object(store_module, 'MAX_BSON_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '^source_record_too_large$'):
                self.import_runtime()
        self.assertEqual(self.store.revisions.count_documents({'project_id':self.project}), 0)
        self.import_runtime()

    def test_search_limit_zero_and_bad_head(self):
        self.import_runtime()
        found = self.store.search_runtime(project_id=self.project, term='á', limit=0)
        self.assertEqual(found['results'], [])
        self.assertEqual(found['excluded']['result_limit'], 2)
        self.store.heads.update_one({'project_id':self.project}, {'$set':{'revision_key':'wrong'}})
        with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
            self.store.search_runtime(project_id=self.project, term='á')

    def test_global_limit_counts_multiple_sources(self):
        self.import_runtime(source_id='a')
        self.import_runtime(source_id='b')
        found = self.store.search_runtime(project_id=self.project, term='á', limit=1)
        self.assertEqual(len(found['results']), 1)
        self.assertEqual(found['results'][0]['source_id'], 'a')
        self.assertEqual(found['excluded']['result_limit'], 3)

    def test_record_envelope_identity_mismatch_aborts(self):
        self.import_runtime()
        doc = self.store.revisions.find_one({'project_id': self.project})
        doc['envelope']['project_id'] = 'foreign'
        seal(doc['envelope'])
        self.store.revisions.replace_one({'_id':doc['_id']}, doc)
        with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
            self.store.search_runtime(project_id=self.project, term='á')

    def test_runtime_search_does_not_open_other_family_original(self):
        self.import_runtime()
        txt = Path(self.directory.name) / 'missing-after-import.txt'
        txt.write_bytes(b'[0.0 - 1.0] SPEAKER_00: test\n')
        self.store.import_file(txt, project_id=self.project, source_id='txt', captured_at=TIME)
        txt.unlink()
        result = self.store.search_runtime(project_id=self.project, term='á')
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['unavailable_sources'], {})
        self.assertEqual(result['excluded_source_kinds'], {'meeting-transcript': 1})


if __name__ == '__main__':
    unittest.main()
