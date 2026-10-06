"""Lector experimental DSH v0: bytes a evidencia, sin IO ni admisión productiva.

La salida contiene datos privados potenciales; no es una vista de búsqueda.
No adjudica éxito, identidad de modelo, autoridad ni completitud de captura.
"""
import hashlib
import json
import math

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 10_000
MAX_EVENTS = 100_000
MAX_REFERENCES = 100_000
MAX_DEPTH = 64
SAFE_INTEGER = 2**53 - 1
BATCH_TYPES = {'text-chunks', 'reasoning-chunks', 'tool-call-chunks'}


def _require(condition, code='invalid_runtime_row'):
    if not condition:
        raise ValueError(code)


def _integer(value, minimum=-SAFE_INTEGER):
    return type(value) is int and minimum <= value <= SAFE_INTEGER


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result)
        result[key] = value
    return result


def _constant(_):
    raise ValueError('invalid_runtime_row')


def _load(line):
    try:
        text = line.decode('utf-8')
        depth = 0
        quoted = escaped = False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in '[{':
                depth += 1
                _require(depth <= MAX_DEPTH, 'runtime_limit_exceeded')
            elif char in ']}':
                depth -= 1
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
        stack = [value]
        while stack:
            item = stack.pop()
            if type(item) is dict:
                stack.extend(item.keys())
                stack.extend(item.values())
            elif type(item) is list:
                stack.extend(item)
            elif type(item) is str:
                item.encode('utf-8')
            elif type(item) is float:
                _require(math.isfinite(item))
        _require(type(value) is dict)
        return value
    except (ValueError, UnicodeError, RecursionError) as error:
        code = ('runtime_limit_exceeded' if str(error) == 'runtime_limit_exceeded'
                else 'invalid_runtime_row')
        raise ValueError(code) from None


def _expand_batch(row, remaining):
    code = 'invalid_runtime_batch'
    _require(set(row) == {'type', 'seq0', 'time0', 'data'}, code)
    _require(_integer(row['seq0'], 0) and _integer(row['time0']), code)
    data = row['data']
    tool = row['type'] == 'tool-call-chunks'
    field = 'args' if tool else 'texts'
    required = {'turn', 'step', 'index', 'dt', field} | ({'id'} if tool else set())
    _require(type(data) is dict and required <= data.keys()
             and data.keys() <= required | ({'name'} if tool else set()), code)
    _require(all(_integer(data[key], 0) for key in ('turn', 'step', 'index')), code)
    payload, gaps = data[field], data['dt']
    _require(type(payload) is list and len(payload) > 0
             and all(type(member) is str for member in payload), code)
    _require(len(payload) <= remaining, 'runtime_limit_exceeded')
    _require(type(gaps) is list and len(gaps) == len(payload) - 1
             and all(_integer(gap) for gap in gaps), code)
    _require(_integer(row['seq0'] + len(payload) - 1, 0), code)
    if tool:
        _require(type(data['id']) is str and bool(data['id'])
                 and ('name' not in data or type(data['name']) is str), code)
    events = []
    time = row['time0']
    for index, member in enumerate(payload):
        if index:
            time += gaps[index - 1]
        _require(_integer(time), code)
        chunk = {'index': data['index']}
        if tool:
            chunk.update(type='tool-call-delta', id=data['id'], argumentsDelta=member)
            if 'name' in data:
                chunk['name'] = data['name']
        else:
            chunk.update(type=('text-delta' if row['type'] == 'text-chunks'
                               else 'reasoning-delta'), text=member)
        events.append({'type': 'assistant/chunk', 'seq': row['seq0'] + index,
                       'time': time, 'data': {'turn': data['turn'],
                                             'step': data['step'], 'chunk': chunk}})
    return events


def _references(value, remaining):
    _require(type(value) is list)
    output = []
    has_range = False
    for member in value:
        if type(member) is list:
            _require(len(member) == 2 and all(_integer(x, 0) for x in member))
            start, end = member
            _require(start <= end)
            has_range = True
        else:
            _require(_integer(member, 0))
            start = end = member
        _require(end - start + 1 <= remaining - len(output), 'runtime_limit_exceeded')
        output.extend(range(start, end + 1))
    if has_range:
        _require(all(left < right for left, right in zip(output, output[1:])))
    return output


def parse(raw):
    """Construye todo o rechaza todo; no abre archivos, ejecuta ni almacena."""
    _require(type(raw) is bytes and bool(raw))
    _require(len(raw) <= MAX_BYTES, 'runtime_limit_exceeded')
    # Sólo LF separa registros. splitlines también aceptaría separadores ajenos.
    count = raw.count(b'\n') + int(not raw.endswith(b'\n'))
    _require(count <= MAX_ROWS, 'runtime_limit_exceeded')
    rows, events, references = [], [], []
    seen = set()
    offset = 0
    while offset < len(raw):
        newline = raw.find(b'\n', offset)
        end = len(raw) if newline < 0 else newline + 1
        line = raw[offset:end]
        value = _load(line)
        row_id = 'row-%d' % (len(rows) + 1)
        rows.append({'id': row_id, 'start_byte': offset, 'end_byte': end,
                     'sha256': hashlib.sha256(line).hexdigest(), 'value': value})
        offset = end
        if len(rows) == 1:
            _require(value.get('type') == 'session'
                     and type(value.get('version')) is int and value['version'] == 0
                     and type(value.get('id')) is str and bool(value['id']),
                     'invalid_runtime_header')
            continue
        kind = value.get('type')
        _require(type(kind) is str and bool(kind) and kind != 'session')
        if kind in BATCH_TYPES:
            members = _expand_batch(value, MAX_EVENTS - len(events))
        else:
            _require('seq0' not in value and 'time0' not in value)
            _require(_integer(value.get('seq'), 0) and _integer(value.get('time')))
            _require(len(events) < MAX_EVENTS, 'runtime_limit_exceeded')
            members = [value]
        for index, event in enumerate(members):
            _require(event['seq'] not in seen, 'duplicate_runtime_seq')
            seen.add(event['seq'])
            events.append({'row_id': row_id,
                           'member_index': index if kind in BATCH_TYPES else None,
                           'value': event})
        if 'sourceEventSeqs' in value:
            references.extend(_references(value['sourceEventSeqs'],
                                          MAX_REFERENCES - len(references)))
    # No materializar range(max_seq): una secuencia distante puede ser válida.
    missing_count = max(seen) + 1 - len(seen) if seen else 0
    return {'schema': 'skopos/experimental-dsh-reader/v0',
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_bytes': len(raw),
            'rows': rows, 'events': events,
            'diagnostics': {'sequence_gap_count': missing_count,
                            'reference_count': len(references),
                            'unresolved_reference_count': sum(x not in seen for x in references)},
            'capture_completeness': 'unknown', 'producer_claims': 'not_verified'}
