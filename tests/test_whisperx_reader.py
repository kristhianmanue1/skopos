"""Contrato JSON ASR: datos sintéticos, sin acceso a la reunión privada."""
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import pymongo

from skopos.whisperx_reader import parse, load_json
from skopos.source_envelope import build_envelope
from skopos.source_reader import checksum
from skopos.source_store import SourceStore

TIME = '2026-10-06T00:00:00Z'


def fixture(text='miércoles 🙂', **fields):
    return {'start': 0.0, 'end': 1.0, 'text': text, 'words': [], **fields}


def raw_source(*segments, **kwargs):
    return json.dumps({'segments': list(segments)}, **kwargs).encode()


class JsonReaderTests(unittest.TestCase):
    def test_cli_passes_explicit_format_without_network(self):
        from skopos.source_cli import source_command
        with patch('skopos.source_cli.pymongo.MongoClient'), \
                patch('skopos.source_cli.SourceStore') as factory, redirect_stdout(io.StringIO()):
            factory.return_value.import_file.return_value = {'status': 'imported'}
            code = source_command(['--database', 'skopos_test', 'import', '/synthetic.json',
                '--format', 'whisperx-json', '--project-id', 'p', '--source-id', 's',
                '--revision', '1', '--captured-at', TIME])
            self.assertEqual(code, 0)
            self.assertEqual(factory.return_value.import_file.call_args.kwargs['source_format'],
                             'whisperx-json')

    def test_original_spans_unicode_escaping_order_and_newlines(self):
        for ascii_only in (True, False):
            for indent in (None, 2):
                raw = json.dumps({'metadata': '🙂 segments fake',
                    'segments': [fixture(), fixture('repetido')], 'tail': {}},
                    ensure_ascii=ascii_only, indent=indent).replace('\n', '\r\n').encode()
                result = parse(raw)
                for index, segment in enumerate(result['segments']):
                    locator = segment['locator']
                    original = raw[locator['start_byte']:locator['end_byte']]
                    self.assertEqual(json.loads(original)['text'], segment['text'])
                    self.assertEqual(checksum(original), locator['sha256'])
                    self.assertEqual(locator['pointer'], '/segments/%d' % index)
                    self.assertNotEqual(original, segment['text'].encode())
                self.assertEqual(result['source_sha256'], checksum(raw))

    def test_missing_speaker_and_word_times_preserved_without_inference(self):
        word = {'word': 'hola'}
        result = parse(raw_source(fixture(words=[word])))['segments'][0]
        self.assertIsNone(result['speaker'])
        self.assertEqual(result['word_count'], 1)

    def test_flat_word_list_must_match_nested(self):
        word = {'word': 'hola', 'start': 0, 'end': 0, 'score': 1}
        data = {'segments': [fixture(words=[word])], 'word_segments': [word]}
        self.assertEqual(len(parse(json.dumps(data).encode())['segments']), 1)
        data['word_segments'] = []
        with self.assertRaisesRegex(ValueError, 'word_segments_mismatch'):
            parse(json.dumps(data).encode())
        data['word_segments'] = [{**word, 'start': False}]
        with self.assertRaisesRegex(ValueError, 'word_segments_mismatch'):
            parse(json.dumps(data).encode())

    def test_strict_json_rejections_with_positive_controls(self):
        for raw in (b'{"a":1,"a":2}', b'[NaN]', b'[Infinity]', b'[1e999]',
                    b'["\\ud800"]', b'["\xff"]', b'\xef\xbb\xbf{}',
                    b'{', b'{} trailing', b'[' * 65 + b']' * 65):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_json(raw)
        self.assertEqual(load_json(b'{"a":1}'), {'a': 1})
        self.assertEqual(load_json(b'["\\ud83d\\ude42"]'), ['🙂'])
        nested = load_json(b'[' * 64 + b'0' + b']' * 64)
        for _ in range(64):
            nested = nested[0]
        self.assertEqual(nested, 0)

    def test_schema_rejects_bad_types_and_intervals(self):
        for fields in ({'start': True}, {'start': -1}, {'end': 0}, {'text': ' '},
                       {'words': {}}, {'speaker': 1}, {'speaker': ''}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                parse(raw_source(fixture(**fields)))
        for root in ([], {}, {'segments': []}, {'segments': [None]}):
            with self.assertRaises(ValueError):
                parse(json.dumps(root).encode())
        self.assertEqual(len(parse(raw_source(fixture()))['segments']), 1)

    def test_word_validation(self):
        for word in ({'word': ''}, {'word': 'a', 'start': 0},
                     {'word': 'a', 'start': 1, 'end': 0},
                     {'word': 'a', 'score': True}, {'word': 'a', 'score': 1.1},
                     {'word': 'a', 'speaker': 3}):
            with self.subTest(word=word), self.assertRaises(ValueError):
                parse(raw_source(fixture(words=[word])))

    def test_limits_exact_and_excess(self):
        raw = raw_source(fixture(words=[{'word': 'x'}]))
        for budget, okay in ((len(raw)-1, False), (len(raw), True)):
            with patch('skopos.whisperx_reader.MAX_BYTES', budget):
                if okay:
                    parse(raw)
                else:
                    with self.assertRaisesRegex(ValueError, 'source_size_out_of_range'):
                        parse(raw)
        with patch('skopos.whisperx_reader.MAX_SEGMENTS', 1):
            parse(raw)
            with self.assertRaisesRegex(ValueError, 'segment_limit_exceeded'):
                parse(raw_source(fixture(), fixture()))
        with patch('skopos.whisperx_reader.MAX_WORDS', 1):
            parse(raw)
            with self.assertRaisesRegex(ValueError, 'word_limit_exceeded'):
                parse(raw_source(fixture(words=[{'word':'x'}, {'word':'y'}])))

    def test_envelope_explicit_version_and_default_txt(self):
        raw = raw_source(fixture())
        args = dict(project_id='p', source_id='s', captured_at=TIME)
        result = build_envelope(raw, **args, source_format='whisperx-json')
        self.assertEqual(result['schema'], 'skopos/source-envelope/v1')
        self.assertEqual(result['capture_completeness']['value'], 'unknown')
        with self.assertRaises(ValueError):
            build_envelope(raw, **args)
        with self.assertRaisesRegex(ValueError, 'unsupported_source_format'):
            build_envelope(raw, **args, source_format='guess')
        txt = build_envelope(b'[0.0 - 1.0] SPEAKER_UNKNOWN: hola', **args)
        self.assertEqual(txt['schema'], 'skopos/source-envelope/v0')


class JsonStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=1000)
        try:
            hello = cls.client.admin.command('hello')
        except pymongo.errors.PyMongoError:
            cls.client.close()
            raise unittest.SkipTest('Mongo temporal no disponible')
        if not hello.get('setName'):
            cls.client.close()
            raise unittest.SkipTest('Se requiere replica set temporal')
        cls.db = cls.client['skopos_test_json_' + uuid.uuid4().hex]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db.name)
        cls.client.close()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'source.json'
        self.raw = raw_source(fixture('antiguo 🙂'))
        self.path.write_bytes(self.raw)
        self.project = 'p' + uuid.uuid4().hex
        self.store = SourceStore(self.db)

    def admit(self, **overrides):
        args = dict(project_id=self.project, source_id='json', captured_at=TIME,
                    source_format='whisperx-json')
        args.update(overrides)
        return self.store.import_file(self.path, **args)

    def fetch(self):
        return self.store.fetch(project_id=self.project, source_id='json', source_revision=1,
                                source_sha256=checksum(self.raw), segment_id='segment-000001')

    def test_replay_fetch_history_and_current_revision(self):
        first = self.admit()
        self.assertEqual(self.admit(), {**first, 'status': 'duplicate'})
        fragment = self.fetch()
        self.assertEqual(fragment['status'], 'json_bytes_verified')
        self.assertEqual(json.loads(fragment['original_json'])['text'], 'antiguo 🙂')
        self.assertIsNone(fragment['segment']['speaker'])
        old_path = self.path
        self.path = old_path.with_name('new.json')
        self.path.write_bytes(raw_source(fixture('nuevo')))
        self.admit(source_revision=2, expected_previous_sha256=checksum(self.raw))
        self.assertEqual(self.store.search(project_id=self.project, term='antiguo')['results'], [])
        self.assertEqual(len(self.store.search(project_id=self.project, term='nuevo')['results']), 1)
        self.assertEqual(self.fetch(), fragment)

    def test_source_integrity_rejection_and_positive_restore(self):
        self.admit()
        self.path.write_bytes(self.raw + b' ')
        with self.assertRaisesRegex(ValueError, 'source_integrity_failed'):
            self.fetch()
        self.assertEqual(self.store.search(project_id=self.project, term='antiguo')['results'], [])
        self.path.write_bytes(self.raw)
        self.assertEqual(self.fetch()['status'], 'json_bytes_verified')

    def test_output_budget_includes_original_json_and_rejection_is_atomic(self):
        self.admit()
        with patch('skopos.source_store.MAX_FRAGMENT_BYTES', 100):
            result = self.store.search(project_id=self.project, term='antiguo')
            self.assertEqual(result['results'], [])
            self.assertEqual(result['excluded']['fragment_too_large'], 1)
        self.path.write_bytes(b'{"segments":NaN}')
        with self.assertRaises(ValueError):
            self.admit(source_id='invalid')
        self.assertEqual(self.store.revisions.count_documents({'project_id': self.project}), 1)
