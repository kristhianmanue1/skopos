"""Sobre puro de fuentes (ADR-020); identidad y procedencia sin persistencia."""
from datetime import datetime, timezone
import hashlib
import json
import re

from skopos.source_reader import MAX_BYTES, parse

MAX_SEGMENTS = 10_000
MAX_REVISION = 2**63 - 1
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')
DIGEST = re.compile(r'[0-9a-f]{64}')
CAPTURE_TIME = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?'
    r'(?:Z|[+-](?:(?:0\d|1[0-3]):[0-5]\d|14:00))'
)


def _identifier(value, field):
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        raise ValueError('invalid_' + field)
    return value


def _capture_time(value):
    if (type(value) is not str or CAPTURE_TIME.fullmatch(value) is None
            or value.endswith('-00:00')):
        raise ValueError('invalid_capture_time')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except (ValueError, OverflowError):
        raise ValueError('invalid_capture_time') from None


def build_envelope(raw, *, project_id, source_id, captured_at,
                   source_revision=1, previous_source_sha256=None,
                   capture_completeness='unknown', completeness_basis=None):
    """Construye datos; no verifica autoridad, cadena de revisiones ni audio."""
    if type(raw) is not bytes:
        raise ValueError('invalid_source_bytes')
    project_id = _identifier(project_id, 'project_id')
    source_id = _identifier(source_id, 'source_id')
    if type(source_revision) is not int or not 1 <= source_revision <= MAX_REVISION:
        raise ValueError('invalid_source_revision')
    if source_revision == 1:
        if previous_source_sha256 is not None:
            raise ValueError('invalid_predecessor')
    elif (type(previous_source_sha256) is not str
          or DIGEST.fullmatch(previous_source_sha256) is None):
        raise ValueError('invalid_predecessor')
    if (type(capture_completeness) is not str
            or capture_completeness not in ('unknown', 'partial', 'complete')):
        raise ValueError('invalid_completeness')
    if capture_completeness == 'unknown':
        if completeness_basis is not None:
            raise ValueError('invalid_completeness_basis')
    elif (type(completeness_basis) is not str or not completeness_basis.strip()
          or len(completeness_basis) > 512):
        raise ValueError('invalid_completeness_basis')
    timestamp = _capture_time(captured_at)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('source_size_out_of_range')
    # Limitar antes de construir los objetos de segmento; no truncar el origen.
    if sum(bool(line.strip()) for line in raw.decode('utf-8').splitlines()) > MAX_SEGMENTS:
        raise ValueError('segment_limit_exceeded')
    parsed = parse(raw)
    if len(parsed['segments']) > MAX_SEGMENTS:
        raise ValueError('segment_limit_exceeded')
    result = {
        'schema': 'skopos/source-envelope/v0',
        'project_id': project_id, 'source_id': source_id,
        'source_kind': 'meeting-transcript', 'source_revision': source_revision,
        'previous_source_sha256': previous_source_sha256,
        'source_sha256': parsed['source_sha256'], 'source_bytes': len(raw),
        'adapter': {'id': 'skopos/diarized-reader/v0', 'format': parsed['schema']},
        'captured_at': timestamp, 'captured_at_basis': 'caller_declared',
        'occurred_at': None,
        'capture_completeness': {'value': capture_completeness,
                                 'basis': completeness_basis},
        'audio_alignment': 'not_verified', 'speaker_identity': 'not_verified',
        'segments': parsed['segments'], 'adjacent_overlaps': parsed['adjacent_overlaps'],
    }
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':')).encode('utf-8')
    result['envelope_sha256'] = hashlib.sha256(canonical).hexdigest()
    return result
