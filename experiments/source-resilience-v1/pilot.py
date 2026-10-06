"""Caídas reales de mongod exclusivo con fuentes sintéticas; nunca producción.

Uso: .venv/bin/python experiments/source-resilience-v1/pilot.py --workdir RUTA
La ruta debe existir y estar vacía. Sólo se usa loopback:37033 y base de pruebas.
No certifica failover multinodo, cortes eléctricos ni todos los interleavings.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from skopos.source_store import SourceStore
from skopos.source_reader import checksum


def run(root):
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError('empty_workdir_required')
    dbpath = root / 'db'
    dbpath.mkdir(mode=0o700)
    uri = 'mongodb://127.0.0.1:37033'
    # No adoptar un servicio ajeno aunque use el puerto esperado.
    with MongoClient(uri, serverSelectionTimeoutMS=300) as probe:
        try:
            probe.admin.command('ping')
        except PyMongoError:
            pass
        else:
            raise RuntimeError('port_already_in_use')
    process = None

    def start(initialize=False):
        nonlocal process
        process = subprocess.Popen([
            'mongod', '--dbpath', str(dbpath), '--bind_ip', '127.0.0.1',
            '--port', '37033', '--replSet', 'skopos_crash_rs', '--oplogSize', '64',
            '--wiredTigerCacheSizeGB', '0.25', '--logpath', str(root / 'mongod.log'),
            '--logappend'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = MongoClient(uri, directConnection=True, serverSelectionTimeoutMS=500)
        deadline = time.monotonic() + 45
        initiated = not initialize
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('mongod_start_failed')
            try:
                hello = client.admin.command('hello')
                options = client.admin.command('getCmdLineOpts')['parsed']
                if Path(options['storage']['dbPath']).resolve() != dbpath.resolve():
                    client.close()
                    raise RuntimeError('unexpected_server_dbpath')
                if not initiated:
                    client.admin.command('replSetInitiate', {
                        '_id': 'skopos_crash_rs',
                        'members': [{'_id': 0, 'host': '127.0.0.1:37033'}]})
                    initiated = True
                elif hello.get('isWritablePrimary'):
                    # Renovar topología: el cliente de bootstrap pudo observar
                    # el nodo antes de iniciar el replica set (sin sesiones).
                    client.close()
                    ready = MongoClient(uri, replicaSet='skopos_crash_rs',
                                        serverSelectionTimeoutMS=3000)
                    ready.admin.command('ping')
                    return ready
            except PyMongoError:
                pass
            time.sleep(0.2)
        client.close()
        raise RuntimeError('primary_timeout')

    def crash(client):
        process.kill()  # Sólo el hijo creado por este ejecutor, nunca PID descubierto.
        process.wait(timeout=15)
        client.close()

    raw = b'[0.0 - 1.0] SPEAKER_01: durable baseline\n'
    new = b'[0.0 - 1.0] SPEAKER_01: committed revision\n'
    first, second = root / 'v1.txt', root / 'v2.txt'
    first.write_bytes(raw)
    second.write_bytes(new)
    args = dict(project_id='crash', source_id='s', captured_at='2026-10-06T00:00:00Z')
    checks = {}
    try:
        client = start(initialize=True)
        store = SourceStore(client['skopos_test_crash'])
        receipt = store.import_file(first, **args)
        checks['positive_before_crash'] = receipt['status'] == 'imported'
        # Publicación pendiente sin commit: revisión y cabeza dentro de una
        # transacción real. Se mata el servidor, no se simula una excepción.
        from skopos.source_envelope import build_envelope
        document = {'_id': 'crash:s:2', 'schema': 'skopos/source-record/v3',
            'project_id': 'crash', 'source_id': 's', 'source_revision': 2,
            'source_path': str(second), 'admitted_at': args['captured_at'],
            'envelope': build_envelope(new, **args, source_revision=2,
                                      previous_source_sha256=checksum(raw))}
        session = client.start_session()
        session.start_transaction(read_concern=ReadConcern('snapshot'),
                                  write_concern=WriteConcern('majority'))
        store._publish(document, session)
        crash(client)
        client = start()
        store = SourceStore(client['skopos_test_crash'])
        checks['uncommitted_revision_absent'] = store.revisions.count_documents({}) == 1
        checks['head_not_partially_advanced'] = store.heads.find_one({})['source_revision'] == 1
        receipt = store.import_file(second, **args, source_revision=2,
                                    expected_previous_sha256=checksum(raw))
        checks['retry_after_crash'] = receipt['status'] == 'imported'
        crash(client)
        client = start()
        store = SourceStore(client['skopos_test_crash'])
        second.unlink()  # Fixture propio; probar recibo sin custodia del original.
        checks['committed_receipt_survives_restart'] = store.receipt(
            project_id='crash', source_id='s', source_revision=2,
            source_sha256=checksum(new))['status'] == 'duplicate'
        checks['two_revisions_one_head'] = (store.revisions.count_documents({}) == 2
                                           and store.heads.count_documents({}) == 1)
        second.write_bytes(new)
        checks['restored_fetch_positive'] = store.fetch(project_id='crash', source_id='s',
            source_revision=2, source_sha256=checksum(new),
            segment_id='segment-000001')['segment']['text'] == 'committed revision'
        client.close()
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=30)
    if not all(checks.values()):
        raise AssertionError(checks)
    return {'checks': checks, 'shutdown_exit': process.returncode,
            'scope': 'single_node_process_crash_not_power_loss_or_failover'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(run(options.workdir.resolve()), sort_keys=True))
