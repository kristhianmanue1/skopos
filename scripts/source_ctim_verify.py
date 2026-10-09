"""Repite recibo/recuperación tras reinicio y exige rechazo de hash falso."""

import argparse
import hashlib
import json
import os

from skopos.pdf_custody import _read_under, load_policy
from skopos.pdf_custody_host import HostGateway, load_host_config
from source_ctim_prepare import MATERIALS, PILOT
from source_ctim_pilot import _write_new


def run(material):
    area = PILOT / material
    policy = load_policy(str(area / 'custody-policy.json'))
    item = policy['allowed_materials'][0]
    gateway = HostGateway(load_host_config(str(area / 'custody-host.json')))
    try:
        receipt = gateway.handle({'envelope_ref': 'receipt-envelope.json'})
        fetched = gateway.handle({'envelope_ref': 'fetch-envelope.json'})
        if receipt['status'] != 'ok' or fetched['status'] != 'ok':
            raise RuntimeError('recovery_failed')
        output_ref = fetched['result']['bytes_ref']
        raw = _read_under(policy['delivery_root'], output_ref, policy['max_bytes'])
        if (hashlib.sha256(raw).hexdigest() != item['source_sha256']
                or receipt['result']['receipt_id'] !=
                   'expertogobernanza:' + material + ':1:' +
                   json.loads((area / 'requests' / 'admission-envelope.json').read_text())[
                       'request_sha256'][:16]):
            raise RuntimeError('recovery_hash_mismatch')
        os.unlink(area / 'custody-delivery' / output_ref)
        denied_request = json.loads((area / 'requests' / 'admission.json').read_text())
        denied_request['request_id'] = 'deny-' + material
        denied_request['expected_source_sha256'] = '0' * 64
        digest = _write_new(area / 'requests' / 'denied.json', denied_request)
        _write_new(area / 'requests' / 'denied-envelope.json', {
            'request_file_ref': 'denied.json', 'request_sha256': digest,
            'request_id': denied_request['request_id'],
            'contract_id': denied_request['contract_id'],
            'contract_version': denied_request['contract_version']})
        denied = gateway.handle({'envelope_ref': 'denied-envelope.json'})
        if (denied['status'] == 'ok' or denied['error']['code'] != 'material_not_allowed'):
            raise RuntimeError('negative_control_failed')
        return {'material_id': material, 'recovered_bytes': len(raw),
                'receipt_id': receipt['result']['receipt_id'],
                'negative_code': denied['error']['code']}
    finally:
        gateway.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', required=True, choices=sorted(MATERIALS))
    args = parser.parse_args()
    print(json.dumps(run(args.material), sort_keys=True))


if __name__ == '__main__':
    main()
