"""Intercambio local de custodia PDF; la política procede del host."""

import argparse
import json

import pymongo
from pymongo.errors import PyMongoError

from skopos.pdf_custody import (PROFILE, SCHEMA,
                               MAX_REQUEST_BYTES, CustodyError, PdfCustodyStore,
                               _load_json, _read_under, load_policy, read_request)


def _response(request, status, result=None, error=None):
    return {'schema': SCHEMA, 'contract_id': request.get('contract_id'),
            'contract_version': request.get('contract_version'),
            'request_id': request.get('request_id'),
            'request_sha256': request.get('_request_sha256'), 'status': status,
            'error': error, 'producer_version': 'skopos/pdf-custody/v0.1',
            'adapter_version': PROFILE, 'result': result}


def custody_command(argv=None):
    parser = argparse.ArgumentParser(prog='skopos custody',
                                     description='Custodia local de PDF bajo política del host.')
    parser.add_argument('--policy', required=True, help='JSON absoluto preconfigurado por el host.')
    parser.add_argument('--database', required=True)
    parser.add_argument('--uri', default='mongodb://localhost:27017')
    parser.add_argument('--envelope-ref', required=True,
                        help='Sobre JSON bajo requests_root de la política.')
    args = parser.parse_args(argv)
    request = {}
    try:
        policy = load_policy(args.policy)
        envelope = _load_json(_read_under(policy['requests_root'], args.envelope_ref,
                                           MAX_REQUEST_BYTES), MAX_REQUEST_BYTES)
        request = read_request(policy, envelope)
        request['_request_sha256'] = envelope['request_sha256']
        operation = request.get('operation')
        if operation == 'describe_capabilities':
            if request.get('project_id') != policy['project_id']:
                raise CustodyError('policy_mismatch')
            result = {'policy': {'id': policy['policy_id'],
                                 'version': policy['policy_version'],
                                 'custody_modes': ['verified_external_reference'],
                                 'scope': ['single_object'],
                                 'seal_policy': policy['seal_policy'],
                                 'retention_basis': policy['retention_basis']},
                      'operations': ['admit_original', 'fetch_original', 'receipt'],
                      'format_validation': 'pdf_header_only'}
        elif operation in ('admit_original', 'fetch_original', 'receipt'):
            with pymongo.MongoClient(args.uri, serverSelectionTimeoutMS=2000) as client:
                store = PdfCustodyStore(client[args.database], policy)
                if operation == 'admit_original':
                    result = store.admit(request)
                elif operation == 'fetch_original':
                    result = store.fetch(request)
                else:
                    result = store.receipt(request)
        else:
            raise CustodyError('unsupported_operation')
        print(json.dumps(_response(request, 'ok', result=result), ensure_ascii=False))
        return 0
    except CustodyError as error:
        status = 'execution_failed' if error.stage in ('admission', 'retrieval', 'delivery') else 'invalid_input'
        print(json.dumps(_response(request, status,
                                   error={'code': error.code, 'stage': error.stage}),
                         ensure_ascii=False))
        return 1
    except (PyMongoError, OSError):
        print(json.dumps(_response(request, 'execution_failed',
                                   error={'code': 'store_unavailable', 'stage': 'execution'}),
                         ensure_ascii=False))
        return 1
