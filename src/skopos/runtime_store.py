"""Almacén mixto de fuentes; activación y custodia son decisiones separadas."""
from datetime import datetime, timezone
from pathlib import Path

from bson import BSON
from bson.int64 import Int64
from bson.errors import InvalidDocument
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo import ReadPreference

from skopos.source_store import (SourceStore, read_source, revision_key, _digest,
                                 MAX_BSON_BYTES, DECLARATION as TRANSCRIPT_DECLARATION)
from skopos.source_envelope import _identifier
from skopos.runtime_envelope import build_envelope
from skopos.runtime_verification import validate, verify, checksum
from skopos.runtime_views import fetch_verified, search_verified, DECLARATION


def json_integers(value):
    """Restaurar enteros JSON tras BSON; no convertir bool ni otros tipos."""
    if type(value) is Int64:
        return int(value)
    if type(value) is dict:
        return {key: json_integers(item) for key, item in value.items()}
    if type(value) is list:
        return [json_integers(item) for item in value]
    return value


class RuntimeSourceStore(SourceStore):
    """Fuentes runtime y transcripciones, sin ACL multiusuario propia."""

    @staticmethod
    def _verified_envelope(document, expected_key=None):
        document = json_integers(document)
        try:
            envelope = document['envelope']
            if envelope['schema'] not in ('skopos/source-envelope/v0', 'skopos/source-envelope/v1',
                                           'skopos/source-envelope/v2'):
                raise ValueError('unsupported_envelope_version')
            if envelope['schema'] != 'skopos/source-envelope/v2':
                result = SourceStore._verified_envelope(document, expected_key)
                if result['source_kind'] != 'meeting-transcript':
                    raise ValueError('store_integrity_failed')
                return result
            key = revision_key(document['project_id'], document['source_id'], document['source_revision'])
            if (set(document) != {'_id', 'schema', 'project_id', 'source_id', 'source_revision',
                                  'envelope', 'source_path', 'admitted_at'}
                    or document['schema'] != 'skopos/source-record/v3'
                    or document['_id'] != key or (expected_key is not None and key != expected_key)
                    or type(document['admitted_at']) is not str
                    or type(document['source_path']) is not str
                    or not Path(document['source_path']).is_absolute()
                    or any(type(document[k]) is not type(envelope[k]) or document[k] != envelope[k]
                           for k in ('project_id', 'source_id', 'source_revision'))):
                raise ValueError('store_integrity_failed')
            validate(envelope)
            return envelope
        except (KeyError, TypeError):
            raise ValueError('store_integrity_failed') from None

    @staticmethod
    def _verified_raw(document):
        envelope = RuntimeSourceStore._verified_envelope(document)
        raw = read_source(document['source_path'])
        if len(raw) != envelope['source_bytes'] or checksum(raw) != envelope['source_sha256']:
            raise ValueError('source_integrity_failed')
        return raw

    def _head_document(self, head, project_id, session=None):
        head = json_integers(head)
        try:
            key = revision_key(project_id, head['source_id'], head['source_revision'])
            if (head['_id'] != project_id + ':' + head['source_id']
                    or head['project_id'] != project_id or head['revision_key'] != key):
                raise ValueError('store_integrity_failed')
            document = self.revisions.find_one({'_id': key}, session=session)
            document = json_integers(document)
            if (document is None or document['project_id'] != project_id
                    or document['source_id'] != head['source_id']
                    or type(document['source_revision']) is not int
                    or document['source_revision'] != head['source_revision']
                    or any(type(document[k]) is not type(document['envelope'][k])
                           or document[k] != document['envelope'][k]
                           for k in ('project_id', 'source_id', 'source_revision'))
                    or document['envelope']['source_sha256'] != head['source_sha256']):
                raise ValueError('store_integrity_failed')
            return document
        except (KeyError, TypeError, ValueError):
            raise ValueError('store_integrity_failed') from None

    def _publish(self, document, session):
        # Validar familia dentro de la misma transacción que CAS e inserción.
        existing = self.revisions.find_one({'_id': document['_id']}, session=session)
        if existing is None:
            head = self.heads.find_one({'_id': document['project_id'] + ':' + document['source_id']}, session=session)
            if head is not None:
                existing = self._head_document(head, document['project_id'], session)
        if existing is not None:
            previous = self._verified_envelope(existing)
            if previous['source_kind'] != document['envelope']['source_kind']:
                raise ValueError('source_kind_conflict')
        return super()._publish(document, session)

    def import_file(self, path, *, project_id, source_id, captured_at,
                    source_revision=1, expected_previous_sha256=None,
                    capture_completeness='unknown', completeness_basis=None,
                    source_format='diarized-text'):
        metadata = dict(project_id=project_id, source_id=source_id, captured_at=captured_at,
                        source_revision=source_revision, expected_previous_sha256=expected_previous_sha256,
                        capture_completeness=capture_completeness, completeness_basis=completeness_basis)
        if source_format != 'dsh-session-v0-jsonl':
            return super().import_file(path, source_format=source_format, **metadata)
        raw = read_source(path)
        metadata['previous_source_sha256'] = metadata.pop('expected_previous_sha256')
        envelope = build_envelope(raw, **metadata)
        verify(envelope, raw)
        document = {'_id': revision_key(project_id, source_id, source_revision),
                    'schema': 'skopos/source-record/v3', 'project_id': project_id,
                    'source_id': source_id, 'source_revision': source_revision,
                    'envelope': envelope, 'source_path': str(Path(path).absolute()),
                    'admitted_at': datetime.now(timezone.utc).isoformat()}
        try:
            if len(BSON.encode(document)) > MAX_BSON_BYTES:
                raise ValueError('source_record_too_large')
        except (OverflowError, InvalidDocument):
            raise ValueError('source_record_not_encodable') from None
        self._prepare()
        for attempt in range(3):
            try:
                with self.database.client.start_session() as session:
                    return session.with_transaction(lambda current: self._publish(document, current),
                                                    read_concern=ReadConcern('snapshot'),
                                                    write_concern=WriteConcern('majority'),
                                                    read_preference=ReadPreference.PRIMARY)
            except DuplicateKeyError:
                if attempt == 2:
                    raise ValueError('revision_conflict') from None

    def fetch(self, *, project_id, source_id, source_revision, source_sha256, segment_id):
        key = revision_key(project_id, source_id, source_revision)
        _digest(source_sha256)
        document = self.revisions.find_one({'_id': key})
        if document is not None:
            if self._verified_envelope(document, key)['source_kind'] != 'meeting-transcript':
                raise ValueError('source_kind_conflict')
        return super().fetch(project_id=project_id, source_id=source_id, source_revision=source_revision,
                             source_sha256=source_sha256, segment_id=segment_id)

    def fetch_runtime(self, *, project_id, source_id, source_revision, source_sha256,
                      view, text_id=None, row_id=None, event_id=None):
        key = revision_key(project_id, source_id, source_revision)
        _digest(source_sha256)
        selectors = {'text_projection': text_id, 'original_jsonl': row_id, 'derived_event': event_id}
        if type(view) is not str or view not in selectors:
            raise ValueError('invalid_runtime_view')
        if (type(selectors[view]) is not str or not selectors[view]
                or sum(x is not None for x in (text_id, row_id, event_id)) != 1):
            raise ValueError('invalid_runtime_selector')
        document = self.revisions.find_one({'_id': key})
        if document is None:
            raise ValueError('revision_not_found')
        envelope = self._verified_envelope(document, key)
        if envelope['source_kind'] != 'runtime-events':
            raise ValueError('source_kind_conflict')
        if envelope['source_sha256'] != source_sha256:
            raise ValueError('revision_conflict')
        return fetch_verified(envelope, self._verified_raw(document), project_id=project_id,
                              source_id=source_id, source_revision=source_revision,
                              source_sha256=source_sha256, view=view,
                              text_id=text_id, row_id=row_id, event_id=event_id)

    def search(self, *, project_id, term, limit=20):
        return self._search(project_id, term, limit, False)

    def search_runtime(self, *, project_id, term, limit=20):
        return self._search(project_id, term, limit, True)

    def _search(self, project_id, term, limit, runtime):
        _identifier(project_id, 'project_id')
        try:
            valid = type(term) is str and bool(term.strip()) and len(term.encode()) <= 1024
        except UnicodeError:
            valid = False
        if not valid:
            raise ValueError('invalid_term')
        if type(limit) is not int or not 0 <= limit <= 20:
            raise ValueError('invalid_limit')
        results, unavailable = [], {}
        excluded = {'result_limit': 0, 'fragment_too_large': 0}
        other = 'meeting-transcript' if runtime else 'runtime-events'
        families = {other: 0}
        for head in self.heads.find({'project_id': project_id}).sort('source_id', 1):
            document = self._head_document(head, project_id)
            try:
                envelope = self._verified_envelope(document, head['revision_key'])
                if envelope['source_kind'] == other:
                    families[other] += 1
                    continue
                raw = self._verified_raw(document)
                if runtime:
                    found = search_verified(envelope, raw, project_id=project_id,
                                            term=term, limit=limit - len(results))
                else:
                    # Acumular por fuente: no filtrar resultados previos al último error.
                    local, counts = [], {'result_limit': 0, 'fragment_too_large': 0}
                    for segment in envelope['segments']:
                        if term.casefold() not in segment['text'].casefold():
                            continue
                        try:
                            fragment = self._fragment(document, segment, raw)
                        except ValueError as error:
                            if str(error) != 'fragment_too_large':
                                raise
                            counts['fragment_too_large'] += 1
                            continue
                        if len(results) + len(local) >= limit:
                            counts['result_limit'] += 1
                        else:
                            local.append(fragment)
                    found = {'results': local, 'excluded': counts}
            except ValueError as error:
                code = str(error)
                unavailable[code] = unavailable.get(code, 0) + 1
                continue
            results.extend(found['results'])
            for key in excluded:
                excluded[key] += found['excluded'][key]
        return {'results': results, 'excluded': excluded, 'unavailable_sources': unavailable,
                'excluded_source_kinds': families, 'selection': 'per_source_head_observed',
                'declaration': DECLARATION if runtime else TRANSCRIPT_DECLARATION}


class LaboratoryStore(RuntimeSourceStore):
    """Compatibilidad del laboratorio; no elimina sus restricciones de destino."""

    def __init__(self, database):
        if not database.name.startswith("skopos_test"):
            raise ValueError("laboratory_database_required")
        host, port = database.client.address
        if host not in ("127.0.0.1", "localhost", "::1") or port == 27017:
            raise ValueError("laboratory_endpoint_required")
        super().__init__(database)
