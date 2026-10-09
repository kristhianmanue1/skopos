"""Comprueba separación literal y normalizada sin mutar v0.4."""

import copy
import hashlib
import json
from pathlib import Path
import unittest

from skopos.pdf_graph_labels_v05 import build_manifest
from skopos.pdf_graph_labels_v05_host import load_config


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.4-experimental.json'
ANNOTATIONS = ROOT / 'docs/evidencia/pdf-imss-graph-label-annotations-v0.5-local.json'
MANIFEST = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.5-local.json'


class GraphLabelsV05Tests(unittest.TestCase):
    def setUp(self):
        self.parent_raw = PARENT.read_bytes()
        self.parent = json.loads(self.parent_raw)
        self.annotations = json.loads(ANNOTATIONS.read_bytes())
        self.parent_sha = hashlib.sha256(self.parent_raw).hexdigest()

    def test_projection_preserves_v04_and_distinguishes_typo(self):
        original = copy.deepcopy(self.parent)
        result = build_manifest(self.parent, self.parent_sha, self.annotations)
        self.assertEqual(result, json.loads(MANIFEST.read_bytes()))
        self.assertEqual(self.parent, original)
        self.assertEqual(self.parent_sha,
                         '07018142b74249edf0bc056f3b10bee5d1d004e43e77f556b3ef745027efaa98')
        labels = [item for page in result['pages'] for item in page['labels']]
        self.assertEqual(len(labels), 86)
        different = [item for item in labels
                     if item['literal_text'] != item['normalized_text']]
        self.assertEqual([(item['page_number'], item['node_id']) for item in different],
                         [(21, 'n5')])
        self.assertTrue(different[0]['literal_text'].endswith('SALUID'))
        self.assertTrue(different[0]['normalized_text'].endswith('SALUD'))

    def test_tamper_fails_closed(self):
        wrong = copy.deepcopy(self.annotations)
        next(x for x in wrong['labels'] if x['page_number'] == 21 and
             x['node_id'] == 'n5')['literal_text'] = 'SALUD'
        with self.assertRaisesRegex(ValueError, 'literal_override_mismatch'):
            build_manifest(self.parent, self.parent_sha, wrong)
        wrong = copy.deepcopy(self.annotations)
        wrong['labels'][0]['parent_item_id'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'label_lineage_mismatch'):
            build_manifest(self.parent, self.parent_sha, wrong)

    def test_host_config_is_pinned(self):
        path = ROOT / 'runs/pdf-document-imss-pilot-v1/graph-labels-v05-host.json'
        self.assertEqual(load_config(str(path))['schema'],
                         'skopos/pdf-graph-labels-host/v0.5-local')


if __name__ == '__main__':
    unittest.main()
