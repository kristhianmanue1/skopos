"""Controles positivos y fallos de respaldo; nunca conectan a Mongo real."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from runtime_operations import RuntimeOperations, operation_lock, checksum
from runtime_restore import extract_checked


class RuntimeOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cloud = self.root / 'cloud'
        self.cloud.mkdir()
        for name in ('db', 'sources'):
            (self.root / name).mkdir()
            (self.root / name / 'example').write_text(name)
        (self.root / 'keyfile').write_text('never-archive')
        self.ops = RuntimeOperations(self.root, self.cloud)
        for name, value in [('preflight', ('fingerprint', 2)), ('stop', None), ('start_and_verify', None)]:
            mock = patch.object(self.ops, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_success_excludes_credentials_and_skips_unchanged(self):
        result = self.ops.backup()
        self.assertEqual(result['status'], 'complete')
        self.ops.start_and_verify.assert_called_once()
        with tarfile.open(Path(result['cloud_directory']) / 'runtime-v3-data.tar.gz') as archive:
            self.assertEqual(set(archive.getnames()), {'db', 'db/example', 'sources', 'sources/example'})
        self.assertEqual(self.ops.backup(True)['status'], 'unchanged')
        self.ops.stop.assert_called_once()

    def test_copy_failure_restarts_and_never_advances_state(self):
        with patch.object(self.ops, 'write_archive', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                self.ops.backup()
        self.ops.start_and_verify.assert_called_once()
        self.assertFalse(self.ops.state_path.exists())

    def test_uncertain_stop_still_verifies_restart(self):
        self.ops.stop.side_effect = OSError('synthetic')
        with self.assertRaises(OSError):
            self.ops.backup()
        self.ops.start_and_verify.assert_called_once()

    def test_restart_failure_never_publishes(self):
        self.ops.start_and_verify.side_effect = OSError('synthetic')
        with self.assertRaises(OSError):
            self.ops.backup()
        self.assertEqual(list(self.cloud.iterdir()), [])

    def test_publish_failure_preserves_service_and_no_state(self):
        with patch.object(self.ops, 'publish', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                self.ops.backup()
        self.ops.start_and_verify.assert_called_once()
        self.assertFalse(self.ops.state_path.exists())

    def test_preflight_failure_never_stops(self):
        self.ops.preflight.side_effect = ValueError('wrong-instance')
        with self.assertRaises(ValueError):
            self.ops.backup()
        self.ops.stop.assert_not_called()

    def test_changed_during_backup_never_publishes(self):
        self.ops.preflight.side_effect = [('before', 2), ('after', 3)]
        with self.assertRaises(ValueError):
            self.ops.backup()
        self.assertFalse(self.ops.state_path.exists())

    def test_corrupt_cloud_copy_requires_new_backup(self):
        result = self.ops.backup()
        (Path(result['cloud_directory']) / 'runtime-v3-data.tar.gz').write_text('corrupted')
        self.assertEqual(self.ops.backup(True)['status'], 'complete')
        self.assertEqual(self.ops.stop.call_count, 2)

    def test_changed_manifest_is_not_an_unchanged_backup(self):
        result = self.ops.backup()
        (Path(result['cloud_directory']) / 'manifest.json').write_text('{}')
        self.assertEqual(self.ops.backup(True)['status'], 'complete')

    def test_backup_symlink_rejected_and_service_restarted(self):
        (self.root / 'sources' / 'link').symlink_to(self.root / 'keyfile')
        with self.assertRaises(ValueError):
            self.ops.backup()
        self.ops.start_and_verify.assert_called_once()

    def test_lock_positive_contention_release_and_symlink_rejection(self):
        with operation_lock(self.root):
            with self.assertRaises(ValueError):
                with operation_lock(self.root):
                    self.fail('second writer admitted')
        with operation_lock(self.root):
            pass
        (self.root / 'operation.lock').unlink()
        (self.root / 'operation.lock').symlink_to(self.root / 'keyfile')
        with self.assertRaises(OSError):
            with operation_lock(self.root):
                self.fail('symlink admitted')

    def test_restore_rejects_traversal_links_and_credentials(self):
        for name, link in [('../outside', False), ('db/link', True), ('keyfile', False)]:
            archive = self.root / 'unsafe.tar'
            with tarfile.open(archive, 'w') as package:
                item = tarfile.TarInfo(name)
                if link:
                    item.type = tarfile.SYMTYPE
                    item.linkname = '/etc/passwd'
                package.addfile(item)
            with self.assertRaises(ValueError):
                extract_checked(archive, self.root / 'destination')

    def test_restore_positive_extract(self):
        archive = self.ops.write_archive(self.root)
        destination = self.root / 'restored'
        destination.mkdir()
        extract_checked(archive, destination)
        self.assertEqual((destination / 'sources/example').read_text(), 'sources')
