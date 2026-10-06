"""Validación y vistas puras: manipulación sintética y controles positivos."""
from copy import deepcopy
import importlib.util
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from test_runtime_envelope import envelope, message, source, reader, batch

root = Path(__file__).resolve().parents[1] / 'experiments/runtime-source-v1'


def load(name, bindings):
    if name in ('verification', 'views', 'store'):
        return importlib.import_module('skopos.runtime_' + name)
    spec = importlib.util.spec_from_file_location('runtime_' + name, root / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, bindings):
        spec.loader.exec_module(module)
    return module


verification = load('verification', {'envelope': envelope, 'reader': reader})
views = load('views', {'verification': verification, 'reader': reader})


def seal(value):
    value['envelope_sha256'] = verification.checksum(verification.canonical(
        {k: v for k, v in value.items() if k != 'envelope_sha256'}))


class RuntimeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.raw = source(message(), message(1, True))
        self.value = envelope.build_envelope(self.raw, project_id='p', source_id='s',
                                             captured_at='2026-10-05T00:00:00Z')

    def fetch(self, **kwargs):
        identity = {k: self.value[k] for k in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        identity.update(kwargs)
        return views.fetch_verified(self.value, self.raw, **identity)

    def test_positive_structural_and_derivation(self):
        before = deepcopy(self.value)
        self.assertIsNone(verification.validate(self.value))
        self.assertEqual(verification.verify(self.value, self.raw), self.value)
        self.assertEqual(self.value, before)

    def test_resealed_false_text_passes_s_but_fails_d(self):
        text = self.value['texts'][-1]
        text['text'] = 'forged'
        text['derived_text_sha256'] = verification.checksum(b'forged')
        seal(self.value)
        verification.validate(self.value)
        with self.assertRaisesRegex(ValueError, '^runtime_derivation_mismatch$'):
            views.search_verified(self.value, self.raw, project_id='p', term='á')

    def test_resealed_false_diagnostics_fail_d(self):
        self.value['diagnostics']['reference_count'] = 1
        seal(self.value)
        verification.validate(self.value)
        with self.assertRaisesRegex(ValueError, '^runtime_derivation_mismatch$'):
            verification.verify(self.value, self.raw)

    def test_invalid_shapes_with_recomputed_seal(self):
        for mutate in [lambda x: x.update(extra='hidden'),
                       lambda x: x['events'][0].update(seq=True),
                       lambda x: x['events'].append(deepcopy(x['events'][0])),
                       lambda x: x['texts'][0].update(row_id='row-999'),
                       lambda x: x['rows'][1].update(start_byte=0),
                       lambda x: x['diagnostics'].update(reference_count=True),
                       lambda x: x['texts'][0].update(block_index=True),
                       lambda x: x['events'][0].update(member_index=0)]:
            value = deepcopy(self.value)
            mutate(value)
            seal(value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
                verification.validate(value)

    def test_unsupported_versions_and_policy(self):
        for key, value, error in [('schema', 'future', 'unsupported_envelope_version'),
                                   ('projection_policy', 'future', 'unsupported_runtime_policy')]:
            candidate = deepcopy(self.value)
            candidate[key] = value
            seal(candidate)
            with self.assertRaisesRegex(ValueError, '^' + error + '$'):
                verification.validate(candidate)

    def test_hash_tamper_and_source_restore(self):
        self.value['envelope_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, '^envelope_integrity_failed$'):
            verification.validate(self.value)
        seal(self.value)
        for raw in (None, self.raw + b' ', self.raw.replace(b'native', b'forged')):
            with self.assertRaisesRegex(ValueError, '^source_integrity_failed$'):
                verification.verify(self.value, raw)
        verification.verify(self.value, self.raw)

    def test_three_explicit_views(self):
        projection = self.fetch(view='text_projection', text_id='event-0-block-0')
        self.assertNotIn('original_jsonl', projection)
        self.assertNotIn('event', projection)
        raw = self.fetch(view='original_jsonl', row_id='row-1')
        row = self.value['rows'][0]
        self.assertEqual(raw['original_jsonl'].encode(), self.raw[:row['end_byte']])
        event = self.fetch(view='derived_event', event_id='event-1')
        self.assertEqual(event['event'], message(1, True))
        self.assertIsNone(event['member_index'])

    def test_view_selector_and_identity_rejection(self):
        for args, error in [({'view': 'all'}, 'invalid_runtime_view'),
                            ({'view': 'text_projection'}, 'invalid_runtime_selector'),
                            ({'view': 'original_jsonl', 'row_id': 'row-1', 'event_id': 'event-0'}, 'invalid_runtime_selector'),
                            ({'view': 'original_jsonl', 'row_id': 'row-999'}, 'runtime_item_not_found'),
                            ({'view': 'original_jsonl', 'row_id': 'row-1', 'source_revision': True}, 'revision_conflict')]:
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, '^'+error+'$'):
                self.fetch(**args)

    def test_search_zero_limits_and_invalid_parameters(self):
        for limit in (0, 1, 20):
            result = views.search_verified(self.value, self.raw, project_id='p', term='Á', limit=limit)
            self.assertEqual(len(result['results']), min(limit, 2))
            self.assertEqual(result['excluded']['result_limit'], max(0, 2-limit))
            self.assertEqual(result['selection'], 'explicit_revision')
        for kwargs, error in [({'term': ''}, 'invalid_term'), ({'term': '\ud800'}, 'invalid_term'),
                              ({'term': 'x', 'limit': True}, 'invalid_limit')]:
            with self.assertRaisesRegex(ValueError, '^'+error+'$'):
                views.search_verified(self.value, self.raw, project_id='p', **kwargs)

    def test_full_serialized_budget_exact_boundary(self):
        result = self.fetch(view='text_projection', text_id='event-0-block-0')
        size = len(verification.canonical(result))
        with patch.object(views, 'MAX_RESULT_BYTES', size):
            self.fetch(view='text_projection', text_id='event-0-block-0')
        with patch.object(views, 'MAX_RESULT_BYTES', size - 1):
            with self.assertRaisesRegex(ValueError, '^fragment_too_large$'):
                self.fetch(view='text_projection', text_id='event-0-block-0')
            result = views.search_verified(self.value, self.raw, project_id='p', term='á')
            self.assertEqual(result['results'], [])
            self.assertEqual(result['excluded']['fragment_too_large'], 2)

    def test_private_lure_absent_from_search_explicit_raw_only(self):
        self.raw = source(message(content=[{'type':'text','text':'visible'},
                                          {'type':'reasoning','text':'PRIVATE'}]))
        self.value = envelope.build_envelope(self.raw, project_id='p', source_id='s', captured_at='2026-10-05T00:00:00Z')
        result = views.search_verified(self.value, self.raw, project_id='p', term='PRIVATE')
        self.assertEqual(result['results'], [])
        result = views.search_verified(self.value, self.raw, project_id='p', term='visible')
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertIn('PRIVATE', self.fetch(view='original_jsonl', row_id='row-2')['original_jsonl'])

    def test_returned_view_does_not_mutate_input(self):
        result = self.fetch(view='text_projection', text_id='event-0-block-0')
        result['projection']['text'] = 'mutation'
        verification.verify(self.value, self.raw)

    def test_header_and_batch_controls(self):
        for raw in (source(), source(batch())):
            value = envelope.build_envelope(raw, project_id='p', source_id='s',
                                            captured_at='2026-10-05T00:00:00Z')
            verification.verify(value, raw)
        self.raw, self.value = raw, value
        result = self.fetch(view='derived_event', event_id='event-1')
        self.assertEqual(result['member_index'], 1)
        self.assertEqual(result['event']['data']['chunk']['text'], '終')
        self.value['events'][1]['member_index'] = 0
        seal(self.value)
        with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
            verification.validate(self.value)

    def test_validation_bounds_and_invalid_root(self):
        size = len(verification.canonical(self.value))
        with patch.object(verification, 'MAX_ENVELOPE_BYTES', size):
            verification.validate(self.value)
        with patch.object(verification, 'MAX_ENVELOPE_BYTES', size - 1):
            with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
                verification.validate(self.value)
        for candidate in (None, [], {'schema': 'skopos/source-envelope/v2'}):
            with self.assertRaisesRegex(ValueError, '^store_integrity_failed$'):
                verification.validate(candidate)

    def test_views_are_pure_and_search_order_is_numeric(self):
        raw = source(message(10), message(2))
        value = envelope.build_envelope(raw, project_id='p', source_id='s',
                                        captured_at='2026-10-05T00:00:00Z')
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = views.search_verified(value, raw, project_id='p', term='á')
        self.assertEqual([r['projection']['event_id'] for r in result['results']],
                         ['event-2', 'event-10'])


if __name__ == '__main__':
    unittest.main()
