"""Integridad de manifiestos y recibos de derivados sin Mongo externo."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from skopos.pdf_document_store import DocumentError, PdfDocumentStore, _canonical


class DocumentStoreIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'requests').mkdir()
        self.source = {'material_id': 'sample', 'source_revision': 1,
                       'source_sha256': 'a' * 64,
                       'custody_receipt_id': 'sample:1:receipt',
                       'custody_policy_sha256': 'b' * 64}
        self.store = PdfDocumentStore.__new__(PdfDocumentStore)
        self.store.policy = {'derived_root': str(self.root),
                             'max_output_bytes': 10000, **self.source}
        self.store.policy_sha256 = 'c' * 64

    def _write_manifest(self, policy_sha256):
        derivation_id = 'd' * 64
        directory = self.root / derivation_id
        directory.mkdir()
        manifest = {'schema': 'skopos/pdf-document-manifest/v0.1',
                    'derivation_id': derivation_id,
                    'policy_sha256': policy_sha256, 'parent': self.source}
        raw = _canonical(manifest)
        (directory / 'manifest.json').write_bytes(raw)
        (directory / 'manifest.sha256').write_text(hashlib.sha256(raw).hexdigest())
        return derivation_id

    def test_current_policy_manifest_is_recoverable(self):
        derivation_id = self._write_manifest(self.store.policy_sha256)
        manifest, _ = self.store._manifest(derivation_id)
        self.assertEqual(self.store.policy_sha256, manifest['policy_sha256'])

    def test_previous_policy_manifest_is_not_served(self):
        derivation_id = self._write_manifest('e' * 64)
        with self.assertRaises(DocumentError) as error:
            self.store._manifest(derivation_id)
        self.assertEqual('manifest_integrity_failed', error.exception.code)

    def test_corrupt_existing_receipt_is_not_treated_as_missing(self):
        (self.root / 'requests' / 'sample.json').write_text('{')
        with self.assertRaises(DocumentError) as error:
            self.store._receipt('sample')
        self.assertEqual('receipt_integrity_failed', error.exception.code)


if __name__ == '__main__':
    unittest.main()
