"""Ensayo de restauración autenticada aislada; no sustituye recuperación remota."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import tarfile
import time
import uuid

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from skopos.runtime_store import RuntimeSourceStore
from runtime_operations import checksum, save_json


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def extract_checked(archive, destination):
    with tarfile.open(archive) as package:
        members = package.getmembers()
        require(sum(item.size for item in members) <= 10 * 1024 ** 3, 'archive_too_large')
        names = set()
        for item in members:
            path = PurePosixPath(item.name)
            require(not path.is_absolute() and '..' not in path.parts
                    and path.parts and path.parts[0] in ('db', 'sources')
                    and (item.isfile() or item.isdir()) and item.name not in names,
                    'unsafe_archive_member')
            names.add(item.name)
        # Sólo directorios y archivos regulares, destino nuevo privado.
        package.extractall(destination, members=members)


def validate_restored(database, restored, original_root, expected_count):
    for collection in ('source_revisions_v3', 'source_heads_v3'):
        require(database.command('validate', collection, full=True)['valid'], 'invalid_collection')
    require(database.source_revisions_v3.count_documents({}) == expected_count, 'revision_count_mismatch')
    heads_before = list(database.source_heads_v3.find())
    store = RuntimeSourceStore(database)
    projections = 0
    for document in database.source_revisions_v3.find():
        envelope = store._verified_envelope(document)
        relative = Path(document['source_path']).relative_to(original_root / 'sources')
        require('..' not in relative.parts, 'invalid_source_path')
        path = restored / 'sources' / relative
        require(checksum(path) == envelope['source_sha256'], 'source_hash_mismatch')
        database.source_revisions_v3.update_one({'_id': document['_id']}, {'$set': {'source_path': str(path)}})
        identity = {key: envelope[key] for key in ('project_id', 'source_id', 'source_revision', 'source_sha256')}
        receipt = store.receipt(**identity)
        require(receipt['status'] == 'duplicate', 'receipt_mismatch')
        for item in envelope['texts']:
            require(store.fetch_runtime(**identity, view='text_projection', text_id=item['id'])['projection'] == item, 'projection_mismatch')
            if item['text'].strip():
                require(store.search_runtime(project_id=envelope['project_id'], term=item['text'].strip()[:32])['results'], 'search_mismatch')
            projections += 1
        replay = store.import_file(path, **{key: identity[key] for key in ('project_id', 'source_id', 'source_revision')}, captured_at=envelope['captured_at'], source_format='dsh-session-v0-jsonl')
        require(replay == receipt, 'replay_mismatch')
    require(database.source_revisions_v3.count_documents({}) == expected_count, 'replay_changed_count')
    require(list(database.source_heads_v3.find()) == heads_before, 'replay_changed_heads')
    # Control positivo de transacción: escritura visible y rollback verificable.
    with database.client.start_session() as session:
        session.start_transaction()
        database.restore_probe.insert_one({'_id': 'transaction'}, session=session)
        require(database.restore_probe.find_one({'_id': 'transaction'}, session=session), 'transaction_write_failed')
        session.abort_transaction()
    require(database.restore_probe.find_one({'_id': 'transaction'}) is None, 'transaction_rollback_failed')
    return projections


def restore_latest(operations):
    state = json.loads(operations.state_path.read_text())
    archive = Path(state['cloud_directory']) / 'runtime-v3-data.tar.gz'
    require(checksum(archive) == state['archive_sha256'], 'archive_hash_mismatch')
    # Reservar la comprobación; mongod verificará también la exclusividad del bind.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 37033))
    parent = operations.root / 'restore-drills'
    parent.mkdir(mode=0o700, exist_ok=True)
    root = parent / uuid.uuid4().hex
    root.mkdir(mode=0o700)
    restored = root / 'restored'
    restored.mkdir(mode=0o700)
    report = {'schema': 'skopos/runtime-restore/v1', 'observed_at': datetime.now(timezone.utc).isoformat(), 'status': 'failed', 'archive_sha256': state['archive_sha256'], 'cloud_download_verified': False, 'port': 37033}
    keyfile = root / 'restore-keyfile'
    process = None
    try:
        extract_checked(archive, restored)
        with keyfile.open('x') as stream:
            os.chmod(keyfile, 0o600)
            stream.write(operations.load_launcher().credential('keyfile'))
        password = operations.load_launcher().credential('admin')
        process = subprocess.Popen(['/opt/homebrew/bin/mongod', '--dbpath', str(restored / 'db'), '--port', '37033', '--bind_ip', '127.0.0.1', '--replSet', 'skopos_runtime_v3_rs', '--keyFile', str(keyfile), '--logpath', str(root / 'mongod.log')], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with MongoClient('mongodb://127.0.0.1:37033/?directConnection=true', username='skopos_admin', password=password, authSource='admin', serverSelectionTimeoutMS=1000) as client:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                require(process.poll() is None, 'restore_process_stopped')
                try:
                    config = client.admin.command('replSetGetConfig')['config']
                    break
                except ConnectionFailure:
                    time.sleep(0.25)
            else:
                raise ValueError('restore_unavailable')
            require(len(config['members']) == 1, 'unexpected_replica_topology')
            config['members'][0]['host'] = 'localhost:37033'
            config['version'] += 1
            client.admin.command('replSetReconfig', config, force=True)
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if client.admin.command('hello').get('isWritablePrimary'):
                    break
                time.sleep(0.25)
            else:
                raise ValueError('restore_primary_unavailable')
            projections = validate_restored(client.skopos_runtime_v3, restored, operations.root, state['revisions'])
            report.update(status='pass', revisions=state['revisions'], projections=projections, transaction_rollback=True)
    except Exception as error:
        report.update(error_type=type(error).__name__, error_code=getattr(error, 'code', None))
        if isinstance(error, ValueError):
            report['check_failed'] = str(error)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=30)
        if process is None or process.poll() is not None:
            if keyfile.exists():
                keyfile.unlink()
            report.update(process_stopped=True, temporary_key_removed=True)
        save_json(root / 'report.json', report)
    return report
