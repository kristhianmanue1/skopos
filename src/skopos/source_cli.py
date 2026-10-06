"""Entrada manual y explícita de fuentes diversas; sin watcher ni LLM."""
import argparse
import json
import sys

import pymongo
from pymongo.errors import PyMongoError

from skopos.source_store import SourceStore


def source_command(argv=None):
    parser = argparse.ArgumentParser(
        prog='skopos source', description='Fuentes externas verificadas (ADR-020).')
    parser.add_argument('--database', required=True, help='Base explícita; sin migración v2.')
    parser.add_argument('--uri', default='mongodb://localhost:27017',
                        help='Mongo local; import requiere replica set.')
    commands = parser.add_subparsers(dest='operation', required=True)
    admission = commands.add_parser('import', help='Importa un archivo diarizado explícito.')
    admission.add_argument('path')
    admission.add_argument('--format', choices=('diarized-text', 'whisperx-json'),
                           default='diarized-text', help='Formato explícito; no autodetecta.')
    admission.add_argument('--captured-at', required=True)
    admission.add_argument('--expected-previous-sha256')
    admission.add_argument('--completeness', choices=('unknown', 'partial', 'complete'),
                           default='unknown')
    admission.add_argument('--completeness-basis')
    search = commands.add_parser('search', help='Busca subcadena en cabezas verificadas.')
    search.add_argument('term')
    search.add_argument('--limit', type=int, default=20)
    fetch = commands.add_parser('fetch', help='Recupera segmento con revisión y hash fijos.')
    fetch.add_argument('--segment-id', required=True)
    receipt = commands.add_parser('receipt', help='Reconcilia una admisión sin releer la fuente.')
    for command in (admission, search, fetch, receipt):
        command.add_argument('--project-id', required=True)
    for command in (admission, fetch, receipt):
        command.add_argument('--source-id', required=True)
        command.add_argument('--revision', type=int, required=True)
    for command in (fetch, receipt):
        command.add_argument('--source-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        with pymongo.MongoClient(args.uri, serverSelectionTimeoutMS=2000) as client:
            store = SourceStore(client[args.database])
            if args.operation == 'search':
                result = store.search(project_id=args.project_id, term=args.term, limit=args.limit)
            else:
                identity = dict(project_id=args.project_id, source_id=args.source_id,
                                source_revision=args.revision)
                if args.operation == 'import':
                    result = store.import_file(
                        args.path, **identity, captured_at=args.captured_at,
                        expected_previous_sha256=args.expected_previous_sha256,
                        capture_completeness=args.completeness,
                        completeness_basis=args.completeness_basis,
                        source_format=args.format)
                elif args.operation == 'fetch':
                    result = store.fetch(**identity, source_sha256=args.source_sha256,
                                         segment_id=args.segment_id)
                else:
                    result = store.receipt(**identity, source_sha256=args.source_sha256)
    except (ValueError, OSError) as error:
        print('No se completó la operación: ' + str(error), file=sys.stderr)
        return 1
    except PyMongoError:
        # No imprimir URI ni detalles del driver que pudieran contener credenciales.
        print('Error de Mongo; si la admisión fue incierta, consultar receipt.',
              file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    return 0
