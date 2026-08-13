"""Tests para skopos.analisis (SPEC-002). Runner: `python3 -m unittest`."""

from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from skopos.analisis import Analisis, AnalisisFallido, analizar_turno
from skopos.captura import Turno

TURNO_EJEMPLO = Turno(
    turn_id="t1",
    session_id="s1",
    texto_usuario="¿qué es MongoDB?",
    texto_agente="Una base de datos documental.",
    timestamp_cierre="2026-08-12T00:00:00Z",
    ruta_origen="/tmp/rollout-test.jsonl",
    offset_inicio=0,
    offset_fin=100,
)


def _modelo_falso(respuesta: dict):
    def llamar(prompt, *, modelo, base_url, timeout):
        return respuesta

    return llamar


class AnalizarTurnoTests(unittest.TestCase):
    def test_respuesta_valida_produce_analisis_completo(self):
        analisis = analizar_turno(
            TURNO_EJEMPLO,
            llamar_modelo=_modelo_falso(
                {"tema": "bases de datos", "resumen": "explica MongoDB", "entidades": ["MongoDB"]}
            ),
        )
        self.assertIsInstance(analisis, Analisis)
        self.assertEqual(analisis.tema, "bases de datos")
        self.assertEqual(analisis.resumen, "explica MongoDB")
        self.assertEqual(analisis.entidades, ["MongoDB"])
        self.assertEqual(analisis.turn_id, "t1")
        self.assertEqual(analisis.ruta_origen, "/tmp/rollout-test.jsonl")

    def test_respuesta_sin_entidades_usa_lista_vacia(self):
        analisis = analizar_turno(
            TURNO_EJEMPLO,
            llamar_modelo=_modelo_falso({"tema": "x", "resumen": "y"}),
        )
        self.assertEqual(analisis.entidades, [])

    def test_respuesta_sin_tema_falla_explicito(self):
        with self.assertRaises(AnalisisFallido):
            analizar_turno(
                TURNO_EJEMPLO,
                llamar_modelo=_modelo_falso({"resumen": "sin tema"}),
            )

    def test_respuesta_con_tema_vacio_falla_explicito(self):
        with self.assertRaises(AnalisisFallido):
            analizar_turno(
                TURNO_EJEMPLO,
                llamar_modelo=_modelo_falso({"tema": "", "resumen": "algo"}),
            )

    def test_respuesta_no_es_objeto_falla_explicito(self):
        with self.assertRaises(AnalisisFallido):
            analizar_turno(TURNO_EJEMPLO, llamar_modelo=_modelo_falso(["no", "es", "objeto"]))

    def test_fallo_de_conexion_se_propaga_como_analisis_fallido(self):
        def llamar_que_falla(prompt, *, modelo, base_url, timeout):
            raise AnalisisFallido("Ollama no respondió: connection refused")

        with self.assertRaises(AnalisisFallido):
            analizar_turno(TURNO_EJEMPLO, llamar_modelo=llamar_que_falla)

    def test_config_de_dominio_se_registra_en_el_resultado(self):
        analisis = analizar_turno(
            TURNO_EJEMPLO,
            dominio_config={"domain": "arquitectura-software", "keywords": ["API"]},
            llamar_modelo=_modelo_falso({"tema": "x", "resumen": "y"}),
        )
        self.assertEqual(analisis.dominio, "arquitectura-software")

    def test_prompt_incluye_texto_del_turno_y_dominio(self):
        capturado = {}

        def llamar(prompt, *, modelo, base_url, timeout):
            capturado["prompt"] = prompt
            return {"tema": "x", "resumen": "y"}

        analizar_turno(
            TURNO_EJEMPLO,
            dominio_config={"domain": "arquitectura-software"},
            llamar_modelo=llamar,
        )
        self.assertIn("¿qué es MongoDB?", capturado["prompt"])
        self.assertIn("arquitectura-software", capturado["prompt"])

    def test_entidades_con_tipo_incorrecto_se_ignoran_sin_romper(self):
        analisis = analizar_turno(
            TURNO_EJEMPLO,
            llamar_modelo=_modelo_falso(
                {"tema": "x", "resumen": "y", "entidades": "MongoDB"}
            ),
        )
        self.assertEqual(analisis.entidades, [])

    def test_sin_escrubery_script_metadata_cli_es_none(self):
        analisis = analizar_turno(
            TURNO_EJEMPLO, llamar_modelo=_modelo_falso({"tema": "x", "resumen": "y"})
        )
        self.assertIsNone(analisis.metadata_cli)


def _ollama_disponible() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
        return True
    except (urllib.error.URLError, OSError):
        return False


@unittest.skipUnless(_ollama_disponible(), "Ollama no está corriendo en localhost:11434")
class AnalizarTurnoIntegracionRealTests(unittest.TestCase):
    """Prueba end-to-end contra el Ollama real del entorno (EV-6). Se salta
    automáticamente si Ollama no responde, en vez de fallar la suite."""

    def test_analiza_turno_real_con_qwen3(self):
        analisis = analizar_turno(TURNO_EJEMPLO)
        self.assertTrue(analisis.tema.strip())
        self.assertTrue(analisis.resumen.strip())


if __name__ == "__main__":
    unittest.main()
