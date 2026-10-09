"""Proyecta candidatos PDF v0.2 y evalúa una referencia visual local."""

import argparse
import hashlib
import json
from pathlib import Path

from skopos.pdf_label_evaluation import evaluate, project_labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--render-root', type=Path, required=True)
    parser.add_argument('--show-candidates', action='store_true')
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    manifest = json.loads(raw)
    reference = json.loads(args.reference.read_bytes())
    for page in reference['pages']:
        render_path = args.render_root / ('page-%03d.png' % page['page_number'])
        digest = hashlib.sha256(render_path.read_bytes()).hexdigest()
        if digest != page['render_sha256']:
            raise ValueError('reference_render_bytes_mismatch')
    projection = project_labels(manifest, raw)
    result = evaluate(projection, reference)
    if args.show_candidates:
        result['label_candidates'] = [page for page in projection['pages']
                                      if page['page_number'] in
                                      {item['page_number'] for item in reference['pages']}]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
