"""Prepara políticas privadas del segundo manual IMSS sin alterar el piloto DPM."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from skopos.pdf_custody import _policy_digest, _read_under, load_policy
from skopos.pdf_document_store import (_canonical, _file_sha256,
                                       load_document_policy)
from skopos.pdf_document_policy_v02 import (POLICY_SCRIPT,
                                            load_document_policy_v02)


ROOT = Path(__file__).resolve().parents[1]
CONSUMER = Path('/Users/krisnova/www/expertoGobernanza')
PILOT = ROOT / 'runs/pdf-imss-0500-pilot-v1'
PDF_REF = 'docs/fuentes/imss/0500-002-001_3.pdf'
PROVENANCE_REF = 'docs/fuentes/imss/0500-002-001_3-PROCEDENCIA.md'
PDF_SHA256 = 'ce665959759f74331464471c71dc9cff107e061de09b8be5419a7cf1302e48b7'
MATERIAL_ID = 'imss-0500-002-001-2022'
RETENTION_UNTIL = '2026-11-08T00:00:00Z'
MONGO_URI = 'mongodb://127.0.0.1:37034/?replicaSet=skoposPdfImssPilot'
DATABASE = 'skopos_pdf_imss_pilot_v1'


def _write_new(path, value):
    raw = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True).encode() + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _directory(path):
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or os.stat(path).st_mode & 0o077:
        raise ValueError('unsafe_directory:' + str(path))


def _source_preflight():
    original = _read_under(str(CONSUMER), PDF_REF, 2_000_000)
    if hashlib.sha256(original).hexdigest() != PDF_SHA256:
        raise ValueError('source_hash_mismatch:' + PDF_REF)
    provenance = _read_under(str(CONSUMER), PROVENANCE_REF, 256_000)
    return hashlib.sha256(provenance).hexdigest()


def prepare_custody():
    provenance_sha256 = _source_preflight()
    for path in (PILOT, PILOT / 'requests', PILOT / 'input',
                 PILOT / 'custody-delivery', PILOT / 'derived',
                 PILOT / 'derived/requests',
                 PILOT / 'document-delivery', PILOT / 'cache'):
        _directory(path)
    previous_path = ROOT / 'runs/pdf-custody-imss-pilot-v1/policy.json'
    old = load_policy(str(previous_path))
    policy = dict(old)
    policy.update({
        'policy_id': 'expertogobernanza/imss-0500-002-001-2022-reference',
        'policy_version': 'v0.2-2026-10-08',
        'requests_root': str(PILOT / 'requests'),
        'input_root': str(PILOT / 'input'),
        'source_root': str(CONSUMER),
        'delivery_root': str(PILOT / 'custody-delivery'),
        'retention_basis': 'operator_instruction_second_imss_pilot_2026-10-08',
        'retention_until': RETENTION_UNTIL,
        'allowed_materials': [{
            'material_id': MATERIAL_ID, 'source_revision': 1,
            'source_ref': PDF_REF, 'source_sha256': PDF_SHA256,
            'provenance_ref': PROVENANCE_REF,
            'provenance_sha256': provenance_sha256,
        }],
    })
    _write_new(PILOT / 'custody-policy.json', policy)
    config = {
        'schema': 'skopos/pdf-custody-host/v0.1',
        'policy_path': str(PILOT / 'custody-policy.json'),
        'mongo_uri': MONGO_URI, 'database': DATABASE,
        'socket_path': str(PILOT / 'custody.sock'),
    }
    _write_new(PILOT / 'custody-host.json', config)
    load_policy(str(PILOT / 'custody-policy.json'))
    return {'custody_policy_sha256': _policy_digest(policy),
            'custody_policy_path': str(PILOT / 'custody-policy.json')}


def prepare_document(receipt_id):
    if not isinstance(receipt_id, str) or not receipt_id.startswith(
            'expertogobernanza:' + MATERIAL_ID + ':1:'):
        raise ValueError('invalid_receipt_id')
    custody_path = PILOT / 'custody-policy.json'
    custody = load_policy(str(custody_path))
    previous_path = ROOT / 'runs/pdf-document-imss-pilot-v1/policy.json'
    old = load_document_policy(str(previous_path))
    policy = dict(old)
    policy.update({
        'schema': 'skopos/pdf-document-policy/v0.2',
        'policy_id': 'expertogobernanza/imss-0500-002-001-2022-derivatives',
        'policy_version': 'v0.2-2026-10-08',
        'custody_policy_path': str(custody_path),
        'custody_policy_sha256': _policy_digest(custody),
        'custody_receipt_id': receipt_id,
        'material_id': MATERIAL_ID, 'source_sha256': PDF_SHA256,
        'provenance_sha256': custody['allowed_materials'][0]['provenance_sha256'],
        'requests_root': str(PILOT / 'requests'),
        'derived_root': str(PILOT / 'derived'),
        'delivery_root': str(PILOT / 'document-delivery'),
        'cache_root': str(PILOT / 'cache'),
        'retention_basis': 'operator_instruction_second_imss_pilot_2026-10-08',
        'retention_until': RETENTION_UNTIL,
        'max_page': 80, 'max_pages': 80, 'max_ocr_pages': 2,
        'ocr_pages': [1, 37], 'graph_pages': [37],
        'policy_engine_sha256': _file_sha256(POLICY_SCRIPT),
    })
    _write_new(PILOT / 'document-policy.json', policy)
    config = {
        'schema': 'skopos/pdf-document-host-config/v0.2',
        'policy_path': str(PILOT / 'document-policy.json'),
        'mongo_uri': MONGO_URI, 'database': DATABASE,
        'socket_path': str(PILOT / 'document.sock'),
    }
    _write_new(PILOT / 'document-host.json', config)
    load_document_policy_v02(str(PILOT / 'document-policy.json'))
    return {'document_policy_sha256': hashlib.sha256(_canonical(policy)).hexdigest(),
            'document_policy_path': str(PILOT / 'document-policy.json')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('custody', 'document'))
    parser.add_argument('--receipt-id')
    args = parser.parse_args()
    if args.phase == 'document' and not args.receipt_id:
        parser.error('--receipt-id required')
    result = prepare_custody() if args.phase == 'custody' else prepare_document(
        args.receipt_id)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
