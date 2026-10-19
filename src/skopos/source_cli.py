"""Entrada manual y explícita de fuentes diversas; sin watcher ni LLM."""
import argparse
import json
import sys

import pymongo
from pymongo.errors import PyMongoError

from skopos.consumer_access import ConsumerAccessStore, load_consumer_policy
from skopos.source_store import SourceStore
from skopos.runtime_store import RuntimeSourceStore


def source_command(argv=None):
    parser = argparse.ArgumentParser(
        prog='skopos source', description='Fuentes externas verificadas (ADR-020).')
    parser.add_argument('--database', help='Base explícita; sin migración v2.')
    parser.add_argument('--uri', default=None,
                        help='Mongo local; import requiere replica set.')
    parser.add_argument('--policy',
                        help='Política de consumidor (source-consumer-access/v0.1): '
                             'sólo lectura; punto y base salen de la política.')
    commands = parser.add_subparsers(dest='operation', required=True)
    admission = commands.add_parser('import', help='Importa una fuente de formato explícito.')
    admission.add_argument('path')
    admission.add_argument('--format', choices=('diarized-text', 'whisperx-json', 'dsh-session-v0-jsonl'),
                           default='diarized-text', help='Formato explícito; no autodetecta.')
    admission.add_argument('--captured-at', required=True)
    admission.add_argument('--expected-previous-sha256')
    admission.add_argument('--completeness', choices=('unknown', 'partial', 'complete'),
                           default='unknown')
    admission.add_argument('--completeness-basis')
    search = commands.add_parser('search', help='Busca subcadena en cabezas verificadas.')
    search.add_argument('term')
    search.add_argument('--limit', type=int, default=20)
    search.add_argument('--kind', choices=('meeting-transcript', 'runtime-events'), default='meeting-transcript')
    fetch = commands.add_parser('fetch', help='Recupera segmento con revisión y hash fijos.')
    fetch.add_argument('--segment-id', required=True)
    receipt = commands.add_parser('receipt', help='Reconcilia una admisión sin releer la fuente.')
    receipt.add_argument('--kind', choices=('meeting-transcript', 'runtime-events'), default='meeting-transcript')
    runtime_fetch = commands.add_parser('fetch-runtime', help='Recupera una vista runtime explícita y verificada.')
    runtime_fetch.add_argument('--view', required=True, choices=('text_projection', 'original_jsonl', 'derived_event'))
    selector = runtime_fetch.add_mutually_exclusive_group(required=True)
    for flag in ('text-id', 'row-id', 'event-id'):
        selector.add_argument('--' + flag)
    for command in (admission, search, fetch, receipt, runtime_fetch):
        command.add_argument('--project-id', required=True)
    for command in (admission, fetch, receipt, runtime_fetch):
        command.add_argument('--source-id', required=True)
        command.add_argument('--revision', type=int, required=True)
    for command in (fetch, receipt, runtime_fetch):
        command.add_argument('--source-sha256', required=True)
    args = parser.parse_args(argv)
    runtime = (getattr(args, 'format', None) == 'dsh-session-v0-jsonl'
               or getattr(args, 'kind', None) == 'runtime-events'
               or args.operation == 'fetch-runtime')
    if args.operation == 'fetch-runtime':
        selected = {'text_projection': args.text_id, 'original_jsonl': args.row_id, 'derived_event': args.event_id}
        if selected[args.view] is None:
            parser.error('El selector no corresponde a --view.')
    if (args.database is None) == (args.policy is None):
        parser.error('Elegir una vía: --database (Operador) o --policy (consumidor).')
    if args.policy is not None and args.uri is not None:
        parser.error('--policy ya fija la conexión; no combinar con --uri.')
    try:
        policy = digest = None
        if args.policy:
            if args.operation == 'import':
                # La admisión es autoridad del Operador, no acceso de consumidor.
                raise ValueError('operation_not_allowed')
            policy, digest = load_consumer_policy(args.policy)
        uri = policy['mongo_uri'] if policy else (args.uri or 'mongodb://localhost:27017')
        with pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
            database = client[args.database or policy['database']]
            base_store = (RuntimeSourceStore if runtime else SourceStore)(database)
            store = ConsumerAccessStore(base_store, policy, digest) if policy else base_store
            if args.operation == 'search':
                result = (store.search_runtime if runtime else store.search)(project_id=args.project_id, term=args.term, limit=args.limit)
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
                elif args.operation == 'fetch-runtime':
                    result = store.fetch_runtime(**identity, source_sha256=args.source_sha256,
                                                 view=args.view, text_id=args.text_id,
                                                 row_id=args.row_id, event_id=args.event_id)
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
