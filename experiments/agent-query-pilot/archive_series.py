"""Empaqueta evidencia sintética sin credenciales del laboratorio."""
import hashlib
import json
from pathlib import Path
import stat
import sys
import tarfile


def _files(root):
    return sorted(path for path in root.rglob('*') if path.is_file())


def archive(corpus, series, lab, output, include_message_snapshots=False):
    if output.exists():
        raise ValueError('archive_exists')
    credentials = json.loads((lab / 'credentials.json').read_text())
    secret_bytes = [value.encode() for value in credentials.values()]
    corpus_files = _files(corpus)
    series_files = _files(series)
    snapshots = [path for path in series_files
                 if 'messages' in path.relative_to(series).parts]
    if snapshots and not include_message_snapshots:
        raise ValueError('message_snapshots_require_explicit_archive_flag')
    if snapshots:
        freeze = json.loads((series / 'freeze-final.json').read_text())
        if (freeze.get('schema') != 'skopos/agent-query-freeze/v1'
                or freeze.get('message_capture') != 'synthetic_bounded_v1'):
            raise ValueError('message_snapshot_profile_mismatch')
        for path in snapshots:
            details = path.lstat()
            if (path.is_symlink() or not stat.S_ISREG(details.st_mode)
                    or details.st_size > 512 * 1024
                    or stat.S_IMODE(details.st_mode) != 0o600):
                raise ValueError('message_snapshot_invalid:' + str(path))
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
            'message_snapshots': len(snapshots),
            'bytes': output.stat().st_size}


def main():
    if len(sys.argv) not in (5, 6) or (len(sys.argv) == 6 and
                                  sys.argv[5] != '--include-synthetic-message-snapshots'):
        raise SystemExit('usage: archive_series.py CORPUS SERIES LAB OUTPUT_TAR_GZ '
                         '[--include-synthetic-message-snapshots]')
    print(json.dumps(archive(*(Path(value) for value in sys.argv[1:5]),
                             include_message_snapshots=len(sys.argv) == 6), sort_keys=True))


if __name__ == '__main__':
    main()
