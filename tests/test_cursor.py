"""Tests para la lectura incremental (ADR-011): almacén y frontera.

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skopos.cursor import AlmacenCursores, Cursor
from skopos.parseo import parsear, sellar_prefijo


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _session_meta() -> dict:
    return {"type": "session_meta", "payload": {"originator": "codex-tui"}}


def _mensaje(texto: str) -> dict:
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": "user",
                    "content": [{"type": "input_text", "text": texto}]},
    }


def _cierre(turn_id: str) -> dict:
    return {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn_id}}


class _ConRollout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text("\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8")

    def _anexar(self, eventos: list[dict]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(_linea(e) for e in eventos) + "\n")

    def _cursor_tras_parsear(self):
        r = parsear(self.path)
        offset = r.turnos[-1].offset_fin
        return Cursor(offset, sellar_prefijo(r.instantanea, offset)), r


class LecturaIncrementalTests(_ConRollout):
    def test_solo_parsea_la_cola_y_produce_lo_mismo_que_una_lectura_completa(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        cursor, _ = self._cursor_tras_parsear()
        self._anexar([_mensaje("dos"), _cierre("t2")])

        incremental = parsear(self.path, cursor=cursor)
        completo = parsear(self.path)

        self.assertTrue(incremental.incremental)
        self.assertEqual([t.turn_id for t in incremental.turnos], ["t2"])
        # byte a byte lo mismo que la lectura completa: offsets y sellos
        nuevos_del_completo = [t for t in completo.turnos if t.turn_id == "t2"]
        self.assertEqual(incremental.turnos, nuevos_del_completo)

    def test_el_proyecto_sobrevive_a_la_frontera_incremental(self):
        # `proyecto` viene de un turn_context anterior al cursor; sin
        # herencia, toda lectura incremental lo degradaría a None
        cwd = str(Path.home() / "www" / "skopos")
        self._escribir([
            _session_meta(),
            {"type": "turn_context", "payload": {"cwd": cwd}},
            _mensaje("uno"), _cierre("t1"),
        ])
        cursor, completo = self._cursor_tras_parsear()
        self.assertEqual(completo.turnos[0].proyecto, "skopos")

        self._anexar([_mensaje("dos"), _cierre("t2")])
        incremental = parsear(self.path, cursor=cursor)
        self.assertEqual(incremental.turnos[0].proyecto, "skopos")

    def test_un_reset_de_proyecto_anterior_al_cursor_tambien_se_hereda(self):
        self._escribir([
            _session_meta(),
            {"type": "turn_context", "payload": {"cwd": str(Path.home() / "www" / "skopos")}},
            _mensaje("uno"), _cierre("t1"),
            {"type": "turn_context", "payload": {"cwd": str(Path.home())}},  # sin significado
        ])
        r = parsear(self.path)
        offset = r.turnos[-1].offset_fin
        # cursor tras el turno; el reset queda entre el cursor y la cola
        cursor = Cursor(len(r.instantanea), sellar_prefijo(r.instantanea, len(r.instantanea)))
        self._anexar([_mensaje("dos"), _cierre("t2")])
        incremental = parsear(self.path, cursor=cursor)
        self.assertIsNone(incremental.turnos[0].proyecto)

    def test_sin_turnos_nuevos_no_afirma_que_el_archivo_no_tenga_cierres(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        cursor, _ = self._cursor_tras_parsear()
        incremental = parsear(self.path, cursor=cursor)
        self.assertEqual(incremental.diagnostico, "ok")
        self.assertEqual(incremental.turnos, [])
        self.assertIsNone(incremental.detalle)  # no identidad_reconocida_sin_cierres


class ValidacionDelCursorTests(_ConRollout):
    def test_digest_que_no_casa_fuerza_reparseo_completo(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        cursor, _ = self._cursor_tras_parsear()
        cursor_falso = Cursor(cursor.offset, "0" * 64)
        r = parsear(self.path, cursor=cursor_falso)
        self.assertFalse(r.incremental)
        self.assertEqual([t.turn_id for t in r.turnos], ["t1"])

    def test_archivo_editado_por_debajo_del_cursor_se_reparsea_entero(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        cursor, _ = self._cursor_tras_parsear()
        # rotación: mismo prefijo de longitud, contenido distinto
        self._escribir([_session_meta(), _mensaje("XXX"), _cierre("t9")])
        r = parsear(self.path, cursor=cursor)
        self.assertFalse(r.incremental)
        self.assertEqual([t.turn_id for t in r.turnos], ["t9"])

    def test_archivo_truncado_por_debajo_del_cursor_se_reparsea_entero(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1"),
                        _mensaje("dos"), _cierre("t2")])
        cursor, _ = self._cursor_tras_parsear()
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        r = parsear(self.path, cursor=cursor)
        self.assertFalse(r.incremental)
        self.assertEqual([t.turn_id for t in r.turnos], ["t1"])

    def test_cursor_ausente_o_en_cero_no_es_incremental(self):
        self._escribir([_session_meta(), _mensaje("uno"), _cierre("t1")])
        self.assertFalse(parsear(self.path).incremental)
        self.assertFalse(parsear(self.path, cursor=Cursor(0, "0" * 64)).incremental)

    def test_el_cursor_nunca_sustituye_a_la_deteccion_de_identidad(self):
        # un archivo sin identidad se descarta aunque traiga cursor
        self._escribir([_mensaje("uno"), _cierre("t1")])
        r = parsear(self.path, cursor=Cursor(10, "0" * 64))
        self.assertEqual(r.diagnostico, "formato_desconocido")


class EstadoQueCruzaLaFronteraTests(_ConRollout):
    """Lo que vive por debajo del cursor y aun asi gobierna la cola."""

    def test_version_cli_observada_sobrevive_al_cursor(self):
        # session_meta vive en la cabecera: sin herencia explicita, toda
        # lectura incremental la degradaria a None
        self._escribir([
            {"type": "session_meta",
             "payload": {"originator": "codex-tui", "cli_version": "0.147.0"}},
            _mensaje("uno"), _cierre("t1"),
        ])
        cursor, completo = self._cursor_tras_parsear()
        self.assertEqual(completo.version_cli_observada, "0.147.0")
        self._anexar([_mensaje("dos"), _cierre("t2")])
        self.assertEqual(parsear(self.path, cursor=cursor).version_cli_observada, "0.147.0")

    def test_los_conteos_son_de_la_lectura_no_del_archivo(self):
        # deviacion declarada de ADR-010 §3 ("total por archivo"): en
        # lectura incremental se cuenta lo observado en ESTE tramo, que
        # es lo unico que el ciclo puede afirmar de primera mano
        self._escribir([
            _session_meta(), {"type": "world_state", "payload": {}},
            _mensaje("uno"), _cierre("t1"),
        ])
        cursor, completo = self._cursor_tras_parsear()
        self.assertEqual(completo.eventos_no_reconocidos, 1)
        self._anexar([{"type": "world_state", "payload": {}}, _cierre("t2")])
        incremental = parsear(self.path, cursor=cursor)
        self.assertEqual(incremental.eventos_no_reconocidos, 1)  # el del tramo, no 2
        self.assertEqual(parsear(self.path).eventos_no_reconocidos, 2)  # completo si


class PodaDelAlmacenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "cursores.json"

    def test_olvida_los_archivos_que_ya_no_existen(self):
        # sin poda, el almacen crece para siempre con cada sesion
        # archivada, renombrada o borrada
        almacen = AlmacenCursores(self.ruta)
        almacen.actualizar("/x/vivo.jsonl", Cursor(1, "a" * 64))
        almacen.actualizar("/x/borrado.jsonl", Cursor(2, "b" * 64))
        self.assertEqual(almacen.podar(["/x/vivo.jsonl"]), 1)
        self.assertIsNone(almacen.obtener("/x/borrado.jsonl"))
        self.assertIsNotNone(almacen.obtener("/x/vivo.jsonl"))

    def test_podar_sin_bajas_no_ensucia_el_almacen(self):
        almacen = AlmacenCursores(self.ruta)
        almacen.actualizar("/x/vivo.jsonl", Cursor(1, "a" * 64))
        almacen.guardar()
        self.assertEqual(almacen.podar(["/x/vivo.jsonl"]), 0)
        self.assertFalse(almacen.guardar())


class AlmacenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "cursores.json"

    def test_ida_y_vuelta(self):
        almacen = AlmacenCursores(self.ruta)
        almacen.actualizar("/x/rollout.jsonl", Cursor(42, "a" * 64))
        self.assertTrue(almacen.guardar())
        self.assertEqual(
            AlmacenCursores(self.ruta).cargar().obtener("/x/rollout.jsonl"),
            Cursor(42, "a" * 64),
        )

    def test_no_reescribe_si_nada_cambio(self):
        almacen = AlmacenCursores(self.ruta)
        almacen.actualizar("/x/r.jsonl", Cursor(1, "b" * 64))
        almacen.guardar()
        almacen.actualizar("/x/r.jsonl", Cursor(1, "b" * 64))
        self.assertFalse(almacen.guardar())

    def test_almacen_corrupto_se_trata_como_vacio(self):
        # es una caché: se rehace sola, nunca rompe el ciclo
        self.ruta.write_text("{no es json", encoding="utf-8")
        self.assertIsNone(AlmacenCursores(self.ruta).cargar().obtener("/x/r.jsonl"))

    def test_version_desconocida_se_ignora(self):
        self.ruta.write_text(
            json.dumps({"version": "otra/v9", "entradas": {"/x": {"offset": 1, "digest_prefijo": "c"}}}),
            encoding="utf-8",
        )
        self.assertIsNone(AlmacenCursores(self.ruta).cargar().obtener("/x"))

    def test_archivo_inexistente_no_es_error(self):
        self.assertIsNone(AlmacenCursores(self.ruta).cargar().obtener("/x"))


if __name__ == "__main__":
    unittest.main()
