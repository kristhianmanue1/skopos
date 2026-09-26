"""Comprobar bytes/localizadores exportados y rechazo de origen no verificable."""
import importlib.util
from pathlib import Path
import unittest
import test_meeting_pilot as fixtures

path=Path(__file__).resolve().parents[1]/'experiments/meeting-source-v1/export.py'
spec=importlib.util.spec_from_file_location('meeting_export',path)
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)

class MeetingExportTests(unittest.TestCase):
    setUp = fixtures.MeetingPilotTests.setUp
    source = fixtures.MeetingPilotTests.source
    def test_export_keeps_exact_utf8_and_native_locator(self):
        self.store.ingest(self.source(text='Entrega: miércoles, responsable Nerea.'))
        p=export.export_packet(self.store,['Entrega','Nerea'])
        self.assertEqual(len(p['spans']),1)
        span=p['spans'][0]
        self.assertEqual(p['text'].encode()[span['start_byte']:span['end_byte']].decode(),span['text'])
        self.assertEqual(span['locator']['speaker'],'Nerea')
        self.assertEqual(p['selection_complete'],'not_established')

    def test_unavailable_origin_blocks_export(self):
        path=self.source();self.store.ingest(path);path.unlink()
        with self.assertRaisesRegex(ValueError,'source_not_verified'):
            export.export_packet(self.store,['lunes'])
