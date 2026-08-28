"""Tests del adaptador parser-claude-code/v1 (fase B de P-003).

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skopos import claude_code
from skopos.parseo import parsear


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _base(**extra) -> dict:
    evento = {
        "sessionId": "s-1",
        "uuid": extra.pop("uuid", "u-x"),
        "version": "2.1.231",
        "isSidechain": False,
        "userType": "external",
        "entrypoint": "cli",
        "cwd": str(Path.home() / "www" / "skopos"),
        "timestamp": "2026-08-28T10:00:00.000Z",
    }
    evento.update(extra)
    return evento


def _usuario(texto: str, uuid: str = "u-1", **extra) -> dict:
    return _base(uuid=uuid, type="user",
                 message={"role": "user", "content": texto}, **extra)


def _agente(texto: str, uuid: str = "a-1") -> dict:
    return _base(uuid=uuid, type="assistant",
                 message={"role": "assistant", "content": [{"type": "text", "text": texto}]})


def _tool_result(uuid: str = "tr-1") -> dict:
    # en este formato los resultados de herramienta vuelven como `user`
    return _base(uuid=uuid, type="user",
                 message={"role": "user",
                          "content": [{"type": "tool_result", "content": "salida"}]})


class _ConTranscripcion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "sesion-abc.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text("\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8")


class IdentidadTests(_ConTranscripcion):
    def test_transcripcion_de_claude_code_se_detecta(self):
        self._escribir([_usuario("hola"), _agente("qué tal"), _usuario("otra", uuid="u-2")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.cli_producto, "claude-code")
        self.assertEqual(r.version_formato, "claude-code-transcript/v1")
        self.assertEqual(r.version_cli_observada, "2.1.231")

    def test_sin_las_marcas_del_harness_no_casa(self):
        self._escribir([{"sessionId": "s", "uuid": "u", "version": "2.1.231"}])
        self.assertEqual(parsear(self.path).diagnostico, "formato_desconocido")

    def test_un_rollout_de_codex_no_lo_reclama_este_adaptador(self):
        self._escribir([
            {"type": "session_meta", "payload": {"originator": "codex-tui"}},
            {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "t1"}},
        ])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.cli_producto, "codex-cli")  # ni ambigüedad ni robo de identidad


class ExtraccionTests(_ConTranscripcion):
    def test_el_turno_va_de_un_mensaje_de_usuario_al_siguiente(self):
        self._escribir([
            _usuario("primera pregunta", uuid="u-1"),
            _agente("primera respuesta"),
            _usuario("segunda pregunta", uuid="u-2"),
            _agente("segunda respuesta", uuid="a-2"),
            _usuario("tercera", uuid="u-3"),
        ])
        turnos = parsear(self.path).turnos
        # el tercero queda abierto: sin marca de fin, sólo lo cierra el siguiente
        self.assertEqual([t.turn_id for t in turnos],
                         ["claude-code:u-1", "claude-code:u-2"])
        self.assertEqual(turnos[0].texto_usuario, "primera pregunta")
        self.assertEqual(turnos[0].texto_agente, "primera respuesta")

    def test_los_tool_result_no_abren_turno_ni_ensucian_el_texto(self):
        # son el 90 % de los eventos `user` del corpus real: tratarlos
        # como voz del usuario multiplicaría los turnos por nueve
        self._escribir([
            _usuario("haz algo", uuid="u-1"),
            _agente("voy"),
            _tool_result(),
            _tool_result("tr-2"),
            _agente("hecho", uuid="a-2"),
            _usuario("gracias", uuid="u-2"),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual([t.turn_id for t in turnos], ["claude-code:u-1"])
        self.assertEqual(turnos[0].texto_usuario, "haz algo")
        self.assertNotIn("salida", turnos[0].texto_agente)

    def test_sidechain_y_meta_se_excluyen(self):
        self._escribir([
            _usuario("real", uuid="u-1"),
            _usuario("de subagente", uuid="u-side", isSidechain=True),
            _usuario("meta del harness", uuid="u-meta", isMeta=True),
            _usuario("cierra", uuid="u-2"),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual([t.turn_id for t in turnos], ["claude-code:u-1"])
        self.assertEqual(turnos[0].texto_usuario, "real")

    def test_identidad_calificada_por_defecto(self):
        # ADR-010 §7: el id crudo es la excepción que Codex se ganó con
        # evidencia; todo adaptador nuevo califica
        self._escribir([_usuario("uno", uuid="u-1"), _usuario("dos", uuid="u-2")])
        self.assertTrue(parsear(self.path).turnos[0].turn_id.startswith("claude-code:"))

    def test_proyecto_sale_del_cwd_con_la_regla_de_c9(self):
        self._escribir([
            _usuario("uno", uuid="u-1", cwd=str(Path.home() / "www" / "skopos")),
            _usuario("dos", uuid="u-2", cwd=str(Path.home())),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual(turnos[0].proyecto, "skopos")

    def test_cwd_sin_significado_deja_el_proyecto_ausente(self):
        self._escribir([
            _usuario("uno", uuid="u-1", cwd=str(Path.home())),
            _usuario("dos", uuid="u-2"),
        ])
        self.assertIsNone(parsear(self.path).turnos[0].proyecto)

    def test_el_fragmento_sellado_cubre_el_rango_del_turno(self):
        self._escribir([
            _usuario("uno", uuid="u-1"), _agente("respuesta"),
            _usuario("dos", uuid="u-2"),
        ])
        import hashlib

        turno = parsear(self.path).turnos[0]
        crudo = self.path.read_bytes()[turno.offset_inicio : turno.offset_fin]
        self.assertEqual(turno.fragmento_sha256, hashlib.sha256(crudo).hexdigest())
        self.assertIn(b"respuesta", crudo)

    def test_sesion_sin_segundo_mensaje_no_produce_turnos(self):
        self._escribir([_usuario("sigo escribiendo", uuid="u-1"), _agente("ok")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.turnos, [])
        self.assertEqual(r.detalle.codigo, "identidad_reconocida_sin_cierres")

    def test_eventos_aditivos_se_cuentan_sin_cambiar_el_diagnostico(self):
        self._escribir([
            _usuario("uno", uuid="u-1"),
            _base(uuid="x-1", type="pr-link"),
            _base(uuid="x-2", type="ai-title"),
            _usuario("dos", uuid="u-2"),
        ])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.eventos_no_reconocidos, 2)


class LecturaIncrementalTests(_ConTranscripcion):
    def test_el_cursor_produce_los_mismos_turnos_que_la_lectura_completa(self):
        from skopos.cursor import Cursor
        from skopos.parseo import sellar_prefijo

        self._escribir([_usuario("uno", uuid="u-1"), _agente("r1"),
                        _usuario("dos", uuid="u-2")])
        completo = parsear(self.path)
        offset = completo.turnos[-1].offset_fin
        cursor = Cursor(offset, sellar_prefijo(completo.instantanea, offset))

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_linea(_agente("r2", uuid="a-2")) + "\n")
            handle.write(_linea(_usuario("tres", uuid="u-3")) + "\n")

        incremental = parsear(self.path, cursor=cursor)
        self.assertTrue(incremental.incremental)
        nuevos = [t for t in parsear(self.path).turnos if t.turn_id == "claude-code:u-2"]
        self.assertEqual(incremental.turnos, nuevos)


if __name__ == "__main__":
    unittest.main()
