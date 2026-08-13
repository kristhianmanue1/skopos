"""Tests para skopos.almacenamiento (SPEC-003), contra Mongo local real.

Se salta automáticamente si no hay MongoDB corriendo en localhost:27017,
en vez de fallar la suite (mismo patrón que la integración de Ollama en
test_analisis.py).
"""

from __future__ import annotations

import unittest

import pymongo

from skopos.almacenamiento import buscar_por_tema, coleccion_local, guardar_analisis
from skopos.analisis import Analisis

DB_DE_PRUEBA = "skopos_test"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).admin.command("ping")
        return True
    except Exception:
        return False


def _analisis_ejemplo(tema="bases de datos", turn_id="t1") -> Analisis:
    return Analisis(
        tema=tema,
        resumen="explica MongoDB",
        turn_id=turn_id,
        session_id="s1",
        ruta_origen="/tmp/rollout-test.jsonl",
        offset_inicio=0,
        offset_fin=100,
        entidades=["MongoDB"],
    )


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class AlmacenamientoTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

    def test_guardar_y_recuperar_por_tema(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        resultados = buscar_por_tema("bases de datos", coleccion=self.coleccion)
        self.assertEqual(len(resultados), 1)
        documento = resultados[0]
        self.assertEqual(documento["turn_id"], "t1")
        self.assertEqual(documento["ruta_origen"], "/tmp/rollout-test.jsonl")
        self.assertEqual(documento["offset_inicio"], 0)
        self.assertEqual(documento["offset_fin"], 100)
        self.assertIn("creado_en", documento)

    def test_tema_sin_coincidencias_devuelve_lista_vacia(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        self.assertEqual(buscar_por_tema("tema inexistente", coleccion=self.coleccion), [])

    def test_campos_opcionales_ausentes_no_se_guardan_vacios(self):
        analisis = _analisis_ejemplo()
        guardar_analisis(analisis, coleccion=self.coleccion)
        documento = buscar_por_tema("bases de datos", coleccion=self.coleccion)[0]
        self.assertNotIn("dominio", documento)
        self.assertNotIn("metadata_cli", documento)

    def test_dominio_y_metadata_cli_se_guardan_si_estan_presentes(self):
        analisis = Analisis(
            tema="arquitectura",
            resumen="discute microservicios",
            turn_id="t2",
            session_id="s1",
            ruta_origen="/tmp/rollout-test.jsonl",
            offset_inicio=100,
            offset_fin=200,
            dominio="arquitectura-software",
            metadata_cli={"cli_producto": {"nombre": "codex-cli"}},
        )
        guardar_analisis(analisis, coleccion=self.coleccion)
        documento = buscar_por_tema("arquitectura", coleccion=self.coleccion)[0]
        self.assertEqual(documento["dominio"], "arquitectura-software")
        self.assertEqual(documento["metadata_cli"]["cli_producto"]["nombre"], "codex-cli")

    def test_documento_siempre_resoluble_al_fragmento_de_origen(self):
        guardar_analisis(_analisis_ejemplo(), coleccion=self.coleccion)
        documento = buscar_por_tema("bases de datos", coleccion=self.coleccion)[0]
        for campo in ("ruta_origen", "offset_inicio", "offset_fin"):
            self.assertIn(campo, documento)


if __name__ == "__main__":
    unittest.main()
