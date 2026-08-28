"""Tests del adaptador parser-cline/v1 — primer origen que no es JSONL.

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from skopos.parseo import parsear


def _mensaje(rol: str, texto: str, identificador: str, ts: int = 1776790935897) -> dict:
    return {
        "id": identificador,
        "role": rol,
        "ts": ts,
        "content": [{"type": "text", "text": texto}],
    }


class _ConSesion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "s-1.messages.json"

    def _escribir(self, mensajes: list[dict], **raiz) -> None:
        documento = {
            "version": 1,
            "updated_at": "2026-08-28T10:00:00.000Z",
            "agent": "lead",
            "sessionId": "s-1",
            "messages": mensajes,
        }
        documento.update(raiz)
        # pretty-printed, como los archivos reales
        self.path.write_text(json.dumps(documento, indent=2, ensure_ascii=False), encoding="utf-8")


class IdentidadTests(_ConSesion):
    def test_sesion_de_cline_se_detecta(self):
        self._escribir([_mensaje("user", "hola", "m1"), _mensaje("user", "adios", "m2")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.cli_producto, "cline")
        self.assertEqual(r.version_formato, "cline-messages/v1")

    def test_un_jsonl_no_lo_reclama_este_adaptador(self):
        # la primera linea de un JSONL es un objeto COMPLETO; aqui es la
        # apertura de uno repartido en varias lineas
        self.path.write_text(
            json.dumps({"sessionId": "s", "messages": [], "uuid": "u", "version": "2.1.231",
                        "userType": "external"}) + "\n",
            encoding="utf-8",
        )
        self.assertNotEqual(parsear(self.path).cli_producto, "cline")

    def test_version_de_formato_desconocida_es_version_no_soportada(self):
        # primer adaptador con predicado POSITIVO de incompatibilidad:
        # el archivo declara la version de su propio esquema
        self._escribir([_mensaje("user", "hola", "m1")], version=99)
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "version_no_soportada")
        self.assertEqual(r.cli_producto, "cline")
        self.assertEqual(r.turnos, [])


class ExtraccionTests(_ConSesion):
    def test_offsets_y_sello_son_bytes_reales_del_archivo(self):
        # el contrato exige offsets sobre los bytes crudos aunque el
        # origen no tenga lineas (ADR-010 §5)
        self._escribir([
            _mensaje("user", "pregunta", "m1"),
            _mensaje("assistant", "respuesta", "m2"),
            _mensaje("user", "cierra", "m3"),
        ])
        turno = parsear(self.path).turnos[0]
        crudo = self.path.read_bytes()[turno.offset_inicio : turno.offset_fin]
        self.assertEqual(turno.fragmento_sha256, hashlib.sha256(crudo).hexdigest())
        self.assertIn(b"pregunta", crudo)
        self.assertIn(b"respuesta", crudo)
        self.assertNotIn(b"cierra", crudo)

    def test_los_tool_result_no_abren_turno(self):
        self._escribir([
            _mensaje("user", "haz algo", "m1"),
            {"id": "m2", "role": "assistant", "ts": 1776790935897,
             "content": [{"type": "tool_use", "name": "bash"}]},
            {"id": "m3", "role": "user", "ts": 1776790935897,
             "content": [{"type": "tool_result", "content": "salida"}]},
            _mensaje("user", "gracias", "m4"),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual([t.turn_id for t in turnos], ["cline:m1"])
        self.assertEqual(turnos[0].texto_usuario, "haz algo")

    def test_el_pensamiento_del_modelo_no_es_conversacion(self):
        self._escribir([
            _mensaje("user", "pregunta", "m1"),
            {"id": "m2", "role": "assistant", "ts": 1776790935897,
             "content": [{"type": "thinking", "thinking": "razonando en privado"},
                         {"type": "text", "text": "respuesta"}]},
            _mensaje("user", "cierra", "m3"),
        ])
        turno = parsear(self.path).turnos[0]
        self.assertEqual(turno.texto_agente, "respuesta")

    def test_timestamp_epoch_se_sirve_en_iso_para_adr_008(self):
        # sin convertir, el corte "desde ahora" lo trataria como
        # historico y ningun turno de cline entraria jamas
        from skopos.orquestador import _parsear_timestamp

        self._escribir([_mensaje("user", "uno", "m1"), _mensaje("user", "dos", "m2")])
        turno = parsear(self.path).turnos[0]
        momento = _parsear_timestamp(turno.timestamp_cierre)
        self.assertIsNotNone(momento)
        self.assertIsNotNone(momento.tzinfo)

    def test_identidad_calificada(self):
        self._escribir([_mensaje("user", "uno", "m1"), _mensaje("user", "dos", "m2")])
        self.assertEqual(parsear(self.path).turnos[0].turn_id, "cline:m1")

    def test_sesion_de_subagente_no_produce_turnos(self):
        self._escribir([_mensaje("user", "uno", "m1"), _mensaje("user", "dos", "m2")],
                       agent="subagent")
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.turnos, [])

    def test_sesion_con_un_solo_mensaje_no_cierra_turno(self):
        self._escribir([_mensaje("user", "sigo escribiendo", "m1")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.turnos, [])
        self.assertEqual(r.detalle.codigo, "identidad_reconocida_sin_cierres")


if __name__ == "__main__":
    unittest.main()
