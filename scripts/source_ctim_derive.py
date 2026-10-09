"""Deriva páginas CTIM acotadas tras comprobar custodia original."""

import argparse
import hashlib
import json

from skopos.pdf_document_host import DocumentGateway, load_host_config
from source_ctim_prepare import PILOT
from source_ctim_pilot import _write_new


PAGES = {
    'imss-administration-1000-002-001-2025': [1, 282],
    'imss-procedure-2900-003-001-2021': [3, 6, 15, 20],
    'imss-pobalines-1000-001-029-2022': [20, 75],
}


def run(material):
    if material not in PAGES:
        raise ValueError('unsupported_format')
    area = PILOT / material
    config = load_host_config(str(area / 'document-host.json'))
    gateway = DocumentGateway(config)
    try:
        policy = gateway.policy
        pages = PAGES[material]
        request = {
            'contract_id': 'expertogobernanza/skopos-document-derivatives',
            'contract_version': 'v0.1', 'request_id': 'derive-' + material,
            'operation': 'derive_document', 'project_id': 'expertogobernanza',
            'source': {
                'material_id': material, 'source_revision': 1,
                'source_sha256': policy['source_sha256'],
                'custody_receipt_id': policy['custody_receipt_id'],
                'custody_policy_sha256': policy['custody_policy_sha256'],
            },
            'pages': pages,
            'modalities': (['native_text', 'selective_ocr']
                           if material == 'imss-pobalines-1000-001-029-2022'
                           else ['native_text']),
            'ocr_pages': ([75] if material == 'imss-pobalines-1000-001-029-2022'
                          else []),
            'graph_pages': [],
            'limits': {'allow_network': False, 'max_pages': len(pages),
                       'max_render_pixels': policy['max_render_pixels'],
                       'max_seconds': policy['max_seconds'],
                       'max_output_bytes': policy['max_output_bytes']},
        }
        raw = json.dumps(request, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode() + b'\n'
        request_sha256 = _write_new(area / 'requests' / 'derivation.json', request)
        assert hashlib.sha256(raw).hexdigest() == request_sha256
        envelope = {'request_file_ref': 'derivation.json',
                    'request_sha256': request_sha256,
                    'request_id': request['request_id'],
                    'contract_id': request['contract_id'],
                    'contract_version': request['contract_version']}
        _write_new(area / 'requests' / 'derivation-envelope.json', envelope)
        response = gateway.handle({'envelope_ref': 'derivation-envelope.json'})
        if (response['status'] != 'ok' or response['request_sha256'] != request_sha256):
            raise RuntimeError(json.dumps(response, sort_keys=True))
        receipt = response['result']
        manifest_path = area / 'derived' / receipt['manifest_ref']
        manifest_raw = manifest_path.read_bytes()
        if hashlib.sha256(manifest_raw).hexdigest() != receipt['manifest_sha256']:
            raise RuntimeError('manifest_hash_mismatch')
        manifest = json.loads(manifest_raw)
        result = {'material_id': material, 'derivation_id': receipt['derivation_id'],
                  'manifest_sha256': receipt['manifest_sha256'],
                  'pages': pages, 'page_summary': receipt['page_summary'],
                  'fidelity_status': manifest['fidelity_status']}
        _write_new(area / 'derivation-operation-receipt.json', result)
        return result
    finally:
        gateway.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', required=True, choices=sorted(PAGES))
    args = parser.parse_args()
    print(json.dumps(run(args.material), sort_keys=True))


if __name__ == '__main__':
    main()
