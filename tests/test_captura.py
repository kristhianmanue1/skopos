"""Tests para skopos.captura (SPEC-001). Runner: `python3 -m unittest`."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skopos.captura import extraer_turnos


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _mensaje(role: str, texto: str) -> dict:
    tipo_parte = "input_text" if role == "user" else "output_text"
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": role, "content": [{"type": tipo_parte, "text": texto}]},
    }


class ExtraerTurnosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text(
            "\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8"
        )

    def test_turno_simple_extrae_texto_real(self):
        self._escribir(
            [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "¿qué es MongoDB?"}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "developer",
                        "content": [
                            {"type": "input_text", "text": "instrucciones de sistema, no conversación"}
                        ],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": "Una base de datos documental."}
                        ],
                    },
                },
                {
                    "type": "event_msg",
                    "timestamp": "2026-08-12T00:00:00Z",
                    "payload": {"type": "task_complete", "turn_id": "t1"},
                },
            ]
        )
        turnos = extraer_turnos(self.path)
        self.assertEqual(len(turnos), 1)
        turno = turnos[0]
        self.assertEqual(turno.turn_id, "t1")
        self.assertEqual(turno.texto_usuario, "¿qué es MongoDB?")
        self.assertEqual(turno.texto_agente, "Una base de datos documental.")
        self.assertEqual(turno.session_id, "rollout-test")
        self.assertEqual(turno.timestamp_cierre, "2026-08-12T00:00:00Z")

    def test_turno_duplicado_no_se_repite(self):
        cierre = {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "t1"},
        }
        self._escribir(
            [
                _mensaje("user", "hola"),
                cierre,
                cierre,
            ]
        )
        turnos = extraer_turnos(self.path)
        self.assertEqual(len(turnos), 1)

    def test_linea_corrupta_no_detiene_el_procesamiento(self):
        self.path.write_text(
            "\n".join(
                [
                    "{esto no es json valido",
                    _linea(_mensaje("user", "hola")),
                    _linea(
                        {
                            "type": "event_msg",
                            "payload": {"type": "task_complete", "turn_id": "t1"},
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        turnos = extraer_turnos(self.path)
        self.assertEqual(len(turnos), 1)
        self.assertEqual(turnos[0].texto_usuario, "hola")

    def test_evento_sin_turn_id_se_ignora(self):
        self._escribir(
            [
                {"type": "event_msg", "payload": {"type": "task_complete"}},
                {"type": "event_msg", "payload": {"type": "task_started"}},
            ]
        )
        turnos = extraer_turnos(self.path)
        self.assertEqual(turnos, [])

    def test_offsets_permiten_recuperar_el_fragmento_de_origen(self):
        self._escribir(
            [
                _mensaje("user", "hola"),
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "t1"},
                },
            ]
        )
        turno = extraer_turnos(self.path)[0]
        contenido = self.path.read_bytes()
        fragmento = contenido[turno.offset_inicio : turno.offset_fin]
        self.assertIn(b"t1", fragmento)

    def test_sin_eventos_de_cierre_no_produce_turnos(self):
        self._escribir([_mensaje("user", "hola, nadie cierra")])
        self.assertEqual(extraer_turnos(self.path), [])

    def test_varios_mensajes_de_usuario_en_el_mismo_turno_se_acumulan(self):
        self._escribir(
            [
                _mensaje("user", "primera parte"),
                _mensaje("user", " segunda parte"),
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "t1"},
                },
            ]
        )
        turno = extraer_turnos(self.path)[0]
        self.assertEqual(turno.texto_usuario, "primera parte segunda parte")

    def test_contenido_tras_cierre_duplicado_no_se_filtra_al_siguiente_turno(self):
        cierre_t1 = {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "t1"},
        }
        self._escribir(
            [
                _mensaje("user", "turno uno"),
                cierre_t1,
                cierre_t1,  # duplicado, con contenido real después
                _mensaje("user", "contenido espurio tras el duplicado"),
                cierre_t1,  # sigue siendo duplicado, se descarta también
                _mensaje("user", "turno dos real"),
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "t2"},
                },
            ]
        )
        turnos = extraer_turnos(self.path)
        self.assertEqual(len(turnos), 2)
        self.assertEqual(turnos[0].texto_usuario, "turno uno")
        self.assertEqual(turnos[1].texto_usuario, "turno dos real")

    def test_rol_developer_se_excluye_de_la_conversacion(self):
        self._escribir(
            [
                _mensaje("developer", "instrucciones de sistema extensas"),
                _mensaje("user", "hola"),
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "t1"},
                },
            ]
        )
        turno = extraer_turnos(self.path)[0]
        self.assertEqual(turno.texto_usuario, "hola")
        self.assertEqual(turno.texto_agente, "")


if __name__ == "__main__":
    unittest.main()
