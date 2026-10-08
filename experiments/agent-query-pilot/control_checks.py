"""Controles reproducibles del adaptador sobre un MongoDB de laboratorio."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import backend


HERE = Path(__file__).resolve().parent


def _invoke(run_dir, request):
    return subprocess.run([sys.executable, str(HERE / 'adapter.py'), str(run_dir)],
                          input=json.dumps(request), text=True, capture_output=True,
                          timeout=30)


def _config(run_dir, condition, corpus, lab):
    (run_dir / 'config.json').write_text(json.dumps({
        'run_id': 'technical-control', 'task_id': 'Q01', 'variant_id': 'v1',
        'condition': condition, 'project_id': 'pilot-cedro',
        'corpus_dir': str(corpus), 'lab_dir': str(lab)}))


def run(corpus, lab):
    manifest = json.loads((corpus / 'manifest.json').read_text())
    source = next(item for item in manifest['sources']
                  if item['project_id'] == 'pilot-cedro' and item['source_id'] == 's001')
    fetch = {'operation': 'fetch', 'source_id': source['source_id'],
             'source_revision': source['source_revision'],
             'source_sha256': source['source_sha256'], 'text_id': source['text_id']}
    search = {'operation': 'search', 'term': 'umbral-cedro'}
    observed = {}
    with tempfile.TemporaryDirectory(prefix='skopos-pilot-controls-') as temp:
        root = Path(temp)
        for condition in ('A', 'B'):
            directory = root / condition
            directory.mkdir()
            _config(directory, condition, corpus, lab)
            first = _invoke(directory, search)
            assert first.returncode == 0, first.stderr
            result = json.loads(first.stdout)
            assert result['result_status'] == 'produced'
            assert result['result']['results'][0]['source_id'] == 's001'
            assert hashlib.sha256((directory / result['raw_stdout']).read_bytes()).hexdigest() == result['response_sha256']
            good_fetch = _invoke(directory, fetch)
            assert good_fetch.returncode == 0, good_fetch.stderr
            assert json.loads(good_fetch.stdout)['result']['projection']['text'].endswith('Azul-17.')
            altered = {**fetch, 'source_sha256': '0' * 64}
            bad_fetch = _invoke(directory, altered)
            assert bad_fetch.returncode == 0
            assert json.loads(bad_fetch.stdout)['result_status'] == 'failed'
            observed[condition] = {'search': 'produced', 'fetch': 'produced',
                                   'altered_hash': 'failed'}
        directory = root / 'budget'
        directory.mkdir()
        _config(directory, 'B', corpus, lab)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_invoke, directory, search) for _ in range(2)]
            concurrent = [future.result() for future in futures]
        assert all(item.returncode == 0 for item in concurrent)
        ids = [json.loads(item.stdout)['request_id'] for item in concurrent]
        assert len(set(ids)) == 2
        assert json.loads((directory / 'budget.json').read_text())['searches'] == 2
        assert _invoke(directory, search).returncode == 0
        fourth = _invoke(directory, search)
        assert fourth.returncode == 1 and 'operation_budget_exceeded' in fourth.stderr
        observed['concurrency_and_budget'] = 'pass'
        directory = root / 'invalid'
        directory.mkdir()
        _config(directory, 'B', corpus, lab)
        for invalid in ({'operation': 'import', 'term': 'x'},
                        {'operation': 'search', 'term': ''},
                        {'operation': 'search', 'term': 'x', 'project_id': 'pilot-olmo'}):
            assert _invoke(directory, invalid).returncode == 1
        observed['allowlist'] = 'pass'
        os.environ['SKOPOS_PILOT_LAB'] = str(lab)
        os.environ['SKOPOS_PILOT_CORPUS'] = str(corpus)
        limits = {}
        for limit in (0, 1, 5, 20):
            request = {'operation': 'search', 'project_id': 'pilot-cedro',
                       'term': 'límite-cedro', 'limit': limit}
            result = backend._skopos(request)
            limits[str(limit)] = len(result['results'])
        assert limits == {'0': 0, '1': 1, '5': 5, '20': 6}, limits
        try:
            backend._skopos({'operation': 'search', 'project_id': 'pilot-cedro',
                             'term': 'límite-cedro', 'limit': 21})
        except ValueError:
            limits['21'] = 'rejected'
        else:
            raise AssertionError('limit_21_accepted')
        observed['backend_limits'] = limits
        unicode_request = {'operation': 'search', 'project_id': 'pilot-cedro',
                           'term': 'ÁMBITO-CEDRO', 'limit': 5}
        upper = backend._skopos(unicode_request)
        lower = backend._skopos({**unicode_request, 'term': 'ámbito-cedro'})
        assert upper['results'] == lower['results'] and len(lower['results']) == 1
        observed['unicode_casefold'] = 'pass'
    return observed


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: control_checks.py CORPUS_DIR LAB_DIR')
    result = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
