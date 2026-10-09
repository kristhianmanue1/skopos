"""El segundo perfil PDF no amplía material, página ni raíz por solicitud."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from skopos.pdf_custody import _policy_digest
from skopos.pdf_document_host import (HOST_CONFIG_V02, HOST_SCHEMA,
                                      _policy_loader, load_host_config)
from skopos.pdf_document_policy_v02 import (POLICY_SCRIPT,
                                            load_document_policy_v02)
from skopos.pdf_document_store import (DocumentError, EXTRACT_SCRIPT,
                                       GRAPH_SCRIPT, SCRIPT, STORE_SCRIPT,
                                       _file_sha256)


class DocumentPolicyProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('requests', 'input', 'source', 'delivery', 'derived', 'cache'):
            (self.root / name).mkdir()
        expiry = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        self.custody = {
            'schema': 'skopos/pdf-custody-policy/v0.2',
            'project_id': 'expertogobernanza', 'owner': 'expertogobernanza',
            'policy_id': 'fixture/second-reference', 'policy_version': 'v0.2',
            'classification': 'consumer_declared_public',
            'requests_root': str(self.root / 'requests'),
            'input_root': str(self.root / 'input'),
            'source_root': str(self.root / 'source'),
            'delivery_root': str(self.root / 'delivery'),
            'retention_until': expiry, 'retention_basis': 'test',
            'max_bytes': 2_000_000, 'seal_policy': 'not_required',
            'seal_profile_id': 'fixture/not-required',
            'recovery_requirement': 'while_reference_available',
            'allowed_materials': [{
                'material_id': 'fixture-2022', 'source_revision': 1,
                'source_ref': 'original.pdf', 'source_sha256': 'a' * 64,
                'provenance_ref': 'origin.md', 'provenance_sha256': 'b' * 64,
            }],
        }
        self.custody_path = self.root / 'custody-policy.json'
        self.custody_path.write_text(json.dumps(self.custody))
        self.policy = {
            'schema': 'skopos/pdf-document-policy/v0.2',
            'policy_id': 'fixture/second-derivatives', 'policy_version': 'v0.2',
            'project_id': 'expertogobernanza', 'owner': 'expertogobernanza',
            'custody_policy_path': str(self.custody_path),
            'custody_policy_sha256': _policy_digest(self.custody),
            'custody_receipt_id': 'fixture:1:receipt',
            'material_id': 'fixture-2022', 'source_revision': 1,
            'source_sha256': 'a' * 64, 'provenance_sha256': 'b' * 64,
            'requests_root': str(self.root / 'requests'),
            'derived_root': str(self.root / 'derived'),
            'delivery_root': str(self.root / 'delivery'),
            'cache_root': str(self.root / 'cache'),
            'retention_until': expiry, 'retention_basis': 'test',
            'retention_action': 'block_then_explicit_retirement',
            'max_page': 80, 'max_pages': 80, 'max_ocr_pages': 2,
            'ocr_pages': [1, 37], 'graph_pages': [37],
            'allowed_modalities': ['native_text', 'selective_ocr', 'visual_graph'],
            'max_render_pixels': 4_452_000, 'max_seconds': 120,
            'max_output_bytes': 10_000_000, 'render_scale_to': 2400,
            'allow_network': False, 'swift_path': '/usr/bin/swift',
            'renderer_path': '/usr/bin/true',
            'engine_script_sha256': _file_sha256(SCRIPT),
            'graph_engine_sha256': _file_sha256(GRAPH_SCRIPT),
            'extract_engine_sha256': _file_sha256(EXTRACT_SCRIPT),
            'store_engine_sha256': _file_sha256(STORE_SCRIPT),
            'policy_engine_sha256': _file_sha256(POLICY_SCRIPT),
        }
        self.policy_path = self.root / 'document-policy.json'
        self.save()

    def save(self):
        self.policy_path.write_text(json.dumps(self.policy))

    def test_80_page_policy_and_config_are_accepted(self):
        self.assertEqual(load_document_policy_v02(str(self.policy_path))['max_page'], 80)
        config_path = self.root / 'host.json'
        config_path.write_text(json.dumps({
            'schema': HOST_CONFIG_V02, 'policy_path': str(self.policy_path),
            'mongo_uri': 'mongodb://127.0.0.1:37034/', 'database': 'fixture',
            'socket_path': str(self.root / 'document.sock')}))
        self.assertEqual(load_host_config(str(config_path))['schema'], HOST_CONFIG_V02)
        self.assertEqual(HOST_SCHEMA, 'skopos/pdf-document-host/v0.1')

    def test_page_and_engine_mutations_fail_closed(self):
        self.policy['graph_pages'] = [81]
        self.save()
        with self.assertRaisesRegex(DocumentError, 'policy_unavailable'):
            load_document_policy_v02(str(self.policy_path))
        self.policy['graph_pages'] = [37]
        self.policy['policy_engine_sha256'] = '0' * 64
        self.save()
        with self.assertRaisesRegex(DocumentError, 'engine_mismatch'):
            load_document_policy_v02(str(self.policy_path))

    def test_custody_identity_mutation_fails_closed(self):
        self.policy['provenance_sha256'] = 'c' * 64
        self.save()
        with self.assertRaisesRegex(DocumentError, 'custody_policy_mismatch'):
            load_document_policy_v02(str(self.policy_path))

    def test_malformed_host_policy_is_typed_failure(self):
        self.policy['ocr_pages'] = [{'page': 1}]
        self.save()
        with self.assertRaisesRegex(DocumentError, 'policy_unavailable'):
            _policy_loader({'schema': HOST_CONFIG_V02})(str(self.policy_path))


if __name__ == '__main__':
    unittest.main()
