"""Mutaciones controladas para falsar acuses de incorporación."""
import json
from pathlib import Path
import shutil
import sys
import tempfile

from verify_delivery import verify


def _mutate(path, operation):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    operation(rows)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


def run(positive, omitted):
    assert verify(positive)['status'] == 'pass'
    negative = verify(omitted)
    assert negative['status'] == 'fail'
    assert any(item.startswith('not_incorporated:') for item in negative['errors'])
    observed = {'positive': 'pass', 'omitted': 'rejected'}
    with tempfile.TemporaryDirectory(prefix='skopos-pilot-ack-') as temp:
        root = Path(temp)
        for name, operation, expected in (
            ('changed_hash', lambda rows: rows[0].update(context_sha256='0' * 64),
             'context_digest_mismatch'),
            ('foreign_session', lambda rows: rows[0].update(session_id='foreign'),
             'foreign_session'),
            ('duplicate', lambda rows: rows.append(dict(rows[0])),
             'duplicate_delivery')):
            target = root / name
            target.mkdir()
            for filename in ('events.jsonl', 'deliveries.jsonl', 'call-trace.jsonl'):
                shutil.copyfile(positive / filename, target / filename)
            _mutate(target / 'deliveries.jsonl', operation)
            result = verify(target)
            assert result['status'] == 'fail' and expected in result['errors'], result
            observed[name] = 'rejected'
        target = root / 'stale_ack'
        target.mkdir()
        for filename in ('events.jsonl', 'deliveries.jsonl', 'call-trace.jsonl'):
            shutil.copyfile(positive / filename, target / filename)
        (target / 'deliveries.jsonl').write_text('')
        result = verify(target)
        assert result['status'] == 'fail' and 'stale_ack' in result['errors'], result
        observed['stale_ack'] = 'rejected'
    return observed


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: verify_controls.py POSITIVE_RUN OMITTED_RUN')
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == '__main__':
    main()
