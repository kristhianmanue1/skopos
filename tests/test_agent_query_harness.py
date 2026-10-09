"""Controles de falsación para una serie futura del laboratorio agéntico."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PILOT = Path(__file__).resolve().parents[1] / 'experiments/agent-query-pilot'
sys.path.insert(0, str(PILOT))
import adapter  # noqa: E402
import archive_series  # noqa: E402
import run_series  # noqa: E402
from freeze import CODE  # noqa: E402
from verify_delivery import verify  # noqa: E402


def frozen_fixture():
    same = '0' * 64
    return {'schema': 'skopos/agent-query-freeze/v1',
            'code_hashes': {name: same for name in CODE},
            'product_code_hashes': {name: same for name in run_series.PRODUCT_CODE},
            'corpus_hashes': {name: same for name in
                              ('manifest.json', 'tasks.json', 'oracle.json')},
            'source_files': [{'path': '/synthetic/s%03d' % index,
                              'status': 'present', 'sha256': same}
                             for index in range(66)],
            'slots': [{'slot': index} for index in range(1, 109)],
            'model_requested': run_series.MODEL, 'client_version': '1.18.35',
            'plan_sha256': same, 'message_capture': 'synthetic_bounded_v1',
            'limits': {'message_snapshot_bytes': 524288}}


class FreezeTests(unittest.TestCase):
    def test_product_and_plan_mutations_fail_before_slot(self):
        freeze = frozen_fixture()
        with mock.patch.object(run_series, '_sha', return_value='0' * 64):
            run_series._check_frozen(freeze, Path('/synthetic'), Path('/synthetic'))
            freeze['product_code_hashes']['runtime_store.py'] = '1' * 64
            with self.assertRaisesRegex(ValueError, 'product_code_changed'):
                run_series._check_frozen(freeze, Path('/synthetic'), Path('/synthetic'))
            freeze['product_code_hashes']['runtime_store.py'] = '0' * 64
            freeze['plan_sha256'] = '1' * 64
            with self.assertRaisesRegex(ValueError, 'plan_changed'):
                run_series._check_frozen(freeze, Path('/synthetic'), Path('/synthetic'))

    def test_optimized_python_does_not_disable_guard(self):
        program = '''from pathlib import Path
import run_series
from freeze import CODE
f={'schema':'skopos/agent-query-freeze/v1',
'code_hashes':{n:'0'*64 for n in CODE},
'product_code_hashes':{n:'0'*64 for n in run_series.PRODUCT_CODE},
'corpus_hashes':{n:'0'*64 for n in ('manifest.json','tasks.json','oracle.json')},
'source_files':[{'path':'/synthetic/s%03d'%i,'status':'present','sha256':'0'*64} for i in range(66)],
'slots':[{'slot':i} for i in range(1,109)],
'model_requested':run_series.MODEL,'client_version':'1.18.35',
'plan_sha256':'1'*64,'message_capture':'synthetic_bounded_v1',
'limits':{'message_snapshot_bytes':524288}}
run_series._sha=lambda path:'0'*64
try:
 run_series._check_frozen(f,Path('/synthetic'),Path('/synthetic'))
except ValueError as error:
 if not str(error).startswith('plan_changed:'):
  raise SystemExit('wrong_failure:'+str(error))
else:
 raise SystemExit('invalid_freeze_accepted')
'''
        env = dict(os.environ, PYTHONPATH=str(PILOT))
        completed = subprocess.run([sys.executable, '-O', '-c', program],
                                   env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


class DeliveryTests(unittest.TestCase):
    def test_hook_writes_exact_bounded_snapshots(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node.js no disponible')
        hook = PILOT / 'opencode/trace.js'
        program = '''import { pathToFileURL } from "node:url";
const { Trace } = await import(pathToFileURL(process.argv[1]).href);
const hook = await Trace();
await hook["experimental.chat.messages.transform"]({}, { messages: [{content:"PILOT_PAYLOAD"}] });
await hook["experimental.chat.messages.transform"]({}, { messages: [{content:"PILOT_PAYLOAD"}] });
'''
        with tempfile.TemporaryDirectory() as temp:
            payload = 'PILOT_PAYLOAD'
            delivery = {'request_id': 'r1', 'invocation_id': 'i1',
                        'session_id': 's1', 'context_sha256': hashlib.sha256(
                            payload.encode()).hexdigest(),
                        'payload': payload, 'delivered_bytes': len(payload)}
            (Path(temp) / 'deliveries.jsonl').write_text(json.dumps(delivery) + '\n')
            events = [{'type': kind, 'sessionID': 's1'}
                      for _ in range(2) for kind in ('step_start', 'step_finish')]
            (Path(temp) / 'events.jsonl').write_text(
                ''.join(json.dumps(event) + '\n' for event in events))
            env = dict(os.environ, SKOPOS_PILOT_RUN_DIR=temp,
                       SKOPOS_PILOT_MESSAGE_CAPTURE='synthetic_bounded_v1')
            completed = subprocess.run([node, '--input-type=module', '-e',
                                        program, str(hook)], env=env,
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            calls = [json.loads(line) for line in
                     (Path(temp) / 'call-trace.jsonl').read_text().splitlines()]
            self.assertEqual(len(calls), 2)
            for index, call in enumerate(calls, 1):
                raw = (Path(temp) / 'messages' / ('call-%03d.json' % index)).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),
                                 call['messages_sha256'])
                self.assertEqual(call['messages_ref'],
                                 'messages/call-%03d.json' % index)
            self.assertEqual(verify(temp, capture_expected=True)['status'], 'pass')

    def fixture(self, directory, capture=True):
        root = Path(directory)
        payload = 'PILOT_PAYLOAD'
        raw = json.dumps([{'content': payload}], separators=(',', ':')).encode()
        (root / 'messages').mkdir()
        (root / 'messages/call-001.json').write_bytes(raw)
        delivery = {'request_id': 'r1', 'invocation_id': 'i1', 'session_id': 's1',
                    'context_sha256': hashlib.sha256(payload.encode()).hexdigest(),
                    'payload': payload, 'delivered_bytes': len(payload)}
        match = {key: delivery[key] for key in ('request_id', 'invocation_id',
                                                'context_sha256', 'session_id')}
        match.update({'representation': 'raw',
                      'effective_sha256': delivery['context_sha256'],
                      'effective_bytes': len(payload)})
        call = {'call_index': 1, 'message_count': 1,
                'matched_deliveries': [match], 'delivered_bytes': len(payload),
                'cumulative_bytes': len(payload), 'violation': None,
                'messages_sha256': hashlib.sha256(raw).hexdigest()}
        if capture:
            call.update({'messages_capture': 'synthetic_bounded_v1',
                         'messages_ref': 'messages/call-001.json'})
        for name, rows in (
                ('deliveries.jsonl', [delivery]), ('call-trace.jsonl', [call]),
                ('events.jsonl', [{'type': 'step_start', 'sessionID': 's1'},
                                  {'type': 'step_finish', 'sessionID': 's1'}])):
            (root / name).write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return root

    def test_verified_snapshot_and_mutations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(temp)
            result = verify(root, capture_expected=True)
            self.assertEqual(result['status'], 'pass')
            self.assertEqual(result['messages_sha256_checks'][0]['status'], 'verified')
            (root / 'messages/call-001.json').write_text('[{"content":"ALTERED"}]')
            result = verify(root, capture_expected=True)
            self.assertEqual(result['status'], 'fail')
            self.assertIn('messages_digest_mismatch', result['errors'])

    def test_legacy_hash_is_not_recomputed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(temp, capture=False)
            result = verify(root)
            self.assertEqual(result['status'], 'pass')
            self.assertEqual(result['messages_sha256_checks'][0]['status'],
                             'not_recomputable')
            self.assertIn('messages_snapshot_missing',
                          verify(root, capture_expected=True)['errors'])


class ClientScopeTests(unittest.TestCase):
    def test_q10_limit_is_prominent_without_global_absence_claim(self):
        result = {'selection': 'per_source_head_observed',
                  'excluded': {'result_limit': 1, 'fragment_too_large': 0},
                  'unavailable_sources': {'source_unavailable': 1}}
        scope = adapter._search_scope(result)
        self.assertEqual(scope['result_limit'], 1)
        self.assertEqual(scope['unavailable_sources']['source_unavailable'], 1)
        self.assertEqual(scope['interpretation'],
                         'literal_observed_heads_only_no_global_absence')


class ArchiveTests(unittest.TestCase):
    def test_snapshots_require_explicit_synthetic_archive_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus, series, lab = (root / name for name in ('corpus', 'series', 'lab'))
            for directory in (corpus, series / 'slot/messages', lab):
                directory.mkdir(parents=True)
            (corpus / 'manifest.json').write_text('{}')
            (lab / 'credentials.json').write_text('{"reader":"secret-test"}')
            (series / 'freeze-final.json').write_text(json.dumps({
                'schema': 'skopos/agent-query-freeze/v1',
                'message_capture': 'synthetic_bounded_v1'}))
            path = series / 'slot/messages/call-001.json'
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(b'[{"content":"synthetic"}]')
            output = root / 'series.tar.gz'
            with self.assertRaisesRegex(ValueError, 'explicit_archive_flag'):
                archive_series.archive(corpus, series, lab, output)
            self.assertFalse(output.exists())
            receipt = archive_series.archive(corpus, series, lab, output,
                                             include_message_snapshots=True)
            self.assertEqual(receipt['message_snapshots'], 1)


if __name__ == '__main__':
    unittest.main()
