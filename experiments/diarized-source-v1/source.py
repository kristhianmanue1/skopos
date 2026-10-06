"""Lector experimental local; preserva texto, tiempos y etiquetas sin corregirlos."""
from collections import Counter
from decimal import Decimal
import hashlib
from pathlib import Path
import re

LINE = re.compile(r'^\[(?P<start>\d+\.\d{1,3}) - (?P<end>\d+\.\d{1,3})\] (?P<speaker>SPEAKER_(?:\d+|UNKNOWN)): (?P<text>.+)$')
MAX_BYTES = 16 * 1024 * 1024


def checksum(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('source_size_out_of_range')
    text = raw.decode('utf-8')
    segments = []; byte_offset = 0; overlaps = []
    for line_number, line in enumerate(text.splitlines(keepends=True), 1):
        body = line.rstrip('\r\n')
        if not body.strip():
            byte_offset += len(line.encode('utf-8'))
            continue
        match = LINE.fullmatch(body)
        if match is None:
            raise ValueError('invalid_segment_line_%d' % line_number)
        start = int(Decimal(match['start']) * 1000)
        end = int(Decimal(match['end']) * 1000)
        if end <= start or not match['text'].strip():
            raise ValueError('invalid_interval_or_text_line_%d' % line_number)
        if segments and start < segments[-1]['start_ms']:
            raise ValueError('non_monotonic_start_line_%d' % line_number)
        identity = 'segment-%06d' % (len(segments) + 1)
        if segments and start < segments[-1]['end_ms']:
            overlaps.append({'previous':segments[-1]['id'], 'current':identity,
                             'overlap_ms':min(segments[-1]['end_ms'], end) - start})
        start_byte = byte_offset + len(body[:match.start('text')].encode('utf-8'))
        end_byte = start_byte + len(match['text'].encode('utf-8'))
        segments.append({'id':identity, 'line':line_number, 'start_ms':start,
                         'end_ms':end, 'speaker':match['speaker'], 'text':match['text'],
                         'start_byte':start_byte, 'end_byte':end_byte})
        byte_offset += len(line.encode('utf-8'))
    if not segments:
        raise ValueError('no_segments')
    return {'schema':'skopos/diarized-transcript/v0', 'source_sha256':checksum(raw),
            'source_bytes':len(raw), 'capture_completeness':'unknown',
            'audio_alignment':'not_verified', 'speaker_identity':'not_verified',
            'meeting_date':'unknown', 'segments':segments, 'adjacent_overlaps':overlaps}


class DiarizedSource:
    """No persiste ni envía contenido. Cada lectura exige la revisión esperada."""
    def __init__(self, path, revision):
        self.path = Path(path)
        self.revision = revision

    def _read(self):
        with self.path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if checksum(raw) != self.revision:
            raise ValueError('source_revision_changed')
        return raw, parse(raw)

    def search(self, term):
        if type(term) is not str or not term.strip():
            raise ValueError('invalid_term')
        _, parsed = self._read()
        return [s for s in parsed['segments'] if term.casefold() in s['text'].casefold()]

    def fetch(self, identity):
        raw, parsed = self._read()
        for segment in parsed['segments']:
            if segment['id'] == identity:
                if raw[segment['start_byte']:segment['end_byte']].decode('utf-8') != segment['text']:
                    raise ValueError('locator_mismatch')
                return {'status':'transcript_bytes_verified', 'source_sha256':self.revision,
                        'audio_alignment':'not_verified', 'segment':segment}
        raise KeyError('segment_not_found')


def inspect(path):
    path = Path(path)
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    parsed = parse(raw)
    verified = sum(raw[s['start_byte']:s['end_byte']].decode('utf-8') == s['text'] for s in parsed['segments'])
    counts = Counter(s['speaker'] for s in parsed['segments'])
    return {'schema':'skopos/diarized-inspection/v0',
            'source_sha256':parsed['source_sha256'], 'source_bytes':len(raw),
            'segment_count':len(parsed['segments']), 'verified_text_ranges':verified,
            'speaker_labels':dict(counts), 'adjacent_overlaps':len(parsed['adjacent_overlaps']),
            'last_end_ms':max(s['end_ms'] for s in parsed['segments']),
            'capture_completeness':'unknown', 'audio_alignment':'not_verified',
            'speaker_identity':'not_verified', 'meeting_date':'unknown'}
