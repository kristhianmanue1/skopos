"""Tests para skopos.orquestador. Runner: `python3 -m unittest`."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pymongo.errors import PyMongoError

from skopos.analisis import Analisis, AnalisisFallido
from skopos.orquestador import procesar_rollout


def _linea(evento: dict) -> str:
    return json.dumps(evento, ensure_ascii=False)


def _mensaje(role: str, texto: str) -> dict:
    tipo_parte = "input_text" if role == "user" else "output_text"
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": role, "content": [{"type": tipo_parte, "text": texto}]},
    }


def _cierre(turn_id: str) -> dict:
    return {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn_id}}


def _session_meta() -> dict:
    # identidad Codex: desde ADR-010 la ingesta pasa por la frontera de
    # SPEC-006, que descarta lo que no la lleva (nunca parsea "por
    # parecido"). Las fixtures son rollouts, así que la declaran.
    return {"type": "session_meta", "payload": {"originator": "codex-tui", "cli_version": "0.147.0"}}


def _nunca_visto(turn_id, *, coleccion):
    return False


class FronteraSpec006Tests(unittest.TestCase):
    """La ingesta pasa por parsear(), no por el parser de Codex directo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"

    def _escribir_crudo(self, eventos: list[dict]) -> None:
        self.path.write_text(
            "\n".join(_linea(e) for e in eventos) + "\n", encoding="utf-8"
        )

    def test_archivo_sin_identidad_no_se_procesa_ni_analiza(self):
        # mismo contenido de un rollout, sin session_meta: antes de
        # ADR-010 se parseaba igual; ahora se descarta (§4, sin fallback)
        self._escribir_crudo([_mensaje("user", "hola"), _cierre("t1")])
        llamadas = []
        resultados = procesar_rollout(
            self.path,
            coleccion=None,
            analizar=lambda t, **k: llamadas.append(t),
            guardar=lambda a, **k: llamadas.append(a),
            ya_guardado=_nunca_visto,
        )
        self.assertEqual(resultados, [])
        self.assertEqual(llamadas, [])

    def test_el_descarte_es_atribuible_a_su_diagnostico(self):
        # ADR-010 §3: un descarte sin diagnóstico es un bug de contrato
        self._escribir_crudo([_mensaje("user", "hola"), _cierre("t1")])
        vistos = []
        procesar_rollout(
            self.path,
            coleccion=None,
            ya_guardado=_nunca_visto,
            on_diagnostico=lambda ruta, parseo: vistos.append((ruta, parseo.diagnostico)),
        )
        self.assertEqual(vistos, [(self.path, "formato_desconocido")])

    def test_el_diagnostico_ok_tambien_se_notifica(self):
        self._escribir_crudo([_session_meta(), _mensaje("user", "hola"), _cierre("t1")])
        vistos = []
        procesar_rollout(
            self.path,
            coleccion=None,
            analizar=lambda t, **k: Analisis(
                tema="x", resumen="y", turn_id=t.turn_id, session_id=t.session_id,
                ruta_origen=t.ruta_origen, offset_inicio=t.offset_inicio,
                offset_fin=t.offset_fin, cli="codex-cli", modelo_analisis="test-modelo",
            ),
            guardar=lambda a, **k: {},
            ya_guardado=_nunca_visto,
            on_diagnostico=lambda ruta, parseo: vistos.append(parseo.diagnostico),
        )
        self.assertEqual(vistos, ["ok"])


