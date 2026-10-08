"""Congela entradas y orden balanceado de la serie comparativa."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


HERE = Path(__file__).resolve().parent
SEED = 20261007
PERMUTATIONS = ('ABC', 'ACB', 'BAC', 'BCA', 'CAB', 'CBA')
CODE = ('adapter.py', 'backend.py', 'run_one.py', 'run_series.py', 'verify_delivery.py',
        'opencode/evidence.js', 'opencode/trace.js', 'opencode/config.json',
        'schema.json', 'rubric.json', 'freeze.py')


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(corpus, output):
    if output.exists():
        raise ValueError('freeze_exists')
    manifest = json.loads((corpus / 'manifest.json').read_text())
    tasks = json.loads((corpus / 'tasks.json').read_text())
    assert len(tasks) == 36 and len(manifest['sources']) == 66
    source_files = []
    for item in manifest['sources']:
        path = Path(item['path'])
        if path.exists():
            assert _sha(path) == item['source_sha256'], path
            source_files.append({'path': str(path), 'sha256': _sha(path), 'status': 'present'})
        elif item['hold_after_import']:
            held = path.with_suffix('.held')
            assert held.exists() and _sha(held) == item['source_sha256'], held
            source_files.append({'path': str(path), 'sha256': item['source_sha256'],
                                 'status': 'unavailable_after_import'})
        else:
            raise ValueError('unexpected_missing_source:' + str(path))
    blocks = [(item['task_id'], item['variant_id']) for item in tasks]
    assert len(set(blocks)) == 36
    rng = random.Random(SEED)
    rng.shuffle(blocks)
    permutations = list(PERMUTATIONS) * 6
    rng.shuffle(permutations)
    slots = []
    for block, order in zip(blocks, permutations):
        for position, condition in enumerate(order, 1):
            slots.append({'slot': len(slots) + 1, 'task_id': block[0],
                          'variant_id': block[1], 'condition': condition,
                          'position': position, 'block_order': order})
    assert len(slots) == 108
    result = {'schema': 'skopos/agent-query-freeze/v0',
              'frozen_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
              'seed': SEED, 'model_requested': 'zai-coding-plan/glm-5.3-flash',
              'client_version': '1.18.35',
              'limits': {'agent_deadline_seconds': 120, 'operation_deadline_seconds': 10,
                         'searches': 3, 'fetches': 3, 'results_per_search': 5,
                         'cumulative_context_bytes': 131072, 'model_calls': 8},
              'code_hashes': {name: _sha(HERE / name) for name in CODE},
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                                       cwd=HERE.parents[1], text=True).strip(),
              'product_code_hashes': {name: _sha(HERE.parents[1] / 'src/skopos' / name)
                                      for name in ('source_cli.py', 'runtime_store.py',
                                                   'runtime_views.py', 'runtime_reader.py')},
              'plan_sha256': _sha(HERE.parents[1] / 'docs/planes/activos/piloto-consulta-agente-2026-10-07.md'),
              'corpus_hashes': {name: _sha(corpus / name) for name in
                                ('manifest.json', 'tasks.json', 'oracle.json')},
              'source_files': source_files, 'slots': slots}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: freeze.py CORPUS_DIR OUTPUT_JSON')
    result = freeze(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({'slots': len(result['slots']), 'seed': SEED,
                      'sha256': _sha(Path(sys.argv[2]))}))


if __name__ == '__main__':
    main()
