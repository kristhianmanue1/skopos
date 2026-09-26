"""Reapertura y coherencia del piloto persistente, sólo directorios temporales."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from test_meeting_pilot import module as pilot

spec = importlib.util.spec_from_file_location('persistent_meeting',
    Path(__file__).resolve().parents[1] / 'experiments/meeting-source-v1/persistent.py')
module = importlib.util.module_from_spec(spec)
# La dependencia vive en el mismo directorio experimental, sin instalar paquetes.
previous = sys.modules.get('pilot')
sys.modules['pilot'] = pilot
try:
    spec.loader.exec_module(module)
finally:
    if previous is None:
        del sys.modules['pilot']
    else:
        sys.modules['pilot'] = previous


class MeetingPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'pilot.sqlite'

    def source(self, revision=1, parent=None, text='Entrega lunes.'):
        p = self.root / ('v%d.json' % revision)
        p.write_text(json.dumps({'source_id':'meeting', 'revision':revision,
            'supersedes':parent, 'complete':False, 'segments':[{'id':'s',
            'start_ms':0, 'end_ms':1000, 'speaker':'Nerea', 'text':text}]}))
        return p

    def test_reopen_preserves_revision_chain_and_verified_navigation(self):
        store = module.PersistentMeetingStore(self.db)
        first = self.source(); store.ingest(first)
        old = store.search('lunes')[0]; store.close()
        store = module.PersistentMeetingStore(self.db)
        self.addCleanup(store.close)
        self.assertEqual(store.ingest(first), 'duplicate')
        store.ingest(self.source(2, old['sha256'], 'Entrega martes.'))
        self.assertEqual(store.search('lunes'), [])
        self.assertEqual(store.search('martes')[0]['revision'], 2)
        self.assertEqual(store.fetch('meeting', 1, 's')['status'], 'verified')
        self.assertFalse(store.fetch('meeting', 2, 's')['complete'])

    def test_two_handles_refresh_and_reject_conflicting_revision(self):
        a = module.PersistentMeetingStore(self.db)
        b = module.PersistentMeetingStore(self.db)
        self.addCleanup(a.close); self.addCleanup(b.close)
        a.ingest(self.source()); parent = b.search('lunes')[0]['sha256']
        a.ingest(self.source(2, parent, 'Entrega martes.'))
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            b.ingest(self.source(2, parent, 'Entrega viernes.'))
        self.assertEqual(b.search('viernes'), [])
        self.assertEqual(a.search('martes')[0]['revision'], 2)
        self.assertEqual(b.fetch('meeting', 2, 's')['status'], 'integrity_mismatch')

    def test_rejected_chain_does_not_persist(self):
        a = module.PersistentMeetingStore(self.db)
        a.ingest(self.source())
        with self.assertRaisesRegex(ValueError, 'invalid_revision_chain'):
            a.ingest(self.source(2, 'wrong'))
        a.close()
        b = module.PersistentMeetingStore(self.db)
        self.addCleanup(b.close)
        self.assertEqual(b.search('lunes')[0]['revision'], 1)

    def test_unrelated_database_is_not_adopted(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute('CREATE TABLE unrelated (value TEXT)')
        with self.assertRaisesRegex(ValueError, 'unsupported_pilot_database'):
            module.PersistentMeetingStore(self.db)
        with sqlite3.connect(self.db) as connection:
            names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual(names, ['unrelated'])

    def test_missing_source_after_restart_stays_unavailable(self):
        a = module.PersistentMeetingStore(self.db)
        p = self.source(); a.ingest(p); a.close(); p.unlink()
        b = module.PersistentMeetingStore(self.db)
        self.addCleanup(b.close)
        self.assertEqual(b.fetch('meeting', 1, 's')['status'], 'source_unavailable')
        self.assertEqual(b.search('lunes')[0]['integrity'], 'not_checked')
