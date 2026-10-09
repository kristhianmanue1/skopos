"""Derivados PDF sobre recibos de custodia de fuentes v0.3."""

import hashlib

from skopos.pdf_custody import (SOURCE_POLICY_SCHEMA, SOURCE_SCHEMA, _policy_digest,
                               _read_under, _verified_document)
from skopos.pdf_document_store import DocumentError, PdfDocumentStore


class SourceDocumentStore(PdfDocumentStore):
    """Reutiliza el motor PDF, verificando la nueva frontera de procedencia."""

    def _source(self, supplied):
        policy = self.policy
        expected = {
            'material_id': policy['material_id'],
            'source_revision': policy['source_revision'],
            'source_sha256': policy['source_sha256'],
            'custody_receipt_id': policy['custody_receipt_id'],
            'custody_policy_sha256': policy['custody_policy_sha256'],
        }
        if supplied != expected:
            raise DocumentError('source_mismatch')
        if (self.custody['schema'] != SOURCE_POLICY_SCHEMA
                or _policy_digest(self.custody) != policy['custody_policy_sha256']):
            raise DocumentError('custody_policy_mismatch')
        allowed = self.custody['allowed_materials'][0]
        if allowed['media_type'] != 'application/pdf':
            raise DocumentError('unsupported_format')
        if (allowed['material_id'] != policy['material_id']
                or allowed['source_revision'] != policy['source_revision']
                or allowed['source_sha256'] != policy['source_sha256']
                or allowed['provenance_sha256'] != policy['provenance_sha256']):
            raise DocumentError('custody_policy_mismatch')
        key = ':'.join((policy['project_id'], policy['material_id'],
                        str(policy['source_revision'])))
        document = self.database.source_custody_revisions_v1.find_one({'_id': key})
        if document is None:
            raise DocumentError('custody_receipt_missing')
        try:
            _verified_document(document, key, SOURCE_SCHEMA)
        except ValueError:
            raise DocumentError('custody_integrity_failed') from None
        provenance = document.get('provenance')
        if (key + ':' + document['request_sha256'][:16] != policy['custody_receipt_id']
                or document['source_sha256'] != policy['source_sha256']
                or document['policy_sha256'] != policy['custody_policy_sha256']
                or not isinstance(provenance, dict)
                or provenance.get('record_sha256') != policy['provenance_sha256']
                or provenance.get('record_ref') != allowed['provenance_ref']
                or document.get('source_ref') != allowed['source_ref']):
            raise DocumentError('custody_receipt_mismatch')
        raw = _read_under(self.custody['source_root'], allowed['source_ref'],
                          self.custody['max_bytes'], stage='retrieval')
        record = _read_under(self.custody['provenance_root'], allowed['provenance_ref'],
                             256 * 1024, stage='retrieval')
        if (hashlib.sha256(raw).hexdigest() != policy['source_sha256']
                or hashlib.sha256(record).hexdigest() != policy['provenance_sha256']):
            raise DocumentError('source_hash_mismatch', 'retrieval')
        return raw
