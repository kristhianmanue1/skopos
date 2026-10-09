"""Extracción local conservadora de HTML Latin-1/UTF-8 con offsets crudos."""

from html import unescape
from html.parser import HTMLParser
import hashlib
import re


class HtmlDerivativeError(ValueError):
    pass


class _VisibleText(HTMLParser):
    def __init__(self, raw, decoded, encoding):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.decoded = decoded
        self.encoding = encoding
        self.source_sha256 = hashlib.sha256(raw).hexdigest()
        self.line_starts = [0]
        for match in re.finditer('\n', decoded):
            self.line_starts.append(match.end())
        self.byte_offsets = [0]
        for character in decoded:
            self.byte_offsets.append(self.byte_offsets[-1] + len(character.encode(encoding)))
        self.hidden = []
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'head'):
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'head') and tag in self.hidden:
            self.hidden.remove(tag)

    def _append(self, data, raw_length):
        if self.hidden or not data.strip():
            return
        line, column = self.getpos()
        start_char = self.line_starts[line - 1] + column
        end_char = start_char + raw_length
        if self.decoded[start_char:end_char] != data:
            raise HtmlDerivativeError('offset_mismatch')
        start = self.byte_offsets[start_char]
        end = self.byte_offsets[end_char]
        text = unescape(data)
        fragment_sha256 = hashlib.sha256(self.raw[start:end]).hexdigest()
        item_id = hashlib.sha256((self.source_sha256 + ':' + str(start) + ':' +
                                  str(end) + ':' +
                                  fragment_sha256).encode()).hexdigest()
        self.items.append({'item_id': item_id, 'start_byte': start,
                           'end_byte': end, 'raw_sha256': fragment_sha256,
                           'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                           'text': text, 'line': line})

    def handle_data(self, data):
        self._append(data, len(data))

    def handle_entityref(self, name):
        raw = '&' + name + ';'
        self._append(raw, len(raw))

    def handle_charref(self, name):
        raw = '&#' + name + ';'
        self._append(raw, len(raw))


def derive_html_text(raw):
    """Devuelve candidatos textuales; los offsets apuntan al HTML original."""
    if not isinstance(raw, bytes) or len(raw) > 4 * 1024 * 1024:
        raise HtmlDerivativeError('invalid_bytes')
    opening = raw[:4096].lower()
    if not raw[:1024].lstrip().lower().startswith((b'<!doctype html', b'<html')):
        raise HtmlDerivativeError('unsupported_encoding_or_format')
    declared = re.search(rb'charset\s*=\s*["\']?([a-z0-9_-]+)', opening)
    if declared and declared.group(1) in (b'iso-8859-1', b'latin1'):
        encoding, basis = 'latin-1', 'declared'
    elif declared and declared.group(1) == b'utf-8':
        encoding, basis = 'utf-8', 'declared'
    elif declared:
        raise HtmlDerivativeError('unsupported_encoding_or_format')
    else:
        encoding, basis = 'utf-8', 'inferred_strict_utf8'
    try:
        decoded = raw.decode(encoding)
        parser = _VisibleText(raw, decoded, encoding)
        parser.feed(decoded)
        parser.close()
    except (UnicodeError, ValueError) as error:
        raise HtmlDerivativeError('parse_failed') from error
    return {'schema': 'skopos/html-text-derivative/v0.1',
            'source_sha256': parser.source_sha256,
            'source_bytes': len(raw), 'encoding': encoding,
            'encoding_basis': basis,
            'fidelity_status': 'unreviewed',
            'coverage': {'scope': 'parser_visible_text',
                         'css_visibility_evaluated': False,
                         'scripts_executed': False},
            'items': parser.items}
