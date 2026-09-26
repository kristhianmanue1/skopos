"""Paquete experimental verificado, independiente del consumidor Ágora."""
import hashlib


def export_packet(store, terms):
    if not terms:
        raise ValueError('missing_terms')
    selected = {}
    for term in terms:
        for hit in store.search(term):
            key = (hit['source_id'], hit['revision'], hit['locator']['id'])
            selected[key] = hit
    if not selected:
        raise ValueError('no_evidence')
    identities = {(h['source_id'], h['revision'], h['sha256']) for h in selected.values()}
    if len(identities) != 1:
        raise ValueError('single_revision_required')
    spans = []; content = b''
    for hit in sorted(selected.values(), key=lambda h: (h['locator']['start_ms'], h['locator']['id'])):
        record = store.fetch(hit['source_id'], hit['revision'], hit['locator']['id'])
        if record['status'] != 'verified' or record['sha256'] != hit['sha256']:
            raise ValueError('source_not_verified')
        segment = record['segment']
        if segment['text'] != hit['text'] or any(segment[k] != v for k,v in hit['locator'].items()):
            raise ValueError('index_source_mismatch')
        text = segment['text'].encode('utf-8')
        start = len(content); content += text
        spans.append({'start_byte':start, 'end_byte':len(content),
                      'text':segment['text'], 'locator':hit['locator']})
        content += b'\n\n'
    source_id, revision, checksum = next(iter(identities))
    return {'schema':'skopos/meeting-evidence-packet/v0', 'source_id':source_id,
            'revision':revision, 'source_sha256':checksum,
            'capture_complete_declared':all(h['complete'] for h in selected.values()),
            'selection_complete':'not_established', 'text':content.decode('utf-8'),
            'content_sha256':hashlib.sha256(content).hexdigest(), 'spans':spans}
