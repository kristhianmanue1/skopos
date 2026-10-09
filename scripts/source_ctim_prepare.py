"""Prepara custodia acotada para tres fuentes CTIM sin escribir en el consumidor."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from skopos.pdf_custody import _policy_digest, _read_under, load_policy
from skopos.pdf_document_policy_v02 import (POLICY_SCRIPT,
                                            load_document_policy_v02)
from skopos.pdf_document_store import _canonical, _file_sha256


ROOT = Path(__file__).resolve().parents[1]
CONSUMER = Path('/Users/krisnova/www/expertoGobernanza')
PILOT = ROOT / 'runs/source-imss-ctim-pilot-v1'
INVENTORY_REF = 'docs/evidencia/ctim-source-register-2026-10-08.json'
RETENTION_UNTIL = '2026-11-08T00:00:00Z'
RETENTION_BASIS = 'operator_instruction_ctim_source_pilot_2026-10-08'
MONGO_URI = 'mongodb://127.0.0.1:37034/?replicaSet=skoposPdfImssPilot'
DATABASE = 'skopos_pdf_imss_pilot_v1'
MATERIALS = {
    'imss-administration-1000-002-001-2025': ('application/pdf', 403),
    'imss-procedure-2900-003-001-2021': ('application/pdf', 91),
    'dof-pobalines-1000-001-029-2021': ('text/html', None),
    'imss-pobalines-1000-001-029-2022': ('application/pdf', 78),
    'dof-pobalines-1000-001-029-2022-agreement': ('text/html', None),
}


def _directory(path):
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or os.stat(path).st_mode & 0o077:
        raise ValueError('unsafe_directory:' + str(path))


def _write_new(path, data):
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode() + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def _inventory():
    raw = _read_under(str(CONSUMER), INVENTORY_REF, 64 * 1024)
    inventory = json.loads(raw)
    if inventory.get('schema') != 'expertogobernanza/source-inventory/v1':
        raise ValueError('inventory_schema_mismatch')
    sources = {item['id']: item for item in inventory['sources']}
    if any(material not in sources for material in MATERIALS):
        raise ValueError('inventory_missing_material')
    return sources, hashlib.sha256(raw).hexdigest()


def _source(material, sources):
    source = sources[material]
    media_type, pages = MATERIALS[material]
    if source['media_type'] != media_type or source['pages'] != pages:
        raise ValueError('inventory_material_mismatch:' + material)
    raw = _read_under(str(CONSUMER), source['path'], 32 * 1024 * 1024)
    if (hashlib.sha256(raw).hexdigest() != source['sha256']
            or len(raw) != source['bytes']):
        raise ValueError('source_hash_mismatch:' + material)
    if media_type == 'application/pdf' and not raw.startswith(b'%PDF-'):
        raise ValueError('unsupported_format:' + material)
    if (media_type == 'text/html' and not raw[:1024].lstrip().lower().startswith(
            (b'<!doctype html', b'<html'))):
        raise ValueError('unsupported_format:' + material)
    return source


def prepare_custody(material):
    sources, inventory_sha256 = _inventory()
    source = _source(material, sources)
    area = PILOT / material
    for path in (PILOT, area, area / 'requests', area / 'input', area / 'provenance',
                 area / 'custody-delivery', area / 'derived', area / 'derived/requests',
                 area / 'document-delivery', area / 'cache'):
        _directory(path)
    provenance = {
        'schema': 'skopos/attributed-provenance/v0.1',
        'material_id': material, 'asserted_by': 'expertogobernanza',
        'claim_status': 'consumer_declared',
        'source_inventory_ref': INVENTORY_REF,
        'source_inventory_sha256': inventory_sha256,
        'origin_url_attributed': source['url'],
        'source_ref': source['path'], 'source_sha256': source['sha256'],
        'source_bytes': source['bytes'], 'media_type': source['media_type'],
        'pages_declared': source['pages'],
        'observed_at': '2026-10-08',
        'limits': 'local bytes checked; remote byte equality and legal currency unverified',
    }
    provenance_sha256 = _write_new(area / 'provenance' / 'record.json', provenance)
    policy = {
        'schema': 'skopos/source-custody-policy/v0.3',
        'project_id': 'expertogobernanza', 'owner': 'expertogobernanza',
        'policy_id': 'expertogobernanza/' + material + '-reference',
        'policy_version': 'v0.3-2026-10-08',
        'classification': 'consumer_declared_public',
        'requests_root': str(area / 'requests'), 'input_root': str(area / 'input'),
        'source_root': str(CONSUMER),
        'provenance_root': str(area / 'provenance'),
        'delivery_root': str(area / 'custody-delivery'),
        'retention_until': RETENTION_UNTIL, 'retention_basis': RETENTION_BASIS,
        'max_bytes': min(32 * 1024 * 1024, max(source['bytes'], 1)),
        'seal_policy': 'not_required',
        'seal_profile_id': 'expertogobernanza/not-required',
        'recovery_requirement': 'while_reference_available',
        'allowed_materials': [{
            'material_id': material, 'source_revision': 1,
            'source_ref': source['path'], 'source_sha256': source['sha256'],
            'media_type': source['media_type'],
            'provenance_ref': 'record.json',
            'provenance_sha256': provenance_sha256,
        }],
    }
    policy_path = area / 'custody-policy.json'
    _write_new(policy_path, policy)
    host = {'schema': 'skopos/source-custody-host/v0.3',
            'policy_path': str(policy_path), 'mongo_uri': MONGO_URI,
            'database': DATABASE, 'socket_path': str(area / 'custody.sock')}
    _write_new(area / 'custody-host.json', host)
    load_policy(str(policy_path))
    return {'policy_path': str(policy_path), 'policy_sha256': _policy_digest(policy),
            'material_id': material, 'source_sha256': source['sha256'],
            'provenance_sha256': provenance_sha256}


def prepare_document(material, receipt_id):
    if MATERIALS[material][0] != 'application/pdf':
        raise ValueError('unsupported_format')
    if not isinstance(receipt_id, str) or not receipt_id.startswith(
            'expertogobernanza:' + material + ':1:'):
        raise ValueError('invalid_receipt_id')
    area = PILOT / material
    custody_path = area / 'custody-policy.json'
    custody = load_policy(str(custody_path))
    source = custody['allowed_materials'][0]
    previous = ROOT / 'runs/pdf-imss-0500-pilot-v1/document-policy.json'
    with previous.open('r', encoding='utf-8') as stream:
        policy = json.load(stream)
    policy.update({
        'policy_id': 'expertogobernanza/' + material + '-derivatives',
        'policy_version': 'v0.2-2026-10-08',
        'custody_policy_path': str(custody_path),
        'custody_policy_sha256': _policy_digest(custody),
        'custody_receipt_id': receipt_id,
        'material_id': material, 'source_sha256': source['source_sha256'],
        'provenance_sha256': source['provenance_sha256'],
        'requests_root': str(area / 'requests'),
        'derived_root': str(area / 'derived'),
        'delivery_root': str(area / 'document-delivery'),
        'cache_root': str(area / 'cache'),
        'retention_basis': RETENTION_BASIS, 'retention_until': RETENTION_UNTIL,
        'max_page': MATERIALS[material][1],
        'max_pages': MATERIALS[material][1],
        'max_ocr_pages': (1 if material == 'imss-pobalines-1000-001-029-2022' else 0),
        'ocr_pages': ([75] if material == 'imss-pobalines-1000-001-029-2022'
                      else []),
        'graph_pages': [],
        'policy_engine_sha256': _file_sha256(POLICY_SCRIPT),
    })
    policy_path = area / 'document-policy.json'
    _write_new(policy_path, policy)
    host = {'schema': 'skopos/pdf-document-host-config/v0.2',
            'policy_path': str(policy_path), 'mongo_uri': MONGO_URI,
            'database': DATABASE, 'socket_path': str(area / 'document.sock')}
    _write_new(area / 'document-host.json', host)
    load_document_policy_v02(str(policy_path))
    return {'policy_path': str(policy_path),
            'policy_sha256': hashlib.sha256(_canonical(policy)).hexdigest(),
            'material_id': material}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('custody', 'document'))
    parser.add_argument('--material', required=True, choices=sorted(MATERIALS))
    parser.add_argument('--receipt-id')
    args = parser.parse_args()
    if args.phase == 'document' and not args.receipt_id:
        parser.error('--receipt-id required for document')
    result = (prepare_custody(args.material) if args.phase == 'custody'
              else prepare_document(args.material, args.receipt_id))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
