"""Tests para el dispatcher skopos.__main__. Runner: `python3 -m unittest`."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from skopos.__main__ import main


class MainDispatchTests(unittest.TestCase):
    def test_sin_argumentos_muestra_version_y_comandos(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            codigo = main([])
        self.assertEqual(codigo, 0)
        salida = buf.getvalue()
        self.assertIn("skopos", salida)
        self.assertIn("query", salida)
        self.assertIn("watch", salida)

    def test_help_muestra_lo_mismo_que_sin_argumentos(self):
        for flag in ("-h", "--help", "help"):
            with self.subTest(flag=flag):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    codigo = main([flag])
                self.assertEqual(codigo, 0)
                self.assertIn("query", buf.getvalue())

    def test_comando_desconocido_falla_y_muestra_ayuda(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            codigo = main(["no-existe"])
        self.assertEqual(codigo, 1)
        salida = buf.getvalue()
        self.assertIn("no-existe", salida)
        self.assertIn("query", salida)

    def test_query_sin_tema_falla_por_argparse_no_por_dispatcher(self):
        # argparse exige el argumento posicional 'tema' y sale con SystemExit;
        # confirma que el dispatcher sí llegó a invocar query_command.
        buf = io.StringIO()
        with redirect_stderr(buf):
            with self.assertRaises(SystemExit):
                main(["query"])


if __name__ == "__main__":
    unittest.main()
