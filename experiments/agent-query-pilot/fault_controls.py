"""Sondas del capturador con procesos sintéticos que fallan de forma controlada."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adapter  # noqa: E402


def run():
    observed = {}
    with tempfile.TemporaryDirectory(prefix='skopos-pilot-faults-') as temp:
        root = Path(temp)
        for name, body, expected in (
            ('invalid_json', 'print("{")\n', 'invalid_json'),
            ('process_abort', 'raise SystemExit(7)\n', 'failed'),
            ('too_large', 'print("x" * 2048)\n', 'response_too_large'),
            ('timeout', 'import time\ntime.sleep(2)\n', 'timed_out')):
            directory = root / name
            directory.mkdir()
            (directory / 'config.json').write_text(json.dumps({
                'run_id': 'fault-' + name, 'task_id': 'Q01', 'variant_id': 'v1',
                'condition': 'B', 'project_id': 'pilot-cedro',
                'corpus_dir': str(root), 'lab_dir': str(root)}))
            backend = directory / 'backend.py'
            backend.write_text(body)
            adapter.BACKEND = backend
            adapter.MAX_STDOUT = 1024
            adapter.DEADLINE = .2 if name == 'timeout' else 3
            result = json.loads(adapter.invoke(directory, {'operation': 'search', 'term': 'x'}))
            assert result['result_status'] == expected, (name, result['result_status'])
            observed[name] = expected
    return observed


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
