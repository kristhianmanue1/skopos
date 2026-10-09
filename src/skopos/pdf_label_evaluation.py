"""Proyección y evaluación local de rótulos; nunca modifica el derivado padre."""

import hashlib
import json
import unicodedata


SCHEMA = 'skopos/pdf-label-candidates/v0.2-experimental'
EVALUATION_SCHEMA = 'skopos/pdf-label-evaluation/v0.1'


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _inside(line, bbox):
    region = line.get('bbox')
    if not isinstance(region, list) or len(region) != 4:
        return False
    x = (region[0] + region[2]) / 2
    y = (region[1] + region[3]) / 2
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def project_labels(manifest, manifest_bytes):
    """Conserva alternativas e identidades de línea; no elige una verdad."""
    if (manifest.get('schema') != 'skopos/pdf-document-manifest/v0.1'
            or not isinstance(manifest.get('pages'), list)):
        raise ValueError('invalid_parent_manifest')
    pages = []
    for page in manifest['pages']:
        nodes = []
        for node in page['visual_graph']['nodes']:
            candidates = []
            for method, key in (('native_text', 'native_text'),
                                ('selective_ocr', 'ocr_text')):
                lines = [line for line in page[key]['lines']
                         if _inside(line, node['bbox'])]
                lines.sort(key=lambda line: (line['bbox'][1], line['bbox'][0],
                                             line['item_id']))
                candidates.append({
                    'method': method,
                    'text': ' '.join(line['text'] for line in lines),
                    'line_item_ids': [line['item_id'] for line in lines],
                    'line_bboxes': [line['bbox'] for line in lines],
                    'status': 'unreviewed' if lines else 'no_lines',
                })
            nodes.append({'node_id': node['node_id'], 'parent_item_id': node['item_id'],
                          'bbox': node['bbox'], 'label_candidates': candidates})
        pages.append({'page_number': page['page_number'],
                      'render_sha256': page['render']['sha256'] if page['render'] else None,
                      'nodes': nodes,
                      'edges': page['visual_graph']['edges'],
                      'direction_rule': page['visual_graph'].get('direction_rule')})
    return {'schema': SCHEMA, 'parent_derivation_id': manifest['derivation_id'],
            'parent_manifest_sha256': _sha256(manifest_bytes),
            'source_sha256': manifest['parent']['source_sha256'],
            'policy_sha256': manifest['policy_sha256'],
            'fidelity_status': 'unreviewed', 'pages': pages}


def _normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold())
    value = ''.join(char for char in value if not unicodedata.combining(char))
    return ' '.join(''.join(char if char.isalnum() else ' ' for char in value).split())


def _distance(first, second):
    previous = list(range(len(second) + 1))
    for index, left in enumerate(first, 1):
        current = [index]
        for column, right in enumerate(second, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (left != right)))
        previous = current
    return previous[-1]


def _iou(first, second):
    width = max(0, min(first[2], second[2]) - max(first[0], second[0]))
    height = max(0, min(first[3], second[3]) - max(first[1], second[1]))
    overlap = width * height
    area_first = (first[2] - first[0]) * (first[3] - first[1])
    area_second = (second[2] - second[0]) * (second[3] - second[1])
    return overlap / (area_first + area_second - overlap) if overlap else 0


def _fraction(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'percent': round(100 * numerator / denominator, 2)
            if denominator else None}


