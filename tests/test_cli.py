"""Tests para skopos.cli (SPEC-004), contra Mongo local real.

Mismo patrón que test_almacenamiento.py: se salta si no hay Mongo local.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

import pymongo

from skopos.almacenamiento import (
    coleccion_local,
    guardar_analisis,
    superseder_documento,
    version_vigente,
)
from skopos.analisis import Analisis
from skopos.cli import query, query_command, reanalizar_command

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
        self.assertEqual(salida, {"resultados": [], "excluidos": {"por_limite": 0}})

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
        self.assertEqual(salida["resultados"], [])
        self.assertEqual(salida["excluidos"], {"por_limite": 0})

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
        # H3 (ronda adversarial de Fase 1) + ADR-007 v2: el índice único
        # es el compuesto (turn_id, version); el simple ya no existe
        nombres = {i["name"] for i in self.coleccion.list_indexes()}
        self.assertIn("proyecto_1", nombres)
        self.assertIn("cli_1", nombres)
        self.assertIn("ocurrido_en_1", nombres)
        self.assertIn("turn_id_1_version_1", nombres)
        self.assertNotIn("turn_id_1", nombres)

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


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class FragmentoSelladoTests(unittest.TestCase):
    """ADR-009 (P4a+P5, decisión 9 🔒 2026-08-20): servido sellado,
    acotado y con señal de exclusión. Cierre de Y-5."""

    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rollout = Path(self.tmp.name) / "rollout-sellado.jsonl"

    def _guardar(self, *, contenido: bytes, sha256: str | None, turn_id="s1",
                 tema="tema sellado", **extra):
        self.rollout.write_bytes(contenido)
        guardar_analisis(
            Analisis(
                tema=tema,
                resumen="resumen del tema sellado",
                turn_id=turn_id,
                session_id="s",
                ruta_origen=str(self.rollout),
                offset_inicio=extra.pop("offset_inicio", 0),
                offset_fin=extra.pop("offset_fin", len(contenido)),
                cli="codex-cli", modelo_analisis="test-modelo",
                fragmento_sha256=sha256,
            ),
            coleccion=self.coleccion,
        )

    def _resultado(self, tema="tema sellado", **kwargs):
        salida = query(tema, coleccion=self.coleccion, **kwargs)
        self.assertEqual(len(salida["resultados"]), 1)
        return salida["resultados"][0]

    def test_integro_sirve_texto_verificado(self):
        contenido = b"contenido completo y verificado del turno\n"
        self._guardar(
            contenido=contenido,
            sha256=hashlib.sha256(contenido).hexdigest(),
        )
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "integro")
        self.assertTrue(r["sellado"])
        self.assertEqual(r["fragmento_completo"], contenido.decode())

    def test_edicion_del_origen_da_integridad_fallida_y_null(self):
        # Y-5 cerrado: nunca bytes de otro turno en silencio
        contenido = b"texto original del turno\n"
        self._guardar(contenido=contenido, sha256=hashlib.sha256(contenido).hexdigest())
        self.rollout.write_bytes(b"texto EDITADO del turno\n")  # misma longitud
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "integridad_fallida")
        self.assertIsNone(r["fragmento_completo"])

    def test_lectura_corta_da_integridad_fallida(self):
        # ronda 6 R6-3: seek fuera de EOF no falla — sin chequeo de
        # longitud esto se serviría parcial/vacío en silencio
        contenido = b"texto que luego se trunca\n"
        self._guardar(contenido=contenido, sha256=hashlib.sha256(contenido).hexdigest())
        self.rollout.write_bytes(b"texto que luego se ")  # truncado
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "integridad_fallida")
        self.assertIsNone(r["fragmento_completo"])

    def test_origen_perdido_se_declara_sin_fallar_la_consulta(self):
        self._guardar(contenido=b"x" * 100, sha256=hashlib.sha256(b"x" * 100).hexdigest())
        self.rollout.unlink()
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "origen_perdido")
        self.assertIsNone(r["fragmento_completo"])

    def test_legado_sin_sello_se_sirve_con_chequeo_de_longitud(self):
        contenido = b"documento legado pre-ADR-009\n"
        self._guardar(contenido=contenido, sha256=None)
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "integro")
        self.assertFalse(r["sellado"])
        # y si el legado queda truncado, también se detecta (mínimo Y-5)
        self.rollout.write_bytes(contenido[:10])
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "integridad_fallida")

    def test_fragmento_grande_se_sirve_truncado_con_marcador(self):
        from skopos.cli import TOPE_FRAGMENTO_BYTES, MARCADOR_TRUNCADO

        contenido = b"a" * (TOPE_FRAGMENTO_BYTES + 1000)
        self._guardar(contenido=contenido, sha256=hashlib.sha256(contenido).hexdigest())
        r = self._resultado()
        self.assertEqual(r["fragmento_estado"], "truncado")
        self.assertTrue(r["sellado"])
        marcador = MARCADOR_TRUNCADO.format(
            servidos=TOPE_FRAGMENTO_BYTES, total=len(contenido)
        )
        self.assertTrue(r["fragmento_completo"].endswith(marcador))

    def test_max_acota_y_declara_el_excedente(self):
        # P5: presupuesto + señal de exclusión (P-001 C-4)
        contenido = b"x" * 50
        sha = hashlib.sha256(contenido).hexdigest()
        for i in range(3):
            guardar_analisis(
                Analisis(
                    tema="presupuesto consultable",
                    resumen=f"resultado numero {i}",
                    turn_id=f"p{i}",
                    session_id="s",
                    ruta_origen=str(self.rollout),
                    offset_inicio=0,
                    offset_fin=len(contenido),
                    cli="codex-cli", modelo_analisis="test-modelo",
                    fragmento_sha256=sha,
                ),
                coleccion=self.coleccion,
            )
        salida = query("presupuesto", coleccion=self.coleccion, max_resultados=2)
        self.assertEqual(len(salida["resultados"]), 2)
        self.assertEqual(salida["excluidos"], {"por_limite": 1})
        # sin recorte: excluidos en cero, no ausente
        salida = query("presupuesto", coleccion=self.coleccion, max_resultados=20)
        self.assertEqual(salida["excluidos"], {"por_limite": 0})

    def test_rango_invalido_en_documento_da_integridad_fallida_sin_traza(self):
        # ronda 8, H2: offsets corruptos (fin < inicio) no revientan la
        # consulta con ValueError — se declara integridad_fallida
        guardar_analisis(
            Analisis(
                tema="rango corrupto",
                resumen="offsets imposibles",
                turn_id="corrupto",
                session_id="s",
                ruta_origen=str(self.rollout),
                offset_inicio=100,
                offset_fin=10,
                cli="codex-cli", modelo_analisis="test-modelo",
            ),
            coleccion=self.coleccion,
        )
        r = self._resultado(tema="rango corrupto")
        self.assertEqual(r["fragmento_estado"], "integridad_fallida")
        self.assertIsNone(r["fragmento_completo"])

    def test_max_cableado_por_argparse(self):
        # ronda 8, H7: el flag --max llega por query_command, y un
        # negativo se rechaza en el borde (H1)
        import json as _json

        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = query_command(["tema sellado", "--max", "0"])
            self.assertEqual(exit_code, 0)
            salida = _json.loads(buffer.getvalue())
            self.assertEqual(salida["resultados"], [])
            self.assertEqual(salida["excluidos"], {"por_limite": 0})

            stderr = StringIO()
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    query_command(["tema sellado", "--max", "-1"])


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class ReanalizarTests(unittest.TestCase):
    """`skopos reanalizar` (SPEC-003 v2 / ADR-007): supersede explícito."""

    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

    def _guardar(self, turn_id="r1", tema="arquitectura de memoria", **extra):
        guardar_analisis(
            Analisis(
                tema=tema,
                resumen=extra.pop("resumen", "resumen sobre memoria"),
                turn_id=turn_id,
                session_id="s1",
                ruta_origen="/no/existe/rollout.jsonl",
                offset_inicio=0,
                offset_fin=10,
                cli="codex-cli", modelo_analisis="test-modelo",
                **extra,
            ),
            coleccion=self.coleccion,
        )

    def test_solo_redaccion_inserta_version_redactada(self):
        # necesidad 2 del ADR-007: un secreto en claro (guardado aquí a
        # propósito, saltándose la redacción del análisis) se redacta en
        # una versión nueva; la vieja queda como auditoría
        self._guardar(tema="deploy con sk-AAAABBBBCCCCDDDDEEEE")
        buffer, codigo = StringIO(), None
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with redirect_stdout(buffer):
                codigo = reanalizar_command(["r1", "--solo-redaccion"])
        self.assertEqual(codigo, 0)
        vigente = version_vigente("r1", coleccion=self.coleccion)
        self.assertEqual(vigente["version"], 2)
        self.assertNotIn("sk-AAAABBBBCCCCDDDDEEEE", vigente["tema"])
        self.assertIn("[REDACTADO]", vigente["tema"])
        # y query sirve sólo la redactada
        salida = query("deploy", coleccion=self.coleccion)
        self.assertNotIn("sk-AAAABBBBCCCCDDDDEEEE", salida["resultados"][0]["tema"])

    def test_solo_redaccion_sin_cambios_no_inserta_version(self):
        self._guardar(turn_id="r2", tema="tema limpio")
        buffer = StringIO()
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with redirect_stdout(buffer):
                codigo = reanalizar_command(["r2", "--solo-redaccion"])
        self.assertEqual(codigo, 0)
        self.assertIn('"cambiado": false', buffer.getvalue())
        self.assertEqual(version_vigente("r2", coleccion=self.coleccion)["version"], 1)

    def test_turn_id_inexistente_falla_con_mensaje_claro(self):
        stderr = StringIO()
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with redirect_stderr(stderr):
                codigo = reanalizar_command(["no-existe"])
        self.assertEqual(codigo, 1)
        self.assertIn("no hay versión guardada", stderr.getvalue())

    def test_rollout_que_ya_no_se_identifica_no_supersede_a_ciegas(self):
        # ADR-010 §4 + lección Y-5: si el archivo de origen ya no casa
        # con ningún parser (rotado, sustituido), el supersede se detiene
        # con el diagnóstico a la vista, nunca reparsea "por parecido".
        rollout = Path(self.id().replace(".", "_") + ".jsonl")
        self.addCleanup(rollout.unlink, missing_ok=True)
        contenido = '{"type":"algo-de-otro-formato","payload":{}}\n'
        rollout.write_text(contenido, encoding="utf-8")
        guardar_analisis(
            Analisis(
                tema="viejo",
                resumen="analisis original",
                turn_id="r9",
                session_id=rollout.stem,
                ruta_origen=str(rollout),
                offset_inicio=0,
                offset_fin=len(contenido),
                cli="codex-cli", modelo_analisis="test-modelo",
            ),
            coleccion=self.coleccion,
        )
        stderr = StringIO()
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with redirect_stderr(stderr):
                codigo = reanalizar_command(["r9"])
        self.assertEqual(codigo, 1)
        self.assertIn("formato_desconocido", stderr.getvalue())
        # y la versión guardada sigue intacta
        self.assertEqual(version_vigente("r9", coleccion=self.coleccion)["tema"], "viejo")

    def test_reanalisis_completo_reextrae_y_supersede(self):
        # modo completo: re-extrae el turno del rollout real y re-analiza
        # (Ollama mockeado); fallo explícito si el rollout ya no sirve
        rollout = Path(self.id().replace(".", "_") + ".jsonl")
        self.addCleanup(rollout.unlink, missing_ok=True)
        contenido = (
            # identidad Codex: la re-lectura pasa por la frontera de
            # SPEC-006, que rechaza lo que no se identifica (ADR-010 §4)
            '{"type":"session_meta","payload":{"originator":"codex-tui"}}\n'
            '{"type":"response_item","payload":{"type":"message","role":"user",'
            '"content":[{"type":"input_text","text":"hola"}]}}\n'
            '{"type":"event_msg","payload":{"type":"task_complete","turn_id":"r3"}}\n'
        )
        rollout.write_text(contenido, encoding="utf-8")
        guardar_analisis(
            Analisis(
                tema="viejo",
                resumen="analisis original",
                turn_id="r3",
                session_id=rollout.stem,
                ruta_origen=str(rollout),
                offset_inicio=0,
                offset_fin=len(contenido),
                cli="codex-cli", modelo_analisis="test-modelo",
            ),
            coleccion=self.coleccion,
        )
        from skopos.analisis import Analisis as _Analisis

        analisis_nuevo = _Analisis(
            tema="nuevo",
            resumen="reanalizado",
            turn_id="r3",
            session_id=rollout.stem,
            ruta_origen=str(rollout),
            offset_inicio=0,
            offset_fin=len(contenido),
            cli="codex-cli", modelo_analisis="test-modelo",
            fragmento_sha256=hashlib.sha256(contenido.encode()).hexdigest(),
        )
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with mock.patch("skopos.cli.analizar_turno", return_value=analisis_nuevo):
                buffer = StringIO()
                with redirect_stdout(buffer):
                    codigo = reanalizar_command(["r3"])
        self.assertEqual(codigo, 0)
        vigente = version_vigente("r3", coleccion=self.coleccion)
        self.assertEqual(vigente["version"], 2)
        self.assertEqual(vigente["tema"], "nuevo")
        # el supersede asienta el sello recomputado (ronda 8, H7)
        self.assertEqual(
            vigente.get("fragmento_sha256"),
            hashlib.sha256(contenido.encode()).hexdigest(),
        )

    def test_reanalisis_completo_con_rollout_perdido_falla_explicito(self):
        # lección Y-5: nunca supersede a ciegas desde una referencia rota
        self._guardar(turn_id="r4", tema="huérfano")
        stderr = StringIO()
        with mock.patch("skopos.cli.coleccion_local", return_value=self.coleccion):
            with redirect_stderr(stderr):
                codigo = reanalizar_command(["r4"])
        self.assertEqual(codigo, 1)
        self.assertIn("no se puede releer", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
