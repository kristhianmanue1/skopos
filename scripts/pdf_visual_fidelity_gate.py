"""Verifica el recibo visual acotado y recupera sus ítems bajo demanda."""

import argparse
import json
import math
from pathlib import Path
import re
import unicodedata

from pdf_full_document_gate import (NATIVE_ID, NATIVE_SHA, POLICY_SHA,
                                    _canonical, checked, exchange, require, sha)
from skopos.pdf_document_host import load_host_config
from skopos.pdf_document_store import load_document_policy


ROOT = Path(__file__).resolve().parents[1]
ANNOTATION = ROOT / 'docs/evidencia/pdf-imss-visual-self-review-2026-10-08.json'
GRAPH_ID = '1ef12d5a480075214369e9d19dcb6949370119e212b84007ce1b1a5ef1b7b8cf'
GRAPH_SHA = '8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee'
PAGES = [2, 8, 17, 23, 61, 100, 145, 188]
QUANTILES = [0.25, 0.50, 0.75]


def words(text):
    return re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())


def word_edits(actual, reference):
    previous = list(range(len(reference) + 1))
    for index, observed in enumerate(actual, 1):
        current = [index]
        for position, expected in enumerate(reference, 1):
            current.append(min(current[-1] + 1, previous[position] + 1,
                               previous[position - 1] + (observed != expected)))
        previous = current
    return previous[-1]


def selected_lines(manifest):
    selected = []
    for number in PAGES:
        lines = [item for item in manifest['pages'][number - 1]['native_text']['lines']
                 if item['bbox'][1] > 0.14 and item['bbox'][3] < 0.90]
        require(len(lines) >= 3, 'selection_unavailable')
        for quantile in QUANTILES:
            selected.append((number, quantile,
                             lines[math.floor((len(lines) - 1) * quantile)]))
    return selected


def expected_edges(parent_children, node_ids):
    edges = []
    for parent, children in parent_children.items():
        require(parent in node_ids and isinstance(children, list), 'visual_parent')
        for child in children:
            require(child in node_ids and child != parent, 'visual_child')
            edges.append((parent, child))
    require(len(edges) == len(set(edges)) == len(node_ids) - 1, 'visual_edge_count')
    require({child for _, child in edges} == node_ids - {'n1'}, 'visual_tree_coverage')
    return set(edges)


def validate(record, native, graph, policy):
    require(record['schema'] == 'skopos/imss-visual-self-review/v0.1' and
            record['review_type'] == 'nonblind_self_review' and
            record['render_dpi'] == 200, 'review_identity')
    require(record['source_sha256'] == policy['source_sha256'] and
            record['native_derivation_id'] == NATIVE_ID and
            record['native_manifest_sha256'] == NATIVE_SHA and
            record['graph_derivation_id'] == GRAPH_ID and
            record['graph_manifest_sha256'] == GRAPH_SHA, 'review_derivatives')
    require([p['page_number'] for p in native['pages']] == list(range(1, 189)),
            'native_inventory')
    require([p['page_number'] for p in graph['pages']] == [18, 19, 20, 21, 22],
            'graph_inventory')
    selected = selected_lines(native)
    require(len(record['text_samples']) == len(selected) == 24, 'sample_count')
    words_reviewed = 0
    edits = 0
    for annotation, (number, quantile, line) in zip(record['text_samples'], selected):
        require(annotation['page_number'] == number and
                annotation['quantile'] == quantile and
                annotation['item_id'] == line['item_id'] and
                annotation['bbox'] == line['bbox'] and
                annotation['skopos_text'] == line['text'] and
                annotation['visual_review'] == 'match_in_rendered_crop',
                'sample_identity')
        count = len(words(line['text']))
        visual = annotation['visual_transcription']
        require(isinstance(visual, str) and
                annotation['word_count'] == len(words(visual)), 'sample_word_count')
        difference = word_edits(words(line['text']), words(visual))
        require(difference == 0, 'visual_word_discrepancy')
        words_reviewed += count
        edits += difference

    require(len(record['graph_pages']) == 5, 'graph_review_count')
    graph_counts = []
    for annotation, page in zip(record['graph_pages'], graph['pages']):
        number = page['page_number']
        layer = page['visual_graph']
        nodes = {node['node_id']: node for node in layer['nodes']}
        require(annotation['page_number'] == number and
                annotation['observed_box_count'] == len(nodes) and
                layer['status'] == 'partial', 'graph_page_status')
        expected = expected_edges(annotation['visual_parent_children'], set(nodes))
        emitted = {(edge['from_node'], edge['to_node']) for edge in layer['edges']}
        require(len(emitted) == len(layer['edges']), 'duplicate_graph_edge')
        example = annotation['label_counterexample']
        node = nodes[example['node_id']]
        require(example['item_id'] == node['item_id'] and
                example['extracted_label'] == node['label'] and
                example['visual_label'] != node['label'], 'label_counterexample')
        graph_counts.append({'page_number': number, 'boxes': len(nodes),
                             'visual_edges': len(expected),
                             'emitted_edges': len(emitted),
                             'missing_edges': len(expected - emitted),
                             'unsupported_edges': len(emitted - expected),
                             'missing_examples': sorted(expected - emitted)[:3]})
    return selected, graph_counts, words_reviewed, edits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host-config', type=Path,
                        default=ROOT / 'runs/pdf-document-imss-pilot-v1/host.json')
    args = parser.parse_args()
    config = load_host_config(str(args.host_config))
    policy = load_document_policy(config['policy_path'])
    require(sha(_canonical(policy)) == POLICY_SHA, 'policy_mismatch')
    derived = Path(policy['derived_root'])

    def manifest(identifier, digest):
        raw = (derived / identifier / 'manifest.json').read_bytes()
        require(sha(raw) == digest and
                (derived / identifier / 'manifest.sha256').read_text().strip() == digest,
                'manifest_integrity')
        result = json.loads(raw)
        require(result['derivation_id'] == identifier and
                result['policy_sha256'] == POLICY_SHA and
                result['parent']['source_sha256'] == policy['source_sha256'],
                'manifest_parent')
        return result

    native = manifest(NATIVE_ID, NATIVE_SHA)
    graph = manifest(GRAPH_ID, GRAPH_SHA)
    record = json.loads(ANNOTATION.read_text())
    selected, counts, words_reviewed, edits = validate(record, native, graph, policy)
    parent = native['parent']
    for number, _, line in selected:
        result = checked(exchange(config, policy, 'fetch_evidence', source=parent,
                         derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                         item_id=line['item_id'])[0])
        require(result['item'] == line and result['page_number'] == number and
                result['modality'] == 'native_text', 'native_recovery')
    for annotation in record['graph_pages']:
        example = annotation['label_counterexample']
        result = checked(exchange(config, policy, 'fetch_evidence', source=parent,
                         derivation_id=GRAPH_ID, manifest_sha256=GRAPH_SHA,
                         item_id=example['item_id'])[0])
        require(result['page_number'] == annotation['page_number'] and
                result['modality'] == 'visual_graph_node' and
                result['item']['item_id'] == example['item_id'], 'graph_recovery')
    print(json.dumps({'status': 'visual_receipt_gate_passed',
                      'text_lines_selected': len(selected),
                      'text_words_self_reviewed': words_reviewed,
                      'text_word_edits_observed': edits,
                      'graph_pages': counts,
                      'review_type': 'nonblind_self_review',
                      'fidelity_claim': 'sample_only;graph_partial'},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
