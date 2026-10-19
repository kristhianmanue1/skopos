"""Contrato source-consumer-access v0.1: carga fail-closed y frontera de lectura.

Pruebas puras (sin Mongo) para el loader y el guard con un almacén que
registra sus llamadas — el rechazo debe ocurrir sin tocar el almacén, que es
la única ruta a la base, de modo que no se filtra contenido ni existencia.
La integración sobre Mongo real corre sólo bajo el runner aislado.
"""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import uuid

import test_runtime_store as base
from skopos.consumer_access import (
    POLICY_SCHEMA, ConsumerAccessStore, load_consumer_policy)
from skopos.source_cli import source_command

ALLOWED = 'pilot-cedro'
OTHER = 'pilot-olmo'


def policy_document(**overrides):
    document = {'schema': POLICY_SCHEMA, 'consumer_id': 'cedro-agent',
                'mongo_uri': 'mongodb://127.0.0.1:37035/skopos_runtime',
                'database': 'skopos_runtime',
                'allowed_projects': [ALLOWED]}
    document.update(overrides)
    return document


class PolicyFile:
    """Política temporal en disco; digiere sus propios bytes."""

    def __init__(self, document):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'policy.json'
        raw = json.dumps(document).encode('utf-8')
        self.path.write_bytes(raw)
        self.sha256 = hashlib.sha256(raw).hexdigest()

    def close(self):
        self.directory.cleanup()


class LoaderTests(unittest.TestCase):
    def policy_for(self, document):
        handle = PolicyFile(document)
        self.addCleanup(handle.close)
        return handle

    def test_valid_policy_returns_document_and_file_digest(self):
        handle = self.policy_for(policy_document())
        policy, digest = load_consumer_policy(handle.path)
        self.assertEqual(policy, policy_document())
        self.assertEqual(digest, handle.sha256)

    def test_every_violation_fails_closed_with_policy_unavailable(self):
        cases = [
            policy_document(schema='skopos/other/v9'),
            policy_document(consumer_id=''),
            policy_document(consumer_id=' '),
            policy_document(consumer_id=True),
            policy_document(consumer_id=7),
            policy_document(mongo_uri='mongodb://localhost:27017'),
            policy_document(mongo_uri='mongodb://10.0.0.5:27017'),
            policy_document(mongo_uri='mongodb+srv://127.0.0.1:37035'),
            policy_document(database=''),
            policy_document(allowed_projects=[]),
            policy_document(allowed_projects=[ALLOWED, ALLOWED]),
            policy_document(allowed_projects=[ALLOWED, '']),
            policy_document(allowed_projects=[ALLOWED, 3]),
            policy_document(allowed_projects='pilot-cedro'),
            policy_document(extra='field'),
            {key: value for key, value in policy_document().items() if key != 'database'},
        ]
        for document in cases:
            with self.subTest(document=document):
                handle = self.policy_for(document)
                with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
                    load_consumer_policy(handle.path)

    def test_missing_file_and_invalid_json_fail_closed(self):
        with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
            load_consumer_policy('/nonexistent/policy.json')
        handle = PolicyFile(policy_document())
        self.addCleanup(handle.close)
        handle.path.write_bytes(b'{not json')
        with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
            load_consumer_policy(handle.path)

    def test_oversized_policy_fails_closed(self):
        handle = PolicyFile(policy_document(allowed_projects=['x' * 70000]))
        self.addCleanup(handle.close)
        with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
            load_consumer_policy(handle.path)


class RecordingStore:
    """Almacén doble que registra; la única ruta hacia la base en estas pruebas."""

    def __init__(self):
        self.calls = []

    def _record(self, name, kwargs, result):
        self.calls.append((name, kwargs))
        return dict(result)

    def search(self, **kwargs):
        return self._record('search', kwargs, {'results': []})

    def search_runtime(self, **kwargs):
        return self._record('search_runtime', kwargs, {'results': []})

    def fetch(self, **kwargs):
        return self._record('fetch', kwargs, {'segment': 'verificado'})

    def fetch_runtime(self, **kwargs):
        return self._record('fetch_runtime', kwargs, {'projection': 'verificada'})

    def receipt(self, **kwargs):
        return self._record('receipt', kwargs, {'status': 'duplicate'})


OPERATIONS = [
    ('search', dict(term='á', limit=5)),
    ('search_runtime', dict(term='evento', limit=20)),
    ('fetch', dict(source_id='s', source_revision=1,
                   source_sha256='0' * 64, segment_id='seg-0')),
    ('fetch_runtime', dict(source_id='s', source_revision=1,
                           source_sha256='0' * 64, view='text_projection',
                           text_id='event-0-block-0', row_id=None, event_id=None)),
    ('receipt', dict(source_id='s', source_revision=1, source_sha256='0' * 64)),
]


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.handle = PolicyFile(policy_document())
        self.addCleanup(self.handle.close)
        self.policy, self.digest = load_consumer_policy(self.handle.path)
        self.store = RecordingStore()

    def guarded(self, store=None):
        return ConsumerAccessStore(store or self.store, self.policy, self.digest)

    def test_unlisted_project_rejects_uniformly_without_touching_the_store(self):
        for name, kwargs in OPERATIONS:
            with self.subTest(operation=name):
                with self.assertRaisesRegex(ValueError, '^project_not_allowed$'):
                    getattr(self.guarded(), name)(project_id=OTHER, **kwargs)
        self.assertEqual(self.store.calls, [])

    def test_listed_project_delegates_and_serves_access(self):
        for name, kwargs in OPERATIONS:
            with self.subTest(operation=name):
                served = getattr(self.guarded(), name)(project_id=ALLOWED, **kwargs)
                self.assertEqual(served['access'],
                                 {'consumer_id': 'cedro-agent',
                                  'policy_sha256': self.handle.sha256})
                self.assertEqual(self.store.calls[-1],
                                 (name, dict(project_id=ALLOWED, **kwargs)))

    def test_fabricated_policy_is_rejected_at_construction(self):
        for fabricated in ({}, {'schema': POLICY_SCHEMA},
                           dict(policy_document(), allowed_projects=[])):
            with self.subTest(policy=fabricated):
                with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
                    ConsumerAccessStore(self.store, fabricated, '0' * 64)
        with self.assertRaisesRegex(ValueError, '^policy_unavailable$'):
            ConsumerAccessStore(self.store, self.policy, '')


