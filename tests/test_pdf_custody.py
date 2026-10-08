"""Custodia PDF: bytes, permisos de ruta y recibos sobre Mongo temporal."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest import mock

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import (CustodyError, PdfCustodyStore, _read_under,
                               load_policy, read_request)
from skopos.pdf_custody_cli import custody_command


PDF = b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n'
SHA = hashlib.sha256(PDF).hexdigest()


class PdfCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ('requests', 'input', 'source', 'delivery'):
            (self.root / name).mkdir()
        (self.root / 'source' / 'original.pdf').write_bytes(PDF)
        (self.root / 'source' / 'provenance.md').write_text('Origen atribuido al consumidor.')
        self.policy_path = self.root / 'policy.json'
        self.policy = {
            'schema': 'skopos/pdf-custody-policy/v0.1',
            'project_id': 'expertogobernanza', 'policy_id': 'test/consumer-reference',
            'policy_version': 'v0.1', 'owner': 'expertogobernanza',
            'classification': 'consumer_declared_public',
            'requests_root': str(self.root / 'requests'),
            'input_root': str(self.root / 'input'),
            'source_root': str(self.root / 'source'),
            'delivery_root': str(self.root / 'delivery'),
            'retention_until': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            'retention_basis': 'test-policy', 'max_bytes': 10000,
            'seal_policy': 'not_required', 'seal_profile_id': 'test/not-required',
            'recovery_requirement': 'while_reference_available'}
        self.save_policy()
        self.request = {
            'contract_id': 'expertogobernanza/skopos-source', 'contract_version': 'v0.1',
            'request_id': 'admit-001', 'operation': 'admit_original',
            'project_id': 'expertogobernanza', 'material_id': 'fixture-pdf',
            'source_revision': 1, 'scope': 'single_object',
            'source_delivery': {'mode': 'authorized_reference', 'file_ref': 'original.pdf'},
            'expected_source_sha256': SHA, 'media_type_declared': 'application/pdf',
            'classification': 'consumer_declared_public',
            'custody_mode': 'verified_external_reference',
            'custody_policy_id': 'test/consumer-reference',
            'custody_policy_version': 'v0.1',
            'seal_profile_id': 'test/not-required',
            'recovery_requirement': 'while_reference_available',
            'limits': {'max_bytes': 10000, 'allow_network': False, 'allow_ocr': False},
            'provenance': {'asserted_by': 'expertogobernanza',
                           'claim_status': 'consumer_declared',
                           'record_ref': 'provenance.md',
                           'record_sha256': hashlib.sha256(
                               (self.root / 'source' / 'provenance.md').read_bytes()).hexdigest(),
                           'origin_url': 'https://example.test/origin'}}

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.policy))

    def write_request(self, request=None, name='request.json'):
        raw = json.dumps(request or self.request, separators=(',', ':')).encode()
        (self.root / 'requests' / name).write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        envelope = {'request_file_ref': name, 'request_sha256': digest,
                    'request_id': (request or self.request)['request_id'],
                    'contract_id': 'expertogobernanza/skopos-source',
                    'contract_version': 'v0.1'}
        (self.root / 'requests' / 'envelope.json').write_text(json.dumps(envelope))
        parsed = read_request(load_policy(self.policy_path), envelope)
        parsed['_request_sha256'] = digest
        return parsed

    def test_policy_request_and_path_boundaries(self):
        request = self.write_request()
        self.assertEqual(request['request_id'], 'admit-001')
        self.policy['retention_until'] = '2000-01-01T00:00:00Z'
        self.save_policy()
        with self.assertRaisesRegex(CustodyError, 'retention_policy_missing'):
            load_policy(self.policy_path)
        self.policy['retention_until'] = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        self.save_policy()
        with self.assertRaisesRegex(CustodyError, 'policy_unavailable'):
            load_policy(self.root / 'missing.json')
        (self.root / 'source' / 'link.pdf').symlink_to(self.root / 'source' / 'original.pdf')
        for reference in ('../policy.json', '/tmp/escape.pdf', 'link.pdf'):
            with self.subTest(reference=reference), self.assertRaises(CustodyError):
                _read_under(self.policy['source_root'], reference, 10000)

    def test_provided_file_requires_identical_persistent_copy(self):
        request = self.write_request()
        request['source_delivery'] = {'mode': 'provided_file', 'file_ref': 'sidecar.pdf'}
        (self.root / 'input' / 'sidecar.pdf').write_bytes(PDF)
        store = PdfCustodyStore(mock.MagicMock(), load_policy(self.policy_path))
        with self.assertRaisesRegex(CustodyError, 'persistent_reference_missing'):
            store.admit(request)
        request['source_delivery']['persistent_ref'] = 'original.pdf'
        (self.root / 'input' / 'sidecar.pdf').write_bytes(PDF + b'extra')
        with self.assertRaisesRegex(CustodyError, 'hash_mismatch'):
            store.admit(request)

    def test_unsupported_page_constraint_rejected(self):
        request = self.write_request()
        request['limits']['max_pages'] = 200
        store = PdfCustodyStore(mock.MagicMock(), load_policy(self.policy_path))
        with self.assertRaisesRegex(CustodyError, 'unsupported_limit'):
            store.admit(request)

    def test_cli_capabilities_and_tampered_request(self):
        request = dict(self.request, operation='describe_capabilities', request_id='cap-001')
        self.write_request(request)
        args = ['--policy', str(self.policy_path), '--database', 'unused',
                '--envelope-ref', 'envelope.json']
        output = io.StringIO()
        with redirect_stdout(output):
            code = custody_command(args)
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['result']['format_validation'], 'pdf_header_only')
        (self.root / 'requests' / 'request.json').write_bytes(b'{}')
        output = io.StringIO()
        with redirect_stdout(output):
            code = custody_command(args)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['error']['code'], 'hash_mismatch')


class PdfCustodyMongoTests(PdfCustodyTests):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=1000)
        try:
            hello = cls.client.admin.command('hello')
        except PyMongoError:
            cls.client.close()
            raise unittest.SkipTest('Mongo de pruebas no disponible')
        if not hello.get('setName'):
            cls.client.close()
            raise unittest.SkipTest('Custodia requiere replica set de pruebas')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        super().setUp()
        self.database = self.client['skopos_test_pdf_' + uuid.uuid4().hex]
        self.addCleanup(lambda: self.client.drop_database(self.database.name))
        self.store = PdfCustodyStore(self.database, load_policy(self.policy_path))

    def test_admit_receipt_fetch_and_mutated_reference(self):
        request = self.write_request()
        admitted = self.store.admit(request)
        self.assertEqual(admitted['admission_status'], 'admitted')
        self.assertEqual(self.store.admit(request)['receipt_id'], admitted['receipt_id'])
        lookup = {'project_id': 'expertogobernanza', 'material_id': 'fixture-pdf',
                  'source_revision': 1, 'expected_source_sha256': SHA,
                  'admission_request_sha256': request['_request_sha256']}
        self.assertEqual(self.store.receipt(lookup)['receipt_id'], admitted['receipt_id'])
        fetch = dict(lookup, operation='fetch_original', output_ref='returned.pdf')
        result = self.store.fetch(fetch)
        self.assertEqual(result['source_sha256'], SHA)
        self.assertEqual((self.root / 'delivery' / 'returned.pdf').read_bytes(), PDF)
        with self.assertRaisesRegex(CustodyError, 'output_unavailable'):
            self.store.fetch(fetch)
        self.assertEqual((self.root / 'delivery' / 'returned.pdf').read_bytes(), PDF)
        (self.root / 'source' / 'original.pdf').write_bytes(PDF + b'changed')
        with self.assertRaisesRegex(CustodyError, 'hash_mismatch'):
            self.store.fetch(dict(fetch, output_ref='second.pdf'))
        self.assertFalse((self.root / 'delivery' / 'second.pdf').exists())

    def test_wrong_revision_and_policy_fail_closed(self):
        request = self.write_request()
        self.store.admit(request)
        different = dict(request, expected_source_sha256='0' * 64)
        with self.assertRaisesRegex(CustodyError, 'hash_mismatch'):
            self.store.admit(different)
        second = dict(request, source_revision=2, request_id='admit-002',
                      expected_previous_sha256='0' * 64)
        with self.assertRaisesRegex(CustodyError, 'predecessor_conflict'):
            self.store.admit(second)
        self.assertEqual(self.store.heads.count_documents({}), 1)
        self.store.policy = dict(self.policy, retention_basis='changed-without-version')
        with self.assertRaisesRegex(CustodyError, 'policy_mismatch'):
            self.store.fetch({'project_id': 'expertogobernanza',
                              'material_id': 'fixture-pdf', 'source_revision': 1,
                              'operation': 'fetch_original', 'expected_source_sha256': SHA,
                              'output_ref': 'drift.pdf'})
        self.policy['retention_until'] = '2000-01-01T00:00:00Z'
        self.store.policy = self.policy
        with self.assertRaisesRegex(CustodyError, 'retention_policy_missing'):
            self.store.fetch({'project_id': 'expertogobernanza',
                              'material_id': 'fixture-pdf', 'source_revision': 1,
                              'operation': 'fetch_original', 'expected_source_sha256': SHA,
                              'output_ref': 'late.pdf'})

    def test_stored_reference_change_is_detected(self):
        request = self.write_request()
        self.store.admit(request)
        self.store.revisions.update_one({}, {'$set': {'source_ref': 'other.pdf'}})
        with self.assertRaisesRegex(CustodyError, 'store_integrity_failed'):
            self.store.fetch({'project_id': 'expertogobernanza',
                              'material_id': 'fixture-pdf', 'source_revision': 1,
                              'operation': 'fetch_original', 'expected_source_sha256': SHA,
                              'output_ref': 'tampered.pdf'})
        self.assertFalse((self.root / 'delivery' / 'tampered.pdf').exists())

    def test_provided_file_positive_and_cli_admission(self):
        request = dict(self.request)
        request['source_delivery'] = {'mode': 'provided_file',
                                      'file_ref': 'sidecar.pdf',
                                      'persistent_ref': 'original.pdf'}
        (self.root / 'input' / 'sidecar.pdf').write_bytes(PDF)
        self.write_request(request)
        output = io.StringIO()
        with redirect_stdout(output):
            code = custody_command(['--policy', str(self.policy_path),
                                    '--database', self.database.name,
                                    '--envelope-ref', 'envelope.json'])
        self.assertEqual(code, 0)
        response = json.loads(output.getvalue())
        self.assertEqual(response['result']['admission_status'], 'admitted')
        stored = self.store.revisions.find_one({})
        self.assertEqual(stored['source_ref'], 'original.pdf')
        self.assertEqual(stored['source_sha256'], SHA)
