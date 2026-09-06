"""Tests del análisis multi-proveedor (ADR-014).

Runner: `python3 -m unittest`.

Cobertura: parseo tolerante (cercados ```json), adaptador
compatible-OpenAI contra un servidor HTTP local real (stdlib), despacho
por entorno, precedencia argumento > entorno > default, y errores
infra/modelo con la taxonomía existente.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from skopos import analisis
from skopos.analisis import (
    ErrorInfraestructura,
    ErrorModelo,
    _des_cercar,
    _llamar_openai_compat,
    analizar_turno,
)


def _turno_simple():
    return analisis.Turno(
        turn_id="t1", session_id="s1", texto_usuario="hola",
        texto_agente="mundo", timestamp_cierre="2026-09-06T00:00:00Z",
        ruta_origen="/x", offset_inicio=0, offset_fin=9, cli="codex-cli",
    )


class _ServidorFalso:
    """HTTP local que responde choices-format (o lo que el test pida)."""

    def __init__(self, contenido: str, capturar_auth: dict | None = None,
                 estado: int = 200):
        cuerpo = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": contenido}}]
        }).encode("utf-8")
        externo = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if capturar_auth is not None:
                    capturar_auth["auth"] = self.headers.get("Authorization")
                largo = int(self.headers.get("Content-Length", 0))
                self.rfile.read(largo)
                self.send_response(estado)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *_):
                pass

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        externo.puerto = self.servidor.server_address[1]
        self.hilo = threading.Thread(target=self.servidor.serve_forever)
        self.hilo.daemon = True
        self.hilo.start()

    def url(self) -> str:
        return f"http://127.0.0.1:{self.puerto}"

    def cerrar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


class TestDesCercar(unittest.TestCase):
    def test_json_puro_pasa_igual(self):
        self.assertEqual(_des_cercar('{"a": 1}'), '{"a": 1}')

    def test_cercado_json_se_quita(self):
        self.assertEqual(_des_cercar('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_cercado_simple_se_quita(self):
        self.assertEqual(_des_cercar('```\n{"a": 1}\n```'), '{"a": 1}')


class TestOpenaiCompat(unittest.TestCase):
    def test_respuesta_choices_se_parsea(self):
        servidor = _ServidorFalso('{"tema": "t", "resumen": "r"}')
        self.addCleanup(servidor.cerrar)
        resultado = _llamar_openai_compat(
            "prompt", modelo="glm-5.3", base_url=servidor.url(), timeout=5)
        self.assertEqual(resultado, {"tema": "t", "resumen": "r"})

    def test_contenido_cercado_se_parsea(self):
        servidor = _ServidorFalso('```json\n{"tema": "t", "resumen": "r"}\n```')
        self.addCleanup(servidor.cerrar)
        resultado = _llamar_openai_compat(
            "prompt", modelo="m", base_url=servidor.url(), timeout=5)
        self.assertEqual(resultado["tema"], "t")

    def test_api_key_va_en_header_y_nunca_en_cuerpo(self):
        captura: dict = {}
        servidor = _ServidorFalso('{"tema": "t", "resumen": "r"}',
                                  capturar_auth=captura)
        self.addCleanup(servidor.cerrar)
        _llamar_openai_compat("prompt", modelo="m", base_url=servidor.url(),
                              timeout=5, api_key="secreto-123")
        self.assertEqual(captura["auth"], "Bearer secreto-123")

    def test_contenido_no_json_es_error_modelo(self):
        servidor = _ServidorFalso("lo siento, no tengo JSON")
        self.addCleanup(servidor.cerrar)
        with self.assertRaises(ErrorModelo):
            _llamar_openai_compat("prompt", modelo="m",
                                  base_url=servidor.url(), timeout=5)

    def test_servidor_caído_es_error_infraestructura(self):
        servidor = _ServidorFalso("{}")
        puerto = servidor.puerto
        servidor.cerrar()  # apagado: nada escucha
        with self.assertRaises(ErrorInfraestructura):
            _llamar_openai_compat("prompt", modelo="m",
                                  base_url=f"http://127.0.0.1:{puerto}",
                                  timeout=2)


class TestDespacho(unittest.TestCase):
    def setUp(self):
        self._variables_previas = {
            var: os.environ.get(var)
            for var in (analisis.ENV_API, analisis.ENV_BASE_URL,
                        analisis.ENV_MODELO, analisis.ENV_API_KEY)
        }
        self.addCleanup(self._restaurar_entorno)

    def _restaurar_entorno(self):
        for var, valor in self._variables_previas.items():
            if valor is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = valor

    def test_sin_entorno_el_default_es_ollama(self):
        self.assertEqual(analisis._configuracion_proveedor(),
                         ("ollama", None, None, None))

    def test_entorno_openai_ruta_end_to_end(self):
        servidor = _ServidorFalso('{"tema": "remoto", "resumen": "vía z.ai"}')
        self.addCleanup(servidor.cerrar)
        os.environ[analisis.ENV_API] = "openai"
        os.environ[analisis.ENV_BASE_URL] = servidor.url()
        os.environ[analisis.ENV_MODELO] = "glm-5.3"
        os.environ[analisis.ENV_API_KEY] = "clave-de-prueba"
        resultado = analizar_turno(_turno_simple())
        self.assertEqual(resultado.tema, "remoto")
        self.assertEqual(resultado.modelo_analisis, "glm-5.3")

    def test_argumento_explícito_gana_al_entorno(self):
        servidor = _ServidorFalso('{"tema": "t", "resumen": "r"}')
        self.addCleanup(servidor.cerrar)
        os.environ[analisis.ENV_API] = "openai"
        os.environ[analisis.ENV_BASE_URL] = servidor.url()
        os.environ[analisis.ENV_MODELO] = "del-entorno"
        llamado: dict = {}

        def _espia(prompt, *, modelo, base_url, timeout):
            llamado["modelo"] = modelo
            return {"tema": "t", "resumen": "r"}

        analizar_turno(_turno_simple(), modelo="explícito",
                       llamar_modelo=_espia)
        self.assertEqual(llamado["modelo"], "explícito")

    def test_llamar_modelo_inyectado_ignora_el_entorno(self):
        os.environ[analisis.ENV_API] = "openai"
        os.environ[analisis.ENV_BASE_URL] = "http://127.0.0.1:1"  # nada escucha
        llamado: dict = {}

        def _espia(prompt, *, modelo, base_url, timeout):
            llamado["sí"] = True
            return {"tema": "t", "resumen": "r"}

        resultado = analizar_turno(_turno_simple(), llamar_modelo=_espia)
        self.assertTrue(llamado.get("sí"))
        self.assertEqual(resultado.tema, "t")


if __name__ == "__main__":
    unittest.main()
