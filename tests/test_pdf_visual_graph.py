"""Controles de topología visual y abstención de dirección."""

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from skopos.pdf_visual_graph import read_visual_graph


def _png(path, width, height, dark):
    def chunk(kind, data):
        body = kind + data
        return (struct.pack('>I', len(data)) + body +
                struct.pack('>I', zlib.crc32(body) & 0xffffffff))

    rows = []
    for y in range(height):
        rows.append(b'\x00' + bytes(0 if (x, y) in dark else 255
                                 for x in range(width)))
    raw = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))
    path.write_bytes(raw)


class VisualGraphTests(unittest.TestCase):
    def test_inverted_arrow_reverses_observed_direction(self):
        dark = set()

        def line(x1, y1, x2, y2):
            if x1 == x2:
                dark.update((x1, y) for y in range(y1, y2 + 1))
            elif y1 == y2:
                dark.update((x, y1) for x in range(x1, x2 + 1))

        for top, bottom in ((30, 100), (190, 260)):
            line(70, top, 210, top)
            line(70, bottom, 210, bottom)
            line(70, top, 70, bottom)
            line(210, top, 210, bottom)
        line(140, 101, 140, 189)
        for delta in range(1, 14):
            dark.add((140 - delta, 101 + delta))
            dark.add((140 + delta, 101 + delta))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reversed.png'
            _png(path, 400, 400, dark)
            graph = read_visual_graph(path, [], max_pixels=400 * 400,
                                      diagram_type='flowchart')
        self.assertEqual(2, len(graph['nodes']))
        self.assertTrue(graph['connectors'])
        self.assertEqual([('n2', 'n1', 'observed')],
                         [(edge['from_node'], edge['to_node'], edge['direction'])
                          for edge in graph['edges']])

    def test_branch_without_arrows_has_no_cross_branch_or_observed_direction(self):
        dark = set()

        def line(x1, y1, x2, y2):
            if x1 == x2:
                dark.update((x1, y) for y in range(y1, y2 + 1))
            elif y1 == y2:
                dark.update((x, y1) for x in range(x1, x2 + 1))

        for x1, x2, y1, y2 in ((230, 370, 30, 100),
                               (60, 200, 210, 280),
                               (400, 540, 210, 280)):
            line(x1, y1, x2, y1)
            line(x1, y2, x2, y2)
            line(x1, y1, x1, y2)
            line(x2, y1, x2, y2)
        line(300, 101, 300, 150)
        line(130, 150, 470, 150)
        line(130, 150, 130, 209)
        line(470, 150, 470, 209)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'branch.png'
            _png(path, 600, 400, dark)
            graph = read_visual_graph(path, [], max_pixels=600 * 400)
        self.assertEqual(3, len(graph['nodes']))
        self.assertEqual({('n1', 'n2'), ('n1', 'n3')},
                         {(edge['from_node'], edge['to_node'])
                          for edge in graph['edges']})
        self.assertTrue(all(edge['direction'] == 'unknown'
                            for edge in graph['edges']))


if __name__ == '__main__':
    unittest.main()
