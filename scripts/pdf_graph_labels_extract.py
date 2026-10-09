"""Genera anotaciones candidatas por caja desde el PDF exacto del piloto."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from skopos.pdf_graph_labels import build_manifest  # noqa: E402


PARENT = ROOT / 'docs/evidencia/pdf-imss-graph-review-v0.3-experimental.json'
ANNOTATIONS = ROOT / 'docs/evidencia/pdf-imss-graph-label-annotations-v0.4-experimental.json'
MANIFEST = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.4-experimental.json'
SOURCE_SHA256 = '719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323'
NS = {'h': 'http://www.w3.org/1999/xhtml'}
VISUAL_18 = {
    'n1': 'DIRECCIÓN DE PRESTACIONES MÉDICAS',
    'n2': 'UNIDAD DE PLANEACIÓN E INNOVACIÓN EN SALUD',
    'n3': 'UNIDAD DE ATENCIÓN MÉDICA',
    'n4': 'UNIDAD DE EDUCACIÓN E INVESTIGACIÓN',
    'n5': 'UNIDAD DE INFRAESTRUCTURA, SERVICIOS MÉDICOS INDIRECTOS E INTEGRACIÓN SECTORIAL',
    'n6': 'COORDINACIÓN DE PROYECTOS ESPECIALES EN SALUD',
    'n7': 'COORDINACIÓN DE SERVICIOS ADMINISTRATIVOS',
    'n8': 'DIVISIÓN DE MEJORA DE GESTIÓN ADMINISTRATIVA Y NORMATIVIDAD MÉDICA',
}
VISUAL_OVERRIDES = {(21, 'n5'): 'COORDINACIÓN DE INFORMACIÓN E INTELIGENCIA EN SALUD'}


def file_sha256(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def native_page(binary, pdf, number):
    raw = subprocess.check_output([binary, '-f', str(number), '-l', str(number),
                                   '-bbox-layout', pdf, '-'], timeout=30)
    root = ET.fromstring(raw)
    page = root.find('.//h:page', NS)
    if page is None:
        raise ValueError('native_page_missing')
    return page


def extract_label(page, bbox):
    width, height = float(page.attrib['width']), float(page.attrib['height'])
    x1, y1, x2, y2 = bbox
    lines = []
    for line in page.findall('.//h:line', NS):
        words = []
        for word in line.findall('h:word', NS):
            box = word.attrib
            left, right = float(box['xMin']), float(box['xMax'])
            top, bottom = float(box['yMin']), float(box['yMax'])
            center_x, center_y = (left + right) / 2, (top + bottom) / 2
            if (x1 * width - 3 <= center_x <= x2 * width + 3 and
                    y1 * height - 3 <= center_y <= y2 * height + 3):
                words.append((word.text or '', left, right))
        if words:
            joined = words[0][0]
            for previous, current in zip(words, words[1:]):
                joined += ('' if current[1] - previous[2] < 0.9 else ' ') + current[0]
            lines.append(joined)
    return ' '.join(lines)


def write_compact(path, value, collection):
    """Mantiene una entrada por línea y el expediente bajo el gate de tamaño."""
    lines = ['{']
    keys = list(value)
    for index, key in enumerate(keys):
        if key != collection:
            encoded = json.dumps(value[key], ensure_ascii=False, separators=(',', ':'))
            lines.append('  ' + json.dumps(key) + ': ' + encoded +
                         (',' if index + 1 < len(keys) else ''))
            continue
        lines.append('  ' + json.dumps(key) + ': [')
        for item_index, item in enumerate(value[key]):
            if collection == 'pages':
                lines.append('    {"page_number":' + str(item['page_number']) +
                             ',"render_sha256":' + json.dumps(item['render_sha256']) +
                             ',"labels":[')
                for label_index, label in enumerate(item['labels']):
                    lines.append('      ' + json.dumps(label, ensure_ascii=False,
                                                   separators=(',', ':')) +
                                 (',' if label_index + 1 < len(item['labels']) else ''))
                lines.append('    ]}' + (',' if item_index + 1 < len(value[key]) else ''))
            else:
                lines.append('    ' + json.dumps(item, ensure_ascii=False,
                                                separators=(',', ':')) +
                             (',' if item_index + 1 < len(value[key]) else ''))
        lines.append('  ]' + (',' if index + 1 < len(keys) else ''))
    lines.append('}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--pdftotext', default=shutil.which('pdftotext'))
    args = parser.parse_args()
    if not args.pdftotext or file_sha256(args.pdf) != SOURCE_SHA256:
        raise ValueError('source_or_extractor_unavailable')
    parent_raw = PARENT.read_bytes()
    parent_sha256 = hashlib.sha256(parent_raw).hexdigest()
    parent = json.loads(parent_raw)
    records = []
    for item in parent['pages']:
        number = item['page_number']
        native = native_page(args.pdftotext, args.pdf, number)
        for node in item['nodes']:
            node_id = node['node_id']
            joined = extract_label(native, node['bbox'])
            if number == 18:
                if joined:
                    raise ValueError('unexpected_native_text_page_18')
                candidate = VISUAL_18[node_id]
                method = 'visual_nonblind'
            elif (number, node_id) in VISUAL_OVERRIDES:
                candidate = VISUAL_OVERRIDES[(number, node_id)]
                method = 'native_bbox_with_visual_override'
            else:
                if not joined:
                    raise ValueError('native_text_missing')
                candidate = joined
                method = 'native_bbox_spacing_join'
            records.append({'page_number': number, 'node_id': node_id,
                            'parent_item_id': node['item_id'], 'bbox': node['bbox'],
                            'render_sha256': item['render_sha256'],
                            'native_joined_label': joined,
                            'label_candidate': candidate, 'method': method})
    annotations = {
        'schema': 'skopos/pdf-graph-label-annotations/v0.4-experimental',
        'source_sha256': SOURCE_SHA256, 'parent_manifest_sha256': parent_sha256,
        'extractor': 'Poppler pdftotext -bbox-layout; center in bbox +/-3pt; '
                     'join adjacent fragments with gap <0.9pt; visual overrides explicit',
        'labels': records,
    }
    manifest = build_manifest(parent, parent_sha256, annotations)
    write_compact(ANNOTATIONS, annotations, 'labels')
    write_compact(MANIFEST, manifest, 'pages')
    print(json.dumps({'labels': len(records), 'derivation_id': manifest['derivation_id'],
                      'annotation_file_sha256': file_sha256(ANNOTATIONS),
                      'manifest_sha256': file_sha256(MANIFEST)}, sort_keys=True))


if __name__ == '__main__':
    main()
