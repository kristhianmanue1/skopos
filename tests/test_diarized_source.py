"""Fixtures sintéticos: ningún test depende de reuniones privadas."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
import stat
import subprocess
import sys

spec=importlib.util.spec_from_file_location('diarized_source',Path(__file__).resolve().parents[1]/'experiments/diarized-source-v1/source.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class DiarizedSourceTests(unittest.TestCase):
    def test_nested_segment_overlap_is_actual_intersection(self):
        raw = (b'[0.0 - 10.0] SPEAKER_01: first\n'
               b'[1.0 - 2.0] SPEAKER_02: second')
        value = module.parse(raw)
        self.assertEqual(value['adjacent_overlaps'][0]['overlap_ms'], 1000)

    def test_exact_utf8_ranges_with_crlf_and_unknown(self):
        raw='[0000.30 - 0001.90] SPEAKER_01: Revisión: miércoles.\r\n[0001.89 - 0002.15] SPEAKER_UNKNOWN: Sí.\r\n'.encode()
        value=module.parse(raw)
        self.assertEqual(value['segments'][0]['start_ms'],300)
        self.assertEqual(len(value['adjacent_overlaps']),1)
        self.assertEqual(value['segments'][1]['speaker'],'SPEAKER_UNKNOWN')
        for s in value['segments']:
            self.assertEqual(raw[s['start_byte']:s['end_byte']].decode(),s['text'])
        self.assertEqual(value['capture_completeness'],'unknown')

    def test_invalid_lines_and_times_rejected_not_dropped(self):
        for raw in (b'ordinary prose',b'[0001.00 - 0000.50] SPEAKER_01: text',b'[0.0011 - 1.0000] SPEAKER_01: text',b'[1.0 - 2.0] SPEAKER_01: first\n[0.5 - 1.0] SPEAKER_02: second'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):module.parse(raw)

    def test_search_and_fetch_pinned_to_original(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'meeting.txt';raw=b'[0.0 - 2.0] SPEAKER_01: delivery Tuesday'
            p.write_bytes(raw);source=module.DiarizedSource(p,module.checksum(raw))
            hit=source.search('Tuesday')[0]
            self.assertEqual(source.fetch(hit['id'])['segment']['text'],'delivery Tuesday')
            p.write_bytes(raw.replace(b'Tuesday',b'Monday'))
            with self.assertRaisesRegex(ValueError,'source_revision_changed'):source.fetch(hit['id'])

    def test_summary_does_not_export_transcript_or_infer_date(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'2307_2026.txt';p.write_text('[0.0 - 2.0] SPEAKER_01: Private synthetic words.')
            result=module.inspect(p)
            self.assertEqual(result['verified_text_ranges'],1)
            self.assertEqual(result['meeting_date'],'unknown')
            self.assertNotIn('Private',str(result))

    def test_cli_creates_private_report_without_transcript_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.txt'
            raw = b'[0.0 - 2.0] SPEAKER_01: Private synthetic words.'
            source.write_bytes(raw)
            output = root / 'report'
            command = [sys.executable, str(Path(module.__file__).with_name('run.py')),
                       str(source), str(output), '--term', 'synthetic']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report_path = output / 'report.json'
            report_bytes = report_path.read_bytes()
            report = json.loads(report_bytes)
            self.assertEqual(report['queries'][0]['matching_segments'], 1)
            self.assertTrue(report['source_unchanged'])
            self.assertNotIn('Private synthetic words.', report_bytes.decode())
            self.assertNotIn('Private synthetic words.', result.stdout)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o600)
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(report_path.read_bytes(), report_bytes)
            self.assertEqual(source.read_bytes(), raw)
