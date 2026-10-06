"""Controles del ejecutor de piloto con ZIP y fuentes exclusivamente sintéticos."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_runtime_store import store_module, load, envelope, reader, verification

pilot = load('pilot', {'store': store_module, 'envelope': envelope,
                       'reader': reader, 'verification': verification})


class RuntimePilotTests(unittest.TestCase):
    def test_extract_hashes_and_entry_shape(self):
        raw = b'{"type":"session","version":0,"id":"synthetic"}\n'
        for name, accepted in [('session.jsonl', True), ('../session.jsonl', False)]:
            stream = BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr(name, raw)
            container = stream.getvalue()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'synthetic.zip'
                path.write_bytes(container)
                with patch.object(pilot, 'ARCHIVE_HASH', verification.checksum(container)), \
                        patch.object(pilot, 'SOURCE_HASH', verification.checksum(raw)):
                    if accepted:
                        self.assertEqual(pilot.extract(path), raw)
                    else:
                        with self.assertRaisesRegex(ValueError, '^invalid_zip_entry$'):
                            pilot.extract(path)
                with self.assertRaisesRegex(ValueError, '^archive_hash_mismatch$'):
                    pilot.extract(path)

    def test_exclusive_private_copy_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            pilot.persist_source(path, b'synthetic')
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            pilot.persist_source(path, b'synthetic')
            with self.assertRaisesRegex(ValueError, '^existing_source_mismatch$'):
                pilot.persist_source(path, b'changed')
            self.assertEqual(path.read_bytes(), b'synthetic')

    def test_symlink_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_bytes(b'synthetic')
            link = Path(directory) / 'session.jsonl'
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, '^invalid_existing_source$'):
                pilot.persist_source(link, b'synthetic')

    def test_production_endpoint_rejected_before_read(self):
        with patch.object(pilot, 'extract', side_effect=AssertionError('unexpected read')):
            with self.assertRaisesRegex(ValueError, '^laboratory_endpoint_required$'):
                pilot.run(Path('unused'), Path('unused'), 'mongodb://127.0.0.1:27017')


if __name__ == '__main__':
    unittest.main()
