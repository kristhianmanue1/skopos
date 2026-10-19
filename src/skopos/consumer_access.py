"""Frontera de lectura por consumidor para el almacén de fuentes (T2).

Contrato `source-consumer-access-v0.1-local.md`: política fail-closed con
lista exacta `allowed_projects` y rechazo tipado `project_not_allowed` antes
de delegar, uniforme —sin distinguir proyecto existente de inexistente— para
no servir contenido ni metadatos de existencia del proyecto ajeno. La
superficie cubierta es la declarada en T0: search, search runtime, fetch,
fetch runtime y receipt. `import` queda fuera porque es admisión (autoridad
del Operador), no acceso de consumidor. El guard no construye conexiones:
el punto y la base salen de la política en la frontera CLI, donde el prefijo
loopback de `mongo_uri` amarra de verdad.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

POLICY_SCHEMA = 'skopos/source-consumer-access-policy/v0.1'
POLICY_FIELDS = frozenset(
    {'schema', 'consumer_id', 'mongo_uri', 'database', 'allowed_projects'})
MAX_POLICY_BYTES = 64 * 1024
# Un solo host loopback, sin lista de seeds ni replicaSet=: el
# descubrimiento de topología no puede ampliar la conexión fuera de
# 127.0.0.1 (ronda adversarial 2026-10-19, H1).
URI_RE = re.compile(r'mongodb://127\.0\.0\.1:\d{1,5}(/.*)?')


def _text(value) -> bool:
    return type(value) is str and bool(value.strip())


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            # El digest ampara los bytes, no la interpretación: dos lecturas
            # humanas no deben discrepar de la política efectiva (ADR-021).
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def load_consumer_policy(path):
    """Carga y valida la política en carga, no en uso; sin ella nada se sirve.

    Toda violación —archivo ausente o ilegible, JSON inválido, conjunto de
    campos distinto, esquema ajeno, uri sin prefijo loopback `127.0.0.1`,
    lista vacía, repetida o con elementos que no son texto— se rechaza con
    el mismo código `policy_unavailable`, sin distinguir la causa.
    """
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise ValueError('policy_unavailable') from None
    if len(raw) > MAX_POLICY_BYTES:
        raise ValueError('policy_unavailable')
    try:
        policy = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, ValueError):
        raise ValueError('policy_unavailable') from None
    if (not isinstance(policy, dict) or set(policy) != POLICY_FIELDS
            or policy['schema'] != POLICY_SCHEMA
            or not _text(policy['consumer_id'])
            or not (type(policy['mongo_uri']) is str
                    and URI_RE.fullmatch(policy['mongo_uri'])
                    and ',' not in policy['mongo_uri']
                    and 'replicaset=' not in policy['mongo_uri'].casefold())
            or not _text(policy['database'])
            or type(policy['allowed_projects']) is not list
            or not policy['allowed_projects']
            or not all(_text(item) for item in policy['allowed_projects'])
            or len(set(policy['allowed_projects'])) != len(policy['allowed_projects'])):
        raise ValueError('policy_unavailable')
    return policy, hashlib.sha256(raw).hexdigest()


class ConsumerAccessStore:
    """Sirve las cinco operaciones de la superficie tras una sola verificación.

    La política debe provenir de `load_consumer_policy`; el constructor sólo
    comprueba lo estructural para no aceptar políticas fabricadas.
    """

    def __init__(self, store, policy, policy_sha256):
        if (not isinstance(policy, dict) or set(policy) != POLICY_FIELDS
                or type(policy['allowed_projects']) is not list
                or not policy['allowed_projects']
                or not _text(policy_sha256)):
            raise ValueError('policy_unavailable')
        self._store = store
        self._consumer_id = policy['consumer_id']
        self._policy_sha256 = policy_sha256
        self._allowed_projects = frozenset(policy['allowed_projects'])

    def _require(self, project_id):
        # Uniforme y antes de delegar: el almacén ni se toca, así que el
        # rechazo no filtra contenido ni existencia del proyecto ajeno.
        # El tipo se comprueba primero: un project_id no de texto también
        # es "no listado", no un accidente de hash (ronda H7).
        if type(project_id) is not str or project_id not in self._allowed_projects:
            raise ValueError('project_not_allowed')

    def _served(self, result):
        result['access'] = {'consumer_id': self._consumer_id,
                            'policy_sha256': self._policy_sha256}
        return result

    def search(self, *, project_id, term, limit=20):
        self._require(project_id)
        return self._served(
            self._store.search(project_id=project_id, term=term, limit=limit))

    def search_runtime(self, *, project_id, term, limit=20):
        self._require(project_id)
        return self._served(
            self._store.search_runtime(project_id=project_id, term=term, limit=limit))

    def fetch(self, *, project_id, source_id, source_revision, source_sha256,
              segment_id):
        self._require(project_id)
        return self._served(
            self._store.fetch(project_id=project_id, source_id=source_id,
                              source_revision=source_revision,
                              source_sha256=source_sha256, segment_id=segment_id))

    def fetch_runtime(self, *, project_id, source_id, source_revision,
                      source_sha256, view, text_id=None, row_id=None, event_id=None):
        self._require(project_id)
        return self._served(
            self._store.fetch_runtime(project_id=project_id, source_id=source_id,
                                      source_revision=source_revision,
                                      source_sha256=source_sha256, view=view,
                                      text_id=text_id, row_id=row_id,
                                      event_id=event_id))

    def receipt(self, *, project_id, source_id, source_revision, source_sha256):
        self._require(project_id)
        return self._served(
            self._store.receipt(project_id=project_id, source_id=source_id,
                                source_revision=source_revision,
                                source_sha256=source_sha256))
