"""Huella lógica de colecciones del laboratorio; no imprime documentos ni secretos."""
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import quote

from bson import json_util
from pymongo import MongoClient


def snapshot(lab):
    state = json.loads((lab / 'state.json').read_text())
    credentials = json.loads((lab / 'credentials.json').read_text())
    uri = ('mongodb://pilot_reader:%s@127.0.0.1:%d/?authSource=%s&directConnection=true'
           % (quote(credentials['reader'], safe=''), state['port'], state['database']))
    result = {}
    with MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
        database = client[state['database']]
        for name in sorted(database.list_collection_names()):
            digest = hashlib.sha256()
            count = 0
            for document in database[name].find().sort('_id', 1):
                digest.update(json_util.dumps(document, sort_keys=True).encode())
                digest.update(b'\n')
                count += 1
            result[name] = {'count': count, 'sha256': digest.hexdigest()}
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: db_snapshot.py LAB_DIR')
    print(json.dumps(snapshot(Path(sys.argv[1])), sort_keys=True))


if __name__ == '__main__':
    main()
