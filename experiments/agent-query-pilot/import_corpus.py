"""Admite fixtures sintéticos mediante la CLI real en Mongo temporal autenticado."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

from pymongo import MongoClient

from skopos.source_cli import source_command


def _call(database, uri, arguments):
    output, error = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(error):
        code = source_command(['--database', database, '--uri', uri, *arguments])
    if code != 0:
        raise RuntimeError('source_cli_failed:%d:%s' % (code, error.getvalue()[:120]))
    return json.loads(output.getvalue())


def import_corpus(corpus, lab):
    corpus, lab = Path(corpus), Path(lab)
    manifest = json.loads((corpus / 'manifest.json').read_text())
    state = json.loads((lab / 'state.json').read_text())
    credentials = json.loads((lab / 'credentials.json').read_text())
    database = state['database']
    port = state['port']
    password = quote(credentials['writer'], safe='')
    uri = ('mongodb://pilot_writer:%s@127.0.0.1:%d/?authSource=%s&directConnection=true'
           % (password, port, database))
    with MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
        hello = client.admin.command('hello')
        if (hello.get('setName') != state['set_name']
                or not hello.get('isWritablePrimary')
                or client.address != ('127.0.0.1', port)):
            raise RuntimeError('laboratory_identity_mismatch')
        if client[database]['source_revisions_v3'].estimated_document_count() != 0:
            raise RuntimeError('laboratory_not_empty')
    receipts = []
    for item in manifest['sources']:
        path = Path(item['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['source_sha256']:
            raise RuntimeError('fixture_hash_mismatch')
        arguments = ['import', str(path), '--format', item['format'],
                     '--project-id', item['project_id'], '--source-id', item['source_id'],
                     '--revision', str(item['source_revision']),
                     '--captured-at', item['captured_at']]
        if item['previous_source_sha256']:
            arguments.extend(['--expected-previous-sha256', item['previous_source_sha256']])
        receipt = _call(database, uri, arguments)
        if (receipt['status'] != 'imported'
                or receipt['source_sha256'] != item['source_sha256']
                or receipt['project_id'] != item['project_id']
                or receipt['source_id'] != item['source_id']
                or receipt['source_revision'] != item['source_revision']):
            raise RuntimeError('admission_receipt_mismatch')
        receipts.append(receipt)
        if item['hold_after_import']:
            path.rename(path.with_suffix('.held'))
    output = {'schema': 'skopos/agent-query-admission/v0',
              'manifest_sha256': hashlib.sha256((corpus / 'manifest.json').read_bytes()).hexdigest(),
              'count': len(receipts), 'receipts': receipts}
    result = corpus / 'admission.json'
    result.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return {'count': len(receipts),
            'admission_sha256': hashlib.sha256(result.read_bytes()).hexdigest()}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus_dir')
    parser.add_argument('lab_dir')
    arguments = parser.parse_args()
    print(json.dumps(import_corpus(arguments.corpus_dir, arguments.lab_dir), sort_keys=True))
