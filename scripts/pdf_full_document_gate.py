"""Comprueba cobertura e identidad del PDF IMSS completo bajo política v0.1."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess

from skopos.pdf_document_host import load_host_config
from skopos.pdf_document_store import _canonical, load_document_policy
from skopos.pdf_custody import load_policy


PILOT = Path('/Users/krisnova/www/aria/skopos/runs/pdf-document-imss-pilot-v1')
NATIVE_ID = '372fdaef7fb1171ec8dce708b79ef1e32b38e43dfb1b079e6b27ae070d8f7587'
NATIVE_SHA = '7f81b1616b10549439cd536737e76663cfea7cec3bf7a6ec3fbf10241d8292ed'
OCR_ID = '7f132071b5e1c372e41d0ce9a83df7c966955c7fcb7036f80cdcbcecf5654a46'
OCR_SHA = '3ca9d7a5be5e451f63608015585a4eee92d2109046d390de99d793ac2f83651d'
POLICY_SHA = '4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b'
CONTRACT = 'expertogobernanza/skopos-document-derivatives'
VERSION = 'v0.1'
ANCHORS = {2: 'ÍNDICE', 17: '5.11', 22: '6.1.4 Unidad de Infraestructura',
           23: '7. Funciones Sustantivas', 100: '8. Determinar los indicadores',
           188: '11. Coordinar el apoyo logístico'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def validate_manifest(manifest, derivation_id, pages, parent):
    require(manifest.get('schema') == 'skopos/pdf-document-manifest/v0.1', 'schema')
    require(manifest.get('contract_id') == CONTRACT and
            manifest.get('contract_version') == VERSION, 'contract')
    require(manifest.get('derivation_id') == derivation_id and
            manifest.get('parent') == parent and
            manifest.get('policy_sha256') == POLICY_SHA, 'identity')
    require(manifest.get('page_count') == 188 and
            manifest.get('fidelity_status') == 'unreviewed', 'page_count_or_fidelity')
    require([p['page_number'] for p in manifest['pages']] == pages, 'page_sequence')
    count = 0
    for page in manifest['pages']:
        for field, modality in (('native_text', 'native_text'),
                                ('ocr_text', 'selective_ocr')):
            layer = page[field]
            require(layer['status'] in ('extracted', 'no_text', 'not_run', 'partial'),
                    'layer_status')
            for index, line in enumerate(layer['lines']):
                box = line['bbox']
                require(isinstance(line['text'], str) and
                        isinstance(box, list) and len(box) == 4 and
                        all(isinstance(v, (float, int)) and 0 <= v <= 1 for v in box)
                        and box[0] <= box[2] and box[1] <= box[3], 'line_geometry')
                identity = {'derivation_id': derivation_id,
                            'page_number': page['page_number'], 'modality': modality,
                            'index': index, 'text': line['text'], 'bbox': box}
                require(line['item_id'] == sha(_canonical(identity)), 'item_identity')
                count += 1
    return count


def exchange(config, policy, operation, **fields):
    request_id = 'sk-full-' + secrets.token_hex(12)
    payload = {'contract_id': CONTRACT, 'contract_version': VERSION,
               'request_id': request_id, 'project_id': 'expertogobernanza',
               'operation': operation, **fields}
    raw = _canonical(payload)
    nonce = secrets.token_hex(12)
    request_ref, envelope_ref = nonce + '.request.json', nonce + '.envelope.json'
    envelope = {'request_file_ref': request_ref, 'request_sha256': sha(raw),
                'request_id': request_id, 'contract_id': CONTRACT,
                'contract_version': VERSION}
    root = Path(policy['requests_root'])
    write_new(root / request_ref, raw)
    write_new(root / envelope_ref, _canonical(envelope))

    def call(read=True):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(config['socket_path'])
            connection.sendall(_canonical({'envelope_ref': envelope_ref}) + b'\n')
            if not read:
                return None
            response_raw = connection.makefile('rb').readline(65537)
        require(0 < len(response_raw) <= 65536, 'response_length')
        response = json.loads(response_raw)
        require(response.get('request_id') == request_id and
                response.get('request_sha256') == sha(raw) and
                response.get('contract_id') == CONTRACT and
                response.get('contract_version') == VERSION, 'response_correlation')
        return response

    return call, {'request_ref': request_ref, 'request_sha256': sha(raw)}


def checked(call):
    response = call()
    require(response['status'] == 'ok', 'host_error:' + str(response['error']))
    return response['result']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host-config', type=Path, default=PILOT / 'host.json')
    args = parser.parse_args()
    config = load_host_config(str(args.host_config))
    policy = load_document_policy(config['policy_path'])
    require(sha(_canonical(policy)) == POLICY_SHA, 'policy_identity')
    custody = load_policy(policy['custody_policy_path'])
    source_ref = custody['allowed_materials'][0]['source_ref']
    source = Path(custody['source_root']) / source_ref
    require(sha(source.read_bytes()) == policy['source_sha256'], 'source_integrity')
    info = subprocess.run(['pdfinfo', str(source)], capture_output=True, text=True,
                          check=True).stdout
    require(any(line.partition(':')[0].strip() == 'Pages' and
                line.partition(':')[2].strip() == '188'
                for line in info.splitlines()),
            'physical_pages')
    parent = {key: policy[key] for key in ('material_id', 'source_revision',
              'source_sha256', 'custody_receipt_id', 'custody_policy_sha256')}
    derived = Path(policy['derived_root'])

    def load_manifest(derivation_id, expected_sha, pages):
        raw = (derived / derivation_id / 'manifest.json').read_bytes()
        sidecar = (derived / derivation_id / 'manifest.sha256').read_text().strip()
        require(sha(raw) == sidecar == expected_sha, 'manifest_digest')
        manifest = json.loads(raw)
        count = validate_manifest(manifest, derivation_id, pages, parent)
        return manifest, count

    native, native_items = load_manifest(NATIVE_ID, NATIVE_SHA, list(range(1, 189)))
    ocr, ocr_items = load_manifest(OCR_ID, OCR_SHA, [1, 18, 19, 20, 21, 22])
    statuses = [p['native_text']['status'] for p in native['pages']]
    require(statuses == ['no_text'] + ['extracted'] * 187, 'native_coverage')
    require(all(p['native_text']['lines'] for p in native['pages'][1:]),
            'empty_extracted_page')
    require(all(p['ocr_text']['status'] == 'not_run' for p in native['pages']),
            'native_unexpected_ocr')
    require(ocr['pages'][0]['native_text']['status'] == 'no_text' and
            ocr['pages'][0]['ocr_text']['status'] == 'extracted' and
            bool(ocr['pages'][0]['ocr_text']['lines']), 'cover_ocr')

    # Controles positivos y mutaciones sólo en memoria, sin tocar derivados.
    for mutation in ('page', 'item'):
        changed = copy.deepcopy(native)
        if mutation == 'page':
            del changed['pages'][22]
        else:
            changed['pages'][22]['native_text']['lines'][0]['item_id'] = '0' * 64
        try:
            validate_manifest(changed, NATIVE_ID, list(range(1, 189)), parent)
        except ValueError:
            pass
        else:
            raise ValueError('mutation_not_detected:' + mutation)

    offer = checked(exchange(config, policy, 'describe_document_capabilities')[0])
    require(offer['policy']['policy_sha256'] == POLICY_SHA, 'offer_policy')
    output_ref = 'sk-full-' + secrets.token_hex(12) + '.json'
    delivered = Path(policy['delivery_root']) / output_ref
    delivered_owned = False
    try:
        fetched = checked(exchange(config, policy, 'fetch_derivative', source=parent,
                          derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                          artifact_id='manifest', artifact_sha256=NATIVE_SHA,
                          output_ref=output_ref)[0])
        delivered_owned = True
        raw = delivered.read_bytes()
        require(fetched['bytes_ref'] == output_ref and
                fetched['byte_length'] == len(raw) and
                fetched['sha256'] == sha(raw) == NATIVE_SHA and
                json.loads(raw) == native, 'delivered_manifest')
    finally:
        if delivered_owned:
            delivered.unlink(missing_ok=True)
    samples = []
    for page_number, anchor in ANCHORS.items():
        page = native['pages'][page_number - 1]
        line = next((item for item in page['native_text']['lines']
                     if anchor in item['text']), None)
        require(line is not None, 'anchor_missing:' + str(page_number))
        evidence = checked(exchange(config, policy, 'fetch_evidence', source=parent,
                           derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                           item_id=line['item_id'])[0])
        require(evidence['item'] == line and evidence['page_number'] == page_number
                and evidence['modality'] == 'native_text' and
                evidence['parent'] == parent and
                evidence['fidelity_status'] == 'unreviewed', 'evidence_mismatch')
        matches = checked(exchange(config, policy, 'search_document', source=parent,
                          derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                          term=anchor, limit=20)[0])
        require(any(c['item_id'] == line['item_id'] and
                    c['page_number'] == page_number for c in matches['candidates']),
                'search_mismatch:' + str(page_number))
        require(len(matches['coverage']['page_statuses']) == 188 and
                'visual_graph_labels' in matches['coverage']['exclusions'],
                'search_coverage')
        samples.append({'page': page_number, 'item_id': line['item_id'],
                        'text': line['text']})

    cover_line = ocr['pages'][0]['ocr_text']['lines'][0]
    cover = checked(exchange(config, policy, 'fetch_evidence', source=parent,
                    derivation_id=OCR_ID, manifest_sha256=OCR_SHA,
                    item_id=cover_line['item_id'])[0])
    require(cover['page_number'] == 1 and cover['modality'] == 'ocr_text' and
            cover['item'] == cover_line, 'cover_recovery')

    negative = {}
    for name, changes, code in (
            ('wrong_manifest', {'manifest_sha256': '0' * 64}, 'manifest_integrity_failed'),
            ('wrong_source', {'source': dict(parent, source_sha256='0' * 64)},
             'source_mismatch'),
            ('unknown_item', {'item_id': '0' * 64}, 'evidence_unavailable')):
        fields = {'source': parent, 'derivation_id': NATIVE_ID,
                  'manifest_sha256': NATIVE_SHA, 'item_id': samples[0]['item_id']}
        fields.update(changes)
        response = exchange(config, policy, 'fetch_evidence', **fields)[0]()
        require(response['error']['code'] == code and response['result'] is None,
                'negative_control:' + name)
        negative[name] = code

    no_match = checked(exchange(config, policy, 'search_document', source=parent,
                       derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                       term='skopos-no-match-' + secrets.token_hex(12), limit=20)[0])
    require(no_match['match_status'] == 'no_match' and
            no_match['candidates'] == [] and
            len(no_match['coverage']['page_statuses']) == 188, 'negative_search')
    negative['absent_term'] = 'no_match'
    out_of_range = exchange(config, policy, 'derive_document', source=parent,
                    pages=[189], modalities=['native_text'], ocr_pages=[],
                    graph_pages=[], limits={'max_pages': 1,
                    'max_render_pixels': policy['max_render_pixels'],
                    'max_seconds': policy['max_seconds'],
                    'max_output_bytes': policy['max_output_bytes'],
                    'allow_network': False})[0]()
    require(out_of_range['error']['code'] == 'invalid_limits' and
            out_of_range['result'] is None, 'out_of_range_page')
    negative['page_189'] = 'invalid_limits'

    replay, replay_request = exchange(config, policy, 'fetch_evidence', source=parent,
                      derivation_id=NATIVE_ID, manifest_sha256=NATIVE_SHA,
                      item_id=samples[-1]['item_id'])
    replay(read=False)
    first, second = replay(), replay()
    require(first == second and first['status'] == 'ok', 'replay_mismatch')
    print(json.dumps({'status': 'coverage_gate_passed', 'source_sha256':
                      policy['source_sha256'], 'native_manifest_sha256': NATIVE_SHA,
                      'ocr_manifest_sha256': OCR_SHA, 'page_count': 188,
                      'native_extracted_pages': 187, 'native_no_text_pages': [1],
                      'native_items': native_items, 'ocr_items': ocr_items,
                      'samples': samples, 'negative_controls': negative,
                      'replay_request': replay_request,
                      'fidelity_status': 'unreviewed'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
