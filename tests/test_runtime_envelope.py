"""Proyección runtime selectiva: datos sintéticos, sin servicios ni corpus."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from test_runtime_source import reader, source, batch

from skopos import runtime_envelope as envelope


def message(seq=0, assistant=False, origin=None, content=None):
    value = {'id': 'native', 'role': 'assistant' if assistant else 'user',
             'source': origin if origin is not None else (
                 {'kind': 'model', 'provider': 'synthetic', 'model': 'unknown'}
                 if assistant else {'kind': 'user'}),
             'content': content if content is not None else [{'type': 'text', 'text': 'á終'}]}
    return {'type': 'assistant/message' if assistant else 'user/message',
            'seq': seq, 'time': 0,
            'data': {'turn': 0, 'step': 0, 'message': value} if assistant else value}


class RuntimeEnvelopeTests(unittest.TestCase):
    def build(self, *events, raw=None, **metadata):
        arguments = dict(project_id='test', source_id='runtime', captured_at='2026-10-05T18:00:00-06:00')
        arguments.update(metadata)
        return envelope.build_envelope(source(*events) if raw is None else raw, **arguments)

    def test_deterministic_hashes_and_exact_projection(self):
        raw = source(message(), message(1, True), ending=b'\r\n')[:-2]
        result = self.build(raw=raw)
        self.assertEqual(result, self.build(raw=raw))
        self.assertEqual(result['captured_at'], '2026-10-06T00:00:00Z')
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        digest = result.pop('envelope_sha256')
        self.assertEqual(digest, hashlib.sha256(json.dumps(result, ensure_ascii=False,
                          sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.assertEqual([t['pointer'] for t in result['texts']],
                         ['/data/content/0', '/data/message/content/0'])
        for text in result['texts']:
            row = next(r for r in result['rows'] if r['id'] == text['row_id'])
            value = json.loads(raw[row['start_byte']:row['end_byte']])
            for token in text['pointer'].split('/')[1:]:
                value = value[int(token)] if type(value) is list else value[token]
            self.assertEqual(value['text'], text['text'])
            self.assertEqual(text['derived_text_sha256'], hashlib.sha256(value['text'].encode()).hexdigest())

    def test_no_raw_payloads_or_transcript_fields(self):
        result = self.build(message(content=[{'type': 'reasoning', 'text': 'PRIVATE'},
                                             {'type': 'text', 'text': 'visible'}]))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('segments', result)
        self.assertNotIn('audio_alignment', result)
        self.assertEqual(set(result['rows'][0]), {'id', 'start_byte', 'end_byte', 'sha256'})
        self.assertEqual(set(result['events'][0]), {'id', 'seq', 'time', 'type', 'row_id', 'member_index'})

    def test_crossed_roles_origins_and_types(self):
        for assistant in (False, True):
            self.assertEqual(len(self.build(message(assistant=assistant))['texts']), 1)
            for origin in ('plugin', 'agent-instructions', 'tool', 'future',
                           'user' if assistant else 'model'):
                result = self.build(message(assistant=assistant, origin={'kind': origin}))
                self.assertEqual(result['texts'], [])
                self.assertEqual(result['diagnostics']['events_excluded']['source_kind'], 1)
            event = message(assistant=assistant)
            target = event['data']['message'] if assistant else event['data']
            target['role'] = 'user' if assistant else 'assistant'
            self.assertEqual(self.build(event)['texts'], [])
        event = message()
        event['type'] = 'tool/result'
        self.assertEqual(self.build(event)['diagnostics']['events_excluded']['event_type'], 1)

    def test_interrupted_presence_never_projected(self):
        for flag in (True, False, None, 'false'):
            event = message(assistant=True)
            event['data']['interrupted'] = flag
            result = self.build(event)
            self.assertEqual(result['texts'], [])
            self.assertEqual(result['diagnostics']['events_excluded']['interrupted'], 1)
        self.assertEqual(len(self.build(message(assistant=True))['texts']), 1)

    def test_nested_lures_and_original_block_indices(self):
        content = [{'type': 'tool-result', 'content': [{'type': 'text', 'text': 'PRIVATE'}]},
                   {'type': 'reasoning', 'text': 'PRIVATE'},
                   {'type': 'future', 'text': 'PRIVATE'},
                   {'type': 'text', 'text': ' \n'}, {'type': 'text', 'text': '  visible\n'}]
        result = self.build(message(content=content))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(result['texts'][0]['id'], 'event-0-block-4')
        self.assertEqual(result['texts'][0]['text'], '  visible\n')
        self.assertEqual(result['diagnostics']['blocks_excluded'], {'non_text': 3, 'empty_text': 1})

    def test_invalid_block_invalidates_entire_message(self):
        for bad in ({'type': 'text', 'text': 1}, {'type': 'text', 'text': 'x', 'extra': 1}, None):
            result = self.build(message(content=[{'type': 'text', 'text': 'valid'}, bad]))
            self.assertEqual(result['texts'], [])
            self.assertEqual(result['diagnostics']['events_excluded']['invalid_message_projection'], 1)
            self.assertEqual(sum(result['diagnostics']['blocks_excluded'].values()), 0)

    def test_malformed_message_and_origin(self):
        for key, value in [('id', ''), ('content', 'text'), ('source', None), ('extra', 1)]:
            event = message()
            event['data'][key] = value
            self.assertEqual(self.build(event)['texts'], [])
        for origin in ({}, {'kind': 'user', 'rpcId': ''}, {'kind': 'user', 'extra': 'x'}):
            self.assertEqual(self.build(message(origin=origin))['texts'], [])
        event = message(assistant=True, origin={'kind': 'model'})
        self.assertEqual(self.build(event)['texts'], [])

    def test_replay_state_not_copied(self):
        origin = {'kind': 'model', 'provider': 'p', 'model': 'm', 'replayState': {'secret': 'PRIVATE'}}
        result = self.build(message(assistant=True, origin=origin))
        self.assertEqual(len(result['texts']), 1)
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_chunks_not_projected_and_identical_messages_retained(self):
        result = self.build(batch(), message(2), message(3))
        self.assertEqual([x['id'] for x in result['texts']], ['event-2-block-0', 'event-3-block-0'])
        self.assertEqual(result['diagnostics']['events_excluded']['event_type'], 2)

    def test_block_budget_counts_excluded_messages_and_rejects_atomically(self):
        with patch.object(envelope, 'MAX_BLOCKS', 1):
            self.assertEqual(len(self.build(message())['texts']), 1)
            with self.assertRaisesRegex(ValueError, '^runtime_limit_exceeded$'):
                self.build(message(), message(1, origin={'kind': 'plugin'}))

    def test_invalid_metadata(self):
        cases = [({'project_id': '../p'}, 'invalid_project_id'),
                 ({'source_id': ''}, 'invalid_source_id'),
                 ({'source_revision': True}, 'invalid_source_revision'),
                 ({'source_revision': 2}, 'invalid_predecessor'),
                 ({'previous_source_sha256': 'a'*64}, 'invalid_predecessor'),
                 ({'captured_at': '2026-10-05'}, 'invalid_capture_time'),
                 ({'capture_completeness': True}, 'invalid_completeness'),
                 ({'completeness_basis': 'unexpected'}, 'invalid_completeness_basis'),
                 ({'capture_completeness': 'complete'}, 'invalid_completeness_basis'),
                 ({'capture_completeness': 'partial', 'completeness_basis': '\ud800'}, 'invalid_completeness_basis')]
        for metadata, error in cases:
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, '^'+error+'$'):
                self.build(message(), **metadata)

    def test_revision_completeness_and_no_io(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = self.build(message(), source_revision=2, previous_source_sha256='a'*64,
                                capture_completeness='partial', completeness_basis='Declaración sintética')
        self.assertEqual(result['source_revision'], 2)
        self.assertEqual(result['capture_completeness']['value'], 'partial')
        self.assertEqual(result['producer_claims'], 'not_verified')
        self.assertIsNone(result['occurred_at'])
        self.assertEqual(self.build()['capture_completeness'], {'value': 'unknown', 'basis': None})

    def test_current_store_rejects_experimental_envelope(self):
        from skopos.source_store import SourceStore
        result = self.build(message())
        document = {'_id': 'test:runtime:1', 'schema': 'skopos/source-record/v3',
                    'project_id': 'test', 'source_id': 'runtime', 'source_revision': 1,
                    'envelope': result, 'admitted_at': '2026-10-05T00:00:00Z'}
        with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
            SourceStore._verified_envelope(document)

    def test_source_bytes_and_unknown_arguments_rejected(self):
        with self.assertRaisesRegex(ValueError, '^invalid_source_bytes$'):
            self.build(raw={'events': []})
        with self.assertRaises(TypeError):
            self.build(unknown_field='not accepted')

    def test_explicit_project_not_native_metadata(self):
        raw = source(message()).replace(b'"id": "synthetic"',
                                        b'"id": "PRIVATE", "cwd": "/PRIVATE"')
        result = self.build(raw=raw)
        self.assertEqual(result['project_id'], 'test')
        self.assertEqual(result['source_id'], 'runtime')
        self.assertNotIn('PRIVATE', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
