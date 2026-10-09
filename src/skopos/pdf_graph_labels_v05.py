"""Separa la grafía visible y la normalización de rótulos PDF."""

from skopos.pdf_graph_labels import digest


SCHEMA = 'skopos/pdf-graph-labels/v0.5-local'
ANNOTATION_SCHEMA = 'skopos/pdf-graph-label-annotations/v0.5-local'


def build_manifest(parent, parent_sha256, annotations):
    if parent.get('schema') != 'skopos/pdf-graph-labels/v0.4-experimental':
        raise ValueError('parent_schema_mismatch')
    if annotations.get('schema') != ANNOTATION_SCHEMA:
        raise ValueError('annotation_schema_mismatch')
    if annotations.get('parent_manifest_sha256') != parent_sha256:
        raise ValueError('parent_mismatch')
    if annotations.get('source_sha256') != parent['source']['source_sha256']:
        raise ValueError('source_mismatch')
    expected = {(page['page_number'], item['node_id']): item
                for page in parent['pages'] for item in page['labels']}
    records = annotations.get('labels')
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError('label_count_mismatch')
    actual = {(item['page_number'], item['node_id']): item for item in records}
    if len(actual) != len(records) or set(actual) != set(expected):
        raise ValueError('label_identity_mismatch')
    for key, record in actual.items():
        old = expected[key]
        if (record['parent_item_id'] != old['item_id'] or
                record['bbox'] != old['bbox'] or
                record['render_sha256'] != old['render_sha256'] or
                record['normalized_text'] != old['label_candidate'] or
                not isinstance(record['literal_text'], str) or
                not record['literal_text']):
            raise ValueError('label_lineage_mismatch')
        if key == (21, 'n5'):
            if (not record['literal_text'].endswith('SALUID') or
                    not record['normalized_text'].endswith('SALUD') or
                    record['literal_text'] != old['native_joined_label']):
                raise ValueError('literal_override_mismatch')
        elif record['literal_text'] != old['label_candidate']:
            raise ValueError('literal_mismatch')
    derivation_id = digest({'schema': SCHEMA, 'parent_derivation_id': parent['derivation_id'],
                            'parent_manifest_sha256': parent_sha256,
                            'annotation_sha256': digest(annotations)})
    pages = []
    for page in parent['pages']:
        labels = []
        for old in page['labels']:
            record = dict(actual[(page['page_number'], old['node_id'])])
            record['item_id'] = digest({'derivation_id': derivation_id,
                                        'parent_item_id': old['item_id']})
            record['derivation_id'] = derivation_id
            record['status'] = 'visually_checked_nonblind'
            labels.append(record)
        pages.append({'page_number': page['page_number'],
                      'render_sha256': page['render_sha256'], 'labels': labels})
    return {'schema': SCHEMA, 'derivation_id': derivation_id,
            'source': parent['source'], 'parent_derivation_id': parent['derivation_id'],
            'parent_manifest_sha256': parent_sha256,
            'annotation_sha256': digest(annotations),
            'fidelity_status': 'bounded_nonblind_review', 'pages': pages}
