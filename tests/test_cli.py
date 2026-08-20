"""Tests para skopos.cli (SPEC-004), contra Mongo local real.

Mismo patrón que test_almacenamiento.py: se salta si no hay Mongo local.
"""

from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import pymongo

from skopos.almacenamiento import coleccion_local, guardar_analisis
from skopos.analisis import Analisis
from skopos.cli import query, query_command

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
                cli="codex-cli", modelo_analisis="test-modelo",
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
                cli="codex-cli", modelo_analisis="test-modelo",
            ),
            coleccion=self.coleccion,
        )
        salida = query("x", coleccion=self.coleccion)
        self.assertIsNone(salida["resultados"][0]["fragmento_completo"])

    def test_filtro_proyecto_deja_solo_los_de_ese_proyecto(self):
        # C-9: dos documentos con el mismo tema, proyectos distintos
        for turn_id, proyecto in (("t3", "skopos"), ("t4", "ektel")):
            guardar_analisis(
                Analisis(
                    tema="arquitectura de memoria",
                    resumen="resumen sobre memoria",
                    turn_id=turn_id,
                    session_id="s1",
                    ruta_origen="/no/existe/rollout.jsonl",
                    offset_inicio=0,
                    offset_fin=10,
                    cli="codex-cli", modelo_analisis="test-modelo",
                    proyecto=proyecto,
                ),
                coleccion=self.coleccion,
            )
        salida = query(
            "arquitectura de memoria", coleccion=self.coleccion, proyecto="skopos"
        )
        self.assertEqual([r["turn_id"] for r in salida["resultados"]], ["t3"])
        self.assertEqual(salida["resultados"][0]["proyecto"], "skopos")

    def test_filtro_proyecto_excluye_documentos_sin_proyecto(self):
        # pre-C-9 / desconocido: sin el campo, fuera del filtro — nunca
        # se inventa una coincidencia para ellos
        guardar_analisis(
            Analisis(
                tema="arquitectura de memoria",
                resumen="documento legado sin eje de proyecto",
                turn_id="t5",
                session_id="s1",
                ruta_origen="/no/existe/rollout.jsonl",
                offset_inicio=0,
                offset_fin=10,
                cli="codex-cli", modelo_analisis="test-modelo",
            ),
            coleccion=self.coleccion,
        )
        salida = query(
            "arquitectura de memoria", coleccion=self.coleccion, proyecto="skopos"
        )
        self.assertEqual(salida, {"resultados": []})

    def test_sin_filtro_devuelve_documentos_con_y_sin_proyecto(self):
        for turn_id, proyecto in (("t6", "skopos"), ("t7", None)):
            guardar_analisis(
                Analisis(
                    tema="consultas federadas",
                    resumen="sobre consultas federadas",
                    turn_id=turn_id,
                    session_id="s1",
                    ruta_origen="/no/existe/rollout.jsonl",
                    offset_inicio=0,
                    offset_fin=10,
                    cli="codex-cli", modelo_analisis="test-modelo",
                    proyecto=proyecto,
                ),
                coleccion=self.coleccion,
            )
        salida = query("consultas federadas", coleccion=self.coleccion)
        self.assertEqual(len(salida["resultados"]), 2)

    def test_coleccion_local_crea_indices_de_eje(self):
        # H3 (ronda adversarial de Fase 1): los índices de proyecto/cli/
        # ocurrido_en no quedan sin cobertura
        nombres = {i["name"] for i in self.coleccion.list_indexes()}
        self.assertIn("proyecto_1", nombres)
        self.assertIn("cli_1", nombres)
        self.assertIn("ocurrido_en_1", nombres)
        self.assertIn("turn_id_1", nombres)

    def test_query_command_con_flag_proyecto_filtra(self):
        # H5: el cableado argparse del flag, no sólo la función query.
        # query_command conecta solo a la DB por defecto: se parchea el
        # punto de conexión hacia la colección de prueba.
        guardar_analisis(
            Analisis(
                tema="arquitectura de memoria",
                resumen="resumen sobre memoria",
                turn_id="t8",
                session_id="s1",
                ruta_origen="/no/existe/rollout.jsonl",
                offset_inicio=0,
                offset_fin=10,
                cli="codex-cli", modelo_analisis="test-modelo",
                proyecto="skopos",
            ),
            coleccion=self.coleccion,
        )
        import json as _json

        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = query_command(
                    ["arquitectura de memoria", "--proyecto", "skopos"]
                )
        self.assertEqual(exit_code, 0)
        salida = _json.loads(buffer.getvalue())
        self.assertEqual([r["turn_id"] for r in salida["resultados"]], ["t8"])


if __name__ == "__main__":
    unittest.main()
