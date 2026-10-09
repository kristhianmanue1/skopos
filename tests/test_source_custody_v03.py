"""Perfil PDF/HTML: bytes permitidos, procedencia separada y rechazo cerrado."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from skopos.pdf_custody import (CustodyError, PdfCustodyStore, SOURCE_SCHEMA,
                               _admission_data, _policy_digest, _record_digest,
                               _verified_document, load_policy)
from skopos.pdf_custody_host import (HostGateway, SOURCE_HOST_SCHEMA,
                                    load_host_config)
from skopos.pdf_document_store import DocumentError
from skopos.source_document_store import SourceDocumentStore


class SourceCustodyV03Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('requests', 'input', 'source', 'provenance', 'delivery'):
            (self.root / name).mkdir()
        self.pdf = b'%PDF-1.7\nfixture\n%%EOF\n'
        self.html = b'<!DOCTYPE html><html><body>fixture</body></html>'
        self.provenance = b'Consumer attributed origin.\n'
        (self.root / 'source' / 'original.pdf').write_bytes(self.pdf)
        (self.root / 'source' / 'original.html').write_bytes(self.html)
        (self.root / 'provenance' / 'record.txt').write_bytes(self.provenance)
        self.policy = {
            'schema': 'skopos/source-custody-policy/v0.3',
            'project_id': 'expertogobernanza', 'owner': 'expertogobernanza',
            'policy_id': 'test/source-v03', 'policy_version': 'v0.3',
            'classification': 'consumer_declared_public',
            'requests_root': str(self.root / 'requests'),
            'input_root': str(self.root / 'input'),
            'source_root': str(self.root / 'source'),
            'provenance_root': str(self.root / 'provenance'),
            'delivery_root': str(self.root / 'delivery'),
            'retention_until': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            'retention_basis': 'fixture', 'max_bytes': 10000,
            'seal_policy': 'not_required', 'seal_profile_id': 'test/not-required',
            'recovery_requirement': 'while_reference_available',
            'allowed_materials': [
                {'material_id': material, 'source_revision': 1,
                 'source_ref': source, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                 'media_type': media, 'provenance_ref': 'record.txt',
                 'provenance_sha256': hashlib.sha256(self.provenance).hexdigest()}
                for material, source, raw, media in (
                    ('pdf', 'original.pdf', self.pdf, 'application/pdf'),
                    ('html', 'original.html', self.html, 'text/html'))]}
        self.policy_path = self.root / 'policy.json'
        self.policy_path.write_text(json.dumps(self.policy))

    def request(self, material='pdf'):
        item = next(item for item in self.policy['allowed_materials']
                    if item['material_id'] == material)
        return {'operation': 'admit_original', 'project_id': 'expertogobernanza',
                'material_id': material, 'source_revision': 1,
                'request_id': 'request-' + material, '_request_sha256': 'a' * 64,
                'scope': 'single_object', 'source_delivery': {
                    'mode': 'authorized_reference', 'file_ref': item['source_ref']},
                'expected_source_sha256': item['source_sha256'],
                'media_type_declared': item['media_type'],
                'classification': 'consumer_declared_public',
                'custody_mode': 'verified_external_reference',
                'custody_policy_id': 'test/source-v03', 'custody_policy_version': 'v0.3',
                'seal_profile_id': 'test/not-required',
                'recovery_requirement': 'while_reference_available',
                'limits': {'max_bytes': 10000, 'allow_network': False,
                           'allow_ocr': False},
                'provenance': {'asserted_by': 'expertogobernanza',
                               'claim_status': 'consumer_declared',
                               'record_ref': 'record.txt',
                               'record_sha256': item['provenance_sha256']}}

    def test_pdf_and_html_allowed_but_other_identity_denied(self):
        policy = load_policy(self.policy_path)
        for material in ('pdf', 'html'):
            with self.subTest(material=material):
                document = _admission_data(self.request(material), policy)
                self.assertEqual(document['schema'], SOURCE_SCHEMA)
                self.assertEqual(document['media_type'], self.request(material)['media_type_declared'])
                document['record_sha256'] = _record_digest(document)
                self.assertIs(_verified_document(document, document['_id'], SOURCE_SCHEMA),
                              document)
        request = self.request('html')
        request['material_id'] = 'unknown'
        with self.assertRaisesRegex(CustodyError, 'material_not_allowed'):
            _admission_data(request, policy)

    def test_mutation_wrong_format_and_missing_provenance_fail(self):
        policy = load_policy(self.policy_path)
        (self.root / 'source' / 'original.html').write_bytes(b'not html')
        with self.assertRaisesRegex(CustodyError, 'hash_mismatch'):
            _admission_data(self.request('html'), policy)
        self.policy['allowed_materials'][1]['source_sha256'] = hashlib.sha256(b'not html').hexdigest()
        self.policy_path.write_text(json.dumps(self.policy))
        with self.assertRaisesRegex(CustodyError, 'unsupported_format'):
            _admission_data(self.request('html'), load_policy(self.policy_path))
        (self.root / 'provenance' / 'record.txt').unlink()
        with self.assertRaises(CustodyError):
            _admission_data(self.request('pdf'), load_policy(self.policy_path))

    def test_host_schema_and_collection_are_separate(self):
        config = {'schema': SOURCE_HOST_SCHEMA,
                  'policy_path': str(self.policy_path),
                  'mongo_uri': 'mongodb://127.0.0.1:27017',
                  'database': 'fixture', 'socket_path': str(self.root / 'host.sock')}
        path = self.root / 'host.json'
        path.write_text(json.dumps(config))
        gateway = HostGateway(load_host_config(path), client=mock.MagicMock())
        self.assertEqual(gateway.contract_version, 'v0.3')
        database = mock.MagicMock()
        PdfCustodyStore(database, gateway.policy)
        self.assertEqual(database.get_collection.call_args_list[0].args[0],
                         'source_custody_revisions_v1')
        config['schema'] = 'skopos/pdf-custody-host/v0.1'
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(CustodyError, 'policy_unavailable'):
            HostGateway(load_host_config(path), client=mock.MagicMock())

    def test_pdf_derivative_checks_policy_and_separate_provenance(self):
        self.policy['allowed_materials'].reverse()
        self.policy_path.write_text(json.dumps(self.policy))
        custody = load_policy(self.policy_path)
        request = self.request('pdf')
        document = _admission_data(request, custody)
        document['record_sha256'] = _record_digest(document)
        database = mock.MagicMock()
        database.get_collection.return_value.find_one.return_value = document
        policy = {'custody_policy_path': str(self.policy_path),
                  'custody_policy_sha256': _policy_digest(custody),
                  'project_id': 'expertogobernanza', 'material_id': 'pdf',
                  'source_revision': 1, 'source_sha256': hashlib.sha256(self.pdf).hexdigest(),
                  'provenance_sha256': hashlib.sha256(self.provenance).hexdigest(),
                  'custody_receipt_id': 'expertogobernanza:pdf:1:' + 'a' * 16}
        store = SourceDocumentStore(database, policy)
        supplied = {key: policy[key] for key in ('material_id', 'source_revision',
                    'source_sha256', 'custody_receipt_id', 'custody_policy_sha256')}
        self.assertEqual(store._source(supplied), self.pdf)
        collection_call = database.get_collection.call_args
        self.assertEqual(collection_call.args[0], 'source_custody_revisions_v1')
        self.assertEqual(collection_call.kwargs['read_concern'].level, 'majority')
        self.assertEqual(str(collection_call.kwargs['read_preference']), 'Primary()')
        store.custody['allowed_materials'][0]['provenance_ref'] = 'other.txt'
        with self.assertRaisesRegex(DocumentError, 'custody_policy_mismatch'):
            store._source(supplied)

    def test_pdf_derivative_rejects_ambiguous_material(self):
        custody = load_policy(self.policy_path)
        custody['allowed_materials'].append(copy.deepcopy(custody['allowed_materials'][0]))
        policy = {'custody_policy_path': str(self.policy_path),
                  'custody_policy_sha256': _policy_digest(custody),
                  'project_id': 'expertogobernanza', 'material_id': 'pdf',
                  'source_revision': 1, 'source_sha256': hashlib.sha256(self.pdf).hexdigest(),
                  'provenance_sha256': hashlib.sha256(self.provenance).hexdigest(),
                  'custody_receipt_id': 'expertogobernanza:pdf:1:' + 'a' * 16}
        store = SourceDocumentStore(mock.MagicMock(), policy)
        store.custody = custody
        supplied = {key: policy[key] for key in ('material_id', 'source_revision',
                    'source_sha256', 'custody_receipt_id', 'custody_policy_sha256')}
        with self.assertRaisesRegex(DocumentError, 'custody_policy_mismatch'):
            store._source(supplied)

    def test_pdf_derivative_typed_error_when_record_lacks_policy_digest(self):
        custody = load_policy(self.policy_path)
        document = _admission_data(self.request('pdf'), custody)
        document['record_sha256'] = _record_digest(document)
        database = mock.MagicMock()
        database.get_collection.return_value.find_one.return_value = document
        policy = {'custody_policy_path': str(self.policy_path),
                  'custody_policy_sha256': _policy_digest(custody),
                  'project_id': 'expertogobernanza', 'material_id': 'pdf',
                  'source_revision': 1, 'source_sha256': hashlib.sha256(self.pdf).hexdigest(),
                  'provenance_sha256': hashlib.sha256(self.provenance).hexdigest(),
                  'custody_receipt_id': ('expertogobernanza:pdf:1:' +
                                         document['request_sha256'][:16])}
        store = SourceDocumentStore(database, policy)
        supplied = {key: policy[key] for key in ('material_id', 'source_revision',
                    'source_sha256', 'custody_receipt_id', 'custody_policy_sha256')}
        self.assertEqual(store._source(supplied), self.pdf)
        document.pop('policy_sha256')
        document['record_sha256'] = _record_digest(document)
        with self.assertRaisesRegex(DocumentError, 'custody_receipt_mismatch'):
            store._source(supplied)


if __name__ == '__main__':
    unittest.main()
