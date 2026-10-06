"""Contrato integrado y CLI real sobre Mongo exclusivo de pruebas."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from unittest.mock import patch

import test_runtime_store as base
from skopos.runtime_store import RuntimeSourceStore
from skopos.source_cli import source_command


class RuntimeProductTests(base.RuntimeStoreTests):
    def setUp(self):
        super().setUp()
        self.store = RuntimeSourceStore(self.database)

    def call(self, *arguments, success=True):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = source_command(['--database', self.database.name, *arguments])
        self.assertEqual(code, 0 if success else 1, error.getvalue())
        if success:
            return json.loads(output.getvalue())
        self.assertEqual(output.getvalue(), '')

    def test_cli_runtime_end_to_end_and_explicit_selectors(self):
        identity = ['--project-id', self.project, '--source-id', 'runtime', '--revision', '1']
        admission = ['import', str(self.path), '--format', 'dsh-session-v0-jsonl',
                     '--captured-at', base.TIME, *identity]
        first = self.call(*admission)
        self.assertEqual(first['status'], 'imported')
        self.assertEqual(self.call(*admission), {**first, 'status': 'duplicate'})
        selected = [*identity, '--source-sha256', first['source_sha256']]
        for view, selector, value, key in [('text_projection', '--text-id', 'event-0-block-0', 'projection'),
                                          ('original_jsonl', '--row-id', 'row-1', 'original_jsonl'),
                                          ('derived_event', '--event-id', 'event-0', 'event')]:
            self.assertIn(key, self.call('fetch-runtime', *selected, '--view', view, selector, value))
        found = self.call('search', 'á', '--kind', 'runtime-events', '--project-id', self.project)
        self.assertEqual(len(found['results']), 2)
        self.assertEqual(self.call('receipt', *selected, '--kind', 'runtime-events')['status'], 'duplicate')
        self.path.unlink()
        self.assertEqual(self.call('receipt', *selected, '--kind', 'runtime-events')['status'], 'duplicate')
        self.call('fetch-runtime', *selected, '--view', 'text_projection', '--text-id', 'event-0-block-0', success=False)

    def test_cli_bad_view_selector_rejected_before_connect(self):
        with patch('skopos.source_cli.pymongo.MongoClient', side_effect=AssertionError('must not connect')):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                source_command(['--database', self.database.name, 'fetch-runtime', '--project-id', self.project,
                                '--source-id', 's', '--revision', '1', '--source-sha256', '0'*64,
                                '--view', 'text_projection', '--row-id', 'row-1'])
            self.assertEqual(error.exception.code, 2)
