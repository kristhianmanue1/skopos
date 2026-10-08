"""Compara consultas fijas A y B sin llamar al modelo."""
import json
import os
from pathlib import Path
import subprocess
import sys


BACKEND = Path(__file__).with_name('backend.py')


def _query(request, *, condition, project, corpus, lab):
    env = {**os.environ, 'SKOPOS_PILOT_CONDITION': condition,
           'SKOPOS_PILOT_PROJECT': project,
           'SKOPOS_PILOT_CORPUS': str(corpus), 'SKOPOS_PILOT_LAB': str(lab)}
    result = subprocess.run([sys.executable, str(BACKEND)],
                            input=json.dumps(request), text=True,
                            capture_output=True, env=env, timeout=12)
    if result.returncode:
        raise RuntimeError('%s_backend_failed:%s' % (condition, result.stderr[:100]))
    return json.loads(result.stdout)


def compare(corpus, lab):
    corpus, lab = Path(corpus), Path(lab)
    tasks = json.loads((corpus / 'tasks.json').read_text())
    sources = json.loads((corpus / 'manifest.json').read_text())['sources']
    comparisons = []
    for task in tasks:
        request = {'operation': 'search', 'project_id': task['project_id'],
                   'term': task['search_term'], 'limit': 5}
        reference = _query(request, condition='A', project=task['project_id'],
                           corpus=corpus, lab=lab)
        skopos = _query(request, condition='B', project=task['project_id'],
                        corpus=corpus, lab=lab)
        if reference != skopos:
            raise RuntimeError('backend_mismatch:%s:%s' %
                               (task['task_id'], task['variant_id']))
        comparisons.append({'task_id': task['task_id'],
                            'variant_id': task['variant_id'], 'equal': True})
    for variant in ('v1', 'v2', 'v3'):
        item = next(s for s in sources if '/%s/' % variant in s['path'])
        request = {'operation': 'fetch', 'project_id': item['project_id'],
                   'source_id': item['source_id'],
                   'source_revision': item['source_revision'],
                   'source_sha256': item['source_sha256'], 'text_id': item['text_id']}
        reference = _query(request, condition='A', project=item['project_id'],
                           corpus=corpus, lab=lab)
        skopos = _query(request, condition='B', project=item['project_id'],
                        corpus=corpus, lab=lab)
        if reference != skopos:
            raise RuntimeError('fetch_backend_mismatch:' + variant)
    destination = corpus / 'backend-parity.json'
    destination.write_text(json.dumps({'schema': 'skopos/agent-query-parity/v0',
                                       'searches': comparisons, 'fetches': 3},
                                      sort_keys=True, indent=2) + '\n')
    return {'searches_equal': len(comparisons), 'fetches_equal': 3}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus_dir')
    parser.add_argument('lab_dir')
    arguments = parser.parse_args()
    print(json.dumps(compare(arguments.corpus_dir, arguments.lab_dir), sort_keys=True))
