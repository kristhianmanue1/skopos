"""Consulta ejemplos de páginas PDF CTIM mediante el host de derivados."""

import argparse
import json

from skopos.pdf_document_host import DocumentGateway, load_host_config
from source_ctim_prepare import PILOT, _directory
from source_ctim_pilot import _write_new


QUERIES = {
    'imss-administration-1000-002-001-2025':
        'Coordinación de Proyectos y Seguimiento Institucional',
    'imss-procedure-2900-003-001-2021':
        'Coordinación Técnica de Infraestructura Médica',
    'imss-pobalines-1000-001-029-2022':
        'A partir de la entrada en vigor de las presentes POBALINES',
}


def run(material):
    if material not in QUERIES:
        raise ValueError('unsupported_format')
    area = PILOT / material
    _directory(area / 'queries')
    receipt = json.loads((area / 'derivation-operation-receipt.json').read_text())
    policy = json.loads((area / 'document-policy.json').read_text())
    source = {'material_id': material, 'source_revision': 1,
              'source_sha256': policy['source_sha256'],
              'custody_receipt_id': policy['custody_receipt_id'],
              'custody_policy_sha256': policy['custody_policy_sha256']}
    request = {'contract_id': 'expertogobernanza/skopos-document-derivatives',
               'contract_version': 'v0.1', 'request_id': 'search-' + material,
               'operation': 'search_document', 'project_id': 'expertogobernanza',
               'source': source, 'derivation_id': receipt['derivation_id'],
               'manifest_sha256': receipt['manifest_sha256'],
               'term': QUERIES[material], 'limit': 20}
    request_sha256 = _write_new(area / 'requests' / 'search.json', request)
    envelope = {'request_file_ref': 'search.json',
                'request_sha256': request_sha256,
                'request_id': request['request_id'],
                'contract_id': request['contract_id'],
                'contract_version': request['contract_version']}
    _write_new(area / 'requests' / 'search-envelope.json', envelope)
    gateway = DocumentGateway(load_host_config(str(area / 'document-host.json')))
    try:
        response = gateway.handle({'envelope_ref': 'search-envelope.json'})
        if response['status'] != 'ok' or response['request_sha256'] != request_sha256:
            raise RuntimeError(json.dumps(response, sort_keys=True))
        _write_new(area / 'queries' / 'search-response.json', response)
        candidates = response['result']['candidates']
        if not candidates:
            raise RuntimeError('expected_candidate_missing')
        first = candidates[0]
        evidence_request = dict(request, request_id='evidence-' + material,
                                operation='fetch_evidence', item_id=first['item_id'])
        evidence_request.pop('term')
        evidence_request.pop('limit')
        evidence_sha256 = _write_new(area / 'requests' / 'evidence.json', evidence_request)
        _write_new(area / 'requests' / 'evidence-envelope.json', {
            'request_file_ref': 'evidence.json', 'request_sha256': evidence_sha256,
            'request_id': evidence_request['request_id'],
            'contract_id': evidence_request['contract_id'],
            'contract_version': evidence_request['contract_version']})
        evidence = gateway.handle({'envelope_ref': 'evidence-envelope.json'})
        if evidence['status'] != 'ok' or evidence['result']['item']['item_id'] != first['item_id']:
            raise RuntimeError('evidence_mismatch')
        _write_new(area / 'queries' / 'evidence-response.json', evidence)
        return {'material_id': material, 'candidates': len(candidates),
                'page_number': first['page_number'], 'item_id': first['item_id'],
                'text': first['text'], 'fidelity_status': first['fidelity_status'],
                'request_sha256': request_sha256}
    finally:
        gateway.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', required=True, choices=sorted(QUERIES))
    args = parser.parse_args()
    print(json.dumps(run(args.material), sort_keys=True, ensure_ascii=False))


if __name__ == '__main__':
    main()
