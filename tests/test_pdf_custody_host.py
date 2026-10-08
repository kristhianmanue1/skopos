"""Controles del canal de host PDF con material permitido exacto."""

from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
import uuid
from unittest import mock

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import CustodyError, PdfCustodyStore, load_policy
from skopos.pdf_custody_host import (HOST_SCHEMA, HostGateway, _Handler,
                                    host_command, load_host_config)


PDF = b'%PDF-1.4\nfixture\n%%EOF\n'
SHA = hashlib.sha256(PDF).hexdigest()
PROVENANCE = b'Origen atribuido al consumidor.\n'
PROVENANCE_SHA = hashlib.sha256(PROVENANCE).hexdigest()


class HostFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('requests', 'input', 'source', 'delivery'):
            (self.root / name).mkdir()
        (self.root / 'source' / 'original.pdf').write_bytes(PDF)
        (self.root / 'source' / 'provenance.md').write_bytes(PROVENANCE)
        (self.root / 'source' / 'other.pdf').write_bytes(b'%PDF-1.4\nother\n')
        self.policy_path = self.root / 'policy.json'
        self.policy = {
            'schema': 'skopos/pdf-custody-policy/v0.2',
            'project_id': 'expertogobernanza', 'policy_id': 'test/one-pdf',
            'policy_version': 'v0.2', 'owner': 'expertogobernanza',
            'classification': 'consumer_declared_public',
            'requests_root': str(self.root / 'requests'),
            'input_root': str(self.root / 'input'),
            'source_root': str(self.root / 'source'),
            'delivery_root': str(self.root / 'delivery'),
            'retention_until': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            'retention_basis': 'fixture-only', 'max_bytes': 10000,
            'seal_policy': 'not_required', 'seal_profile_id': 'test/not-required',
            'recovery_requirement': 'while_reference_available',
            'allowed_materials': [{
                'material_id': 'fixture-pdf', 'source_revision': 1,
                'source_ref': 'original.pdf', 'source_sha256': SHA,
                'provenance_ref': 'provenance.md',
                'provenance_sha256': PROVENANCE_SHA}]}
        self.save_policy()
        self.config_path = self.root / 'host.json'
        self.config = {'schema': HOST_SCHEMA,
                       'policy_path': str(self.policy_path),
                       'mongo_uri': 'mongodb://localhost:27017',
                       'database': 'skopos_test_pdf_host_' + uuid.uuid4().hex,
                       'socket_path': str(self.root / 'agent.sock')}
        self.config_path.write_text(json.dumps(self.config))
        self.request = {
            'contract_id': 'expertogobernanza/skopos-source',
            'contract_version': 'v0.2', 'request_id': 'admit-001',
            'operation': 'admit_original', 'project_id': 'expertogobernanza',
            'material_id': 'fixture-pdf', 'source_revision': 1,
            'scope': 'single_object',
            'source_delivery': {'mode': 'authorized_reference',
                                'file_ref': 'original.pdf'},
            'expected_source_sha256': SHA,
            'media_type_declared': 'application/pdf',
            'classification': 'consumer_declared_public',
            'custody_mode': 'verified_external_reference',
            'custody_policy_id': 'test/one-pdf',
            'custody_policy_version': 'v0.2',
            'seal_profile_id': 'test/not-required',
            'recovery_requirement': 'while_reference_available',
            'limits': {'max_bytes': 10000, 'allow_network': False,
                       'allow_ocr': False},
            'provenance': {'asserted_by': 'expertogobernanza',
                           'claim_status': 'consumer_declared',
                           'record_ref': 'provenance.md',
                           'record_sha256': PROVENANCE_SHA}}

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.policy))

    def write_request(self, request=None):
        request = request or self.request
        raw = json.dumps(request, separators=(',', ':')).encode()
        (self.root / 'requests' / 'request.json').write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        envelope = {'request_file_ref': 'request.json',
                    'request_sha256': digest,
                    'request_id': request['request_id'],
                    'contract_id': request['contract_id'],
                    'contract_version': request['contract_version']}
        (self.root / 'requests' / 'envelope.json').write_text(json.dumps(envelope))
        return digest

    def gateway(self, client=None):
        return HostGateway(load_host_config(self.config_path), client=client)

    def test_host_rejects_agent_config_and_old_policy(self):
        gateway = self.gateway(client=mock.MagicMock())
        for override in ('policy_path', 'mongo_uri', 'database', 'source_root'):
            with self.subTest(override=override):
                result = gateway.handle({'envelope_ref': 'envelope.json',
                                         override: 'agent-selected'})
                self.assertEqual(result['error']['code'], 'invalid_request')
        self.write_request(dict(self.request, contract_version='v0.1'))
        response = gateway.handle({'envelope_ref': 'envelope.json'})
        self.assertEqual(response['error']['code'], 'unsupported_contract')
        self.policy['schema'] = 'skopos/pdf-custody-policy/v0.1'
        self.save_policy()
        with self.assertRaisesRegex(CustodyError, 'policy_unavailable'):
            self.gateway(client=mock.MagicMock())

    def test_policy_validation_and_socket_call(self):
        self.write_request(dict(self.request, operation='describe_capabilities',
                                request_id='cap-001'))
        gateway = self.gateway(client=mock.MagicMock())
        client, server_socket = socket.socketpair()
        server = mock.Mock(gateway=gateway)
        thread = threading.Thread(target=_Handler, args=(server_socket, None, server))
        thread.start()
        with client:
            client.sendall(b'{"envelope_ref":"envelope.json"}\n')
            with client.makefile('rb') as stream:
                response = json.loads(stream.readline())
        thread.join(timeout=2)
        server_socket.close()
        self.assertFalse(thread.is_alive())
        self.assertEqual(response['schema'], HOST_SCHEMA)
        self.assertEqual(response['status'], 'ok')
        self.assertEqual(response['result']['format_validation'], 'pdf_header_only')
        self.assertEqual(response['result']['policy']['id'], 'test/one-pdf')
        self.assertEqual(response['result']['policy']['recovery_requirement'],
                         'while_reference_available')
        self.assertEqual(response['result']['policy']['max_bytes'], 10000)
        self.policy['allowed_materials'].append(dict(self.policy['allowed_materials'][0]))
        self.save_policy()
        with self.assertRaisesRegex(CustodyError, 'policy_unavailable'):
            load_policy(self.policy_path)

    def test_missing_host_returns_typed_transport_error(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = host_command(['request', '--socket', self.config['socket_path'],
                                 '--envelope-ref', 'envelope.json'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['error']['code'],
                         'host_unavailable')

    def test_incomplete_socket_call_is_bounded(self):
        client, server_socket = socket.socketpair()
        server = mock.Mock(gateway=self.gateway(client=mock.MagicMock()))
        thread = threading.Thread(target=_Handler, args=(server_socket, None, server))
        thread.start()
        with client:
            client.sendall(b'{"envelope_ref":"envelope.json"')
            with client.makefile('rb') as stream:
                response = json.loads(stream.readline())
        thread.join(timeout=3)
        server_socket.close()
        self.assertFalse(thread.is_alive())
        self.assertEqual(response['error']['code'], 'invalid_request')


class HostMongoTests(HostFixture):
    @classmethod
    def setUpClass(cls):
        cls.client = pymongo.MongoClient('mongodb://localhost:27017',
                                         serverSelectionTimeoutMS=1000)
        try:
            hello = cls.client.admin.command('hello')
        except PyMongoError:
            cls.client.close()
            raise unittest.SkipTest('Mongo de pruebas no disponible')
        if not hello.get('setName'):
            cls.client.close()
            raise unittest.SkipTest('Se requiere replica set de pruebas')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: self.client.drop_database(self.config['database']))
        self.gateway_instance = self.gateway(client=self.client)

    def call(self, request):
        digest = self.write_request(request)
        return self.gateway_instance.handle({'envelope_ref': 'envelope.json'}), digest

    def test_positive_reconcile_fetch_and_fail_closed_mutations(self):
        admitted, admission_digest = self.call(self.request)
        self.assertEqual(admitted['result']['admission_status'], 'admitted')
        self.assertEqual(admitted['schema'], HOST_SCHEMA)
        lookup = {'contract_id': self.request['contract_id'],
                  'contract_version': self.request['contract_version'],
                  'request_id': 'receipt-001', 'operation': 'receipt',
                  'project_id': 'expertogobernanza', 'material_id': 'fixture-pdf',
                  'source_revision': 1, 'expected_source_sha256': SHA,
                  'admission_request_sha256': admission_digest}
        receipt, receipt_digest = self.call(lookup)
        self.assertEqual(receipt['result']['receipt_id'], admitted['result']['receipt_id'])
        self.assertNotEqual(receipt_digest, admission_digest)
        changed_policy = dict(self.policy, retention_basis='different-policy')
        other_store = PdfCustodyStore(self.client[self.config['database']], changed_policy)
        with self.assertRaisesRegex(CustodyError, 'policy_mismatch'):
            other_store.receipt(lookup)
        fetch = dict(lookup, operation='fetch_original', request_id='fetch-001',
                     output_ref='returned.pdf')
        fetched, _ = self.call(fetch)
        self.assertEqual(fetched['status'], 'ok')
        self.assertEqual((self.root / 'delivery' / 'returned.pdf').read_bytes(), PDF)
        self.assertEqual(self.call(dict(fetch, output_ref='returned.pdf'))[0]
                         ['error']['code'], 'output_unavailable')
        self.assertEqual(self.gateway_instance.client[self.config['database']]
                         ['pdf_custody_revisions_v1'].count_documents({}), 1)

        with mock.patch('skopos.pdf_custody.os.link', side_effect=PermissionError):
            response, _ = self.call(dict(fetch, output_ref='denied.pdf'))
        self.assertEqual(response['error']['code'], 'output_unavailable')
        self.assertFalse((self.root / 'delivery' / 'denied.pdf').exists())

        request_with_pages = dict(self.request, request_id='pages',
                                  limits=dict(self.request['limits'], max_pages=200))
        self.assertEqual(self.call(request_with_pages)[0]['error']['code'],
                         'unsupported_limit')
        missing_recovery = dict(self.request, request_id='missing-recovery')
        del missing_recovery['recovery_requirement']
        self.assertEqual(self.call(missing_recovery)[0]['error']['code'],
                         'policy_mismatch')

        for change in ({'material_id': 'other'},
                       {'source_delivery': {'mode': 'authorized_reference',
                                            'file_ref': 'other.pdf'}},
                       {'expected_source_sha256': '0' * 64}):
            with self.subTest(change=change):
                response, _ = self.call(dict(self.request, request_id='mutated', **change))
                self.assertEqual(response['error']['code'], 'material_not_allowed')
        (self.root / 'source' / 'link.pdf').symlink_to(self.root / 'source' / 'original.pdf')
        response, _ = self.call(dict(self.request, request_id='link',
                                     source_delivery={'mode': 'authorized_reference',
                                                      'file_ref': 'link.pdf'}))
        self.assertEqual(response['error']['code'], 'material_not_allowed')
        (self.root / 'source' / 'original.pdf').write_bytes(PDF + b'changed')
        response, _ = self.call(dict(fetch, output_ref='changed.pdf'))
        self.assertEqual(response['error']['code'], 'hash_mismatch')
        self.assertFalse((self.root / 'delivery' / 'changed.pdf').exists())
        (self.root / 'source' / 'original.pdf').write_bytes(PDF)
        (self.root / 'source' / 'provenance.md').write_bytes(PROVENANCE + b'changed')
        response, _ = self.call(dict(fetch, output_ref='changed-ficha.pdf'))
        self.assertEqual(response['error']['code'], 'hash_mismatch')
        self.assertFalse((self.root / 'delivery' / 'changed-ficha.pdf').exists())
        (self.root / 'source' / 'provenance.md').write_bytes(PROVENANCE)
        (self.root / 'source' / 'original.pdf').rename(
            self.root / 'source' / 'original-real.pdf')
        (self.root / 'source' / 'original.pdf').symlink_to('original-real.pdf')
        response, _ = self.call(dict(fetch, output_ref='symlink.pdf'))
        self.assertEqual(response['error']['code'], 'path_outside_root')
        self.assertFalse((self.root / 'delivery' / 'symlink.pdf').exists())
        (self.root / 'source' / 'original.pdf').unlink()
        (self.root / 'source' / 'original-real.pdf').rename(
            self.root / 'source' / 'original.pdf')
        self.policy['retention_basis'] = 'changed-without-version'
        self.save_policy()
        response, _ = self.call(dict(fetch, output_ref='policy-changed.pdf'))
        self.assertEqual(response['error']['code'], 'policy_mismatch')
        self.assertEqual(response['request_id'], 'fetch-001')
        self.assertFalse((self.root / 'delivery' / 'policy-changed.pdf').exists())

    def test_expired_policy_and_provenance_rejected(self):
        request = dict(self.request, provenance=dict(self.request['provenance'],
                                                     record_sha256='0' * 64))
        response, _ = self.call(request)
        self.assertEqual(response['error']['code'], 'material_not_allowed')
        self.policy['retention_until'] = '2000-01-01T00:00:00Z'
        self.save_policy()
        with self.assertRaisesRegex(CustodyError, 'retention_policy_missing'):
            self.gateway(client=self.client)
