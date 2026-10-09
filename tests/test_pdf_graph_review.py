"""Controles de identidad y topología del derivado visual versionado."""

import copy
import unittest

from skopos.pdf_graph_review import build_manifest


def fixture():
    pages = []
    reviews = []
    for number in range(18, 23):
        nodes = [
            {'node_id': 'n1', 'item_id': f'parent-{number}-1', 'bbox': [0, 0, .5, .5],
             'label': 'ROOT'},
            {'node_id': 'n2', 'item_id': f'parent-{number}-2', 'bbox': [.5, .5, 1, 1],
             'label': 'BAD'},
        ]
        pages.append({'page_number': number, 'render': {'sha256': 'b' * 64},
                      'visual_graph': {'nodes': nodes, 'edges': []}})
        reviews.append({'page_number': number, 'observed_box_count': 2,
                        'visual_parent_children': {'n1': ['n2']},
                        'label_counterexample': {
                            'node_id': 'n2', 'item_id': f'parent-{number}-2',
                            'extracted_label': 'BAD', 'visual_label': 'GOOD'}})
    parent = {'schema': 'skopos/pdf-document-manifest/v0.1',
              'derivation_id': 'a' * 64, 'fidelity_status': 'unreviewed',
              'parent': {'source_sha256': 'c' * 64},
              'policy_sha256': 'd' * 64, 'pages': pages}
    review = {'schema': 'skopos/imss-visual-self-review/v0.1',
              'review_type': 'nonblind_self_review',
              'graph_derivation_id': 'a' * 64,
              'graph_manifest_sha256': 'e' * 64,
              'source_sha256': 'c' * 64, 'graph_pages': reviews}
    return parent, review


class GraphReviewTests(unittest.TestCase):
    def test_versioned_candidate_preserves_parent_and_status(self):
        parent, review = fixture()
        original = copy.deepcopy(parent)
        result = build_manifest(parent, 'e' * 64, review, 'f' * 64)
        self.assertEqual(parent, original)
        self.assertEqual(result['review_sha256'], 'f' * 64)
        self.assertEqual(result['fidelity_status'], 'unreviewed_partial')
        self.assertEqual(len(result['pages']), 5)
        page = result['pages'][0]
        self.assertEqual(page['coverage']['added_visual_candidates'], 1)
        self.assertEqual(page['edges'][0]['status'], 'visual_candidate_unadjudicated')
        self.assertEqual(page['nodes'][1]['raw_ocr_label'], 'BAD')
        self.assertEqual(page['nodes'][1]['visual_label_candidate'], 'GOOD')
        replay = build_manifest(parent, 'e' * 64, review, 'f' * 64)
        self.assertEqual(result, replay)
        changed = build_manifest(parent, 'e' * 64, review, '1' * 64)
        self.assertNotEqual(result['derivation_id'], changed['derivation_id'])

    def test_rejects_unbacked_or_invalid_relations(self):
        parent, review = fixture()
        review['graph_pages'][0]['visual_parent_children']['n1'] = ['n99']
        with self.assertRaisesRegex(ValueError, 'invalid_review_edge'):
            build_manifest(parent, 'e' * 64, review, 'f' * 64)
        parent, review = fixture()
        parent['pages'][0]['visual_graph']['edges'].append(
            {'from_node': 'n2', 'to_node': 'n1'})
        with self.assertRaisesRegex(ValueError, 'unsupported_original_edge'):
            build_manifest(parent, 'e' * 64, review, 'f' * 64)
        parent, review = fixture()
        review['graph_pages'][0]['label_counterexample']['item_id'] = 'alien'
        with self.assertRaisesRegex(ValueError, 'label_reference_mismatch'):
            build_manifest(parent, 'e' * 64, review, 'f' * 64)


if __name__ == '__main__':
    unittest.main()
