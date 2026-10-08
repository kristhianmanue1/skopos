"""Extracción local PDFKit/Vision con render explícito y límites del host."""

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

from skopos.pdf_visual_graph import VisualGraphError, read_visual_graph


ENGINE_SCHEMA = 'skopos/pdf-document-macos-extract/v0.1'
SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/pdf_document_macos.swift'
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class DocumentExtractionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _remaining(started, maximum):
    remaining = maximum - (time.monotonic() - started)
    if remaining <= 0:
        raise DocumentExtractionError('budget_exceeded')
    return remaining


def _run(argv, *, input_bytes=None, timeout, environment=None):
    try:
        result = subprocess.run(argv, input=input_bytes, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout,
                                env=environment, check=False)
    except subprocess.TimeoutExpired:
        raise DocumentExtractionError('budget_exceeded') from None
    except OSError:
        raise DocumentExtractionError('engine_unavailable') from None
    if result.returncode != 0:
        raise DocumentExtractionError('engine_failed')
    return result.stdout


def _png_size(path):
    with path.open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(PNG_SIGNATURE):
        raise DocumentExtractionError('invalid_render')
    return struct.unpack('>II', header[16:24])


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(pdf_path, pages, ocr_pages, graph_pages, render_root, *,
                  render_scale_to, max_render_pixels, max_seconds,
                  max_output_bytes, renderer='pdftoppm', swift='swift',
                  cache_root=None):
    """El llamador ya cotejó PDF, páginas y política; no admite rutas de agente."""
    if (not pages or len(set(pages)) != len(pages)
            or any(type(number) is not int or number < 1 for number in pages)
            or any(number not in pages for number in ocr_pages)
            or any(number not in pages for number in graph_pages)
            or type(render_scale_to) is not int or not 500 <= render_scale_to <= 4000
            or type(max_render_pixels) is not int or max_render_pixels < 1
            or type(max_output_bytes) is not int or max_output_bytes < 1
            or not isinstance(max_seconds, (int, float)) or max_seconds <= 0):
        raise DocumentExtractionError('invalid_limits')
    pdf_path, render_root = Path(pdf_path), Path(render_root)
    render_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.monotonic()
    images = {}
    renders = {}
    for number in sorted(set(ocr_pages) | set(graph_pages)):
        prefix = render_root / ('page-' + str(number).zfill(3))
        _run([renderer, '-f', str(number), '-l', str(number),
              '-scale-to', str(render_scale_to), '-singlefile', '-png',
              str(pdf_path), str(prefix)],
             timeout=_remaining(started, max_seconds))
        path = prefix.with_suffix('.png')
        if not path.is_file() or path.is_symlink():
            raise DocumentExtractionError('render_unavailable')
        width, height = _png_size(path)
        if width * height > max_render_pixels or path.stat().st_size > max_output_bytes:
            raise DocumentExtractionError('limit_exceeded')
        os.chmod(path, 0o600)
        images[str(number)] = str(path)
        renders[str(number)] = {
            'artifact_id': 'render-page-' + str(number),
            'file_ref': 'renders/' + path.name,
            'byte_length': path.stat().st_size,
            'sha256': _sha256(path),
            'width_pixels': width,
            'height_pixels': height,
            'renderer': 'poppler/pdftoppm',
            'scale_to': render_scale_to,
            'format': 'png',
        }
    request = {'pdf_path': str(pdf_path), 'pages': pages, 'ocr_images': images}
    environment = os.environ.copy()
    cache_root = Path(cache_root) if cache_root else render_root.parent / '.cache'
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    environment['SWIFT_MODULE_CACHE_PATH'] = str(cache_root / 'swift')
    environment['CLANG_MODULE_CACHE_PATH'] = str(cache_root / 'clang')
    raw = _run([swift, str(SCRIPT)], input_bytes=json.dumps(request).encode(),
               timeout=_remaining(started, max_seconds), environment=environment)
    if len(raw) > max_output_bytes:
        raise DocumentExtractionError('limit_exceeded')
    try:
        result = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DocumentExtractionError('invalid_engine_output') from None
    if (not isinstance(result, dict) or result.get('schema') != ENGINE_SCHEMA
            or result.get('page_count', 0) < max(pages)
            or [item.get('page_number') for item in result.get('pages', [])] != pages):
        raise DocumentExtractionError('invalid_engine_output')
    for item in result['pages']:
        number = str(item['page_number'])
        item['render'] = renders.get(number)
        if item['page_number'] in graph_pages:
            try:
                item['visual_graph'] = read_visual_graph(
                    images[str(item['page_number'])], item['ocr_text']['lines'],
                    max_pixels=max_render_pixels)
            except VisualGraphError:
                raise DocumentExtractionError('graph_unavailable') from None
        else:
            item['visual_graph'] = {'status': 'not_run', 'nodes': [],
                                    'connectors': [], 'edges': [], 'unknown': []}
        item['fidelity_status'] = 'unreviewed'
        if number in ocr_pages and item['ocr_text']['status'] == 'failed':
            raise DocumentExtractionError('ocr_unavailable')
    return result, renders
