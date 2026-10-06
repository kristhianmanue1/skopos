"""Constructor experimental runtime: proyección selectiva, sin IO ni almacén.

Ejecutar con este directorio en la ruta de importación. No es un validador
de sobres externos ni una interfaz pública de búsqueda o control de acceso.
"""
import hashlib
import json

from reader import parse
from skopos.source_envelope import _identifier, _capture_time, DIGEST, MAX_REVISION

MAX_BLOCKS = 100_000


def _string(value):
    return type(value) is str and bool(value)


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _message(event):
    """Selecciona estructura y origen; no interpreta contenido ni autoridad."""
    kind = event['type']
    if kind not in ('user/message', 'assistant/message'):
        return None, 'event_type'
    data = event.get('data')
    assistant = kind == 'assistant/message'
    if assistant and type(data) is dict and 'interrupted' in data:
        return None, 'interrupted'
    message = data.get('message') if assistant and type(data) is dict else data
    if (type(message) is not dict or set(message) != {'id', 'role', 'content', 'source'}
            or not _string(message['id'])
            or message['role'] != ('assistant' if assistant else 'user')
            or type(message['content']) is not list or type(message['source']) is not dict):
        return None, 'invalid_message_projection'
    origin = message['source']
    if not _string(origin.get('kind')):
        return None, 'invalid_message_projection'
    if origin['kind'] != ('model' if assistant else 'user'):
        return None, 'source_kind'
    required = {'kind', 'provider', 'model'} if assistant else {'kind'}
    optional = {'replayState'} if assistant else {'rpcId', 'clientTimeZone'}
    if (not required <= origin.keys() or not origin.keys() <= required | optional
            or any(not _string(origin[key]) for key in required)
            or (not assistant and any(not _string(origin[key])
                                       for key in optional if key in origin))):
        return None, 'invalid_message_projection'
    return message, None


def _project(parsed):
    texts = []
    event_exclusions = dict.fromkeys(('event_type', 'interrupted',
                                     'invalid_message_projection', 'source_kind'), 0)
    block_exclusions = {'non_text': 0, 'empty_text': 0}
    examined = 0
    # Presupuesto previo a proyectar: también mensajes que luego se excluyen.
    for descriptor in parsed['events']:
        event = descriptor['value']
        data = event.get('data')
        if event['type'] == 'assistant/message' and type(data) is dict:
            data = data.get('message')
        if (event['type'] in ('user/message', 'assistant/message')
                and type(data) is dict and type(data.get('content')) is list):
            examined += len(data['content'])
            if examined > MAX_BLOCKS:
                raise ValueError('runtime_limit_exceeded')
    for descriptor in parsed['events']:
        event = descriptor['value']
        message, reason = _message(event)
        if reason:
            event_exclusions[reason] += 1
            continue
        content = message['content']
        # Comprobar todo antes de emitir: un text mal formado invalida el mensaje.
        if any(type(block) is not dict or not _string(block.get('type'))
               or (block['type'] == 'text' and
                   (set(block) != {'type', 'text'} or type(block['text']) is not str))
               for block in content):
            event_exclusions['invalid_message_projection'] += 1
            continue
        event_id = 'event-%d' % event['seq']
        prefix = '/data/message/content/' if event['type'] == 'assistant/message' else '/data/content/'
        for index, block in enumerate(content):
            if block['type'] != 'text':
                block_exclusions['non_text'] += 1
            elif not block['text'].strip():
                block_exclusions['empty_text'] += 1
            else:
                texts.append({'id': '%s-block-%d' % (event_id, index),
                              'event_id': event_id, 'row_id': descriptor['row_id'],
                              'block_index': index, 'pointer': prefix + str(index),
                              'role': message['role'], 'source_kind': message['source']['kind'],
                              'text': block['text'],
                              'derived_text_sha256': _digest(block['text'].encode('utf-8'))})
    return texts, {'events_excluded': event_exclusions,
                   'blocks_excluded': block_exclusions, 'blocks_examined': examined}


def build_envelope(raw, *, project_id, source_id, captured_at,
                   source_revision=1, previous_source_sha256=None,
                   capture_completeness='unknown', completeness_basis=None):
    """Construye desde bytes; no valida cadena de revisiones ni adjudica captura."""
    if type(raw) is not bytes:
        raise ValueError('invalid_source_bytes')
    project_id = _identifier(project_id, 'project_id')
    source_id = _identifier(source_id, 'source_id')
    timestamp = _capture_time(captured_at)
    if type(source_revision) is not int or not 1 <= source_revision <= MAX_REVISION:
        raise ValueError('invalid_source_revision')
    if source_revision == 1:
        if previous_source_sha256 is not None:
            raise ValueError('invalid_predecessor')
    elif type(previous_source_sha256) is not str or not DIGEST.fullmatch(previous_source_sha256):
        raise ValueError('invalid_predecessor')
    if (type(capture_completeness) is not str
            or capture_completeness not in ('unknown', 'partial', 'complete')):
        raise ValueError('invalid_completeness')
    if capture_completeness == 'unknown':
        if completeness_basis is not None:
            raise ValueError('invalid_completeness_basis')
    else:
        if (type(completeness_basis) is not str or not completeness_basis.strip()
                or len(completeness_basis) > 512):
            raise ValueError('invalid_completeness_basis')
        try:
            completeness_basis.encode('utf-8')
        except UnicodeError:
            raise ValueError('invalid_completeness_basis') from None
    parsed = parse(raw)
    texts, exclusions = _project(parsed)
    result = {
        'schema': 'skopos/source-envelope/v2', 'source_kind': 'runtime-events',
        'project_id': project_id, 'source_id': source_id,
        'source_revision': source_revision, 'previous_source_sha256': previous_source_sha256,
        'captured_at': timestamp, 'captured_at_basis': 'caller_declared',
        'occurred_at': None,
        'capture_completeness': {'value': capture_completeness, 'basis': completeness_basis},
        'source_sha256': parsed['source_sha256'], 'source_bytes': parsed['source_bytes'],
        'adapter': {'id': 'skopos/experimental-runtime-envelope/v0',
                    'format': 'dsh-session-v0-jsonl'},
        'projection_policy': 'skopos/runtime-text-policy/v0',
        'producer_claims': 'not_verified',
        'rows': [{key: row[key] for key in ('id', 'start_byte', 'end_byte', 'sha256')}
                 for row in parsed['rows']],
        'events': [{'id': 'event-%d' % item['value']['seq'],
                    **{key: item['value'][key] for key in ('seq', 'time', 'type')},
                    'row_id': item['row_id'], 'member_index': item['member_index']}
                   for item in parsed['events']],
        'texts': texts, 'diagnostics': {**parsed['diagnostics'], **exclusions}}
    result['envelope_sha256'] = _digest(json.dumps(result, ensure_ascii=False,
                                                  sort_keys=True, separators=(',', ':')).encode())
    return result
