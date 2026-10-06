"""Validación S/D experimental sobre buffers; sin archivos, Mongo ni admisión."""
import hashlib
import json

from skopos.runtime_envelope import build_envelope, MAX_BLOCKS
from skopos.runtime_reader import MAX_BYTES, MAX_ROWS, MAX_EVENTS, MAX_REFERENCES, SAFE_INTEGER

IDENTITY = ('project_id', 'source_id', 'source_revision', 'source_sha256', 'envelope_sha256')
METADATA = ('project_id', 'source_id', 'captured_at', 'source_revision', 'previous_source_sha256')
FIELDS = set(IDENTITY + METADATA) | {
    'schema', 'source_kind', 'source_bytes', 'captured_at_basis', 'occurred_at',
    'capture_completeness', 'adapter', 'projection_policy', 'producer_claims',
    'rows', 'events', 'texts', 'diagnostics'}
MAX_ENVELOPE_BYTES = 16 * 1024 * 1024


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def checksum(raw):
    return hashlib.sha256(raw).hexdigest()


def _check(condition):
    if not condition:
        raise ValueError('store_integrity_failed')


def _keys(value, keys):
    _check(type(value) is dict and set(value) == set(keys))


def _count(value, maximum, minimum=0):
    _check(type(value) is int and minimum <= value <= maximum)


def _hash(value):
    _check(type(value) is str and len(value) == 64
           and all(c in '0123456789abcdef' for c in value))


def _metadata(envelope):
    complete = envelope['capture_completeness']
    return {**{k: envelope[k] for k in METADATA},
            'capture_completeness': complete['value'], 'completeness_basis': complete['basis']}


def validate(envelope):
    """Nivel S: coherencia declarada, no fidelidad ni autenticidad del original."""
    try:
        _validate(envelope)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        known = {'unsupported_envelope_version', 'unsupported_runtime_policy',
                 'envelope_integrity_failed', 'store_integrity_failed'}
        raise ValueError(str(error) if str(error) in known else 'store_integrity_failed') from None


