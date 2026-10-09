"""Fija el perfil privado de lectura para los siete originales CTIM."""

import hashlib
import json
from pathlib import Path

from skopos.ctim_source_access import POLICY_SCHEMA, load_access_policy
from source_ctim_prepare import (CONSUMER, DATABASE, INVENTORY_REF, MONGO_URI,
                                 PILOT, ROOT, _directory, _write_new)


ACCESS_AREA = PILOT / 'seven-source-access'
PDFS = {
    'imss-dpm-2000-002-001-2025':
        ('pdf-custody-imss-pilot-v1/policy.json',
         'pdf-document-imss-pilot-v1/policy.json',
         '372fdaef7fb1171ec8dce708b79ef1e32b38e43dfb1b079e6b27ae070d8f7587',
         'pdf-document-imss-pilot-v1/derived'),
    'imss-organization-0500-002-001-2022':
        ('pdf-imss-0500-pilot-v1/custody-policy.json',
         'pdf-imss-0500-pilot-v1/document-policy.json',
         'e86d5c6ab6d45d1143bc964fdcd4ecfeceda2c4a23965cc693655fd6b643eadd',
         'pdf-imss-0500-pilot-v1/derived'),
    'imss-administration-1000-002-001-2025':
        ('source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/custody-policy.json',
         'source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/document-policy.json',
         'ba5ce2b82273d8f9bc1a43305ba288d71077729abbe0f2e21550cb7f45f57dc1',
         'source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/derived'),
    'imss-procedure-2900-003-001-2021':
        ('source-imss-ctim-pilot-v1/imss-procedure-2900-003-001-2021/custody-policy.json',
         'source-imss-ctim-pilot-v1/imss-procedure-2900-003-001-2021/document-policy.json',
         '0bf9b839c94bc7c57c122700c4f60cad8efa0de0c350058bbbffaee7a2d47973',
         'source-imss-ctim-pilot-v1/imss-procedure-2900-003-001-2021/derived'),
    'imss-pobalines-1000-001-029-2022':
        ('source-imss-ctim-pilot-v1/imss-pobalines-1000-001-029-2022/custody-policy.json',
         'source-imss-ctim-pilot-v1/imss-pobalines-1000-001-029-2022/document-policy.json',
         '1744c626f0300b8b481324ffbcb47addacc8e0d837277b9123e7137a79752959',
         'source-imss-ctim-pilot-v1/imss-pobalines-1000-001-029-2022/derived'),
}
HTMLS = ('dof-pobalines-1000-001-029-2021',
         'dof-pobalines-1000-001-029-2022-agreement')


def prepare():
    inventory_path = CONSUMER / INVENTORY_REF
    inventory_raw = inventory_path.read_bytes()
    inventory = json.loads(inventory_raw)
    if len(inventory['sources']) != 7:
        raise ValueError('inventory_count_mismatch')
    sources = []
    for source in inventory['sources']:
        source_id = source['id']
        if source_id in PDFS:
            custody, document, derivation, derived = PDFS[source_id]
            manifest_path = ROOT / 'runs' / derived / derivation / 'manifest.json'
            manifest_raw = manifest_path.read_bytes()
            manifest = json.loads(manifest_raw)
            if (manifest['parent']['source_sha256'] != source['sha256']
                    or manifest['page_count'] != source['pages']
                    or len(manifest['pages']) != source['pages']):
                raise ValueError('manifest_mismatch:' + source_id)
            sources.append({'source_id': source_id,
                            'custody_policy_path': str(ROOT / 'runs' / custody),
                            'document_policy_path': str(ROOT / 'runs' / document),
                            'derivation_id': derivation,
                            'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest()})
        elif source_id in HTMLS:
            area = PILOT / source_id
            derivative_path = area / 'derived/html-text.json'
            derivative_raw = derivative_path.read_bytes()
            derivative = json.loads(derivative_raw)
            if derivative['source_sha256'] != source['sha256']:
                raise ValueError('derivative_mismatch:' + source_id)
            sources.append({'source_id': source_id,
                            'custody_policy_path': str(area / 'custody-policy.json'),
                            'derivative_path': str(derivative_path),
                            'derivative_sha256': hashlib.sha256(derivative_raw).hexdigest()})
        else:
            raise ValueError('unexpected_source:' + source_id)
    _directory(ACCESS_AREA)
    policy = {'schema': POLICY_SCHEMA, 'inventory_root': str(CONSUMER),
              'inventory_ref': INVENTORY_REF,
              'inventory_sha256': hashlib.sha256(inventory_raw).hexdigest(),
              'mongo_uri': MONGO_URI, 'database': DATABASE,
              'socket_path': str(ACCESS_AREA / 'access.sock'), 'sources': sources}
    path = ACCESS_AREA / 'policy.json'
    digest = _write_new(path, policy)
    load_access_policy(str(path))
    return {'policy_path': str(path), 'policy_file_sha256': digest,
            'source_count': len(sources), 'socket_path': policy['socket_path']}


if __name__ == '__main__':
    print(json.dumps(prepare(), sort_keys=True))
