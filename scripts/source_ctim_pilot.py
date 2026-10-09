"""Admite y recupera tres originales bajo las políticas locales CTIM."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from skopos.pdf_custody import _read_under, load_policy
from skopos.pdf_custody_host import HostGateway, load_host_config
from source_ctim_prepare import MATERIALS, PILOT


def _write_new(path, data):
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':')).encode() + b'\n'
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600)
    except FileExistsError:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as existing:
            if existing.read(len(raw) + 1) != raw:
                raise RuntimeError('existing_request_mismatch:' + str(path))
        return hashlib.sha256(raw).hexdigest()
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def _call(gateway, area, request, name):
    request_sha256 = _write_new(area / 'requests' / (name + '.json'), request)
    envelope = {'request_file_ref': name + '.json',
                'request_sha256': request_sha256,
                'request_id': request['request_id'],
                'contract_id': request['contract_id'],
                'contract_version': request['contract_version']}
    _write_new(area / 'requests' / (name + '-envelope.json'), envelope)
    response = gateway.handle({'envelope_ref': name + '-envelope.json'})
    if (response['status'] != 'ok' or response['request_sha256'] != request_sha256
            or response['request_id'] != request['request_id']):
        raise RuntimeError(json.dumps(response, sort_keys=True))
    return response['result'], request_sha256


def run(material):
    area = PILOT / material
    policy = load_policy(str(area / 'custody-policy.json'))
    item = policy['allowed_materials'][0]
    config = load_host_config(str(area / 'custody-host.json'))
    gateway = HostGateway(config)
    try:
        common = {'contract_id': 'expertogobernanza/skopos-source',
                  'contract_version': 'v0.3', 'project_id': policy['project_id'],
                  'material_id': material, 'source_revision': 1,
                  'expected_source_sha256': item['source_sha256']}
        admission = dict(common, request_id='admit-' + material,
                         operation='admit_original', scope='single_object',
                         source_delivery={'mode': 'authorized_reference',
                                          'file_ref': item['source_ref']},
                         media_type_declared=item['media_type'],
                         classification=policy['classification'],
                         custody_mode='verified_external_reference',
                         custody_policy_id=policy['policy_id'],
                         custody_policy_version=policy['policy_version'],
                         seal_profile_id=policy['seal_profile_id'],
                         recovery_requirement=policy['recovery_requirement'],
                         limits={'max_bytes': policy['max_bytes'],
                                 'allow_network': False, 'allow_ocr': False},
                         provenance={'asserted_by': policy['owner'],
                                     'claim_status': 'consumer_declared',
                                     'record_ref': item['provenance_ref'],
                                     'record_sha256': item['provenance_sha256']})
        admitted, admission_sha256 = _call(gateway, area, admission, 'admission')
        receipt_request = dict(common, request_id='receipt-' + material,
                               operation='receipt',
                               admission_request_sha256=admission_sha256)
        receipt, _ = _call(gateway, area, receipt_request, 'receipt')
        if (admitted['receipt_id'] != receipt['receipt_id']
                or receipt['source_sha256'] != item['source_sha256']):
            raise RuntimeError('receipt_mismatch')
        output_ref = 'recovery-' + material + ('.html' if item['media_type'] == 'text/html'
                                                else '.pdf')
        fetched, _ = _call(gateway, area,
                           dict(common, request_id='fetch-' + material,
                                operation='fetch_original', output_ref=output_ref),
                           'fetch')
        recovered = _read_under(policy['delivery_root'], output_ref,
                                policy['max_bytes'])
        if (hashlib.sha256(recovered).hexdigest() != item['source_sha256']
                or fetched['byte_length'] != len(recovered)):
            raise RuntimeError('recovery_hash_mismatch')
        os.unlink(area / 'custody-delivery' / output_ref)
        result = {'material_id': material, 'receipt_id': receipt['receipt_id'],
                  'source_sha256': item['source_sha256'],
                  'recovered_bytes': len(recovered),
                  'admission_status': admitted['admission_status'],
                  'mode': fetched['custody_mode']}
        _write_new(area / 'operation-receipt.json', result)
        return result
    finally:
        gateway.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', required=True, choices=sorted(MATERIALS))
    args = parser.parse_args()
    print(json.dumps(run(args.material), sort_keys=True))


if __name__ == '__main__':
    main()
