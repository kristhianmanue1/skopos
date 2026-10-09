"""Construye la revisión literal v0.5 desde el cotejo visual acotado."""

import argparse
import hashlib
import json
from pathlib import Path

from skopos.pdf_graph_labels_v05 import ANNOTATION_SCHEMA, build_manifest


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.4-experimental.json'
ANNOTATIONS = ROOT / 'docs/evidencia/pdf-imss-graph-label-annotations-v0.5-local.json'
MANIFEST = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.5-local.json'
AUDIT = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v04-visual-audit-2026-10-08.jsonl'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, default=AUDIT)
    args = parser.parse_args()
    parent_raw = PARENT.read_bytes()
    parent = json.loads(parent_raw)
    audit_raw = args.audit.read_bytes()
    audit = [json.loads(line) for line in audit_raw.splitlines() if line]
    verified = {(entry['page_number'], entry['node_id']): entry for entry in audit}
    if len(audit) != 86 or len(verified) != 86:
        raise ValueError('audit_coverage_mismatch')
    labels = []
    for page in parent['pages']:
        for old in page['labels']:
            entry = verified[(page['page_number'], old['node_id'])]
            if (entry['item_id'] != old['item_id'] or
                    entry['candidate'] != old['label_candidate'] or
                    entry['bbox'] != old['bbox'] or
                    entry['result'] not in ('literal_match',
                                            'candidate_normalizes_source_typo')):
                raise ValueError('audit_lineage_mismatch')
            labels.append({'page_number': page['page_number'],
                           'node_id': old['node_id'], 'parent_item_id': old['item_id'],
                           'bbox': old['bbox'], 'render_sha256': old['render_sha256'],
                           'literal_text': entry['visible_literal'],
                           'normalized_text': old['label_candidate'],
                           'review_method': 'visual_nonblind'})
    annotations = {'schema': ANNOTATION_SCHEMA,
                   'source_sha256': parent['source']['source_sha256'],
                   'parent_manifest_sha256': sha(parent_raw),
                   'audit_sha256': sha(audit_raw), 'labels': labels}
    manifest = build_manifest(parent, sha(parent_raw), annotations)
    for path, value in ((ANNOTATIONS, annotations), (MANIFEST, manifest)):
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')) + '\n')
    print(json.dumps({'annotation_sha256': sha(ANNOTATIONS.read_bytes()),
                      'manifest_sha256': sha(MANIFEST.read_bytes()),
                      'derivation_id': manifest['derivation_id']}))


if __name__ == '__main__':
    main()
