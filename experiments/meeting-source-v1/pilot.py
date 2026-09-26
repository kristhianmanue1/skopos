"""Piloto local y sintético de fuentes de reunión; no usa Mongo ni un LLM."""
import copy
import hashlib
import json
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_source(path):
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if set(value) != {'source_id', 'revision', 'supersedes', 'complete', 'segments'}:
        raise ValueError('invalid_source')
    if not isinstance(value['source_id'], str) or not value['source_id']:
        raise ValueError('invalid_identity')
    if type(value['revision']) is not int or value['revision'] < 1 or type(value['complete']) is not bool:
        raise ValueError('invalid_revision_or_completeness')
    if not isinstance(value['segments'], list) or not value['segments']:
        raise ValueError('invalid_segments')
    seen = set()
    for segment in value['segments']:
        if set(segment) != {'id', 'start_ms', 'end_ms', 'speaker', 'text'}:
            raise ValueError('invalid_segment')
        if any(type(segment[k]) is not str or not segment[k].strip() for k in ('id','speaker','text')):
            raise ValueError('invalid_segment_text')
        if any(type(segment[k]) is not int for k in ('start_ms','end_ms')) or not 0 <= segment['start_ms'] < segment['end_ms'] or segment['id'] in seen:
            raise ValueError('invalid_locator')
        seen.add(segment['id'])
    return value, digest(raw)


class MeetingStore:
    """Almacén efímero para probar el contrato; no es persistencia de producto."""
    def __init__(self):
        self.sources = {}

    def ingest(self, path):
        value, checksum = read_source(path)
        versions = self.sources.get(value['source_id'], {})
        revision = value['revision']
        if revision in versions:
            if versions[revision]['sha256'] != checksum:
                raise ValueError('revision_conflict')
            return 'duplicate'
        current = max(versions, default=0)
        predecessor = versions[current]['sha256'] if current else None
        if revision != current + 1 or value['supersedes'] != predecessor:
            raise ValueError('invalid_revision_chain')
        versions[revision] = {'value':copy.deepcopy(value), 'sha256':checksum,
                              'path':str(Path(path).resolve())}
        self.sources[value['source_id']] = versions
        return 'imported'

    def search(self, term):
        if type(term) is not str or not term.strip():
            raise ValueError('invalid_term')
        results = []
        for source_id, versions in self.sources.items():
            record = versions[max(versions)]
            value = record['value']
            for segment in value['segments']:
                if term.casefold() in segment['text'].casefold():
                    results.append({'source_id':source_id, 'revision':value['revision'],
                                    'sha256':record['sha256'], 'complete':value['complete'],
                                    'locator':{k:segment[k] for k in ('id','start_ms','end_ms','speaker')},
                                    'text':segment['text'], 'integrity':'not_checked'})
        return results

    def fetch(self, source_id, revision, segment_id):
        record = self.sources[source_id][revision]
        try:
            raw = Path(record['path']).read_bytes()
        except OSError:
            return {'status':'source_unavailable'}
        if digest(raw) != record['sha256']:
            return {'status':'integrity_mismatch'}
        for segment in record['value']['segments']:
            if segment['id'] == segment_id:
                return {'status':'verified', 'sha256':record['sha256'],
                        'complete':record['value']['complete'], 'segment':copy.deepcopy(segment)}
        return {'status':'segment_not_found'}
