"""Produce un derivado HTML local sin elevarlo a cita ni contrato de host."""

import hashlib
import json
import os
from pathlib import Path

import pymongo

import skopos.html_derivative as html_derivative
from skopos.html_derivative import derive_html_text
from skopos.pdf_custody import (SOURCE_SCHEMA, _policy_digest, _read_under,
                               _verified_document, load_policy)
from source_ctim_prepare import DATABASE, MONGO_URI, PILOT


MATERIALS = ('dof-pobalines-1000-001-029-2021',
             'dof-pobalines-1000-001-029-2022-agreement')


def run(material):
    area = PILOT / material
    policy = load_policy(str(area / 'custody-policy.json'))
    item = policy['allowed_materials'][0]
    key = 'expertogobernanza:' + material + ':1'
    with pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000) as client:
        document = client[DATABASE].source_custody_revisions_v1.find_one({'_id': key})
    if document is None:
        raise RuntimeError('custody_receipt_missing')
    _verified_document(document, key, SOURCE_SCHEMA)
    receipt_id = key + ':' + document['request_sha256'][:16]
    if (document['source_sha256'] != item['source_sha256']
            or document['policy_sha256'] != _policy_digest(policy)
            or document['provenance']['record_sha256'] != item['provenance_sha256']):
        raise RuntimeError('custody_receipt_mismatch')
    raw = _read_under(policy['source_root'], item['source_ref'], policy['max_bytes'])
    provenance = _read_under(policy['provenance_root'], item['provenance_ref'],
                             256 * 1024)
    if (hashlib.sha256(raw).hexdigest() != item['source_sha256']
            or hashlib.sha256(provenance).hexdigest() != item['provenance_sha256']):
        raise RuntimeError('source_hash_mismatch')
    derivative = derive_html_text(raw)
    derivative['extractor_version'] = 'skopos/html-text-derivative/v0.1'
    derivative['extractor_sha256'] = hashlib.sha256(
        Path(html_derivative.__file__).read_bytes()).hexdigest()
    derivative['parent'] = {'material_id': material, 'source_revision': 1,
                            'custody_receipt_id': receipt_id,
                            'custody_policy_sha256': _policy_digest(policy)}
    output = area / 'derived' / 'html-text.json'
    content = json.dumps(derivative, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode() + b'\n'
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    result = {'material_id': material, 'receipt_id': receipt_id,
              'derivative_sha256': hashlib.sha256(content).hexdigest(),
              'items': len(derivative['items']),
              'fidelity_status': derivative['fidelity_status'],
              'coverage': derivative['coverage']}
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--material', required=True, choices=MATERIALS)
    args = parser.parse_args()
    print(json.dumps(run(args.material), sort_keys=True))


if __name__ == '__main__':
    main()
