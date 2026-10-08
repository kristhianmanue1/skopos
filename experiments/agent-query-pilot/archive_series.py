"""Empaqueta evidencia sintética sin credenciales del laboratorio."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile


def _files(root):
    return sorted(path for path in root.rglob('*') if path.is_file())


def archive(corpus, series, lab, output):
    if output.exists():
        raise ValueError('archive_exists')
    credentials = json.loads((lab / 'credentials.json').read_text())
    secret_bytes = [value.encode() for value in credentials.values()]
    corpus_files = _files(corpus)
    series_files = _files(series)
    for path in corpus_files + series_files:
        raw = path.read_bytes()
        if any(secret in raw for secret in secret_bytes):
            raise ValueError('credential_in_artifact:' + str(path))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz') as bundle:
        for path in corpus_files:
            bundle.add(path, arcname='corpus/' + str(path.relative_to(corpus)))
        for path in series_files:
            bundle.add(path, arcname='series/' + str(path.relative_to(series)))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {'path': str(output), 'sha256': digest,
            'corpus_files': len(corpus_files), 'series_files': len(series_files),
            'bytes': output.stat().st_size}


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: archive_series.py CORPUS SERIES LAB OUTPUT_TAR_GZ')
    print(json.dumps(archive(*(Path(value) for value in sys.argv[1:])), sort_keys=True))


if __name__ == '__main__':
    main()
