"""Ejecuta unittest contra un Mongo temporal ya iniciado; no inicia servicios.

No es sandbox de código hostil. Redirige los clientes del proceso de pruebas y
rechaza bases ajenas a skopos_test*. El llamador debe suministrar una instancia
exclusiva; loopback y un puerto distinto de 27017 no prueban que sea desechable.
"""
import argparse
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

import pymongo

def publication_exit_code(result):
    """Verde exige ejecución efectiva, sin fallos, omisiones ni fallos esperados."""
    return int(not (result.wasSuccessful() and result.testsRun > 0
                    and not result.skipped and not result.expectedFailures))


def check_database(name):
    if name != 'admin' and not name.startswith('skopos_test'):
        raise RuntimeError('non_test_database_blocked')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mongo-uri', required=True,
                        help='Instancia temporal exclusiva: mongodb://127.0.0.1:PUERTO')
    parser.add_argument('--pattern', default='test*.py')
    args = parser.parse_args(argv)
    match = re.fullmatch(r'mongodb://127\.0\.0\.1:(\d{1,5})', args.mongo_uri)
    if not match or not 1024 <= int(match[1]) <= 65535 or int(match[1]) == 27017:
        parser.error('Se exige loopback con puerto de laboratorio distinto de 27017.')
    with pymongo.MongoClient(args.mongo_uri, serverSelectionTimeoutMS=2000) as client:
        hello = client.admin.command('hello')
        if not hello.get('setName') or not hello.get('isWritablePrimary'):
            parser.error('Se exige replica set temporal con primario disponible.')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'src'))
    # El fixture de integración usa Ollama local, nunca proveedor remoto heredado.
    for name in ('SKOPOS_LLM_API', 'SKOPOS_LLM_BASE_URL',
                 'SKOPOS_LLM_MODELO', 'SKOPOS_LLM_API_KEY'):
        os.environ.pop(name, None)
    original_init = pymongo.MongoClient.__init__
    original_getitem = pymongo.MongoClient.__getitem__
    original_get_database = pymongo.MongoClient.get_database

    def isolated_init(self, host=None, *positional, **kwargs):
        if host not in (None, 'mongodb://localhost:27017'):
            raise RuntimeError('unexpected_mongo_host')
        return original_init(self, args.mongo_uri, *positional, **kwargs)

    def isolated_getitem(self, name):
        check_database(name)
        return original_getitem(self, name)

    def isolated_get_database(self, name=None, *positional, **kwargs):
        check_database(name or '')
        return original_get_database(self, name, *positional, **kwargs)

    with patch.object(pymongo.MongoClient, '__init__', isolated_init), \
            patch.object(pymongo.MongoClient, '__getitem__', isolated_getitem), \
            patch.object(pymongo.MongoClient, 'get_database', isolated_get_database):
        suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern=args.pattern)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    code = publication_exit_code(result)
    if code:
        print('Gate no satisfecho: revisar fallos, omisiones o suite vacía.', file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