def evaluate(projection, reference, *, iou_threshold=0.5):
    """Compara sólo páginas anotadas; aristas topológicas sin dirección."""
    if (projection.get('schema') != SCHEMA
            or reference.get('schema') != 'skopos/pdf-visual-reference/v0.1'
            or reference.get('source_sha256') != projection.get('source_sha256')
            or not 0 < iou_threshold <= 1):
        raise ValueError('invalid_evaluation_input')
    reference_pages = reference.get('pages')
    if (not isinstance(reference_pages, list) or not reference_pages
            or len({page['page_number'] for page in reference_pages}) != len(reference_pages)):
        raise ValueError('invalid_reference_pages')
    available = {page['page_number']: page for page in projection['pages']}
    details = []
    totals = {'gt_nodes': 0, 'pred_nodes': 0, 'matched_nodes': 0,
              'gt_edges': 0, 'pred_edges': 0, 'matched_edges': 0}
    for ref_page in reference_pages:
        number = ref_page['page_number']
        page = available.get(number)
        if page is None or page['render_sha256'] != ref_page['render_sha256']:
            raise ValueError('reference_render_mismatch')
        gt_nodes, predicted = ref_page['nodes'], page['nodes']
        ref_ids = [node['id'] for node in gt_nodes]
        if (not ref_ids or len(ref_ids) != len(set(ref_ids))
                or any(len(edge) != 2 or edge[0] == edge[1]
                       or any(endpoint not in ref_ids for endpoint in edge)
                       for edge in ref_page['edges'])):
            raise ValueError('invalid_reference_graph')
        pairs = sorted(((_iou(gt['bbox'], node['bbox']), gi, pi)
                        for gi, gt in enumerate(gt_nodes)
                        for pi, node in enumerate(predicted)), reverse=True)
        used_gt, used_pred, matched = set(), set(), {}
        for score, gi, pi in pairs:
            if score < iou_threshold:
                break
            if gi not in used_gt and pi not in used_pred:
                used_gt.add(gi)
                used_pred.add(pi)
                matched[predicted[pi]['node_id']] = gt_nodes[gi]['id']
        gt_edges = {frozenset(edge) for edge in ref_page['edges']}
        pred_edges = {frozenset((matched.get(edge['from_node'], edge['from_node']),
                                matched.get(edge['to_node'], edge['to_node'])))
                      for edge in page['edges']}
        common_edges = len(gt_edges & pred_edges)
        counts = {'gt_nodes': len(gt_nodes), 'pred_nodes': len(predicted),
                  'matched_nodes': len(matched), 'gt_edges': len(gt_edges),
                  'pred_edges': len(pred_edges), 'matched_edges': common_edges}
        for key, value in counts.items():
            totals[key] += value
        labels = {}
        matched_by_reference = {ref_id: node for node in predicted
                                if (ref_id := matched.get(node['node_id'])) is not None}
        for method in ('native_text', 'selective_ocr'):
            exact = edits = characters = word_edits = words = 0
            for truth_node in gt_nodes:
                node = matched_by_reference.get(truth_node['id'])
                candidate = (next(item['text'] for item in node['label_candidates']
                                  if item['method'] == method) if node else '')
                truth = truth_node['label']
                gold, observed = _normalize(truth), _normalize(candidate)
                exact += gold == observed
                edits += _distance(gold, observed)
                characters += len(gold)
                word_edits += _distance(gold.split(), observed.split())
                words += len(gold.split())
            labels[method] = {'exact': _fraction(exact, len(gt_nodes)),
                              'cer': _fraction(edits, characters),
                              'wer': _fraction(word_edits, words)}
        details.append({'page_number': number, 'counts': counts, 'labels': labels,
                        'node_precision': _fraction(len(matched), len(predicted)),
                        'node_recall': _fraction(len(matched), len(gt_nodes)),
                        'edge_precision': _fraction(common_edges, len(pred_edges)),
                        'edge_recall': _fraction(common_edges, len(gt_edges)),
                        'direction_observed': sum(e['direction'] == 'observed'
                                                  for e in page['edges'])})
    return {'schema': EVALUATION_SCHEMA, 'reference_sha256': _sha256(_canonical(reference)),
            'projection_sha256': _sha256(_canonical(projection)),
            'iou_threshold': iou_threshold, 'normalization': 'casefold_nFKD_alnum_spaces',
            'pages': details, 'totals': totals,
            'scope': 'annotated_pages_only', 'review_status': reference['review_status'],
            'geometry_independent_of_prediction':
                reference.get('geometry_independent_of_prediction') is True}
