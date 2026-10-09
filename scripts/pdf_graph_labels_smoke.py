"""Prueba bilateral local de rótulos candidatos v0.4 bajo demanda."""

import json
from pathlib import Path
import secrets
import socket

from pdf_graph_review_smoke import canonical, require, sha, write_new
from skopos.pdf_graph_labels_host import CONTRACT_ID, CONTRACT_VERSION, SCHEMA


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'runs/pdf-document-imss-pilot-v1'


def exchange(config, requests_root, source, operation, **fields):
    request_id = 'sk-labels-' + secrets.token_hex(12)
    request = {'contract_id': CONTRACT_ID, 'contract_version': CONTRACT_VERSION,
               'request_id': request_id, 'project_id': 'expertogobernanza',
               'source': source, 'operation': operation,
               'labels_config_sha256': sha(canonical(config)), **fields}
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
            response = json.loads(connection.makefile('rb').readline(65537))
        require(response['schema'] == SCHEMA and
                response['contract_id'] == CONTRACT_ID and
                response['contract_version'] == CONTRACT_VERSION and
                response['request_id'] == request_id and
                response['request_sha256'] == sha(raw), 'response_correlation')
        return response

    return call, envelope


def checked(call):
    response = call()
    require(response['status'] == 'ok', 'host_failed:' + str(response['error']))
    return response['result']


def main():
    config = json.loads((PILOT / 'graph-labels-host.json').read_text())
    manifest_path = ROOT / 'docs/evidencia/pdf-imss-graph-labels-v0.4-experimental.json'
    require(sha(manifest_path.read_bytes()) == config['manifest_sha256'],
            'manifest_digest')
    manifest = json.loads(manifest_path.read_bytes())
    source = manifest['source']
    policy = json.loads((PILOT / 'policy.json').read_text())
    requests_root = Path(policy['requests_root'])
    offer = checked(exchange(config, requests_root, source,
                             'describe_graph_labels')[0])
    require(offer['derivation_id'] == manifest['derivation_id'] and
            offer['manifest_sha256'] == config['manifest_sha256'] and
            offer['fidelity_status'] == 'unreviewed_partial', 'offer_identity')
    counts = []
    for page in manifest['pages']:
        result = checked(exchange(config, requests_root, source,
                         'get_graph_labels_page', derivation_id=manifest['derivation_id'],
                         manifest_sha256=config['manifest_sha256'],
                         page_number=page['page_number'])[0])
        require(result['page'] == page and result['source'] == source,
                'page_recovery')
        counts.append((page['page_number'], len(page['labels'])))
    recovered = []
    for number, node_id, label in (
            (18, 'n3', 'UNIDAD DE ATENCIÓN MÉDICA'),
            (21, 'n5', 'COORDINACIÓN DE INFORMACIÓN E INTELIGENCIA EN SALUD'),
            (22, 'n10', 'COORDINACIÓN TÉCNICA DE INFRAESTRUCTURA MÉDICA')):
        page = next(p for p in manifest['pages'] if p['page_number'] == number)
        item = next(x for x in page['labels'] if x['node_id'] == node_id)
        result = checked(exchange(config, requests_root, source,
                         'fetch_graph_label_item', derivation_id=manifest['derivation_id'],
                         manifest_sha256=config['manifest_sha256'],
                         item_id=item['item_id'])[0])
        require(result['item'] == item and result['page_number'] == number and
                item['label_candidate'] == label and
                item['status'] == 'candidate_unadjudicated', 'item_recovery')
        recovered.append(item['item_id'])
    defaults = {'derivation_id': manifest['derivation_id'],
                'manifest_sha256': config['manifest_sha256'], 'page_number': 22}
    negatives = {}
    for name, supplied_source, fields, expected in (
            ('wrong_source', dict(source, source_sha256='0' * 64), defaults,
             'source_mismatch'),
            ('wrong_manifest', source, dict(defaults, manifest_sha256='0' * 64),
             'labels_identity_mismatch'),
            ('page_23', source, dict(defaults, page_number=23), 'page_out_of_scope')):
        response = exchange(config, requests_root, supplied_source,
                            'get_graph_labels_page', **fields)[0]()
        require(response['result'] is None and response['error']['code'] == expected,
                'negative_control:' + name)
        negatives[name] = expected
    item = manifest['pages'][-1]['labels'][0]
    replay, envelope = exchange(config, requests_root, source,
                                'fetch_graph_label_item',
                                derivation_id=manifest['derivation_id'],
                                manifest_sha256=config['manifest_sha256'],
                                item_id=item['item_id'])
    require(replay() == replay(), 'replay_mismatch')
    response = exchange(config, requests_root, source, 'fetch_graph_label_item',
                        derivation_id=manifest['derivation_id'],
                        manifest_sha256=config['manifest_sha256'],
                        item_id='0' * 64)[0]()
    require(response['result'] is None and
            response['error']['code'] == 'evidence_unavailable', 'unknown_item')
    negatives['unknown_item'] = 'evidence_unavailable'
    bad_ref = secrets.token_hex(12) + '.envelope.json'
    bad_envelope = dict(envelope, request_sha256='0' * 64)
    write_new(requests_root / bad_ref, canonical(bad_envelope))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(config['socket_path'])
        connection.sendall(canonical({'envelope_ref': bad_ref}) + b'\n')
        bad_response = json.loads(connection.makefile('rb').readline(65537))
    require(bad_response['result'] is None and
            bad_response['error']['code'] == 'request_hash_mismatch',
            'request_hash_control')
    negatives['request_hash'] = 'request_hash_mismatch'
    print(json.dumps({'status': 'graph_labels_smoke_passed',
                      'derivation_id': manifest['derivation_id'],
                      'manifest_sha256': config['manifest_sha256'],
                      'pages': counts, 'recovered_item_ids': recovered,
                      'negative_controls': negatives,
                      'replay_request_sha256': envelope['request_sha256'],
                      'fidelity_status': 'unreviewed_partial'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
