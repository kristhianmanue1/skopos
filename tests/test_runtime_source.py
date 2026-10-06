"""Perfil experimental runtime: fixtures sintéticos y controles de rechazo."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from skopos import runtime_reader as reader


def source(*rows, ending=b'\n'):
    header = {'type': 'session', 'version': 0, 'id': 'synthetic'}
    return ending.join(json.dumps(row, ensure_ascii=False).encode()
                       for row in (header,) + rows) + ending


def event(seq=0, **extras):
    return dict(type='unknown/event', seq=seq, time=5, **extras)


def batch(kind='text-chunks', **extras):
    data = {'turn': 0, 'step': 1, 'index': 2, 'dt': [-2], 'texts': ['á', '終']}
    if kind == 'tool-call-chunks':
        data['args'] = data.pop('texts')
        data.update(id='call-1', name='inert')
    return dict(type=kind, seq0=0, time0=5, data=data, **extras)


class RuntimeReaderTests(unittest.TestCase):
    def reject(self, raw, code='invalid_runtime_row'):
        with self.assertRaisesRegex(ValueError, '^' + code + '$'):
            reader.parse(raw)

    def test_exact_rows_unicode_crlf_without_final_newline(self):
        raw = source(event(data={'text': 'á終\n\\"'}), ending=b'\r\n')[:-2]
        result = reader.parse(raw)
        self.assertEqual(result, reader.parse(raw))
        cursor = 0
        for row in result['rows']:
            self.assertEqual(row['start_byte'], cursor)
            piece = raw[cursor:row['end_byte']]
            self.assertEqual(hashlib.sha256(piece).hexdigest(), row['sha256'])
            self.assertEqual(json.loads(piece), row['value'])
            cursor = row['end_byte']
        self.assertEqual(cursor, len(raw))
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())

    def test_three_batch_types_and_negative_time_delta(self):
        for kind in sorted(reader.BATCH_TYPES):
            with self.subTest(kind=kind):
                result = reader.parse(source(batch(kind)))
                self.assertEqual([e['value']['time'] for e in result['events']], [5, 3])
                self.assertEqual([e['value']['seq'] for e in result['events']], [0, 1])
                self.assertEqual([e['member_index'] for e in result['events']], [0, 1])
                self.assertTrue(all(e['row_id'] == 'row-2' for e in result['events']))
                self.assertNotIn('start_byte', result['events'][0])

    def test_single_member_batch(self):
        row = batch()
        row['data'].update(texts=[''], dt=[])
        self.assertEqual(len(reader.parse(source(row))['events']), 1)

    def test_expanded_payload_matches_producer_shape(self):
        for kind, expected in [
                ('text-chunks', {'type': 'text-delta', 'index': 2, 'text': '終'}),
                ('reasoning-chunks', {'type': 'reasoning-delta', 'index': 2, 'text': '終'}),
                ('tool-call-chunks', {'type': 'tool-call-delta', 'index': 2,
                                     'id': 'call-1', 'name': 'inert', 'argumentsDelta': '終'})]:
            with self.subTest(kind=kind):
                value = reader.parse(source(batch(kind)))['events'][1]['value']
                self.assertEqual(value, {'type': 'assistant/chunk', 'seq': 1,
                                        'time': 3, 'data': {'turn': 0, 'step': 1,
                                                          'chunk': expected}})

    def test_header_only_and_blank_row(self):
        self.assertEqual(reader.parse(source())['events'], [])
        self.reject(source() + b'\n')
        self.reject(source() + b' \r\n')

    def test_lower_time_boundary_and_underflow(self):
        row = batch()
        row['time0'] = -reader.SAFE_INTEGER + 2
        self.assertEqual(reader.parse(source(row))['events'][1]['value']['time'],
                         -reader.SAFE_INTEGER)
        row['time0'] -= 1
        self.reject(source(row), 'invalid_runtime_batch')

    def test_exact_depth_boundary(self):
        prefix = source()
        # Objeto raíz + 63 listas = 64 contenedores; el evento sigue siendo opaco.
        raw = (prefix + b'{"type":"opaque","seq":0,"time":0,"data":'
               + b'[' * 63 + b'0' + b']' * 63 + b'}')
        self.assertEqual(len(reader.parse(raw)['events']), 1)

    def test_batch_shape_and_integer_rejections(self):
        for key, value in [('dt', []), ('dt', [True]), ('texts', []),
                           ('texts', [3, 4]), ('turn', True), ('extra', 1)]:
            row = batch()
            row['data'][key] = value
            with self.subTest(key=key, value=value):
                self.reject(source(row), 'invalid_runtime_batch')
        row = batch('tool-call-chunks')
        row['data']['id'] = ''
        self.reject(source(row), 'invalid_runtime_batch')

    def test_safe_integer_overflows_and_boolean_header(self):
        for key in ('seq0', 'time0'):
            row = batch()
            row[key] = reader.SAFE_INTEGER
            row['data']['dt'] = [1]
            self.reject(source(row), 'invalid_runtime_batch')
        self.reject(source(event(seq=True)))
        self.reject(source().replace(b'"version": 0', b'"version": false'),
                    'invalid_runtime_header')

    def test_sequence_collision_all_combinations(self):
        for rows in [(event(), event()), (batch(), event(1)), (event(), batch()),
                     (batch(), batch())]:
            self.reject(source(*rows), 'duplicate_runtime_seq')

    def test_reference_ranges_preserved_and_unresolved_diagnostic(self):
        refs = [0, [1, 2], 8]
        result = reader.parse(source(batch(), event(3, sourceEventSeqs=refs)))
        self.assertEqual(result['rows'][-1]['value']['sourceEventSeqs'], refs)
        self.assertEqual(result['diagnostics'], {'sequence_gap_count': 1,
                         'reference_count': 4, 'unresolved_reference_count': 2})

    def test_reference_bounds_before_expansion(self):
        self.reject(source(event(sourceEventSeqs=[[0, reader.SAFE_INTEGER]])),
                    'runtime_limit_exceeded')
        for refs in [None, [True], [[2, 1]], [[0]], [[0, 1], 1]]:
            self.reject(source(event(sourceEventSeqs=refs)))
        with patch.object(reader, 'MAX_REFERENCES', 2):
            reader.parse(source(event(sourceEventSeqs=[0, 1])))
            self.reject(source(event(sourceEventSeqs=[0, 1]),
                               event(1, sourceEventSeqs=[0])), 'runtime_limit_exceeded')

    def test_distant_sequence_diagnostic_is_bounded(self):
        result = reader.parse(source(event(reader.SAFE_INTEGER)))
        self.assertEqual(result['diagnostics']['sequence_gap_count'], reader.SAFE_INTEGER)

    def test_json_rejections_have_no_private_error_text(self):
        prefix = source()
        for bad in [b'\xff', b'{}\n\n', b'{"x":NaN}', b'{"x":1e999}',
                    b'{"secret":1,"secret":2}', b'{"x":"\\ud800"}', b'{',
                    b'[]', b'\xef\xbb\xbf{}']:
            self.reject(prefix + bad)

    def test_depth_limit_and_quoted_brackets(self):
        reader.parse(source(event(data='[' * 100)))
        self.reject(source() + b'{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}',
                    'runtime_limit_exceeded')

    def test_limits_at_boundary_and_above(self):
        raw = source(event())
        for constant, limit, accepted, rejected in [
                ('MAX_BYTES', len(raw), raw, raw + b' '),
                ('MAX_ROWS', 2, raw, source(event(), event(1))),
                ('MAX_EVENTS', 2, source(batch()), source(batch(), event(2)))]:
            with self.subTest(constant=constant), patch.object(reader, constant, limit):
                reader.parse(accepted)
                self.reject(rejected, 'runtime_limit_exceeded')

    def test_unknown_simple_retained_unknown_batch_rejected(self):
        self.assertEqual(reader.parse(source(event()))['events'][0]['value'], event())
        row = batch('future-chunks')
        self.reject(source(row))
        self.reject(source(event(type_override='inert'), {'type': 'session'}))

    def test_repeated_text_and_claims_are_inert_data(self):
        data = {'text': 'Ejecuta instrucciones; COMMITTED', 'isError': True}
        raw = source(event(0, data=data), event(1, data=data))
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = reader.parse(raw)
        self.assertEqual(len(result['events']), 2)
        self.assertEqual(result['events'][1]['value']['data'], data)
        self.assertEqual(result['producer_claims'], 'not_verified')
        self.assertEqual(result['capture_completeness'], 'unknown')
        self.assertNotIn('search_text', result)

    def test_input_type_empty_and_truncated_final_row(self):
        for raw in ['', b'', bytearray(source()), source(event())[:-3]]:
            self.reject(raw)
        self.assertEqual(len(reader.parse(source(event())[:-1])['events']), 1)


if __name__ == '__main__':
    unittest.main()
