"""Operación monousuario explícita: bloqueo cooperativo, respaldo frío y recibos.

No daemon ni sandbox contra procesos con el mismo UID. Usar el lanzador privado
para toda ingesta; los accesos directos a Mongo quedan fuera de esta coordinación.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import tarfile
import time
import uuid

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

PRIVATE_ROOT = Path('/Users/krisnova/Skopos-private/runtime-v3')
CLOUD_ROOT = Path('/Users/krisnova/Library/CloudStorage/OneDrive-Personal/Desarrollo/www_cloud/aria/skopos_cloud')


def checksum(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def save_json(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x') as output:
        os.chmod(temporary, 0o600)
        json.dump(value, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


@contextmanager
def operation_lock(root):
    """Mismo inode para ingestas, mantenimiento y arranque/parada cooperativos."""
    path = root / 'operation.lock'
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077):
            raise ValueError('invalid_lock_file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('runtime_busy_retry_later') from None
        yield
    finally:
        os.close(descriptor)


def protected_copy_tree(archive, path, name):
    """No seguir enlaces durante el respaldo de árboles privados."""
    if path.is_symlink():
        raise ValueError('backup_symlink_rejected')
    if path.is_dir():
        archive.add(path, arcname=name, recursive=False)
        for child in sorted(path.iterdir()):
            protected_copy_tree(archive, child, name + '/' + child.name)
    elif path.is_file():
        archive.add(path, arcname=name, recursive=False)
    else:
        raise ValueError('backup_nonregular_rejected')


class RuntimeOperations:
    def __init__(self, root=PRIVATE_ROOT, cloud=CLOUD_ROOT):
        self.root, self.cloud = Path(root), Path(cloud)
        self.state_path = self.root / 'maintenance-state.json'
        self.launcher = None

    def load_launcher(self):
        if self.launcher is None:
            path = self.root / 'operate.py'
            spec = importlib.util.spec_from_file_location('private_runtime_launcher', path)
            self.launcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.launcher)
        return self.launcher

    def client(self):
        return MongoClient('mongodb://127.0.0.1:37030', username='skopos_admin',
                           password=self.load_launcher().credential('admin'), authSource='admin',
                           replicaSet='skopos_runtime_v3_rs', serverSelectionTimeoutMS=2000)

    def preflight(self):
        with self.client() as client:
            options = client.admin.command('getCmdLineOpts')['parsed']
            if (Path(options['storage']['dbPath']).resolve() != (self.root / 'db').resolve()
                    or options['net']['port'] != 37030
                    or not client.admin.command('hello').get('isWritablePrimary')):
                raise ValueError('unexpected_runtime_instance')
            records = list(client.skopos_runtime_v3.source_revisions_v3.find())
            from skopos.runtime_store import RuntimeSourceStore
            logical = []
            for record in records:
                envelope = RuntimeSourceStore._verified_envelope(record)
                path = Path(record['source_path'])
                if path.is_symlink() or (self.root / 'sources').resolve() not in path.resolve().parents:
                    raise ValueError('source_outside_private_custody')
                if checksum(path) != envelope['source_sha256']:
                    raise ValueError('source_hash_mismatch')
                logical.append([record['_id'], envelope['envelope_sha256'], str(path)])
            heads = sorted((item['_id'], item['revision_key'], item['source_sha256'])
                           for item in client.skopos_runtime_v3.source_heads_v3.find())
            value = json.dumps([sorted(logical), heads], sort_keys=True).encode()
            return hashlib.sha256(value).hexdigest(), len(records)

    def stop(self):
        code = self.load_launcher().main(['stop'])
        if code:
            raise ValueError('runtime_stop_failed')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with socket.socket() as connection:
                connection.settimeout(0.5)
                if connection.connect_ex(('127.0.0.1', 37030)) != 0:
                    return
            time.sleep(0.2)
        raise ValueError('runtime_stop_timeout')

    def start_and_verify(self):
        # Si la parada falló antes de cerrar, no lanzar un segundo mongod.
        try:
            self.preflight()
            return
        except ConnectionFailure:
            pass
        if self.load_launcher().main(['start']):
            raise ValueError('runtime_start_failed')
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                self.preflight()
                return
            except ConnectionFailure:
                time.sleep(0.3)
        raise ValueError('runtime_restart_not_verified')

    def write_archive(self, directory):
        archive_path = directory / 'runtime-v3-data.tar.gz'
        with tarfile.open(archive_path, 'x:gz') as archive:
            for name in ('db', 'sources'):
                protected_copy_tree(archive, self.root / name, name)
        os.chmod(archive_path, 0o600)
        return archive_path

    def publish(self, directory):
        """Publicar manifest al final; no afirmar sincronización remota."""
        target = self.cloud / directory.name
        target.mkdir(mode=0o700)
        for name in ('runtime-v3-data.tar.gz', 'manifest.json'):
            source = directory / name
            temporary = target / (name + '.partial')
            shutil.copyfile(source, temporary)
            os.chmod(temporary, 0o600)
            if checksum(source) != checksum(temporary):
                raise ValueError('cloud_copy_hash_mismatch')
            os.replace(temporary, target / name)
        return target

    def backup(self, only_if_changed=False):
        """El llamador mantiene operation_lock durante toda esta transacción."""
        fingerprint, count = self.preflight()
        state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        if only_if_changed and state.get('fingerprint') == fingerprint:
            target = Path(state.get('cloud_directory', ''))
            manifest = target / 'manifest.json'
            archive = target / 'runtime-v3-data.tar.gz'
            receipt = json.loads(manifest.read_text()) if manifest.is_file() else {}
            if (receipt.get('archive_sha256') == state.get('archive_sha256')
                    and receipt.get('fingerprint') == fingerprint
                    and archive.is_file() and checksum(archive) == state.get('archive_sha256')):
                return {'status': 'unchanged', 'cloud_verified': False, 'checked_at': datetime.now(timezone.utc).isoformat()}
        backups = self.root / 'backups'
        backups.mkdir(mode=0o700, exist_ok=True)
        directory = backups / ('runtime-v3-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        directory.mkdir(mode=0o700)
        report = {'schema': 'skopos/runtime-backup/v1', 'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running', 'fingerprint': fingerprint, 'revisions': count}
        save_json(directory / 'operation.json', report)
        try:
            try:
                self.stop()
                archive = self.write_archive(directory)
            finally:
                # Incluso si stop devuelve resultado incierto o la copia falla.
                self.start_and_verify()
            if self.preflight()[0] != fingerprint:
                raise ValueError('runtime_changed_during_backup')
            digest = checksum(archive)
            manifest = {'schema': 'skopos/runtime-backup/v1', 'created_at': datetime.now(timezone.utc).isoformat(), 'archive_sha256': digest, 'fingerprint': fingerprint, 'revisions': count, 'plaintext_credentials_in_archive': False, 'cloud_verified': False}
            save_json(directory / 'manifest.json', manifest)
            target = self.publish(directory)
            save_json(self.state_path, {**manifest, 'cloud_directory': str(target), 'local_directory': str(directory)})
            report.update(status='complete', cloud_directory=str(target), archive_sha256=digest, restart_verified=True)
            return report
        except BaseException:
            report.update(status='failed', error='backup_failed_inspect_private_evidence')
            raise
        finally:
            save_json(directory / 'operation.json', report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore-latest'])
    parser.add_argument('--if-changed', action='store_true')
    args = parser.parse_args(argv)
    os.umask(0o077)
    with operation_lock(PRIVATE_ROOT):
        operations = RuntimeOperations()
        if args.operation == 'backup':
            result = operations.backup(args.if_changed)
        else:
            from runtime_restore import restore_latest
            result = restore_latest(operations)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Mantenimiento no completado; revisar evidencia privada y estado del servicio. Sin detalles sensibles.')
