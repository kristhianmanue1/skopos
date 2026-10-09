"""Ensayo bilateral local del manual IMSS 0500 con recibos persistidos."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket

from skopos.pdf_custody import load_policy
from skopos.pdf_document_policy_v02 import load_document_policy_v02
from skopos.pdf_document_store import _canonical

from pdf_imss_0500_prepare import PILOT, PDF_SHA256, MATERIAL_ID


SOURCE_CONTRACT = 'expertogobernanza/skopos-source'
DOCUMENT_CONTRACT = 'expertogobernanza/skopos-document-derivatives'


def _write_new(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def exchange(config, request, contract, version):
    raw = _canonical(request)
    request_ref = request['request_id'] + '.request.json'
    envelope_ref = request['request_id'] + '.envelope.json'
    root = PILOT / 'requests'
    _write_new(root / request_ref, raw)
    envelope = {
        'request_file_ref': request_ref, 'request_sha256': hashlib.sha256(raw).hexdigest(),
        'request_id': request['request_id'], 'contract_id': contract,
        'contract_version': version,
    }
    _write_new(root / envelope_ref, _canonical(envelope))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(130)
        connection.connect(config['socket_path'])
        connection.sendall(_canonical({'envelope_ref': envelope_ref}) + b'\n')
        response_raw = connection.makefile('rb').readline(65537)
    if not 0 < len(response_raw) <= 65536:
        raise ValueError('response_limit_or_missing')
    response = json.loads(response_raw)
    if (response.get('request_id') != request['request_id']
            or response.get('request_sha256') != envelope['request_sha256']
            or response.get('contract_id') != contract
            or response.get('contract_version') != version):
        raise ValueError('response_correlation_failed')
    if response.get('status') != 'ok':
        raise ValueError('host_error:' + json.dumps(response))
    return {'envelope_ref': envelope_ref,
            'request_sha256': envelope['request_sha256'], 'result': response['result']}


def _request(operation, contract, version, **fields):
    return {'contract_id': contract, 'contract_version': version,
            'request_id': 'imss0500-' + operation.replace('_', '-') + '-'
                          + secrets.token_hex(8),
            'operation': operation, 'project_id': 'expertogobernanza', **fields}


def admit():
    policy = load_policy(str(PILOT / 'custody-policy.json'))
    config = json.loads((PILOT / 'custody-host.json').read_text())
    allowed = policy['allowed_materials'][0]
    request = _request(
        'admit_original', SOURCE_CONTRACT, 'v0.2',
        material_id=MATERIAL_ID, source_revision=1, scope='single_object',
        source_delivery={'mode': 'authorized_reference',
                         'file_ref': allowed['source_ref']},
        expected_source_sha256=PDF_SHA256, media_type_declared='application/pdf',
        classification=policy['classification'],
        custody_mode='verified_external_reference',
        custody_policy_id=policy['policy_id'],
        custody_policy_version=policy['policy_version'],
        seal_profile_id=policy['seal_profile_id'],
        recovery_requirement=policy['recovery_requirement'],
        limits={'max_bytes': policy['max_bytes'], 'allow_network': False,
                'allow_ocr': False},
        provenance={'asserted_by': policy['owner'],
                    'claim_status': 'consumer_declared',
                    'record_ref': allowed['provenance_ref'],
                    'record_sha256': allowed['provenance_sha256']})
    result = exchange(config, request, SOURCE_CONTRACT, 'v0.2')
    if (result['result']['source_sha256'] != PDF_SHA256
            or result['result']['material_id'] != MATERIAL_ID):
        raise ValueError('admission_receipt_mismatch')
    return result


def derive(mode):
    policy = load_document_policy_v02(str(PILOT / 'document-policy.json'))
    config = json.loads((PILOT / 'document-host.json').read_text())
    source = {key: policy[key] for key in (
        'material_id', 'source_revision', 'source_sha256',
        'custody_receipt_id', 'custody_policy_sha256')}
    if mode == 'native':
        pages, modalities, ocr_pages, graph_pages = (
            list(range(1, 81)), ['native_text'], [], [])
    elif mode == 'ocr':
        pages, modalities, ocr_pages, graph_pages = (
            [1, 37], ['native_text', 'selective_ocr'], [1, 37], [])
    else:
        pages, modalities, ocr_pages, graph_pages = (
            [37], ['native_text', 'selective_ocr', 'visual_graph'], [37], [37])
    request = _request(
        'derive_document', DOCUMENT_CONTRACT, 'v0.1', source=source,
        pages=pages, modalities=modalities, ocr_pages=ocr_pages,
        graph_pages=graph_pages,
        limits={'max_pages': len(pages),
                'max_render_pixels': policy['max_render_pixels'],
                'max_seconds': policy['max_seconds'],
                'max_output_bytes': policy['max_output_bytes'],
                'allow_network': False})
    receipt = exchange(config, request, DOCUMENT_CONTRACT, 'v0.1')
    result = receipt['result']
    raw = (PILOT / 'derived' / result['manifest_ref']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != result['manifest_sha256']:
        raise ValueError('manifest_hash_mismatch')
    manifest = json.loads(raw)
    if (manifest['parent'] != source or manifest['page_count'] != 80
            or [item['page_number'] for item in manifest['pages']] != pages
            or manifest['fidelity_status'] != 'unreviewed'):
        raise ValueError('manifest_coverage_mismatch')
    receipt['page_count'] = manifest['page_count']
    receipt['item_count'] = sum(len(page['native_text']['lines'])
                                for page in manifest['pages'])
    receipt['manifest_status'] = 'verified'
    return receipt


def verify(derivation_id, manifest_sha256, request_id, request_sha256):
    policy = load_document_policy_v02(str(PILOT / 'document-policy.json'))
    config = json.loads((PILOT / 'document-host.json').read_text())
    source = {key: policy[key] for key in (
        'material_id', 'source_revision', 'source_sha256',
        'custody_receipt_id', 'custody_policy_sha256')}

    def call(operation, **fields):
        request = _request(operation, DOCUMENT_CONTRACT, 'v0.1',
                           source=source, **fields)
        return exchange(config, request, DOCUMENT_CONTRACT, 'v0.1')['result']

    receipt = call('derivation_receipt', derivation_request_id=request_id,
                   derivation_request_sha256=request_sha256)
    if (receipt['derivation_status'] != 'duplicate'
            or receipt['derivation_id'] != derivation_id
            or receipt['manifest_sha256'] != manifest_sha256):
        raise ValueError('recovery_receipt_mismatch')
    search = call('search_document', derivation_id=derivation_id,
                  manifest_sha256=manifest_sha256,
                  term='Dirección de Prestaciones Médicas', limit=20)
    candidates = [item for item in search['candidates']
                  if item['page_number'] == 45]
    if not candidates or search['coverage']['fidelity_status'] != 'unreviewed':
        raise ValueError('search_coverage_mismatch')
    item = candidates[0]
    evidence = call('fetch_evidence', derivation_id=derivation_id,
                    manifest_sha256=manifest_sha256, item_id=item['item_id'])
    if (evidence['page_number'] != 45 or evidence['item']['item_id'] != item['item_id']
            or evidence['parent'] != source or evidence['modality'] != 'native_text'):
        raise ValueError('evidence_mismatch')
    output_ref = 'imss0500-' + secrets.token_hex(8) + '.json'
    fetched = call('fetch_derivative', derivation_id=derivation_id,
                   manifest_sha256=manifest_sha256, artifact_id='manifest',
                   artifact_sha256=manifest_sha256, output_ref=output_ref)
    output = PILOT / 'document-delivery' / output_ref
    try:
        if (fetched['sha256'] != manifest_sha256
                or hashlib.sha256(output.read_bytes()).hexdigest() != manifest_sha256):
            raise ValueError('fetched_manifest_mismatch')
    finally:
        if output.exists() and not output.is_symlink():
            output.unlink()
    return {'recovered': True, 'page_45_item_id': item['item_id'],
            'bbox': item['bbox'], 'search_candidates': len(search['candidates']),
            'coverage': search['coverage'], 'manifest_fetched': True,
            'delivery_removed': not output.exists()}


def verify_custody(admission_request_sha256):
    policy = load_policy(str(PILOT / 'custody-policy.json'))
    config = json.loads((PILOT / 'custody-host.json').read_text())
    identity = {'material_id': MATERIAL_ID, 'source_revision': 1,
                'expected_source_sha256': PDF_SHA256}

    def call(operation, **fields):
        request = _request(operation, SOURCE_CONTRACT, 'v0.2',
                           **identity, **fields)
        return exchange(config, request, SOURCE_CONTRACT, 'v0.2')['result']

    receipt = call('receipt', admission_request_sha256=admission_request_sha256)
    if (receipt['source_sha256'] != PDF_SHA256
            or receipt['admission_status'] != 'duplicate'):
        raise ValueError('custody_receipt_mismatch')
    output_ref = 'imss0500-' + secrets.token_hex(8) + '.pdf'
    result = call('fetch_original', output_ref=output_ref)
    output = PILOT / 'custody-delivery' / output_ref
    try:
        if (result['source_sha256'] != PDF_SHA256
                or hashlib.sha256(output.read_bytes()).hexdigest() != PDF_SHA256):
            raise ValueError('original_fetch_mismatch')
    finally:
        if output.exists() and not output.is_symlink():
            output.unlink()
    return {'receipt_id': receipt['receipt_id'], 'original_sha256': PDF_SHA256,
            'bytes_fetched': result['byte_length'], 'delivery_removed': not output.exists()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('admit', 'native', 'ocr', 'graph',
                                          'verify', 'verify-custody'))
    parser.add_argument('--derivation-id')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--request-id')
    parser.add_argument('--request-sha256')
    parser.add_argument('--admission-request-sha256')
    args = parser.parse_args()
    if args.phase == 'verify':
        if not all((args.derivation_id, args.manifest_sha256,
                    args.request_id, args.request_sha256)):
            parser.error('verify requires all four identity arguments')
        outcome = verify(args.derivation_id, args.manifest_sha256,
                         args.request_id, args.request_sha256)
    elif args.phase == 'verify-custody':
        if not args.admission_request_sha256:
            parser.error('verify-custody requires admission request SHA')
        outcome = verify_custody(args.admission_request_sha256)
    else:
        outcome = admit() if args.phase == 'admit' else derive(args.phase)
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
