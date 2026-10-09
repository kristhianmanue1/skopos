"""Offsets verificables y límite de fidelidad del derivado HTML local."""

import hashlib
import unittest

from skopos.html_derivative import HtmlDerivativeError, derive_html_text


class HtmlDerivativeTests(unittest.TestCase):
    def test_visible_text_offsets_and_script_exclusion(self):
        raw = (b'<!DOCTYPE html><html><head><meta charset=iso-8859-1>'
               b'<title>hidden</title></head><body>Se\xf1al &amp; dato'
               b'<script>bad</script></body></html>')
        result = derive_html_text(raw)
        texts = [item['text'] for item in result['items']]
        self.assertIn('Señal ', texts)
        self.assertIn('&', texts)
        self.assertNotIn('hidden', texts)
        self.assertNotIn('bad', texts)
        for item in result['items']:
            fragment = raw[item['start_byte']:item['end_byte']]
            self.assertEqual(len(fragment), item['end_byte'] - item['start_byte'])
            self.assertEqual(hashlib.sha256(fragment).hexdigest(),
                             item['raw_sha256'])
        self.assertEqual(result['fidelity_status'], 'unreviewed')

    def test_unsupported_charset_fails_closed(self):
        with self.assertRaisesRegex(HtmlDerivativeError, 'unsupported_encoding'):
            derive_html_text(b'<!DOCTYPE html><meta charset=shift_jis>texto')

    def test_utf8_inferred_byte_offsets(self):
        raw = b'<!DOCTYPE html><html><body>ni\xc3\xb1o &amp; m\xc3\xa1s</body></html>'
        result = derive_html_text(raw)
        self.assertEqual(result['encoding'], 'utf-8')
        self.assertEqual(result['encoding_basis'], 'inferred_strict_utf8')
        self.assertEqual(result['items'][0]['text'], 'niño ')
        item = result['items'][0]
        self.assertEqual(raw[item['start_byte']:item['end_byte']], b'ni\xc3\xb1o ')


if __name__ == '__main__':
    unittest.main()
