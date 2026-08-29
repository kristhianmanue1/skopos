"""Tests del adaptador parser-opencode/v1 — primer origen de FILAS (ADR-012).

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from skopos.captura import ORIGEN_ARCHIVO, ORIGEN_FILAS
from skopos.opencode import _canonico
from skopos.parseo import parsear


def _base(path: Path, mensajes: list[tuple], directorio="/Users/x/www/skopos",
          version="1.17.7") -> None:
    """Crea una base con la forma mínima de opencode."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE session (id TEXT, directory TEXT, version TEXT)")
    con.execute("CREATE TABLE message (id TEXT, session_id TEXT, time_created INT, data TEXT)")
    con.execute("CREATE TABLE part (id TEXT, message_id TEXT, session_id TEXT, "
                "time_created INT, data TEXT)")
    con.execute("INSERT INTO session VALUES (?,?,?)", ("ses_1", directorio, version))
    for orden, (mid, rol, texto, tipo) in enumerate(mensajes):
        con.execute("INSERT INTO message VALUES (?,?,?,?)",
                    (mid, "ses_1", 1781578629062 + orden, json.dumps({"role": rol})))
        con.execute("INSERT INTO part VALUES (?,?,?,?,?)",
                    (f"prt_{mid}", mid, "ses_1", 1781578629062 + orden,
                     json.dumps({"type": tipo, "text": texto})))
    con.commit()
    con.close()


class _ConBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "opencode.db"


class IdentidadTests(_ConBase):
    def test_una_base_de_opencode_se_detecta_sin_materializarla(self):
        _base(self.path, [("msg_1", "user", "hola", "text"),
                          ("msg_2", "user", "adios", "text")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.cli_producto, "opencode")
        self.assertEqual(r.version_formato, "opencode-sqlite/v1")
        self.assertEqual(r.version_cli_observada, "1.17.7")

    def test_otra_base_sqlite_no_casa(self):
        # sin las tablas de opencode ninguna ficha de filas la reclama, y
        # cae al camino de archivo: un binario no decodifica como UTF-8,
        # y eso el contrato lo llama `entrada_corrupta` (ADR-010 §3:
        # "decodificación imposible"), no `formato_desconocido`. Es
        # observable y atribuible, que es lo que el contrato exige.
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE cosas (id TEXT)")
        con.commit(); con.close()
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "entrada_corrupta")
        self.assertIsNone(r.cli_producto)  # nadie la reclamó

    def test_un_jsonl_sigue_yendo_por_el_camino_de_archivo(self):
        jsonl = Path(self.tmp.name) / "rollout-x.jsonl"
        jsonl.write_text(
            json.dumps({"type": "session_meta", "payload": {"originator": "codex-tui"}}) + "\n"
            + json.dumps({"type": "event_msg",
                          "payload": {"type": "task_complete", "turn_id": "t1"}}) + "\n",
            encoding="utf-8")
        r = parsear(jsonl)
        self.assertEqual(r.cli_producto, "codex-cli")
        self.assertEqual(r.turnos[0].origen_tipo, ORIGEN_ARCHIVO)


class ExtraccionTests(_ConBase):
    def test_el_turno_va_de_un_usuario_al_siguiente(self):
        _base(self.path, [
            ("msg_1", "user", "pregunta", "text"),
            ("msg_2", "assistant", "respuesta", "text"),
            ("msg_3", "user", "otra", "text"),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual([t.turn_id for t in turnos], ["opencode:msg_1"])
        self.assertEqual(turnos[0].texto_usuario, "pregunta")
        self.assertEqual(turnos[0].texto_agente, "respuesta")

    def test_el_razonamiento_no_es_conversacion(self):
        _base(self.path, [
            ("msg_1", "user", "pregunta", "text"),
            ("msg_2", "assistant", "pensando en privado", "reasoning"),
            ("msg_3", "assistant", "respuesta", "text"),
            ("msg_4", "user", "cierra", "text"),
        ])
        self.assertEqual(parsear(self.path).turnos[0].texto_agente, "respuesta")

    def test_el_turno_no_lleva_offsets_y_si_localizador_de_filas(self):
        # ADR-012: una fila no tiene rango de bytes estable; fingir uno
        # seria mentir en un campo que otros componentes usan para releer
        _base(self.path, [
            ("msg_1", "user", "pregunta", "text"),
            ("msg_2", "assistant", "respuesta", "text"),
            ("msg_3", "user", "cierra", "text"),
        ])
        turno = parsear(self.path).turnos[0]
        self.assertIsNone(turno.offset_inicio)
        self.assertIsNone(turno.offset_fin)
        self.assertEqual(turno.origen_tipo, ORIGEN_FILAS)
        self.assertEqual(turno.origen_tabla, "message")
        self.assertEqual(turno.origen_ids, ("msg_1", "msg_2"))

    def test_el_sello_se_reproduce_releyendo_las_filas(self):
        # el invariante del §5 sobrevive: todo turno es resoluble a bytes
        # sellados, aunque se direccione por ids en vez de por offsets
        _base(self.path, [("msg_1", "user", "pregunta", "text"),
                          ("msg_2", "user", "cierra", "text")])
        turno = parsear(self.path).turnos[0]
        filas = [{"id": "msg_1", "session_id": "ses_1", "data": {"role": "user"},
                  "parts": [{"type": "text", "text": "pregunta"}]}]
        self.assertEqual(turno.fragmento_sha256,
                         hashlib.sha256(_canonico(filas)).hexdigest())

    def test_un_turno_no_cruza_de_sesion(self):
        _base(self.path, [("msg_1", "user", "en la sesion 1", "text")])
        con = sqlite3.connect(self.path)
        con.execute("INSERT INTO session VALUES (?,?,?)", ("ses_2", "/Users/x/www/otro", "1.17.7"))
        con.execute("INSERT INTO message VALUES (?,?,?,?)",
                    ("msg_9", "ses_2", 1781578639062, json.dumps({"role": "user"})))
        con.execute("INSERT INTO part VALUES (?,?,?,?,?)",
                    ("prt_9", "msg_9", "ses_2", 1781578639062,
                     json.dumps({"type": "text", "text": "en la sesion 2"})))
        con.commit(); con.close()
        turnos = parsear(self.path).turnos
        # el de la sesion 1 cierra al cambiar de sesion; el de la 2 queda abierto
        self.assertEqual([t.turn_id for t in turnos], ["opencode:msg_1"])
        self.assertEqual(turnos[0].session_id, "ses_1")

    def test_proyecto_del_directorio_con_la_regla_c9(self):
        _base(self.path, [("msg_1", "user", "uno", "text"),
                          ("msg_2", "user", "dos", "text")],
              directorio=str(Path.home() / "www" / "skopos"))
        self.assertEqual(parsear(self.path).turnos[0].proyecto, "skopos")

    def test_timestamp_epoch_se_sirve_en_iso_para_adr_008(self):
        from skopos.orquestador import _parsear_timestamp

        _base(self.path, [("msg_1", "user", "uno", "text"),
                          ("msg_2", "user", "dos", "text")])
        momento = _parsear_timestamp(parsear(self.path).turnos[0].timestamp_cierre)
        self.assertIsNotNone(momento)
        self.assertIsNotNone(momento.tzinfo)

    def test_base_sin_turnos_cerrados(self):
        _base(self.path, [("msg_1", "user", "sigo escribiendo", "text")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.turnos, [])
        self.assertEqual(r.detalle.codigo, "identidad_reconocida_sin_cierres")


if __name__ == "__main__":
    unittest.main()
