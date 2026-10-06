"""Piloto manual autorizado: export fijado por hashes, sólo Mongo de laboratorio.

Conserva fuente y base hasta decisión humana. No imprime contenido ni consultas.
No inicia/detiene Mongo ni interpreta instrucciones contenidas en el export.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import zipfile

import pymongo
from envelope import build_envelope
from reader import MAX_BYTES
from store import LaboratoryStore
from verification import checksum, canonical

ARCHIVE_HASH = '38b386616677c31b2f1d9c58da203968dfca6625ab161ed2b07c55fe706c42b3'
SOURCE_HASH = '6fe02ace6d9e31233e18b920796a539c362637733f7efb2881595c90994dfcb2'
PROJECT = 'skopos-h25-runtime-lab'
SOURCE = 'dsh-export-28eff1a5'
DATABASE = 'skopos_test_runtime_pilot'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def extract(archive):
    require(archive.is_file() and not archive.is_symlink(), 'invalid_archive')
    require(archive.stat().st_size <= MAX_BYTES, 'archive_too_large')
    container = archive.read_bytes()
    require(checksum(container) == ARCHIVE_HASH, 'archive_hash_mismatch')
    # Leer la misma instantánea sellada, no reabrir un ZIP que pudo cambiar.
    from io import BytesIO
    with zipfile.ZipFile(BytesIO(container)) as zipped:
        entries = zipped.infolist()
        require(len(entries) == 1 and entries[0].filename == 'session.jsonl'
                and not entries[0].is_dir() and not entries[0].flag_bits & 1
                and entries[0].file_size <= MAX_BYTES, 'invalid_zip_entry')
        with zipped.open(entries[0]) as stream:
            raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES and checksum(raw) == SOURCE_HASH, 'source_hash_mismatch')
    return raw


def persist_source(path, raw):
    if path.exists() or path.is_symlink():
        require(not path.is_symlink() and path.is_file(), 'invalid_existing_source')
        require(path.read_bytes() == raw and path.stat().st_mode & 0o077 == 0,
                'existing_source_mismatch')
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)


def run(archive, directory, uri):
    match = re.fullmatch(r'mongodb://127\.0\.0\.1:(\d{4,5})', uri)
    require(match is not None and 1024 <= int(match[1]) <= 65535
            and int(match[1]) != 27017, 'laboratory_endpoint_required')
    require(directory.is_dir() and not directory.is_symlink()
            and directory.stat().st_mode & 0o077 == 0, 'private_directory_required')
    raw = extract(archive)
    original_hash = ARCHIVE_HASH
    captured = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    expected = build_envelope(raw, project_id=PROJECT, source_id=SOURCE, captured_at=captured)
    require(len(expected['rows']) == 126 and len(expected['events']) == 1375
            and len(expected['texts']) == 2, 'unexpected_sample_shape')
    # Fijar consultas y objetivos antes de escribir. Es recuperación literal, no relevancia.
    probes = []
    for text in expected['texts']:
        term = text['text'].strip()[:64]
        targets = [x['id'] for x in expected['texts'] if term.casefold() in x['text'].casefold()]
        probes.append((term, targets))
    path = directory / 'session.jsonl'
    persist_source(path, raw)
    with pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
        store = LaboratoryStore(client[DATABASE])
        first = store.import_file(path, project_id=PROJECT, source_id=SOURCE, captured_at=captured,
                                  source_format='dsh-session-v0-jsonl')
        require(first['status'] in ('imported', 'duplicate'), 'admission_failed')
        again = store.import_file(path, project_id=PROJECT, source_id=SOURCE, captured_at=captured,
                                  source_format='dsh-session-v0-jsonl')
        require(again == {**first, 'status': 'duplicate'}, 'replay_mismatch')
        identity = {k: first[k] for k in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        require(store.receipt(**identity) == again, 'receipt_mismatch')
        require(store.revisions.count_documents({'project_id': PROJECT, 'source_id': SOURCE}) == 1,
                'unexpected_revision_count')
        require(store.heads.count_documents({'project_id': PROJECT, 'source_id': SOURCE}) == 1,
                'unexpected_head_count')
        for text in expected['texts']:
            found = store.fetch_runtime(**identity, view='text_projection', text_id=text['id'])
            require(found['projection'] == text and len(canonical(found)) <= 64*1024,
                    'projection_fetch_mismatch')
        row_ids = {'row-1'} | {x['row_id'] for x in expected['texts']}
        for row in expected['rows']:
            if row['id'] in row_ids:
                found = store.fetch_runtime(**identity, view='original_jsonl', row_id=row['id'])
                require(found['original_jsonl'].encode() == raw[row['start_byte']:row['end_byte']],
                        'original_fetch_mismatch')
        from reader import parse
        events = parse(raw)['events']
        batch_member = next(x for x in events if x['member_index'] is not None)
        event_id = 'event-%d' % batch_member['value']['seq']
        found = store.fetch_runtime(**identity, view='derived_event', event_id=event_id)
        require(found['event'] == batch_member['value'] and found['member_index'] == batch_member['member_index'],
                'derived_fetch_mismatch')
        counts = []
        for term, targets in probes:
            found = store.search_runtime(project_id=PROJECT, term=term)
            require([x['projection']['id'] for x in found['results']] == targets
                    and not found['unavailable_sources']
                    and sum(found['excluded'].values()) == 0, 'literal_search_mismatch')
            require(all('original_jsonl' not in x and 'event' not in x for x in found['results']),
                    'search_payload_leak')
            counts.append({'expected': len(targets), 'returned': len(found['results'])})
        absent = '__skopos_pilot_absent_28eff1a5__'
        require(all(absent not in x['text'].casefold() for x in expected['texts']), 'invalid_negative_control')
        require(store.search_runtime(project_id=PROJECT, term=absent)['results'] == [], 'negative_search_failed')
    require(checksum(path.read_bytes()) == SOURCE_HASH and checksum(archive.read_bytes()) == original_hash,
            'source_changed_during_pilot')
    report = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'private_laboratory_pilot_not_production',
              'archive_sha256': ARCHIVE_HASH, 'source_sha256': SOURCE_HASH,
              'source_bytes': len(raw), 'receipt': first, 'replay': again['status'],
              'database': DATABASE, 'rows': len(expected['rows']), 'events': len(expected['events']),
              'texts': len(expected['texts']), 'projection_fetches': len(expected['texts']),
              'original_fetches': len(row_ids), 'derived_fetches': 1,
              'literal_searches': counts, 'negative_search': 'passed',
              'original_unchanged': True, 'retention': 'until_operator_decision',
              'readers': 'operator_and_authorized_local_process_no_multiuser_acl'}
    destination = directory / ('report-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
    with os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--mongo-uri', required=True)
    args = parser.parse_args()
    try:
        run(args.archive, args.directory, args.mongo_uri)
    except Exception as error:
        # No imprimir excepciones del driver o del contenido con datos privados.
        print('Piloto no completado: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
