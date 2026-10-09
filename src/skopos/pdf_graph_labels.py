"""Proyecta rótulos candidatos por caja sin modificar el grafo padre."""

import hashlib
import json


SCHEMA = 'skopos/pdf-graph-labels/v0.4-experimental'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def build_manifest(parent, parent_sha256, annotations):
    if parent.get('schema') != 'skopos/pdf-graph-review/v0.3-experimental':
        raise ValueError('parent_schema_mismatch')
    if annotations.get('schema') != 'skopos/pdf-graph-label-annotations/v0.4-experimental':
        raise ValueError('annotation_schema_mismatch')
    if annotations.get('source_sha256') != parent['source']['source_sha256']:
        raise ValueError('source_mismatch')
    if annotations.get('parent_manifest_sha256') != parent_sha256:
        raise ValueError('parent_mismatch')
    pages = parent['pages']
    expected = {(p['page_number'], n['node_id']): n
                for p in pages for n in p['nodes']}
    records = annotations.get('labels')
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError('label_count_mismatch')
    actual = {(r['page_number'], r['node_id']): r for r in records}
    if len(actual) != len(records) or set(actual) != set(expected):
        raise ValueError('label_identity_mismatch')
    for key, record in actual.items():
        node = expected[key]
        if (record['parent_item_id'] != node['item_id'] or
                record['bbox'] != node['bbox'] or
                record['render_sha256'] != next(p['render_sha256'] for p in pages
                                                 if p['page_number'] == key[0])):
            raise ValueError('label_lineage_mismatch')
        if record['method'] not in ('native_bbox_spacing_join',
                                    'visual_nonblind',
                                    'native_bbox_with_visual_override'):
            raise ValueError('invalid_method')
        if not isinstance(record['label_candidate'], str) or not record['label_candidate']:
            raise ValueError('missing_label')
        if (record['method'] == 'native_bbox_spacing_join' and
                record['label_candidate'] != record['native_joined_label']):
            raise ValueError('native_label_mismatch')
        if (record['method'] == 'visual_nonblind' and record['native_joined_label']):
            raise ValueError('unexpected_native_label')
    derivation_id = digest({'schema': SCHEMA, 'parent_derivation_id': parent['derivation_id'],
                            'parent_manifest_sha256': parent_sha256,
                            'annotation_sha256': digest(annotations)})
    output = []
    for page in pages:
        items = []
        for node in page['nodes']:
            record = dict(actual[(page['page_number'], node['node_id'])])
            record['item_id'] = digest({'derivation_id': derivation_id,
                                        'parent_item_id': node['item_id']})
            record['derivation_id'] = derivation_id
            record['status'] = 'candidate_unadjudicated'
            items.append(record)
        output.append({'page_number': page['page_number'],
                       'render_sha256': page['render_sha256'], 'labels': items})
    return {'schema': SCHEMA, 'derivation_id': derivation_id,
            'source': parent['source'],
            'parent_derivation_id': parent['derivation_id'],
            'parent_manifest_sha256': parent_sha256,
            'annotation_sha256': digest(annotations),
            'fidelity_status': 'unreviewed_partial', 'pages': output}
