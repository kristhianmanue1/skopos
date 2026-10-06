"""Perfil JSON ASR observado: original intacto y derivación explícita (ADR-021)."""
import json
import math
import re

from skopos.source_reader import MAX_BYTES, checksum

MAX_DEPTH = 64
MAX_SEGMENTS = 10_000
MAX_WORDS = 200_000
SPACE = re.compile(r'[ \t\r\n]*')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('invalid_json_number')


def load_json(raw):
    """Valida sintaxis/Unicode/números y profundidad sin ejecutar contenido."""
    if type(raw) is not bytes:
        raise ValueError('invalid_source_bytes')
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('source_size_out_of_range')
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        raise ValueError('invalid_json_utf8') from None
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
            if depth > MAX_DEPTH:
                raise ValueError('json_depth_exceeded')
        elif char in ']}':
            depth -= 1
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (json.JSONDecodeError, RecursionError):
        raise ValueError('invalid_json') from None
    except ValueError as error:
        if str(error) in ('duplicate_json_key', 'invalid_json_number'):
            raise
        raise ValueError('invalid_json_number') from None
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str):
            try:
                item.encode('utf-8')
            except UnicodeError:
                raise ValueError('invalid_json_unicode') from None
        elif type(item) is float and not math.isfinite(item):
            raise ValueError('invalid_json_number')
        elif type(item) is int and not -(2**63) <= item < 2**63:
            raise ValueError('invalid_json_number')
    return value


def _spans(text):
    """Rangos de objetos segments en JSON ya validado; nunca buscar texto por regex."""
    decoder = json.JSONDecoder()
    position = SPACE.match(text, 0).end() + 1
    while True:
        position = SPACE.match(text, position).end()
        if text[position] == '}':
            return
        key, position = decoder.raw_decode(text, position)
        position = SPACE.match(text, position).end() + 1  # dos puntos validado
        position = SPACE.match(text, position).end()
        if key == 'segments':
            position += 1  # corchete validado
            previous_char = previous_byte = 0
            while True:
                position = SPACE.match(text, position).end()
                if text[position] == ']':
                    return
                start = position
                _, position = decoder.raw_decode(text, start)
                start_byte = previous_byte + len(text[previous_char:start].encode('utf-8'))
                end_byte = start_byte + len(text[start:position].encode('utf-8'))
                yield start_byte, end_byte
                previous_char, previous_byte = position, end_byte
                position = SPACE.match(text, position).end()
                if text[position] == ',':
                    position += 1
        else:
            _, position = decoder.raw_decode(text, position)
            position = SPACE.match(text, position).end()
            if text[position] == ',':
                position += 1


def _number(value):
    return type(value) in (float, int) and math.isfinite(value) and value >= 0


def _speaker(item):
    value = item.get('speaker')
    if value is not None and (type(value) is not str or not value.strip()):
        raise ValueError('invalid_speaker')
    return value


def parse(raw):
    data = load_json(raw)
    if type(data) is not dict or type(data.get('segments')) is not list:
        raise ValueError('invalid_whisperx_schema')
    segments = data['segments']
    if not 1 <= len(segments) <= MAX_SEGMENTS:
        raise ValueError('segment_limit_exceeded')
    derived = []
    words = []
    for item in segments:
        if (type(item) is not dict or not _number(item.get('start'))
                or not _number(item.get('end')) or item['end'] <= item['start']
                or type(item.get('text')) is not str or not item['text'].strip()
                or type(item.get('words')) is not list):
            raise ValueError('invalid_whisperx_segment')
        if len(words) + len(item['words']) > MAX_WORDS:
            raise ValueError('word_limit_exceeded')
        for word in item['words']:
            if (type(word) is not dict or type(word.get('word')) is not str
                    or not word['word'].strip()):
                raise ValueError('invalid_whisperx_word')
            if 'start' in word or 'end' in word:
                if (not _number(word.get('start')) or not _number(word.get('end'))
                        or word['end'] < word['start']):
                    raise ValueError('invalid_word_time')
            if 'score' in word and (not _number(word['score']) or word['score'] > 1):
                raise ValueError('invalid_word_score')
            _speaker(word)
        words.extend(item['words'])
        derived.append({'id': 'segment-%06d' % (len(derived) + 1),
                        'start_seconds': item['start'], 'end_seconds': item['end'],
                        'speaker': _speaker(item), 'text': item['text'],
                        'word_count': len(item['words']),
                        'derived_text_sha256': checksum(item['text'].encode('utf-8'))})
    if 'word_segments' in data:
        # Igualdad de Python confunde true con 1: comparar representación tipada.
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(',', ':'))
        if canonical(data['word_segments']) != canonical(words):
            raise ValueError('word_segments_mismatch')
    for index, (segment, (start, end)) in enumerate(zip(derived, _spans(raw.decode('utf-8')))):
        segment['locator'] = {'kind': 'json-value', 'pointer': '/segments/%d' % index,
                              'start_byte': start, 'end_byte': end,
                              'sha256': checksum(raw[start:end])}
    if any('locator' not in segment for segment in derived):
        raise ValueError('json_locator_missing')
    return {'schema': 'skopos/whisperx-json/v1', 'segments': derived,
            'source_sha256': checksum(raw), 'source_bytes': len(raw)}
