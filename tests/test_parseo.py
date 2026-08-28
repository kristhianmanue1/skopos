"""Tests para skopos.parseo (SPEC-006 / parser-contrato v1, ADR-010).

Runner: `python3 -m unittest`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skopos import captura
from skopos.parseo import (
    FICHA_CODEX,
    REGISTRO,
    Detalle,
    Ficha,
    InstantaneaCorrupta,
    materializar_instantanea,
    parsear,
)


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _session_meta(originator: str = "codex-tui", cli_version: str | None = "0.147.0") -> dict:
    payload = {"originator": originator}
    if cli_version is not None:
        payload["cli_version"] = cli_version
    return {"type": "session_meta", "payload": payload}


def _mensaje(role: str, texto: str) -> dict:
    tipo_parte = "input_text" if role == "user" else "output_text"
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": role, "content": [{"type": tipo_parte, "text": texto}]},
    }


def _cierre(turn_id: str) -> dict:
    return {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn_id}}


class _ConArchivo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text("\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8")


class InstantaneaTests(_ConArchivo):
    def test_lee_exactamente_los_bytes_de_fstat(self):
        self._escribir([_session_meta()])
        self.assertEqual(materializar_instantanea(self.path), self.path.read_bytes())

    def test_short_read_es_entrada_corrupta_con_lectura_corta(self):
        # fstat promete más bytes de los que el descriptor entrega
        self._escribir([_session_meta()])
        real = self.path.stat().st_size

        class _Stat:
            st_size = real + 100

        with mock.patch("skopos.parseo.os.fstat", return_value=_Stat()):
            resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "entrada_corrupta")
        self.assertEqual(resultado.detalle, Detalle("lectura_corta"))

    def test_utf8_invalido_es_entrada_corrupta_sin_codigo(self):
        self.path.write_bytes(b'{"type": "session_meta"}\n\xff\xfe no es utf-8\n')
        resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "entrada_corrupta")
        self.assertIsNone(resultado.detalle)

    def test_archivo_inexistente_es_entrada_corrupta(self):
        self.assertEqual(
            parsear(Path(self.tmp.name) / "no-existe.jsonl").diagnostico, "entrada_corrupta"
        )


class DeteccionTests(_ConArchivo):
    def test_rollout_codex_da_ok_con_turnos_y_metadata_de_ficha(self):
        self._escribir([_session_meta(), _mensaje("user", "hola"), _cierre("t1")])
        resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "ok")
        self.assertEqual([t.turn_id for t in resultado.turnos], ["t1"])
        self.assertEqual(resultado.cli_producto, "codex-cli")
        self.assertEqual(resultado.version_formato, "codex-rollout/v1")
        self.assertEqual(resultado.version_cli_observada, "0.147.0")
        self.assertIsNone(resultado.detalle)

    def test_sin_session_meta_es_formato_desconocido_no_fallback(self):
        # ADR-010 §4: sin identidad no se parsea "por parecido", aunque el
        # archivo tenga la forma exacta de un rollout.
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])
        resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "formato_desconocido")
        self.assertEqual(resultado.turnos, [])
        self.assertIsNone(resultado.cli_producto)

    def test_originator_ajeno_no_casa(self):
        self._escribir([_session_meta(originator="claude-code"), _cierre("t1")])
        self.assertEqual(parsear(self.path).diagnostico, "formato_desconocido")

    def test_frontera_de_palabra_codexfoo_no_casa(self):
        self._escribir([_session_meta(originator="codexfoo"), _cierre("t1")])
        self.assertEqual(parsear(self.path).diagnostico, "formato_desconocido")

    def test_enum_observado_en_el_corpus_casa_completo(self):
        for originator in ("codex-tui", "codex_exec", "Codex Desktop", "codex"):
            with self.subTest(originator=originator):
                self._escribir([_session_meta(originator=originator), _cierre("t1")])
                self.assertEqual(parsear(self.path).diagnostico, "ok")

    def test_session_meta_fuera_del_alcance_de_escaneo_no_casa(self):
        relleno = [{"type": "event_msg", "payload": {}} for _ in range(captura.LINEAS_ESCANEO_IDENTIDAD)]
        self._escribir(relleno + [_session_meta(), _cierre("t1")])
        self.assertEqual(parsear(self.path).diagnostico, "formato_desconocido")

    def test_archivo_vivo_sin_cierres_es_ok_con_detalle(self):
        self._escribir([_session_meta(), _mensaje("user", "sin cerrar todavía")])
        resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "ok")
        self.assertEqual(resultado.turnos, [])
        self.assertEqual(resultado.detalle, Detalle("identidad_reconocida_sin_cierres"))


class ConteosTests(_ConArchivo):
    def test_eventos_aditivos_se_cuentan_y_no_cambian_el_diagnostico(self):
        self._escribir(
            [
                _session_meta(),
                {"type": "world_state", "payload": {"x": 1}},
                {"type": "compacted", "payload": {}},
                _mensaje("user", "hola"),
                _cierre("t1"),
            ]
        )
        resultado = parsear(self.path)
        self.assertEqual(resultado.diagnostico, "ok")
        self.assertEqual(resultado.eventos_no_reconocidos, 2)
        self.assertEqual(len(resultado.turnos), 1)

    def test_evento_sin_type_o_con_type_no_string_no_cuenta(self):
        self._escribir([_session_meta(), {"payload": {}}, {"type": 7}, _cierre("t1")])
        self.assertEqual(parsear(self.path).eventos_no_reconocidos, 0)

    def test_linea_invalida_cuenta_solo_como_descarte_de_linea(self):
        self.path.write_text(
            _linea(_session_meta()) + "\n{no es json\n" + _linea(_cierre("t1")) + "\n",
            encoding="utf-8",
        )
        resultado = parsear(self.path)
        self.assertEqual(resultado.descartes_linea, 1)
        self.assertEqual(resultado.eventos_no_reconocidos, 0)
        self.assertEqual(len(resultado.turnos), 1)


class SeparadoresTests(unittest.TestCase):
    def test_solo_el_salto_de_linea_separa_registros(self):
        # Cortar por \r, \v o \f (lo que hace bytes.splitlines) movería
        # offsets y sellos respecto de lo ya guardado: iter_lineas corta
        # sólo por \n, igual que iterar el descriptor de archivo.
        datos = b'{"a": 1}\r\x0b sigue la misma linea\n{"b": 2}\n'
        lineas = list(captura.iter_lineas(datos))
        self.assertEqual(len(lineas), 2)
        self.assertEqual(lineas[0], (b'{"a": 1}\r\x0b sigue la misma linea\n', 0, 32))
        self.assertEqual(lineas[1], (b'{"b": 2}\n', 32, 41))

    def test_ultima_linea_sin_salto_final_conserva_sus_offsets(self):
        datos = b'{"a": 1}\n{"b": 2}'
        self.assertEqual(list(captura.iter_lineas(datos))[-1], (b'{"b": 2}', 9, 17))


class _FichaFalsa:
    """Fichas sintéticas para ejercitar reglas sin inventar formatos."""

    @staticmethod
    def crear(id_ficha, cli_producto, casa=True, incompatible=False, activa=True):
        return Ficha(
            id_ficha=id_ficha,
            cli_producto=cli_producto,
            version_parser=id_ficha,
            version_formato=f"{cli_producto}-formato/v1",
            casa_identidad=lambda _b, casa=casa: casa,
            es_incompatible=lambda _b, inc=incompatible: inc,
            extraer=captura.extraer_de_instantanea,
            activa=activa,
        )


class SeleccionTests(_ConArchivo):
    def setUp(self):
        super().setUp()
        self._escribir([_session_meta(), _mensaje("user", "hola"), _cierre("t1")])

    def test_dos_productos_candidatos_dan_ambiguedad_de_producto(self):
        otro = _FichaFalsa.crear("parser-otro/v1", "otro-cli")
        resultado = parsear(self.path, registro=(FICHA_CODEX, otro))
        self.assertEqual(resultado.diagnostico, "deteccion_ambigua")
        self.assertEqual(
            resultado.detalle, Detalle("identidades_producto_multiples", ("parser-codex/v1", "parser-otro/v1"))
        )
        self.assertEqual(resultado.turnos, [])

    def test_dos_versiones_del_mismo_producto_dan_ambiguedad_de_version(self):
        v2 = _FichaFalsa.crear("parser-codex/v2", captura.CLI_PRODUCTO)
        resultado = parsear(self.path, registro=(FICHA_CODEX, v2))
        self.assertEqual(resultado.diagnostico, "deteccion_ambigua")
        self.assertEqual(
            resultado.detalle, Detalle("versiones_formato_multiples", ("parser-codex/v1", "parser-codex/v2"))
        )
        self.assertEqual(resultado.cli_producto, "codex-cli")

    def test_dos_versiones_con_exclusion_mutua_no_son_ambiguas(self):
        # §8: la ficha nueva declara firma positiva propia y la vieja la
        # excluye — el registro sólo se acepta con esa exclusión.
        v2 = _FichaFalsa.crear("parser-codex/v2", captura.CLI_PRODUCTO, incompatible=True)
        resultado = parsear(self.path, registro=(FICHA_CODEX, v2))
        self.assertEqual(resultado.diagnostico, "ok")
        self.assertEqual(resultado.version_formato, "codex-rollout/v1")

    def test_ficha_retirada_da_version_no_soportada_no_formato_desconocido(self):
        retirada = _FichaFalsa.crear("parser-codex/v1", captura.CLI_PRODUCTO, activa=False)
        resultado = parsear(self.path, registro=(retirada,))
        self.assertEqual(resultado.diagnostico, "version_no_soportada")
        self.assertEqual(resultado.detalle, Detalle("parser_retirado"))
        self.assertEqual(resultado.cli_producto, "codex-cli")

    def test_marcador_incompatible_da_version_no_soportada_sin_detalle(self):
        incompatible = _FichaFalsa.crear("parser-codex/v1", captura.CLI_PRODUCTO, incompatible=True)
        resultado = parsear(self.path, registro=(incompatible,))
        self.assertEqual(resultado.diagnostico, "version_no_soportada")
        self.assertIsNone(resultado.detalle)

    def test_precedencia_corrupta_gana_a_ambiguedad(self):
        # entrada_corrupta > deteccion_ambigua: con dos identidades que
        # casarían, el archivo ilegible se diagnostica corrupto igual.
        self.path.write_bytes(b"\xff\xfe\n")
        otro = _FichaFalsa.crear("parser-otro/v1", "otro-cli")
        self.assertEqual(
            parsear(self.path, registro=(FICHA_CODEX, otro)).diagnostico, "entrada_corrupta"
        )

    def test_precedencia_ambiguedad_gana_a_desconocido(self):
        # deteccion_ambigua > formato_desconocido: si dos casan, no hay
        # "ninguna" (la ficha codex no casa aquí, las falsas sí).
        self._escribir([_mensaje("user", "sin identidad"), _cierre("t1")])
        a = _FichaFalsa.crear("parser-a/v1", "a-cli")
        b = _FichaFalsa.crear("parser-b/v1", "b-cli")
        self.assertEqual(
            parsear(self.path, registro=(FICHA_CODEX, a, b)).diagnostico, "deteccion_ambigua"
        )


class DetalleTests(unittest.TestCase):
    def test_candidatos_obligatorios_en_los_codigos_de_ambiguedad(self):
        with self.assertRaises(ValueError):
            Detalle("identidades_producto_multiples")
        with self.assertRaises(ValueError):
            Detalle("versiones_formato_multiples", ("solo-uno",))

    def test_candidatos_prohibidos_en_el_resto(self):
        with self.assertRaises(ValueError):
            Detalle("parser_retirado", ("a", "b"))

    def test_candidatos_ordenados_y_sin_duplicados(self):
        with self.assertRaises(ValueError):
            Detalle("identidades_producto_multiples", ("b", "a"))
        with self.assertRaises(ValueError):
            Detalle("identidades_producto_multiples", ("a", "a"))

    def test_codigo_fuera_de_la_union_cerrada_se_rechaza(self):
        with self.assertRaises(ValueError):
            Detalle("codigo_inventado")


class RegistroTests(unittest.TestCase):
    def test_el_registro_declara_las_fichas_activas(self):
        self.assertIn(FICHA_CODEX, REGISTRO)
        self.assertEqual(FICHA_CODEX.cli_producto, "codex-cli")
        self.assertEqual(FICHA_CODEX.version_parser, "parser-codex/v1")
        self.assertTrue(all(f.activa for f in REGISTRO))

    def test_cada_producto_registrado_aparece_una_sola_vez(self):
        # dos fichas del mismo producto exigirian exclusion mutua
        # explicita (ADR-010 §8); hoy no hay ninguna pareja asi
        productos = [f.cli_producto for f in REGISTRO]
        self.assertEqual(len(productos), len(set(productos)))

    def test_ningun_producto_repite_ficha_con_el_mismo_id(self):
        ids = [f.id_ficha for f in REGISTRO]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
