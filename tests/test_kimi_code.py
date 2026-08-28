"""Tests del adaptador parser-kimi-code/v1 — único con marcas de turno.

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from skopos.parseo import parsear


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _metadata(version: str = "1.9") -> dict:
    return {"type": "metadata", "protocol_version": version}


def _wire(tipo: str, payload: dict | None = None, ts: float = 1772653777.925) -> dict:
    return {"timestamp": ts, "message": {"type": tipo, "payload": payload or {}}}


def _inicio(texto: str) -> dict:
    return _wire("TurnBegin", {"user_input": [{"type": "text", "text": texto}]})


def _contenido(texto: str, tipo: str = "text") -> dict:
    clave = "text" if tipo == "text" else tipo
    return _wire("ContentPart", {"type": tipo, clave: texto})


class _ConWire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        sesion = Path(self.tmp.name) / "sesion-abc"
        sesion.mkdir()
        self.path = sesion / "wire.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text("\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8")


class IdentidadTests(_ConWire):
    def test_wire_de_kimi_se_detecta(self):
        self._escribir([_metadata(), _inicio("hola"), _wire("TurnEnd")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.cli_producto, "kimi-code")
        self.assertEqual(r.version_cli_observada, "1.9")

    def test_protocolo_no_soportado_es_version_no_soportada(self):
        self._escribir([_metadata("9.9"), _inicio("hola"), _wire("TurnEnd")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "version_no_soportada")
        self.assertEqual(r.cli_producto, "kimi-code")
        self.assertEqual(r.turnos, [])

    def test_sin_metadata_no_casa(self):
        self._escribir([_inicio("hola"), _wire("TurnEnd")])
        self.assertEqual(parsear(self.path).diagnostico, "formato_desconocido")


class ExtraccionTests(_ConWire):
    def test_el_turno_lo_cierra_TurnEnd(self):
        # unico adaptador con marca explicita de cierre, como Codex
        self._escribir([
            _metadata(),
            _inicio("pregunta"), _contenido("respuesta"), _wire("TurnEnd"),
            _inicio("segunda"), _contenido("otra"),  # sin TurnEnd: abierto
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual(len(turnos), 1)
        self.assertEqual(turnos[0].texto_usuario, "pregunta")
        self.assertEqual(turnos[0].texto_agente, "respuesta")

    def test_el_pensamiento_del_modelo_no_es_conversacion(self):
        self._escribir([
            _metadata(), _inicio("pregunta"),
            _contenido("razonando en privado", tipo="think"),
            _contenido("respuesta"), _wire("TurnEnd"),
        ])
        self.assertEqual(parsear(self.path).turnos[0].texto_agente, "respuesta")

    def test_user_input_como_string_suelto_tambien_cuenta(self):
        # el corpus trae las dos formas; ignorar esta dejaba 363 turnos
        # con texto de usuario vacio
        self._escribir([
            _metadata(),
            _wire("TurnBegin", {"user_input": "instruccion inicial"}),
            _wire("TurnEnd"),
        ])
        self.assertEqual(parsear(self.path).turnos[0].texto_usuario, "instruccion inicial")

    def test_timestamp_epoch_se_sirve_en_iso_para_adr_008(self):
        from skopos.orquestador import _parsear_timestamp

        self._escribir([_metadata(), _inicio("hola"), _wire("TurnEnd")])
        momento = _parsear_timestamp(parsear(self.path).turnos[0].timestamp_cierre)
        self.assertIsNotNone(momento)
        self.assertIsNotNone(momento.tzinfo)

    def test_session_id_sale_de_la_carpeta_no_del_archivo(self):
        # todos los wire se llaman igual: wire.jsonl
        self._escribir([_metadata(), _inicio("hola"), _wire("TurnEnd")])
        self.assertEqual(parsear(self.path).turnos[0].session_id, "sesion-abc")

    def test_identidad_calificada_con_ordinal_estable(self):
        self._escribir([
            _metadata(),
            _inicio("uno"), _wire("TurnEnd"),
            _inicio("dos"), _wire("TurnEnd"),
        ])
        turnos = parsear(self.path).turnos
        self.assertEqual([t.turn_id for t in turnos],
                         ["kimi-code:sesion-abc:1", "kimi-code:sesion-abc:2"])

    def test_proyecto_ausente_por_declaracion_de_ficha(self):
        # el wire no expone cwd y deducirlo de la ruta esta prohibido
        self._escribir([_metadata(), _inicio("hola"), _wire("TurnEnd")])
        self.assertIsNone(parsear(self.path).turnos[0].proyecto)

    def test_el_sello_cubre_el_rango_del_turno(self):
        self._escribir([
            _metadata(), _inicio("pregunta"), _contenido("respuesta"), _wire("TurnEnd"),
        ])
        turno = parsear(self.path).turnos[0]
        crudo = self.path.read_bytes()[turno.offset_inicio : turno.offset_fin]
        self.assertEqual(turno.fragmento_sha256, hashlib.sha256(crudo).hexdigest())
        self.assertIn(b"respuesta", crudo)

    def test_sesion_sin_TurnEnd_no_produce_turnos(self):
        self._escribir([_metadata(), _inicio("sigo"), _contenido("trabajando")])
        r = parsear(self.path)
        self.assertEqual(r.diagnostico, "ok")
        self.assertEqual(r.turnos, [])
        self.assertEqual(r.detalle.codigo, "identidad_reconocida_sin_cierres")


if __name__ == "__main__":
    unittest.main()
