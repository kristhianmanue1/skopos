"""Tests para skopos.cli (SPEC-004), contra Mongo local real.

Mismo patrón que test_almacenamiento.py: se salta si no hay Mongo local.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymongo

from skopos.almacenamiento import coleccion_local, guardar_analisis
from skopos.analisis import Analisis
from skopos.cli import query

DB_DE_PRUEBA = "skopos_test_cli"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).admin.command("ping")
        return True
    except Exception:
        return False


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class QueryTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rollout = Path(self.tmp.name) / "rollout-test.jsonl"
        contenido = "contenido completo del turno original, con un cierre real\n"
        self.rollout.write_text(contenido, encoding="utf-8")

    def test_tema_con_resultados_incluye_fragmento_completo(self):
        guardar_analisis(
            Analisis(
                tema="bases de datos",
                resumen="explica MongoDB",
                turn_id="t1",
                session_id="s1",
                ruta_origen=str(self.rollout),
                offset_inicio=0,
                offset_fin=len("contenido completo"),
            ),
            coleccion=self.coleccion,
        )
        salida = query("bases de datos", coleccion=self.coleccion)
        self.assertEqual(len(salida["resultados"]), 1)
        resultado = salida["resultados"][0]
        self.assertEqual(resultado["turn_id"], "t1")
        self.assertEqual(resultado["fragmento_completo"], "contenido completo")

    def test_tema_sin_resultados_devuelve_lista_vacia(self):
        salida = query("tema que no existe", coleccion=self.coleccion)
        self.assertEqual(salida, {"resultados": []})

    def test_ruta_origen_inexistente_devuelve_fragmento_none_sin_fallar(self):
        guardar_analisis(
            Analisis(
                tema="x",
                resumen="y",
                turn_id="t2",
                session_id="s1",
                ruta_origen="/no/existe/rollout.jsonl",
                offset_inicio=0,
                offset_fin=10,
            ),
            coleccion=self.coleccion,
        )
        salida = query("x", coleccion=self.coleccion)
        self.assertIsNone(salida["resultados"][0]["fragmento_completo"])


if __name__ == "__main__":
    unittest.main()
