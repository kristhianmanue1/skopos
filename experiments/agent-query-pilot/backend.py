"""Dos backends de lectura con el mismo contrato de respuesta experimental."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

from skopos.runtime_envelope import build_envelope
from skopos.runtime_views import DECLARATION, fetch_verified, search_verified
from skopos.source_cli import source_command


def _manifest():
    return json.loads((Path(os.environ['SKOPOS_PILOT_CORPUS']) / 'manifest.json').read_text())


def _source(item):
    try:
        raw = Path(item['path']).read_bytes()
    except OSError:
        raise ValueError('source_unavailable') from None
    envelope = build_envelope(raw, project_id=item['project_id'],
                              source_id=item['source_id'],
                              source_revision=item['source_revision'],
                              previous_source_sha256=item['previous_source_sha256'],
                              captured_at=item['captured_at'])
    if envelope['source_sha256'] != item['source_sha256']:
        raise ValueError('source_integrity_failed')
    return envelope, raw


def _reference_search(request):
    sources = [item for item in _manifest()['sources']
               if item['project_id'] == request['project_id']]
    heads = {}
    for item in sources:
        if (item['source_id'] not in heads
                or heads[item['source_id']]['source_revision'] < item['source_revision']):
            heads[item['source_id']] = item
    results = []
    excluded = {'result_limit': 0, 'fragment_too_large': 0}
    unavailable = {}
    for source_id in sorted(heads):
        try:
            envelope, raw = _source(heads[source_id])
            found = search_verified(envelope, raw, project_id=request['project_id'],
                                    term=request['term'], limit=request['limit'] - len(results))
        except ValueError as error:
            code = str(error)
            unavailable[code] = unavailable.get(code, 0) + 1
            continue
        results.extend(found['results'])
        for key in excluded:
            excluded[key] += found['excluded'][key]
    return {'results': results, 'excluded': excluded,
            'unavailable_sources': unavailable,
            'excluded_source_kinds': {'meeting-transcript': 0},
            'selection': 'per_source_head_observed', 'declaration': DECLARATION}


def _reference_fetch(request):
    matches = [item for item in _manifest()['sources']
               if (item['project_id'] == request['project_id']
                   and item['source_id'] == request['source_id']
                   and item['source_revision'] == request['source_revision'])]
    if len(matches) != 1:
        raise ValueError('revision_not_found')
    item = matches[0]
    if item['source_sha256'] != request['source_sha256']:
        raise ValueError('revision_conflict')
    envelope, raw = _source(item)
    return fetch_verified(envelope, raw, project_id=request['project_id'],
                          source_id=request['source_id'],
                          source_revision=request['source_revision'],
                          source_sha256=request['source_sha256'],
                          view='text_projection', text_id=request['text_id'])


def _skopos(request):
    lab = Path(os.environ['SKOPOS_PILOT_LAB'])
    state = json.loads((lab / 'state.json').read_text())
    credentials = json.loads((lab / 'credentials.json').read_text())
    uri = ('mongodb://pilot_reader:%s@127.0.0.1:%d/?authSource=%s&directConnection=true'
           % (quote(credentials['reader'], safe=''), state['port'], state['database']))
    common = ['--database', state['database'], '--uri', uri]
    if request['operation'] == 'search':
        arguments = ['search', request['term'], '--project-id', request['project_id'],
                     '--kind', 'runtime-events', '--limit', str(request['limit'])]
    else:
        arguments = ['fetch-runtime', '--project-id', request['project_id'],
                     '--source-id', request['source_id'],
                     '--revision', str(request['source_revision']),
                     '--source-sha256', request['source_sha256'],
                     '--view', 'text_projection', '--text-id', request['text_id']]
    output, error = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(error):
        code = source_command([*common, *arguments])
    if code:
        raise ValueError('skopos_cli_failed:%d' % code)
    return json.loads(output.getvalue())


def _validate(request):
    if type(request) is not dict or request.get('operation') not in ('search', 'fetch'):
        raise ValueError('operation_not_allowed')
    if request.get('project_id') != os.environ['SKOPOS_PILOT_PROJECT']:
        raise ValueError('project_mismatch')
    if request['operation'] == 'search':
        if (type(request.get('term')) is not str or not request['term'].strip()
                or len(request['term'].encode()) > 1024
                or type(request.get('limit')) is not int
                or not 0 <= request['limit'] <= 5):
            raise ValueError('invalid_search')
        if set(request) != {'operation', 'project_id', 'term', 'limit'}:
            raise ValueError('invalid_request_fields')
    else:
        if set(request) != {'operation', 'project_id', 'source_id',
                            'source_revision', 'source_sha256', 'text_id'}:
            raise ValueError('invalid_request_fields')
        if (type(request['source_id']) is not str or not request['source_id']
                or type(request['source_revision']) is not int
                or request['source_revision'] < 1
                or type(request['source_sha256']) is not str
                or len(request['source_sha256']) != 64
                or type(request['text_id']) is not str or not request['text_id']):
            raise ValueError('invalid_fetch')


def main():
    try:
        request = json.load(sys.stdin)
        _validate(request)
        condition = os.environ['SKOPOS_PILOT_CONDITION']
        if condition not in ('A', 'B', 'C'):
            raise ValueError('invalid_condition')
        result = (_reference_search(request) if request['operation'] == 'search'
                  else _reference_fetch(request)) if condition == 'A' else _skopos(request)
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(str(error).split(':', 1)[0], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
