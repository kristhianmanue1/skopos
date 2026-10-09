"""Controles de linaje y cierre de entradas de rótulos candidatos."""

import copy
import json
from pathlib import Path
import unittest

from skopos.pdf_graph_labels import build_manifest


ROOT = Path(__file__).resolve().parents[1]


class PdfGraphLabelsTests(unittest.TestCase):
    def setUp(self):
        self.parent_path = ROOT / 'docs/evidencia/pdf-imss-graph-review-v0.3-experimental.json'
        self.parent = json.loads(self.parent_path.read_text())
        self.annotations = json.loads((ROOT / 'docs/evidencia/pdf-imss-graph-label-annotations-v0.4-experimental.json').read_text())
        import hashlib
        self.parent_sha256 = hashlib.sha256(self.parent_path.read_bytes()).hexdigest()

    def test_projection_is_stable_and_preserves_parent(self):
        original = copy.deepcopy(self.parent)
        manifest = build_manifest(self.parent, self.parent_sha256, self.annotations)
        self.assertEqual(manifest, build_manifest(self.parent, self.parent_sha256,
                                                 self.annotations))
        self.assertEqual(original, self.parent)
        self.assertEqual(sum(len(p['labels']) for p in manifest['pages']), 86)
        self.assertTrue(all(item['status'] == 'candidate_unadjudicated'
                            for p in manifest['pages'] for item in p['labels']))

    def test_rejects_wrong_bbox_and_missing_label(self):
        wrong = copy.deepcopy(self.annotations)
        wrong['labels'][0]['bbox'][0] = 0.0
        with self.assertRaisesRegex(ValueError, 'label_lineage_mismatch'):
            build_manifest(self.parent, self.parent_sha256, wrong)
        wrong = copy.deepcopy(self.annotations)
        wrong['labels'][0]['label_candidate'] = ''
        with self.assertRaisesRegex(ValueError, 'missing_label'):
            build_manifest(self.parent, self.parent_sha256, wrong)


if __name__ == '__main__':
    unittest.main()
