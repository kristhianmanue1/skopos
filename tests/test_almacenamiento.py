"""Tests para skopos.almacenamiento (SPEC-003), contra Mongo local real.

Se salta automáticamente si no hay MongoDB corriendo en localhost:27017,
en vez de fallar la suite (mismo patrón que la integración de Ollama en
test_analisis.py).
"""

from __future__ import annotations

import unittest

import pymongo
from pymongo.errors import DuplicateKeyError

from skopos.almacenamiento import (
    DocumentoInvalido,
    buscar_por_tema,
    coleccion_local,
    existe_turn_id,
    guardar_analisis,
)
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


def _analisis_ejemplo(tema="bases de datos", turn_id="t1", resumen="explica MongoDB") -> Analisis:
    return Analisis(
        tema=tema,
        resumen=resumen,
        turn_id=turn_id,
        session_id="s1",
        ruta_origen="/tmp/rollout-test.jsonl",
        offset_inicio=0,
        offset_fin=100,
        cli="codex-cli", modelo_analisis="test-modelo",
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
            cli="codex-cli", modelo_analisis="test-modelo",
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

    def test_existe_turn_id_antes_y_despues_de_guardar(self):
        self.assertFalse(existe_turn_id("t1", coleccion=self.coleccion))
        guardar_analisis(_analisis_ejemplo(turn_id="t1"), coleccion=self.coleccion)
        self.assertTrue(existe_turn_id("t1", coleccion=self.coleccion))
        self.assertFalse(existe_turn_id("otro-turno", coleccion=self.coleccion))

    def test_turn_id_duplicado_lo_rechaza_el_indice_unico(self):
        # ronda adversarial 2026-08-13 [HIGH]: sin índice único, dos
        # inserciones para el mismo turn_id convivían sin error.
        guardar_analisis(_analisis_ejemplo(turn_id="dup"), coleccion=self.coleccion)
        with self.assertRaises(DuplicateKeyError):
            guardar_analisis(_analisis_ejemplo(turn_id="dup"), coleccion=self.coleccion)

    def test_guardar_sin_turn_id_o_ruta_origen_se_rechaza(self):
        # ronda adversarial 2026-08-13 [HIGH]: el CONTRATO prometía rechazo
        # en el borde; el código sólo confiaba en que nunca pasara.
        sin_turn_id = _analisis_ejemplo(turn_id="")
        with self.assertRaises(DocumentoInvalido):
            guardar_analisis(sin_turn_id, coleccion=self.coleccion)
        self.assertEqual(self.coleccion.count_documents({}), 0)

    def test_busqueda_por_tema_encuentra_reformulaciones_con_palabras_en_comun(self):
        # ronda adversarial 2026-08-13 [HIGH]: igualdad exacta fallaba
        # contra temas que el LLM redacta distinto para la misma idea.
        guardar_analisis(
            _analisis_ejemplo(tema="Índices en MongoDB", turn_id="t1"),
            coleccion=self.coleccion,
        )
        guardar_analisis(
            _analisis_ejemplo(tema="Optimización de consulta en MongoDB", turn_id="t2"),
            coleccion=self.coleccion,
        )
        guardar_analisis(
            _analisis_ejemplo(tema="Recetas de cocina", turn_id="t3", resumen="pasta al pesto"),
            coleccion=self.coleccion,
        )
        resultados = buscar_por_tema("Índices MongoDB", coleccion=self.coleccion)
        turn_ids = {r["turn_id"] for r in resultados}
        self.assertIn("t1", turn_ids)
        self.assertIn("t2", turn_ids)
        self.assertNotIn("t3", turn_ids)


if __name__ == "__main__":
    unittest.main()