class SoloIndiceTests(unittest.TestCase):
    """Modo observación: indexa y no interpreta (P-004)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"
        self.path.write_text(
            "\n".join(_linea(e) for e in [
                _session_meta(), _mensaje("user", "hola"), _cierre("t1"),
            ]) + "\n",
            encoding="utf-8",
        )

    def test_no_llama_al_modelo_ni_a_la_dedup_pero_si_indexa(self):
        llamadas = []

        class _Indice:
            def __init__(self): self.docs = []
            def insert_one(self, d): self.docs.append(d)

        indice = _Indice()
        resultados = procesar_rollout(
            self.path,
            coleccion=None,
            analizar=lambda t, **k: llamadas.append("analizar"),
            guardar=lambda a, **k: llamadas.append("guardar"),
            ya_guardado=lambda tid, **k: llamadas.append("dedup") or False,
            indice=indice,
            solo_indice=True,
        )
        self.assertEqual(llamadas, [])          # ni modelo, ni dedup, ni guardado
        self.assertEqual(resultados, [])        # no hay desenlace de analisis que reportar
        self.assertEqual(len(indice.docs), 1)   # pero el turno quedo observado

    def test_el_cursor_avanza_porque_no_hay_nada_que_reintentar(self):
        from skopos.parseo import parsear

        class _Indice:
            def insert_one(self, d): pass

        cursores = []
        procesar_rollout(
            self.path, coleccion=None, indice=_Indice(), solo_indice=True,
            on_cursor=lambda ruta, c: cursores.append(c),
        )
        self.assertEqual(cursores[0].offset, parsear(self.path).turnos[-1].offset_fin)


class AvanceDelCursorTests(unittest.TestCase):
    """ADR-011: el cursor es caché inofensiva; jamás pérdida silenciosa."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"
        self.path.write_text(
            "\n".join(
                _linea(e)
                for e in [
                    _session_meta(),
                    _mensaje("user", "uno"), _cierre("t1"),
                    _mensaje("user", "dos"), _cierre("t2"),
                    _mensaje("user", "tres"), _cierre("t3"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _procesar(self, analizar):
        cursores = []
        resultados = procesar_rollout(
            self.path,
            coleccion=None,
            analizar=analizar,
            guardar=lambda a, **k: {},
            ya_guardado=_nunca_visto,
            on_cursor=lambda ruta, cursor: cursores.append(cursor),
        )
        return resultados, (cursores[0] if cursores else None)

    def _analisis(self, turno):
        return Analisis(
            tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
            ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
            offset_fin=turno.offset_fin, cli="codex-cli", modelo_analisis="test-modelo",
        )

    def test_sin_fallos_el_cursor_llega_al_final_del_ultimo_turno(self):
        from skopos.parseo import parsear

        resultados, cursor = self._procesar(lambda t, **k: self._analisis(t))
        self.assertEqual([r.estado for r in resultados], ["guardado"] * 3)
        ultimo = parsear(self.path).turnos[-1]
        self.assertEqual(cursor.offset, ultimo.offset_fin)

    def test_un_turno_fallido_congela_el_cursor_antes_de_el(self):
        # si el cursor pasara por encima de un turno cuyo analisis fallo,
        # ese turno no esta en Mongo y no se volveria a leer NUNCA
        from skopos.parseo import parsear

        def analizar(turno, **_):
            if turno.turn_id.endswith(":t2"):
                raise AnalisisFallido("Ollama caído")
            return self._analisis(turno)

        resultados, cursor = self._procesar(analizar)
        self.assertEqual([r.estado for r in resultados], ["guardado", "fallido", "guardado"])
        primero = parsear(self.path).turnos[0]
        self.assertEqual(cursor.offset, primero.offset_fin)  # se quedo antes de t2

    def test_el_fallo_del_primer_turno_no_emite_cursor(self):
        def analizar(turno, **_):
            raise AnalisisFallido("Ollama caído")

        resultados, cursor = self._procesar(analizar)
        self.assertEqual([r.estado for r in resultados], ["fallido"] * 3)
        self.assertIsNone(cursor)

    def test_los_omitidos_si_avanzan_el_cursor(self):
        # un turno ya guardado o sin contenido no exige reintento
        from skopos.parseo import parsear

        resultados = procesar_rollout(
            self.path,
            coleccion=None,
            analizar=lambda t, **k: self._analisis(t),
            guardar=lambda a, **k: {},
            ya_guardado=lambda tid, **k: True,
            on_cursor=lambda ruta, cursor: None,
        )
        self.assertEqual([r.estado for r in resultados], ["omitido"] * 3)


class ProcesarRolloutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout-test.jsonl"

    def _escribir(self, eventos: list[dict]) -> None:
        self.path.write_text(
            "\n".join(_linea(e) for e in [_session_meta()] + eventos) + "\n",
            encoding="utf-8",
        )

    def test_turno_analizado_y_guardado_queda_en_guardado(self):
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])
        guardados = []

        def analizar_fake(turno, **_):
            return Analisis(
                tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
                ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
                offset_fin=turno.offset_fin,
                cli="codex-cli", modelo_analisis="test-modelo",
            )

        def guardar_fake(analisis, *, coleccion):
            guardados.append(analisis)
            return {}

        resultados = procesar_rollout(
            self.path, coleccion=object(), analizar=analizar_fake, guardar=guardar_fake,
            ya_guardado=_nunca_visto,
        )
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].estado, "guardado")
        self.assertEqual(resultados[0].turn_id, "codex-cli:rollout-test:t1")
        self.assertEqual(len(guardados), 1)

    def test_analisis_fallido_no_llama_a_guardar(self):
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])
        guardar_llamado = []

        def analizar_falla(turno, **_):
            raise AnalisisFallido("modelo no respondió")

        def guardar_fake(analisis, *, coleccion):
            guardar_llamado.append(analisis)
            return {}

        resultados = procesar_rollout(
            self.path, coleccion=object(), analizar=analizar_falla, guardar=guardar_fake,
            ya_guardado=_nunca_visto,
        )
        self.assertEqual(resultados[0].estado, "fallido")
        self.assertIn("modelo no respondió", resultados[0].motivo)
        self.assertEqual(guardar_llamado, [])

    def test_persistencia_fallida_queda_en_fallido(self):
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])

        def analizar_fake(turno, **_):
            return Analisis(
                tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
                ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
                offset_fin=turno.offset_fin,
                cli="codex-cli", modelo_analisis="test-modelo",
            )

        def guardar_que_falla(analisis, *, coleccion):
            raise PyMongoError("conexión rechazada")

        resultados = procesar_rollout(
            self.path, coleccion=object(), analizar=analizar_fake, guardar=guardar_que_falla,
            ya_guardado=_nunca_visto,
        )
        self.assertEqual(resultados[0].estado, "fallido")
        self.assertIn("conexión rechazada", resultados[0].motivo)

    def test_sin_turnos_devuelve_lista_vacia(self):
        self._escribir([_mensaje("user", "nadie cierra este turno")])
        resultados = procesar_rollout(self.path, coleccion=object(), ya_guardado=_nunca_visto)
        self.assertEqual(resultados, [])

    def test_varios_turnos_se_procesan_independientemente(self):
        self._escribir(
            [
                _mensaje("user", "uno"),
                _cierre("t1"),
                _mensaje("user", "dos"),
                _cierre("t2"),
            ]
        )
        llamadas = {"t1": AnalisisFallido("falla t1"), "t2": None}

        def analizar_mixto(turno, **_):
            crudo = turno.turn_id.rsplit(":", 1)[-1]  # identidad calificada
            if llamadas[crudo] is not None:
                raise llamadas[crudo]
            return Analisis(
                tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
                ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
                offset_fin=turno.offset_fin,
                cli="codex-cli", modelo_analisis="test-modelo",
            )

        resultados = procesar_rollout(
            self.path, coleccion=object(), analizar=analizar_mixto, guardar=lambda a, *, coleccion: {},
            ya_guardado=_nunca_visto,
        )
        estados = {r.turn_id: r.estado for r in resultados}
        self.assertEqual(estados, {"codex-cli:rollout-test:t1": "fallido",
                                   "codex-cli:rollout-test:t2": "guardado"})

    def test_fallo_de_dedup_no_tumba_el_proceso_entero(self):
        # ronda adversarial 2026-08-13 [BLOCKER]: ya_guardado sin try/except
        # dejaba que un PyMongoError se propagara sin capturar, matando el
        # ciclo completo del vigilante en vez de fallar sólo este turno.
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])

        def dedup_que_falla(turn_id, *, coleccion):
            raise PyMongoError("mongo caído")

        resultados = procesar_rollout(
            self.path, coleccion=object(), ya_guardado=dedup_que_falla
        )
        self.assertEqual(resultados[0].estado, "fallido")
        self.assertIn("mongo caído", resultados[0].motivo)

    def test_turno_totalmente_vacio_se_omite_sin_llamar_al_modelo(self):
        # ronda adversarial 2026-08-13 [MED]: un turno sin texto real
        # igual disparaba una llamada cara a Ollama y se guardaba como
        # análisis válido.
        self._escribir([_cierre("t1")])  # ningún response_item, sólo el cierre
        analizar_llamado = []

        def analizar_que_no_deberia_llamarse(turno, **_):
            analizar_llamado.append(turno.turn_id)
            raise AssertionError("no debería llamarse para un turno vacío")

        resultados = procesar_rollout(
            self.path,
            coleccion=object(),
            analizar=analizar_que_no_deberia_llamarse,
            ya_guardado=_nunca_visto,
        )
        self.assertEqual(resultados[0].estado, "omitido")
        self.assertEqual(resultados[0].motivo, "sin contenido significativo")
        self.assertEqual(analizar_llamado, [])

    def test_turno_ya_guardado_se_omite_sin_analizar_ni_guardar(self):
        self._escribir([_mensaje("user", "hola"), _cierre("t1")])
        analizar_llamado = []
        guardar_llamado = []

        def analizar_fake(turno, **_):
            analizar_llamado.append(turno.turn_id)
            return Analisis(
                tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
                ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
                offset_fin=turno.offset_fin,
                cli="codex-cli", modelo_analisis="test-modelo",
            )

        def guardar_fake(analisis, *, coleccion):
            guardar_llamado.append(analisis)
            return {}

        resultados = procesar_rollout(
            self.path,
            coleccion=object(),
            analizar=analizar_fake,
            guardar=guardar_fake,
            ya_guardado=lambda turn_id, *, coleccion: True,
        )
        self.assertEqual(resultados[0].estado, "omitido")
        self.assertEqual(analizar_llamado, [])
        self.assertEqual(guardar_llamado, [])


if __name__ == "__main__":
    unittest.main()