class CliPolicyTests(unittest.TestCase):
    """Rechazos de la CLI bajo política, sin tocar Mongo real."""

    def setUp(self):
        self.handle = PolicyFile(policy_document())
        self.addCleanup(self.handle.close)

    def call(self, *arguments):
        output, error = io.StringIO(), io.StringIO()
        with patch('skopos.source_cli.pymongo.MongoClient') as client:
            client.return_value = MagicMock()
            with redirect_stdout(output), redirect_stderr(error):
                code = source_command(['--policy', str(self.handle.path), *arguments])
        return code, output.getvalue(), error.getvalue()

    def test_unlisted_project_exits_without_serving(self):
        code, stdout, stderr = self.call('search', 'término', '--project-id', OTHER)
        self.assertEqual((code, stdout), (1, ''))
        self.assertIn('project_not_allowed', stderr)

    def test_receipt_of_unlisted_project_is_rejected_too(self):
        code, stdout, stderr = self.call(
            'receipt', '--project-id', OTHER, '--source-id', 's', '--revision', '1',
            '--source-sha256', '0' * 64)
        self.assertEqual((code, stdout), (1, ''))
        self.assertIn('project_not_allowed', stderr)

    def test_import_under_policy_rejected_before_connecting(self):
        with patch('skopos.source_cli.pymongo.MongoClient',
                   side_effect=AssertionError('must not connect')):
            output, error = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                code = source_command(
                    ['--policy', str(self.handle.path), 'import', '/tmp/f.txt',
                     '--project-id', ALLOWED, '--source-id', 's', '--revision', '1',
                     '--captured-at', '2026-10-19T00:00:00Z'])
        self.assertEqual(code, 1)
        self.assertIn('operation_not_allowed', error.getvalue())

    def test_invalid_policy_file_fails_closed(self):
        self.handle.path.write_bytes(b'{not json')
        code, stdout, stderr = self.call('search', 'término', '--project-id', ALLOWED)
        self.assertEqual((code, stdout), (1, ''))
        self.assertIn('policy_unavailable', stderr)

    def test_policy_requires_exclusive_route(self):
        for arguments in (['--database', 'skopos_x', 'search', 'x', '--project-id', ALLOWED],
                          ['--uri', 'mongodb://127.0.0.1:37035', 'search', 'x',
                           '--project-id', ALLOWED]):
            with self.subTest(arguments=arguments):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    source_command(['--policy', str(self.handle.path), *arguments])
                self.assertEqual(error.exception.code, 2)


class ConsumerAccessIntegrationTests(base.RuntimeStoreTests):
    """Sobre Mongo temporal exclusivo (runner aislado): servir y rechazar de verdad."""

    def setUp(self):
        super().setUp()
        self.allowed = 'cedro-' + uuid.uuid4().hex
        document = policy_document(allowed_projects=[self.allowed],
                                   database=self.database.name,
                                   mongo_uri='mongodb://127.0.0.1:37035/'
                                             + self.database.name)
        self.handle = PolicyFile(document)
        self.addCleanup(self.handle.close)
        policy, digest = load_consumer_policy(self.handle.path)
        self.guarded = ConsumerAccessStore(self.store, policy, digest)
        identity = dict(project_id=self.allowed, source_id='runtime', captured_at=base.TIME)
        self.admission = self.store.import_file(
            self.path, source_format='dsh-session-v0-jsonl', **identity)

    def test_listed_project_serves_with_access_and_other_is_rejected(self):
        found = self.guarded.search_runtime(project_id=self.allowed, term='á')
        self.assertEqual(len(found['results']), 2)
        self.assertEqual(found['access'],
                         {'consumer_id': 'cedro-agent', 'policy_sha256': self.handle.sha256})
        for name, kwargs in OPERATIONS:
            with self.subTest(operation=name):
                with self.assertRaisesRegex(ValueError, '^project_not_allowed$'):
                    getattr(self.guarded, name)(project_id=self.project, **kwargs)

    def test_receipt_of_other_project_does_not_reveal_existence(self):
        # El proyecto ajeno existe con datos reales: el rechazo es idéntico.
        self.store.import_file(self.path, source_format='dsh-session-v0-jsonl',
                               project_id=self.project, source_id='otro',
                               captured_at=base.TIME)
        with self.assertRaisesRegex(ValueError, '^project_not_allowed$'):
            self.guarded.receipt(project_id=self.project, source_id='otro',
                                 source_revision=1,
                                 source_sha256=self.admission['source_sha256'])
