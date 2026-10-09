"""Prueba bilateral bajo demanda del derivado gráfico v0.3 experimental."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import socket

from skopos.pdf_graph_review_host import CONTRACT_ID, CONTRACT_VERSION, SCHEMA


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'runs/pdf-document-imss-pilot-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def write_new(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def exchange(config, requests_root, source, operation, **fields):
    request_id = 'sk-graph-' + secrets.token_hex(12)
    request = {'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION,
               'request_id': request_id, 'project_id': 'expertogobernanza',
               'source': source, 'operation': operation,
               'graph_config_sha256': sha(canonical(config)), **fields}
    raw = canonical(request)
    nonce = secrets.token_hex(12)
    request_ref, envelope_ref = nonce + '.request.json', nonce + '.envelope.json'
    envelope = {'request_file_ref': request_ref, 'request_sha256': sha(raw),
                'request_id': request_id, 'contract_id': CONTRACT_ID,
                'contract_version': CONTRACT_VERSION}
    write_new(requests_root / request_ref, raw)
    write_new(requests_root / envelope_ref, canonical(envelope))

    def call():
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(config['socket_path'])
            connection.sendall(canonical({'envelope_ref': envelope_ref}) + b'\n')
            response_raw = connection.makefile('rb').readline(65537)
        require(0 < len(response_raw) <= 65536, 'response_length')
        response = json.loads(response_raw)
        require(response['schema'] == SCHEMA and
                response['contract_id'] == CONTRACT_ID and
                response['contract_version'] == CONTRACT_VERSION and
                response['request_id'] == request_id and
                response['request_sha256'] == sha(raw), 'response_correlation')
        return response

    return call, {'request_ref': request_ref, 'request_sha256': sha(raw),
                  'request_id': request_id}


def checked(call):
    result = call()
    require(result['status'] == 'ok', 'host_failed:' + str(result['error']))
    return result['result']


def main():
    config = json.loads((PILOT / 'graph-review-host.json').read_text())
    manifest_raw = Path(config['manifest_path']).read_bytes()
    require(sha(manifest_raw) == config['manifest_sha256'], 'manifest_digest')
    manifest = json.loads(manifest_raw)
    source = manifest['source']
    document_policy = json.loads((PILOT / 'policy.json').read_text())
    requests_root = Path(document_policy['requests_root'])
    offer = checked(exchange(config, requests_root, source,
                             'describe_graph_review')[0])
    require(offer['derivation_id'] == manifest['derivation_id'] and
            offer['manifest_sha256'] == config['manifest_sha256'] and
            offer['fidelity_status'] == 'unreviewed_partial', 'offer_identity')
    counts = []
    for page in manifest['pages']:
        number = page['page_number']
        result = checked(exchange(config, requests_root, source,
                         'get_graph_review_page',
                         derivation_id=manifest['derivation_id'],
                         manifest_sha256=config['manifest_sha256'],
                         page_number=number)[0])
        require(result['page'] == page and result['source'] == source and
                result['fidelity_status'] == 'unreviewed_partial',
                'page_recovery')
        counts.append((number, len(page['nodes']), len(page['edges'])))
    page22 = manifest['pages'][-1]
    node = next(item for item in page22['nodes'] if item['node_id'] == 'n10')
    edge = next(item for item in page22['edges']
                if item['parent_node_id'] == 'n3' and item['child_node_id'] == 'n8')
    for item, modality in ((node, 'visual_graph_node'),
                           (edge, 'visual_graph_edge')):
        result = checked(exchange(config, requests_root, source,
                         'fetch_graph_review_item',
                         derivation_id=manifest['derivation_id'],
                         manifest_sha256=config['manifest_sha256'],
                         item_id=item['item_id'])[0])
        require(result['item'] == item and result['modality'] == modality and
                result['page_number'] == 22 and result['source'] == source,
                'item_recovery')
    require(node['visual_label_candidate'] ==
            'COORDINACIÓN TÉCNICA DE INFRAESTRUCTURA MÉDICA' and
            edge['origin'] == 'nonblind_visual_review' and
            edge['status'] == 'visual_candidate_unadjudicated',
            'candidate_status')
    negatives = {}
    for name, operation, changes, expected in (
            ('wrong_source', 'fetch_graph_review_item',
             {'source': dict(source, source_sha256='0' * 64)}, 'source_mismatch'),
            ('wrong_manifest', 'get_graph_review_page',
             {'manifest_sha256': '0' * 64}, 'graph_identity_mismatch'),
            ('page_23', 'get_graph_review_page',
             {'page_number': 23}, 'page_out_of_scope'),
            ('unknown_item', 'fetch_graph_review_item',
             {'item_id': '0' * 64}, 'evidence_unavailable')):
        fields = {'derivation_id': manifest['derivation_id'],
                  'manifest_sha256': config['manifest_sha256']}
        if operation == 'get_graph_review_page':
            fields['page_number'] = 22
        else:
            fields['item_id'] = edge['item_id']
        fields.update(changes)
        supplied_source = fields.pop('source', source)
        response = exchange(config, requests_root, supplied_source,
                            operation, **fields)[0]()
        require(response['error']['code'] == expected and
                response['result'] is None, 'negative_control:' + name)
        negatives[name] = expected
    replay, receipt = exchange(config, requests_root, source,
                               'fetch_graph_review_item',
                               derivation_id=manifest['derivation_id'],
                               manifest_sha256=config['manifest_sha256'],
                               item_id=edge['item_id'])
    require(replay() == replay() and replay()['status'] == 'ok', 'replay_mismatch')
    bad_envelope_ref = secrets.token_hex(12) + '.envelope.json'
    bad_envelope = {'request_file_ref': receipt['request_ref'],
                    'request_sha256': '0' * 64,
                    'request_id': receipt['request_id'],
                    'contract_id': CONTRACT_ID,
                    'contract_version': CONTRACT_VERSION}
    write_new(requests_root / bad_envelope_ref, canonical(bad_envelope))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(config['socket_path'])
        connection.sendall(canonical({'envelope_ref': bad_envelope_ref}) + b'\n')
        bad_response = json.loads(connection.makefile('rb').readline(65537))
    require(bad_response['error']['code'] == 'request_hash_mismatch' and
            bad_response['result'] is None, 'request_hash_control')
    negatives['request_hash'] = 'request_hash_mismatch'
    print(json.dumps({'status': 'graph_review_smoke_passed',
                      'derivation_id': manifest['derivation_id'],
                      'manifest_sha256': config['manifest_sha256'],
                      'pages': counts, 'node_item_id': node['item_id'],
                      'edge_item_id': edge['item_id'],
                      'negative_controls': negatives,
                      'replay_request': receipt,
                      'fidelity_status': 'unreviewed_partial'},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
