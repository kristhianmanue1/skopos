"""T4: invariantes reales sobre Mongo de pruebas, sin corpus del Operador."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import random
from copy import deepcopy
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from unittest import mock
import uuid

import pymongo
from pymongo.errors import PyMongoError, OperationFailure

from skopos.source_envelope import build_envelope
from skopos.source_reader import checksum
from skopos.source_store import SourceStore, read_source, MAX_FRAGMENT_BYTES
from skopos.source_cli import source_command

RAW = '[0.0 - 1.0] SPEAKER_UNKNOWN: miércoles antiguo\r\n'.encode()
NEW = '[0.0 - 1.0] SPEAKER_01: jueves corregido\n'.encode()
TIME = '2026-10-06T00:00:00Z'


class SourceBoundaryTests(unittest.TestCase):
    def test_product_envelope_matches_experimental_contract(self):
        from test_source_envelope import envelope
        args = dict(project_id='p', source_id='s', captured_at=TIME)
        self.assertEqual(build_envelope(RAW, **args), envelope.build_envelope(RAW, **args))

    def test_reader_regular_missing_directory_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.txt'
            path.write_bytes(RAW)
            self.assertEqual(read_source(path), RAW)
            link = Path(directory) / 'link'
            link.symlink_to(path)
            for invalid in (link, Path(directory), path.with_name('missing')):
                with self.subTest(path=invalid), self.assertRaises(ValueError):
                    read_source(invalid)

    def test_standalone_rejected_before_collection_writes(self):
        database = mock.MagicMock()
        database.get_collection.side_effect = [mock.MagicMock(), mock.MagicMock()]
        database.client.admin.command.return_value = {'logicalSessionTimeoutMinutes': 30}
        store = SourceStore(database)
        with self.assertRaisesRegex(ValueError, 'transactions_required'):
            store._prepare()
        store.revisions.create_index.assert_not_called()
        store.heads.create_index.assert_not_called()
        database.client.admin.command.return_value['setName'] = 'test'
        store._prepare()
        self.assertEqual(store.revisions.create_index.call_count, 1)

    def test_cli_failure_has_no_json_or_credentials(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch('skopos.source_cli.pymongo.MongoClient',
                        side_effect=PyMongoError('secret-password')), redirect_stdout(out), redirect_stderr(err):
            code = source_command(['--database', 'skopos_test', 'search', 'x',
                                   '--project-id', 'p'])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), '')
        self.assertNotIn('secret-password', err.getvalue())

    def test_help_does_not_connect_to_mongo(self):
        with mock.patch('skopos.source_cli.pymongo.MongoClient') as client:
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                source_command(['--help'])
            self.assertEqual(result.exception.code, 0)
            client.assert_not_called()


class SourceStoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017',
                                        serverSelectionTimeoutMS=1000)
        try:
            hello = cls.client.admin.command('hello')
        except PyMongoError:
            cls.client.close()
            raise unittest.SkipTest('Mongo de pruebas no disponible')
        if not hello.get('setName'):
            cls.client.close()
            raise unittest.SkipTest('T4 requiere replica set de pruebas')
        cls.database_name = 'skopos_test_sources_' + uuid.uuid4().hex
        cls.database = cls.client[cls.database_name]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.database_name)
        cls.client.close()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = 'p' + uuid.uuid4().hex
        self.store = SourceStore(self.database)
        self.path = Path(self.directory.name) / 'v1.txt'
        self.path.write_bytes(RAW)
        self.second = Path(self.directory.name) / 'v2.txt'
        self.second.write_bytes(NEW)

    def admit(self, path=None, revision=1, **overrides):
        args = dict(project_id=self.project, source_id='s', captured_at=TIME,
                    source_revision=revision)
        if revision > 1:
            args['expected_previous_sha256'] = checksum(RAW)
        args.update(overrides)
        return self.store.import_file(path or self.path, **args)

    def fetch(self, revision=1, digest=None):
        return self.store.fetch(project_id=self.project, source_id='s',
                                source_revision=revision, source_sha256=digest or checksum(RAW),
                                segment_id='segment-000001')

    def test_import_replay_correction_reopen_and_project_separation(self):
        first = self.admit()
        duplicate = self.admit(self.second.with_name('v1.txt'), captured_at='2026-10-07T00:00:00Z')
        self.assertEqual(first['status'], 'imported')
        self.assertEqual(duplicate, {**first, 'status': 'duplicate'})
        self.admit(self.second, revision=2)
        self.store = SourceStore(self.database)
        self.assertEqual(self.store.search(project_id=self.project, term='antiguo')['results'], [])
        current = self.store.search(project_id=self.project, term='corregido')['results']
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]['source_revision'], 2)
        self.assertEqual(self.fetch()['segment']['text'], 'miércoles antiguo')
        self.assertEqual(self.fetch(2, checksum(NEW))['segment']['text'], 'jueves corregido')
        self.assertEqual(self.store.search(project_id='other', term='corregido')['results'], [])
        self.admit(project_id='other')
        self.assertEqual(len(self.store.search(project_id='other', term='antiguo')['results']), 1)

    def test_replay_does_not_rebind_source_path(self):
        first = self.admit()
        copy = Path(self.directory.name) / 'copy.txt'
        copy.write_bytes(RAW)
        self.assertEqual(self.admit(copy)['status'], 'duplicate')
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, 'source_unavailable'):
            self.fetch()
        self.assertEqual(self.store.receipt(
            project_id=self.project, source_id='s', source_revision=1,
            source_sha256=checksum(RAW)), {**first, 'status': 'duplicate'})

    def test_receipt_replay_and_fetch_reject_corrupt_metadata(self):
        first = self.admit()
        original = self.store.revisions.find_one({'project_id': self.project})
        args = dict(project_id=self.project, source_id='s', source_revision=1,
                    source_sha256=checksum(RAW))
        for mutate, error in (
                (lambda d: d['envelope'].update(project_id='other'), 'store_integrity_failed'),
                (lambda d: d['envelope'].update(envelope_sha256='0'*64), 'envelope_integrity_failed'),
                (lambda d: d.pop('envelope'), 'store_integrity_failed'),
                (lambda d: d.update(schema='unknown'), 'store_integrity_failed')):
            damaged = deepcopy(original)
            mutate(damaged)
            self.store.revisions.replace_one({'_id': original['_id']}, damaged)
            for operation in (lambda: self.store.receipt(**args), self.admit, self.fetch):
                with self.subTest(error=error, operation=operation):
                    with self.assertRaisesRegex(ValueError, error):
                        operation()
            self.store.revisions.replace_one({'_id': original['_id']}, original)
            self.assertEqual(self.store.receipt(**args), {**first, 'status': 'duplicate'})
        self.path.unlink()
        self.assertEqual(self.store.receipt(**args)['status'], 'duplicate')

    def test_generated_histories_match_independent_revision_model(self):
        # Modelo: lista de revisiones; no usa _publish ni consultas del producto
        # para decidir el resultado esperado. Semillas fijas y subtests reproducibles.
        for seed in range(8):
            rng = random.Random(seed)
            source = 'model-' + str(seed)
            model = []
            for step in range(30):
                action = rng.choice(('new', 'replay', 'conflict', 'fetch')) if model else 'new'
                with self.subTest(seed=seed, step=step, action=action):
                    if action == 'new':
                        revision = len(model) + 1
                        text = 'token_%d_%d_end' % (seed, revision)
                        raw = ('[0.0 - 1.0] SPEAKER_01: ' + text + '\n').encode()
                        path = Path(self.directory.name) / ('%s-%d' % (source, revision))
                        path.write_bytes(raw)
                        result = self.admit(path, revision=revision, source_id=source,
                                            expected_previous_sha256=model[-1][1] if model else None)
                        self.assertEqual(result['status'], 'imported')
                        model.append((path, checksum(raw), text))
                    elif action == 'replay':
                        revision = rng.randint(1, len(model))
                        self.assertEqual(self.admit(
                            model[revision-1][0], revision=revision, source_id=source,
                            expected_previous_sha256=model[revision-2][1] if revision > 1 else None
                        )['status'], 'duplicate')
                    elif action == 'conflict':
                        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
                            self.admit(self.path, revision=1, source_id=source)
                    else:
                        revision = rng.randint(1, len(model))
                        result = self.store.fetch(project_id=self.project, source_id=source,
                            source_revision=revision, source_sha256=model[revision-1][1],
                            segment_id='segment-000001')
                        self.assertEqual(result['segment']['text'], model[revision-1][2])
                    found = self.store.search(project_id=self.project, term='token_%d_' % seed)
                    self.assertEqual([x['segment']['text'] for x in found['results']], [model[-1][2]])
                    self.assertEqual(self.store.revisions.count_documents(
                        {'project_id': self.project, 'source_id': source}), len(model))

    def test_all_pairs_newline_unicode_completeness_and_replay(self):
        # Producto cartesiano de 2x3x3 factores: cubre todos los pares y triples.
        import itertools
        for index, (newline, text, completeness) in enumerate(itertools.product(
                ('\n', '\r\n'), ('alpha', 'miércoles', '🙂 café'),
                ('unknown', 'partial', 'complete'))):
            with self.subTest(newline=newline, text=text, completeness=completeness):
                raw = ('[0.0 - 1.0] SPEAKER_UNKNOWN: ' + text + newline).encode()
                path = Path(self.directory.name) / ('pair-%d' % index)
                path.write_bytes(raw)
                args = dict(source_id='pair-%d' % index, capture_completeness=completeness,
                            completeness_basis=None if completeness == 'unknown' else 'fixture')
                self.assertEqual(self.admit(path, **args)['status'], 'imported')
                self.assertEqual(self.admit(path, **args)['status'], 'duplicate')
                result = self.store.fetch(project_id=self.project, source_id=args['source_id'],
                    source_revision=1, source_sha256=checksum(raw), segment_id='segment-000001')
                segment = result['segment']
                self.assertEqual(raw[segment['start_byte']:segment['end_byte']].decode(), text)

    def test_conflicts_cannot_advance_head(self):
        with self.assertRaisesRegex(ValueError, 'predecessor_conflict'):
            self.admit(self.second, revision=2)
        self.admit()
        for path, revision, args, error in (
                (self.second, 1, {}, 'revision_conflict'),
                (self.second, 3, {}, 'predecessor_conflict'),
                (self.second, 2, {'expected_previous_sha256': 'a' * 64}, 'predecessor_conflict')):
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, error):
                self.admit(path, revision, **args)
        self.assertEqual(self.store.heads.find_one({'project_id': self.project})['source_revision'], 1)

    def test_race_same_parent_has_one_winner(self):
        self.admit()
        third = Path(self.directory.name) / 'other.txt'
        third.write_bytes(NEW.replace(b'jueves', b'viernes'))
        barrier = Barrier(2)
        def writer(path):
            barrier.wait(timeout=5)
            try:
                return self.admit(path, revision=2)['status']
            except ValueError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(writer, (self.second, third)))
        self.assertCountEqual(outcomes, ['imported', 'revision_conflict'])
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 2)

    def test_race_first_admission_is_idempotent(self):
        self.store._prepare()
        barrier = Barrier(2)
        def writer(_):
            barrier.wait(timeout=5)
            return self.admit()['status']
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(writer, range(2))), ['imported', 'duplicate'])
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 1)

    def test_interruption_between_insert_and_head_rolls_back(self):
        self.admit()
        with mock.patch.object(self.store.heads, 'replace_one', side_effect=RuntimeError('cut')):
            with self.assertRaisesRegex(RuntimeError, 'cut'):
                self.admit(self.second, revision=2)
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 1)
        self.assertEqual(self.store.heads.find_one({'project_id': self.project})['source_revision'], 1)
        self.assertEqual(self.admit(self.second, revision=2)['status'], 'imported')

    def test_driver_retries_callback_without_duplicate_publication(self):
        publish = self.store._publish
        calls = []
        def transient_after_publish(document, session):
            result = publish(document, session)
            calls.append(result['status'])
            if len(calls) == 1:
                raise OperationFailure('fallo transitorio sintético', code=251,
                    details={'errorLabels': ['TransientTransactionError']})
            return result
        with mock.patch.object(self.store, '_publish', side_effect=transient_after_publish):
            self.assertEqual(self.admit()['status'], 'imported')
        self.assertEqual(calls, ['imported', 'imported'])
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 1)
        self.assertEqual(self.fetch()['status'], 'transcript_bytes_verified')

    def test_lost_ack_reconciled_without_duplicate_or_original(self):
        original = self.store.import_file
        def lose_ack(*args, **kwargs):
            original(*args, **kwargs)
            raise ConnectionError('ack_lost')
        with mock.patch.object(self.store, 'import_file', side_effect=lose_ack):
            with self.assertRaises(ConnectionError):
                self.admit()
        self.assertEqual(self.admit()['status'], 'duplicate')
        self.path.unlink()
        self.assertEqual(self.store.receipt(
            project_id=self.project, source_id='s', source_revision=1,
            source_sha256=checksum(RAW))['status'], 'duplicate')

    def test_unavailable_modified_and_denied_do_not_serve_text(self):
        self.admit()
        self.path.write_bytes(NEW)
        with self.assertRaisesRegex(ValueError, 'source_integrity_failed'):
            self.fetch()
        result = self.store.search(project_id=self.project, term='antiguo')
        self.assertEqual(result['results'], [])
        self.assertEqual(result['unavailable_sources'], {'source_integrity_failed': 1})
        self.path.write_bytes(RAW)
        self.assertEqual(self.fetch()['status'], 'transcript_bytes_verified')
        with mock.patch('skopos.source_store.os.open', side_effect=PermissionError):
            with self.assertRaisesRegex(ValueError, 'source_unavailable'):
                self.fetch()
        self.path.unlink()
        self.assertEqual(self.store.search(project_id=self.project, term='x')['unavailable_sources'],
                         {'source_unavailable': 1})

    def test_tampered_envelope_is_not_served(self):
        self.admit()
        self.store.revisions.update_one({'project_id': self.project},
                                        {'$set': {'envelope.segments.0.text': 'forged'}})
        with self.assertRaisesRegex(ValueError, 'envelope_integrity_failed'):
            self.fetch()
        self.assertEqual(self.store.search(project_id=self.project, term='forged')['results'], [])

    def test_explicit_revision_and_hash_are_mandatory_for_fetch(self):
        self.admit()
        for revision, digest, error in ((2, checksum(RAW), 'revision_not_found'),
                                        (1, 'a' * 64, 'revision_conflict'),
                                        (True, checksum(RAW), 'invalid_source_revision')):
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, error):
                self.fetch(revision, digest)

    def test_reads_do_not_bootstrap_or_require_llm(self):
        self.admit()
        with mock.patch.object(self.store, '_prepare', side_effect=AssertionError('write')):
            with mock.patch('skopos.analisis.analizar_turno', side_effect=AssertionError('llm')):
                self.assertEqual(self.fetch()['status'], 'transcript_bytes_verified')
                self.assertEqual(len(self.store.search(project_id=self.project, term='antiguo')
                                     ['results']), 1)

    def test_output_limits_and_oversize_fragments_are_counted(self):
        self.path.write_bytes(b'[0.0 - 1.0] SPEAKER_01: match\n' * 21)
        self.admit()
        result = self.store.search(project_id=self.project, term='match')
        self.assertEqual(len(result['results']), 20)
        self.assertEqual(result['excluded']['result_limit'], 1)
        self.assertEqual(self.store.search(project_id=self.project, term='match', limit=0)
                         ['excluded']['result_limit'], 21)
        self.second.write_bytes(b'[0.0 - 1.0] SPEAKER_01: ' + b'x' * (MAX_FRAGMENT_BYTES - 2048))
        self.admit(self.second, source_id='large')
        result = self.store.search(project_id=self.project, term='xxx')
        self.assertEqual(len(result['results']), 1)
        self.assertLessEqual(len(json.dumps(result['results'][0], ensure_ascii=False,
                                            separators=(',', ':')).encode()), MAX_FRAGMENT_BYTES)
        self.second.write_bytes(b'[0.0 - 1.0] SPEAKER_01: ' + b'x' * MAX_FRAGMENT_BYTES)
        self.admit(self.second, source_id='larger')
        result = self.store.search(project_id=self.project, term='xxx')
        self.assertEqual(result['excluded']['fragment_too_large'], 1)
        for invalid in (-1, 21, True):
            with self.assertRaisesRegex(ValueError, 'invalid_limit'):
                self.store.search(project_id=self.project, term='x', limit=invalid)

    def test_bson_limit_and_integer_overflow_fail_before_publication(self):
        self.admit()
        with mock.patch('skopos.source_store.MAX_BSON_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'source_record_too_large'):
                self.admit(self.second, source_id='large')
        self.second.write_bytes(b'[0.0 - 999999999999999999999.0] SPEAKER_01: x')
        with self.assertRaisesRegex(ValueError, 'source_record_not_encodable'):
            self.admit(self.second, source_id='overflow')
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 1)

    def test_large_metadata_cannot_bypass_fragment_budget(self):
        self.path.write_bytes(b'[0.0 - 1.0] SPEAKER_' + b'1' * MAX_FRAGMENT_BYTES + b': tiny')
        self.admit()
        result = self.store.search(project_id=self.project, term='tiny')
        self.assertEqual(result['results'], [])
        self.assertEqual(result['excluded']['fragment_too_large'], 1)

    def test_exact_fragment_boundaries_and_result_limits(self):
        self.admit()
        document = self.store.revisions.find_one({'project_id': self.project})
        segment = document['envelope']['segments'][0]
        fragment = self.store._fragment(document, segment, RAW)
        size = len(json.dumps(fragment, ensure_ascii=False, separators=(',', ':')).encode())
        for budget in (size - 1, size, size + 1):
            with self.subTest(budget=budget), mock.patch(
                    'skopos.source_store.MAX_FRAGMENT_BYTES', budget):
                if budget < size:
                    with self.assertRaisesRegex(ValueError, 'fragment_too_large'):
                        self.store._fragment(document, segment, RAW)
                else:
                    self.assertEqual(self.store._fragment(document, segment, RAW), fragment)
        for count in (19, 20, 21):
            path = Path(self.directory.name) / ('limit-%d' % count)
            path.write_bytes(b'[0.0 - 1.0] SPEAKER_01: boundary\n' * count)
            project = 'boundary-' + uuid.uuid4().hex
            self.admit(path, project_id=project)
            result = self.store.search(project_id=project, term='boundary')
            self.assertEqual(len(result['results']), min(count, 20))
            self.assertEqual(result['excluded']['result_limit'], max(0, count - 20))

    def test_corrupt_head_cannot_cross_project(self):
        self.admit()
        self.admit(project_id='other-scope')
        self.store.heads.update_one({'project_id': self.project},
                                   {'$set': {'revision_key': 'other-scope:s:1'}})
        with self.assertRaisesRegex(ValueError, 'store_integrity_failed'):
            self.store.search(project_id=self.project, term='antiguo')

    def test_cli_json_and_v2_collections_unchanged(self):
        sentinel = {'_id': self.project, 'turn_id': 'legacy', 'version': 2,
                    'tema': 'fixture', 'resumen': 'unchanged'}
        self.database.analisis.insert_one(sentinel)
        before = self.database.analisis.find_one({'_id': self.project})
        out = io.StringIO()
        with redirect_stdout(out):
            result = source_command([
                '--database', self.database_name, 'import', str(self.path),
                '--project-id', self.project, '--source-id', 's', '--revision', '1',
                '--captured-at', TIME])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'imported')
        self.assertEqual(before, self.database.analisis.find_one({'_id': self.project}))
        self.assertNotIn('source_revision', before)