def _validate(envelope):
    _check(type(envelope) is dict)
    if envelope.get('schema') != 'skopos/source-envelope/v2':
        raise ValueError('unsupported_envelope_version')
    _keys(envelope, FIELDS)
    if (envelope['adapter'] != {'id': 'skopos/experimental-runtime-envelope/v0',
                               'format': 'dsh-session-v0-jsonl'}
            or envelope['projection_policy'] != 'skopos/runtime-text-policy/v0'):
        raise ValueError('unsupported_runtime_policy')
    _keys(envelope['capture_completeness'], ('value', 'basis'))
    # Reusar exactamente la frontera de metadatos, sobre una fuente mínima pública.
    baseline = build_envelope(b'{"type":"session","version":0,"id":"validation"}',
                              **_metadata(envelope))
    for key in METADATA + ('source_kind', 'captured_at_basis', 'occurred_at', 'producer_claims'):
        _check(type(envelope[key]) is type(baseline[key]) and envelope[key] == baseline[key])
    _count(envelope['source_bytes'], MAX_BYTES, 1)
    for key in ('source_sha256', 'envelope_sha256'):
        _hash(envelope[key])
    for key, maximum in [('rows', MAX_ROWS), ('events', MAX_EVENTS), ('texts', MAX_BLOCKS)]:
        _check(type(envelope[key]) is list)
        _count(len(envelope[key]), maximum, 1 if key == 'rows' else 0)
    rows = {}
    offset = 0
    for index, row in enumerate(envelope['rows'], 1):
        _keys(row, ('id', 'start_byte', 'end_byte', 'sha256'))
        _check(row['id'] == 'row-%d' % index)
        _count(row['start_byte'], envelope['source_bytes'])
        _count(row['end_byte'], envelope['source_bytes'], row['start_byte'] + 1)
        _check(row['start_byte'] == offset)
        _hash(row['sha256'])
        offset = row['end_byte']
        rows[row['id']] = row
    _check(offset == envelope['source_bytes'])
    events, groups = {}, {}
    for event in envelope['events']:
        _keys(event, ('id', 'seq', 'time', 'type', 'row_id', 'member_index'))
        _count(event['seq'], SAFE_INTEGER)
        _count(event['time'], SAFE_INTEGER, -SAFE_INTEGER)
        _check(event['id'] == 'event-%d' % event['seq'] and event['id'] not in events)
        _check(type(event['type']) is str and bool(event['type']) and event['type'] != 'session')
        _check(type(event['row_id']) is str and event['row_id'] in rows and event['row_id'] != 'row-1')
        if event['member_index'] is not None:
            _count(event['member_index'], MAX_EVENTS - 1)
            _check(event['type'] == 'assistant/chunk')
        groups.setdefault(event['row_id'], []).append(event)
        events[event['id']] = event
    _check(set(groups) == set(rows) - {'row-1'})
    for group in groups.values():
        if group[0]['member_index'] is None:
            _check(len(group) == 1)
        else:
            for index, event in enumerate(group):
                _check(type(event['member_index']) is int and event['member_index'] == index
                       and event['seq'] == group[0]['seq'] + index)
    ids = set()
    for text in envelope['texts']:
        _keys(text, ('id', 'event_id', 'row_id', 'block_index', 'pointer', 'role',
                     'source_kind', 'text', 'derived_text_sha256'))
        _check(type(text['event_id']) is str and text['event_id'] in events)
        event = events[text['event_id']]
        _check(event['member_index'] is None and event['type'] in ('user/message', 'assistant/message'))
        assistant = event['type'] == 'assistant/message'
        _check(text['role'] == ('assistant' if assistant else 'user')
               and text['source_kind'] == ('model' if assistant else 'user'))
        _count(text['block_index'], MAX_BLOCKS - 1)
        _check(text['row_id'] == event['row_id'])
        prefix = '/data/message/content/' if assistant else '/data/content/'
        _check(text['pointer'] == prefix + str(text['block_index']))
        _check(text['id'] == '%s-block-%d' % (event['id'], text['block_index']) and text['id'] not in ids)
        ids.add(text['id'])
        _check(type(text['text']) is str and bool(text['text'].strip()))
        _hash(text['derived_text_sha256'])
        _check(checksum(text['text'].encode()) == text['derived_text_sha256'])
    diagnostics = envelope['diagnostics']
    _keys(diagnostics, ('sequence_gap_count', 'reference_count', 'unresolved_reference_count',
                        'events_excluded', 'blocks_excluded', 'blocks_examined'))
    _count(diagnostics['sequence_gap_count'], SAFE_INTEGER)
    expected_gaps = max(e['seq'] for e in events.values()) + 1 - len(events) if events else 0
    _check(diagnostics['sequence_gap_count'] == expected_gaps)
    _count(diagnostics['reference_count'], MAX_REFERENCES)
    _count(diagnostics['unresolved_reference_count'], diagnostics['reference_count'])
    _count(diagnostics['blocks_examined'], MAX_BLOCKS)
    for key, names, maximum in [
            ('events_excluded', ('event_type', 'source_kind', 'interrupted', 'invalid_message_projection'), len(events)),
            ('blocks_excluded', ('non_text', 'empty_text'), diagnostics['blocks_examined'])]:
        _keys(diagnostics[key], names)
        for count in diagnostics[key].values():
            _count(count, maximum)
        _check(sum(diagnostics[key].values()) <= maximum)
    _check(len(envelope['texts']) + sum(diagnostics['blocks_excluded'].values())
           <= diagnostics['blocks_examined'])
    _check(len(canonical(envelope)) <= MAX_ENVELOPE_BYTES)
    unsigned = {k: v for k, v in envelope.items() if k != 'envelope_sha256'}
    if checksum(canonical(unsigned)) != envelope['envelope_sha256']:
        raise ValueError('envelope_integrity_failed')


def verify(envelope, raw):
    """Nivel D: rederiva todo antes de devolver contenido; no modifica el sobre."""
    validate(envelope)
    if (type(raw) is not bytes or len(raw) != envelope['source_bytes']
            or checksum(raw) != envelope['source_sha256']):
        raise ValueError('source_integrity_failed')
    try:
        rebuilt = build_envelope(raw, **_metadata(envelope))
    except ValueError:
        raise ValueError('runtime_derivation_mismatch') from None
    if canonical(rebuilt) != canonical(envelope):
        raise ValueError('runtime_derivation_mismatch')
    return rebuilt
