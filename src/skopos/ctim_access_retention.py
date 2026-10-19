"""Retención duradera de pares petición/respuesta servidos por el acceso CTIM.

Un par servido sólo es verificable por el consumidor si Skopos conserva sus
bytes. Este módulo escribe cada par en forma canónica, falla cerrado ante
colisión y permite al consumidor recargar y revalidar el par por request_id.
La retención es de procedencia: no acredita fidelidad ni autoría del original.
"""

import json
import os
import re
import tempfile
from pathlib import Path

from skopos.ctim_source_access import AccessError, ID, _canonical, _sha

PAIR_SCHEMA = 'skopos/ctim-served-pair/v0.1'
MAX_RETAINED_PAIR_BYTES = 512 * 1024


def retain_served_pair(retention_dir, request, response):
    """Escribe el par servido; reusa la forma canónica del contrato de acceso."""
    directory = Path(retention_dir)
    request_id = request.get('request_id') if isinstance(request, dict) else None
    if (not isinstance(request_id, str) or ID.fullmatch(request_id) is None
            or not isinstance(response, dict)):
        raise AccessError('retention_invalid_pair')
    record = {'schema': PAIR_SCHEMA, 'request': request, 'response': response,
              'request_sha256': _sha(_canonical(request)),
              'response_sha256': _sha(_canonical(response))}
    payload = _canonical(record) + b'\n'
    if len(payload) > MAX_RETAINED_PAIR_BYTES:
        raise AccessError('retention_pair_too_large')
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (request_id + '.json')
    if path.exists():
        raise AccessError('retention_collision')
    handle = tempfile.NamedTemporaryFile(dir=str(directory), delete=False,
                                          prefix='.retention-')
    temporary = handle.name
    try:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise AccessError('retention_collision') from None
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return {'path': str(path), 'request_sha256': record['request_sha256'],
            'response_sha256': record['response_sha256']}


def load_served_pair(retention_dir, request_id):
    """Recarga un par retenido y revalida sus hashes; falla cerrado ante deriva."""
    if not isinstance(request_id, str) or ID.fullmatch(request_id) is None:
        raise AccessError('retention_invalid_pair')
    path = Path(retention_dir) / (request_id + '.json')
    if not path.is_file():
        raise AccessError('retention_pair_not_found')
    try:
        record = json.loads(path.read_bytes())
    except (UnicodeError, ValueError):
        raise AccessError('retention_pair_corrupt') from None
    if (not isinstance(record, dict) or record.get('schema') != PAIR_SCHEMA
            or not isinstance(record.get('request'), dict)
            or not isinstance(record.get('response'), dict)):
        raise AccessError('retention_pair_corrupt')
    if (_sha(_canonical(record['request'])) != record.get('request_sha256')
            or _sha(_canonical(record['response'])) != record.get('response_sha256')):
        raise AccessError('retention_pair_drift')
    return record
