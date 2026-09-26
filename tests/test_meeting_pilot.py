"""Casos sintéticos del contrato experimental, sin CLI, servicios ni datos reales."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'experiments/meeting-source-v1/pilot.py'
spec = importlib.util.spec_from_file_location('meeting_pilot', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MeetingPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = module.MeetingStore()

    def source(self, revision=1, text='La entrega será el lunes.', complete=True, supersedes=None):
        p = self.root / ('meeting-v%d.json' % revision)
        p.write_text(json.dumps({'source_id':'meeting-lumbre', 'revision':revision,
                     'supersedes':supersedes, 'complete':complete,
                     'segments':[{'id':'s1','start_ms':1000,'end_ms':4500,
                                  'speaker':'Nerea','text':text}]}), encoding='utf-8')
        return p

    def test_import_duplicate_correct_and_navigate_both_revisions(self):
        first = self.source()
        self.assertEqual(self.store.ingest(first), 'imported')
        self.assertEqual(self.store.ingest(first), 'duplicate')
        old = self.store.search('lunes')[0]
        second = self.source(2, 'Corrección: la entrega será el martes.', supersedes=old['sha256'])
        self.store.ingest(second)
        self.assertEqual(self.store.search('lunes'), [])
        current = self.store.search('martes')[0]
        self.assertEqual(current['revision'], 2)
        for hit in (old, current):
            result = self.store.fetch(hit['source_id'], hit['revision'], hit['locator']['id'])
            self.assertEqual(result['status'], 'verified')
            self.assertEqual(result['segment']['text'], hit['text'])
            self.assertEqual(result['segment']['start_ms'], 1000)

    def test_partial_capture_is_not_promoted_to_complete(self):
        self.store.ingest(self.source(complete=False))
        self.assertFalse(self.store.search('lunes')[0]['complete'])
        self.assertFalse(self.store.fetch('meeting-lumbre', 1, 's1')['complete'])

    def test_missing_original_does_not_erase_index_or_claim_verification(self):
        p = self.source(); self.store.ingest(p); p.unlink()
        self.assertEqual(self.store.fetch('meeting-lumbre', 1, 's1')['status'], 'source_unavailable')
        self.assertEqual(self.store.search('lunes')[0]['integrity'], 'not_checked')

    def test_modified_original_is_rejected(self):
        p = self.source(); self.store.ingest(p); p.write_text('{}')
        self.assertEqual(self.store.fetch('meeting-lumbre', 1, 's1')['status'], 'integrity_mismatch')

    def test_revision_conflict_and_wrong_parent_rejected(self):
        self.store.ingest(self.source())
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            self.store.ingest(self.source(text='Distinto contenido.'))
        with self.assertRaisesRegex(ValueError, 'invalid_revision_chain'):
            self.store.ingest(self.source(2, supersedes='wrong'))
        self.assertEqual(len(self.store.sources['meeting-lumbre']), 1)
