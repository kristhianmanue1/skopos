"""Control positivo y casos límite del corpus admitido con usuario lector."""
from contextlib import redirect_stderr, redirect_stdout
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


def verify_corpus(corpus, lab):
    corpus, lab = Path(corpus), Path(lab)
    manifest = json.loads((corpus / 'manifest.json').read_text())
    tasks = json.loads((corpus / 'tasks.json').read_text())
    state = json.loads((lab / 'state.json').read_text())
    credentials = json.loads((lab / 'credentials.json').read_text())
    database, port = state['database'], state['port']
    uri = ('mongodb://pilot_reader:%s@127.0.0.1:%d/?authSource=%s&directConnection=true'
           % (quote(credentials['reader'], safe=''), port, database))
    with MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
        hello = client.admin.command('hello')
        if (hello.get('setName') != state['set_name']
                or client.address != ('127.0.0.1', port)):
            raise RuntimeError('laboratory_identity_mismatch')
        count = client[database]['source_revisions_v3'].count_documents({})
        if count != len(manifest['sources']):
            raise RuntimeError('revision_count_mismatch')
    results = []
    for task in tasks:
        found = _call(database, uri, ['search', task['search_term'],
                                      '--project-id', task['project_id'],
                                      '--kind', 'runtime-events', '--limit', '5'])
        if any(item['project_id'] != task['project_id'] for item in found['results']):
            raise RuntimeError('cross_project_result')
        results.append({'task_id': task['task_id'], 'variant_id': task['variant_id'],
                        'count': len(found['results']),
                        'excluded': found['excluded'],
                        'unavailable_sources': found['unavailable_sources']})
    for variant in ('v1', 'v2', 'v3'):
        indexed = {row['task_id']: row for row in results if row['variant_id'] == variant}
        if indexed['Q07']['count'] != 0 or indexed['Q11']['count'] != 0:
            raise RuntimeError('empty_control_failed')
        if indexed['Q10']['count'] != 5 or indexed['Q10']['excluded']['result_limit'] != 1:
            raise RuntimeError('result_limit_control_failed')
        if indexed['Q08']['count'] != 0 or indexed['Q08']['unavailable_sources'].get('source_unavailable') != 1:
            raise RuntimeError('unavailable_control_failed')
        first = next(s for s in manifest['sources'] if '/%s/' % variant in s['path'])
        args = ['fetch-runtime', '--project-id', first['project_id'],
                '--source-id', first['source_id'], '--revision', '1',
                '--source-sha256', first['source_sha256'],
                '--view', 'text_projection', '--text-id', first['text_id']]
        fetched = _call(database, uri, args)
        if (fetched['source_sha256'] != first['source_sha256']
                or fetched['status'] != 'runtime_projection_verified'):
            raise RuntimeError('fetch_control_failed')
    output = {'schema': 'skopos/agent-query-t1-check/v0',
              'revision_count': count, 'checks': results}
    destination = corpus / 't1-check.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return {'revision_count': count, 'searches': len(results),
            'fetch_controls': 3, 'status': 'passed'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus_dir')
    parser.add_argument('lab_dir')
    arguments = parser.parse_args()
    print(json.dumps(verify_corpus(arguments.corpus_dir, arguments.lab_dir), sort_keys=True))
