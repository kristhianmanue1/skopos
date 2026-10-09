"""Proyección inmutable de una autorrevisión visual de organigramas."""

import hashlib
import json


SCHEMA = 'skopos/pdf-graph-review/v0.3-experimental'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _edges(mapping, node_ids):
    pairs = [(parent, child) for parent, children in mapping.items()
             for child in children]
    require(all(parent in node_ids and child in node_ids and parent != child
                for parent, child in pairs), 'invalid_review_edge')
    require(len(pairs) == len(set(pairs)) == len(node_ids) - 1,
            'invalid_review_tree')
    require({child for _, child in pairs} == node_ids - {'n1'},
            'invalid_review_parent')
    visited = {'n1'}
    frontier = ['n1']
    while frontier:
        parent = frontier.pop()
        for child in mapping.get(parent, []):
            require(child not in visited, 'review_cycle')
            visited.add(child)
            frontier.append(child)
    require(visited == node_ids, 'review_disconnected')
    return pairs


def build_manifest(parent, parent_sha256, review, review_sha256):
    require(parent['schema'] == 'skopos/pdf-document-manifest/v0.1' and
            [p['page_number'] for p in parent['pages']] == [18, 19, 20, 21, 22]
            and parent['fidelity_status'] == 'unreviewed', 'parent_mismatch')
    require(review['schema'] == 'skopos/imss-visual-self-review/v0.1' and
            review['review_type'] == 'nonblind_self_review' and
            review['graph_derivation_id'] == parent['derivation_id'] and
            review['graph_manifest_sha256'] == parent_sha256 and
            review['source_sha256'] == parent['parent']['source_sha256'] and
            [p['page_number'] for p in review['graph_pages']] ==
            [18, 19, 20, 21, 22], 'review_mismatch')
    derivation_id = digest(canonical({'schema': SCHEMA,
                                     'parent_derivation_id': parent['derivation_id'],
                                     'parent_manifest_sha256': parent_sha256,
                                     'review_sha256': review_sha256}))
    pages = []
    for original, annotation in zip(parent['pages'], review['graph_pages']):
        number = original['page_number']
        original_nodes = original['visual_graph']['nodes']
        node_ids = {node['node_id'] for node in original_nodes}
        require(len(node_ids) == annotation['observed_box_count'] ==
                len(original_nodes), 'box_count_mismatch')
        pairs = _edges(annotation['visual_parent_children'], node_ids)
        original_pairs = {(edge['from_node'], edge['to_node'])
                          for edge in original['visual_graph']['edges']}
        require(original_pairs.issubset(set(pairs)), 'unsupported_original_edge')
        example = annotation['label_counterexample']
        require(example['node_id'] in node_ids, 'label_node_missing')
        nodes = []
        for node in original_nodes:
            candidate = (example['visual_label']
                         if node['node_id'] == example['node_id'] else None)
            if candidate is not None:
                require(node['item_id'] == example['item_id'] and
                        node['label'] == example['extracted_label'] and
                        candidate != node['label'], 'label_reference_mismatch')
            identity = {'derivation_id': derivation_id, 'page_number': number,
                        'node_id': node['node_id'],
                        'parent_item_id': node['item_id'],
                        'visual_label_candidate': candidate}
            nodes.append(dict(identity, item_id=digest(canonical(identity)),
                              bbox=node['bbox'], raw_ocr_label=node['label'],
                              review_status=('nonblind_visual_candidate'
                                             if candidate is not None else 'unreviewed')))
        item_ids = {node['node_id']: node['item_id'] for node in nodes}
        edges = []
        for parent_id, child_id in pairs:
            identity = {'derivation_id': derivation_id, 'page_number': number,
                        'parent_node_id': parent_id, 'child_node_id': child_id,
                        'parent_item_id': item_ids[parent_id],
                        'child_item_id': item_ids[child_id]}
            edges.append(dict(identity, item_id=digest(canonical(identity)),
                              origin=('v0.1_topology_hypothesis'
                                      if (parent_id, child_id) in original_pairs
                                      else 'nonblind_visual_review'),
                              status='visual_candidate_unadjudicated',
                              direction='layout_parent_to_child_candidate'))
        pages.append({'page_number': number,
                      'render_sha256': original['render']['sha256'],
                      'nodes': nodes, 'edges': edges,
                      'coverage': {'box_count': len(nodes),
                                   'visual_edge_candidates': len(edges),
                                   'inherited_hypotheses': len(original_pairs),
                                   'added_visual_candidates':
                                       len(edges) - len(original_pairs),
                                   'graph_status': 'partial'}})
    return {'schema': SCHEMA, 'derivation_id': derivation_id,
            'source': parent['parent'],
            'document_policy_sha256': parent['policy_sha256'],
            'parent_derivation_id': parent['derivation_id'],
            'parent_manifest_sha256': parent_sha256,
            'review_sha256': review_sha256,
            'review_type': 'nonblind_self_review',
            'fidelity_status': 'unreviewed_partial', 'pages': pages}
