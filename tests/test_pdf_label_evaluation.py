"""Pruebas de candidatos con procedencia y métricas falsables."""

import json
import unittest

from skopos.pdf_label_evaluation import evaluate, project_labels


class PdfLabelEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            'schema': 'skopos/pdf-document-manifest/v0.1',
            'derivation_id': 'a' * 64, 'policy_sha256': 'b' * 64,
            'parent': {'source_sha256': 'c' * 64},
            'pages': [{
                'page_number': 1, 'render': {'sha256': 'd' * 64},
                'native_text': {'lines': [
                    {'text': 'NATIVO', 'bbox': [0.2, 0.2, 0.4, 0.3],
                     'item_id': 'native-1'}]},
                'ocr_text': {'lines': [
                    {'text': 'ERROR', 'bbox': [0.2, 0.2, 0.4, 0.3],
                     'item_id': 'ocr-1'}]},
                'visual_graph': {'nodes': [
                    {'node_id': 'n1', 'bbox': [0.1, 0.1, 0.5, 0.5],
                     'item_id': 'node-1'}], 'edges': [],
                    'direction_rule': 'unknown_without_visible_arrowhead'},
            }]}
        self.reference = {
            'schema': 'skopos/pdf-visual-reference/v0.1',
            'source_sha256': 'c' * 64,
            'review_status': 'producer_self_annotated_unconfirmed',
            'pages': [{'page_number': 1, 'render_sha256': 'd' * 64,
                       'nodes': [{'id': 'r1', 'bbox': [0.1, 0.1, 0.5, 0.5],
                                  'label': 'NATIVO'}], 'edges': []}]}

    def test_candidates_preserve_methods_and_line_ids(self):
        raw = json.dumps(self.manifest).encode()
        projection = project_labels(self.manifest, raw)
        node = projection['pages'][0]['nodes'][0]
        self.assertEqual([('native_text', 'NATIVO', ['native-1']),
                          ('selective_ocr', 'ERROR', ['ocr-1'])],
                         [(c['method'], c['text'], c['line_item_ids'])
                          for c in node['label_candidates']])
        self.assertEqual('unreviewed', projection['fidelity_status'])
        self.assertEqual('a' * 64, projection['parent_derivation_id'])

    def test_wrong_ocr_is_counted_and_wrong_render_is_rejected(self):
        raw = json.dumps(self.manifest).encode()
        projection = project_labels(self.manifest, raw)
        result = evaluate(projection, self.reference)
        labels = result['pages'][0]['labels']
        self.assertEqual(100, labels['native_text']['exact']['percent'])
        self.assertEqual(0, labels['selective_ocr']['exact']['percent'])
        self.assertIsNone(result['pages'][0]['edge_recall']['percent'])
        self.reference['pages'][0]['render_sha256'] = 'e' * 64
        with self.assertRaisesRegex(ValueError, 'reference_render_mismatch'):
            evaluate(projection, self.reference)

    def test_unmatched_prediction_reduces_precision(self):
        raw = json.dumps(self.manifest).encode()
        projection = project_labels(self.manifest, raw)
        extra = dict(projection['pages'][0]['nodes'][0])
        extra['node_id'], extra['bbox'] = 'n2', [0.6, 0.6, 0.9, 0.9]
        projection['pages'][0]['nodes'].append(extra)
        result = evaluate(projection, self.reference)
        self.assertEqual(50, result['pages'][0]['node_precision']['percent'])
        self.assertEqual(100, result['pages'][0]['node_recall']['percent'])

    def test_missing_node_reduces_label_score(self):
        raw = json.dumps(self.manifest).encode()
        projection = project_labels(self.manifest, raw)
        projection['pages'][0]['nodes'].clear()
        result = evaluate(projection, self.reference)
        self.assertEqual(0, result['pages'][0]['labels']['native_text']['exact']['percent'])
        self.assertEqual(0, result['pages'][0]['node_recall']['percent'])

    def test_duplicate_page_and_dangling_edge_rejected(self):
        raw = json.dumps(self.manifest).encode()
        projection = project_labels(self.manifest, raw)
        self.reference['pages'].append(self.reference['pages'][0])
        with self.assertRaisesRegex(ValueError, 'invalid_reference_pages'):
            evaluate(projection, self.reference)
        self.reference['pages'].pop()
        self.reference['pages'][0]['edges'] = [['r1', 'missing']]
        with self.assertRaisesRegex(ValueError, 'invalid_reference_graph'):
            evaluate(projection, self.reference)


if __name__ == '__main__':
    unittest.main()
