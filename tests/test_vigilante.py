"""Tests para skopos.vigilante (SPEC-005). Runner: `python3 -m unittest`."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from io import StringIO
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pymongo

from skopos.almacenamiento import coleccion_local
from skopos.vigilante import ciclo, descubrir_rollouts, ejecutar, watch_command

DB_DE_PRUEBA = "skopos_test_vigilante"


def _mongo_disponible() -> bool:
    try:
        pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=500
        ).admin.command("ping")
        return True
    except Exception:
        return False


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _rollout_de_un_turno(
    path: Path, turn_id: str, texto: str, timestamp: str | None = None
) -> None:
    cierre = {
        "type": "event_msg",
        "payload": {"type": "task_complete", "turn_id": turn_id},
    }
    if timestamp is not None:
        cierre["timestamp"] = timestamp
    eventos = [
        # identidad Codex: la ingesta pasa por la frontera de SPEC-006
        {"type": "session_meta", "payload": {"originator": "codex-tui"}},
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": texto}]},
        },
        cierre,
    ]
    path.write_text("\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8")



class ReporteDeDescartesTests(unittest.TestCase):
    """ADR-010 §3: un archivo que la frontera rechaza no baja en silencio."""

    def test_los_descartes_se_reportan_por_diagnostico(self):
        from collections import Counter
        from skopos.vigilante import _reportar_diagnosticos

        salida = StringIO()
        with redirect_stderr(salida):
            _reportar_diagnosticos(
                Counter({"ok": 3, "formato_desconocido": 2, "entrada_corrupta": 1})
            )
        texto = salida.getvalue()
        self.assertIn("entrada_corrupta: 1", texto)
        self.assertIn("formato_desconocido: 2", texto)
        self.assertNotIn("ok:", texto)  # el caso normal no es ruido de ciclo

    def test_sin_descartes_no_imprime_nada(self):
        from collections import Counter
        from skopos.vigilante import _reportar_diagnosticos

        salida = StringIO()
        with redirect_stderr(salida):
            _reportar_diagnosticos(Counter({"ok": 5}))
        self.assertEqual(salida.getvalue(), "")


class DescubrirRolloutsTests(unittest.TestCase):
    def test_directorio_inexistente_no_produce_error(self):
        self.assertEqual(descubrir_rollouts(Path("/no/existe/nada")), set())

    def test_encuentra_jsonl_recursivamente(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            anidado = raiz / "2026" / "08"
            anidado.mkdir(parents=True)
            archivo = anidado / "rollout-x.jsonl"
            archivo.write_text("{}\n", encoding="utf-8")
            (raiz / "no-es-rollout.txt").write_text("x", encoding="utf-8")
            self.assertEqual(descubrir_rollouts(raiz), {archivo})


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class CicloTests(unittest.TestCase):
    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sessions_dir = Path(self.tmp.name)
        self.rollout = self.sessions_dir / "rollout-a.jsonl"
        _rollout_de_un_turno(self.rollout, "t1", "hola", timestamp=_ahora_iso())

    def _analizar_fake(self, turno, **_):
        from skopos.analisis import Analisis

        return Analisis(
            tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
            ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
            offset_fin=turno.offset_fin,
            cli="codex-cli", modelo_analisis="test-modelo",
        )

    def test_turno_nuevo_queda_guardado(self):
        resultados = ciclo(self.sessions_dir, coleccion=self.coleccion, analizar=self._analizar_fake)
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].estado, "guardado")

    def test_segundo_ciclo_omite_el_turno_ya_guardado(self):
        ciclo(self.sessions_dir, coleccion=self.coleccion, analizar=self._analizar_fake)
        analizar_llamado = []

        def analizar_que_no_deberia_llamarse(turno, **_):
            analizar_llamado.append(turno.turn_id)
            return self._analizar_fake(turno)

        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion, analizar=analizar_que_no_deberia_llamarse
        )
        self.assertEqual(resultados[0].estado, "omitido")
        self.assertEqual(analizar_llamado, [])

    def test_ejecutar_se_detiene_tras_max_ciclos(self):
        # ADR-008, escenario real: al arrancar no hay nada nuevo; un
        # turno llega al archivo ENTRE ciclos (sesión viva) y el ciclo
        # siguiente lo procesa
        rollout = self.sessions_dir / "rollout-vivo.jsonl"
        rollout.write_text("", encoding="utf-8")

        def _llegar_un_turno(resultados):
            if not resultados and not rollout.read_text(encoding="utf-8"):
                # garantiza timestamp > t0 con holgura: _ahora_iso trunca
                # a milisegundos y un turno escrito en el mismo ms que el
                # arranque quedaría (conservador) como histórico
                time.sleep(0.01)
                _rollout_de_un_turno(
                    rollout, "t-vivo", "recien llegado", timestamp=_ahora_iso()
                )

        ciclos_vistos = []
        ejecutar(
            self.sessions_dir,
            coleccion=self.coleccion,
            intervalo=0,
            max_ciclos=2,
            on_ciclo=lambda resultados: (ciclos_vistos.append(resultados), _llegar_un_turno(resultados)),
            analizar=self._analizar_fake,
        )
        self.assertEqual(len(ciclos_vistos), 2)
        self.assertEqual(ciclos_vistos[0], [])  # nada al arranque (desde ahora)
        self.assertEqual(ciclos_vistos[1][0].estado, "guardado")


@unittest.skipUnless(_mongo_disponible(), "MongoDB no está corriendo en localhost:27017")
class PoliticaArranqueTests(unittest.TestCase):
    """ADR-008 (decisión 8, 🔒 2026-08-20): "desde ahora" por defecto,
    `--backfill` opt-in. El corte es semánticamente por turno; el salto
    de archivo por mtime es optimización de descubrimiento."""

    def setUp(self):
        self.coleccion = coleccion_local(db=DB_DE_PRUEBA)
        cliente = self.coleccion.database.client
        self.addCleanup(cliente.close)
        self.addCleanup(cliente.drop_database, DB_DE_PRUEBA)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sessions_dir = Path(self.tmp.name)

        self.analizar_llamado: list[str] = []

    def _analizar_fake(self, turno, **_):
        from skopos.analisis import Analisis

        self.analizar_llamado.append(turno.turn_id)
        return Analisis(
            tema="x", resumen="y", turn_id=turno.turn_id, session_id=turno.session_id,
            ruta_origen=turno.ruta_origen, offset_inicio=turno.offset_inicio,
            offset_fin=turno.offset_fin,
            cli="codex-cli", modelo_analisis="test-modelo",
        )

    def test_por_defecto_solo_turnos_cerrados_desde_arranque(self):
        # ventana realista: t0 un minuto atrás — el histórico queda
        # fuera por filtro de TURNO (su archivo sí pasa el mtime), el
        # recién cerrado entra
        t0 = datetime.now(timezone.utc) - timedelta(seconds=60)
        viejo = self.sessions_dir / "rollout-viejo.jsonl"
        _rollout_de_un_turno(
            viejo, "t-viejo", "historico", timestamp="2026-01-01T00:00:00.000Z"
        )
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=t0, analizar=self._analizar_fake,
        )
        self.assertEqual(resultados, [])
        self.assertEqual(self.analizar_llamado, [])

        nuevo = self.sessions_dir / "rollout-nuevo.jsonl"
        _rollout_de_un_turno(nuevo, "t-nuevo", "fresco", timestamp=_ahora_iso())
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=t0, analizar=self._analizar_fake,
        )
        self.assertEqual([r.turn_id for r in resultados], ["t-nuevo"])
        self.assertEqual(resultados[0].estado, "guardado")

    def test_backfill_procesa_el_historico(self):
        _rollout_de_un_turno(
            self.sessions_dir / "rollout-viejo.jsonl",
            "t-viejo", "historico", timestamp="2026-01-01T00:00:00.000Z",
        )
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=None, analizar=self._analizar_fake,  # backfill: sin corte
        )
        self.assertEqual([r.turn_id for r in resultados], ["t-viejo"])
        self.assertEqual(resultados[0].estado, "guardado")

    def test_turno_sin_timestamp_es_historico_bajo_corte(self):
        # conservador (ADR-008): sin timestamp no entra por defecto…
        _rollout_de_un_turno(self.sessions_dir / "rollout-sin-ts.jsonl", "t-sints", "x")
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=datetime.now(timezone.utc), analizar=self._analizar_fake,
        )
        self.assertEqual(resultados, [])
        # …y en backfill sí (comportamiento pre-ADR-008 intacto)
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=None, analizar=self._analizar_fake,
        )
        self.assertEqual([r.turn_id for r in resultados], ["t-sints"])

    def test_timestamp_tz_naive_es_historico_y_no_tumba_el_ciclo(self):
        # ronda 5, H1: un timestamp parseable pero sin offset compararía
        # naive-vs-aware y revolvería el ciclo; la promesa es "no usable
        # → histórico"
        _rollout_de_un_turno(
            self.sessions_dir / "rollout-naive.jsonl",
            "t-naive", "x", timestamp="2026-08-20T10:00:00.123",
        )
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=datetime.now(timezone.utc), analizar=self._analizar_fake,
        )
        self.assertEqual(resultados, [])
        self.assertEqual(self.analizar_llamado, [])

    def test_turno_cerrado_exactamente_en_t0_se_procesa(self):
        # frontera inclusiva (ronda 5, H3): ts == t0 entra
        t0 = datetime.now(timezone.utc).replace(microsecond=0)
        en_t0 = t0.isoformat().replace("+00:00", "Z")
        _rollout_de_un_turno(
            self.sessions_dir / "rollout-en-t0.jsonl", "t-en-t0", "x",
            timestamp=en_t0,
        )
        resultados = ciclo(
            self.sessions_dir, coleccion=self.coleccion,
            t0=t0, analizar=self._analizar_fake,
        )
        self.assertEqual([r.turn_id for r in resultados], ["t-en-t0"])

    def test_banner_watch_command_distingue_modos(self):
        # ronda 5, H4: superficie declarada en ADR-008
        import io
        import skopos.vigilante as vigilante

        for argv, backfill in ((["--backfill"], True), ([], False)):
            with self.subTest(argv=argv):
                ejecutar_mock = mock.MagicMock()
                with mock.patch(
                    "skopos.vigilante.coleccion_local",
                    return_value=self.coleccion,
                ), mock.patch.object(
                    vigilante, "ejecutar", ejecutar_mock
                ), mock.patch("sys.stderr", new_callable=io.StringIO):
                    watch_command(argv)
                self.assertEqual(ejecutar_mock.call_count, 1)
                self.assertIs(ejecutar_mock.call_args.kwargs["backfill"], backfill)

    def test_prefiltro_mtime_salta_archivo_sin_actividad_sin_parsear(self):
        # optimización de descubrimiento: mtime anterior a t0 → ni se
        # procesa el archivo (el turno nuevo vive en OTRO archivo)
        import skopos.vigilante as vigilante

        antiguo = self.sessions_dir / "rollout-antiguo.jsonl"
        _rollout_de_un_turno(
            antiguo, "t-antiguo", "x", timestamp=_ahora_iso()
        )
        hace_un_dia = time.time() - 86400
        os.utime(antiguo, (hace_un_dia, hace_un_dia))

        fresco = self.sessions_dir / "rollout-fresco.jsonl"
        _rollout_de_un_turno(fresco, "t-fresco", "y", timestamp=_ahora_iso())

        procesados: list[str] = []
        procesar_real = vigilante.procesar_rollout

        def procesar_espia(path, **kwargs):
            procesados.append(Path(path).name)
            return procesar_real(path, **kwargs)

        with mock.patch.object(vigilante, "procesar_rollout", procesar_espia):
            ciclo(
                self.sessions_dir, coleccion=self.coleccion,
                t0=datetime.now(timezone.utc) - timedelta(seconds=60),
                analizar=self._analizar_fake,
            )
        self.assertEqual(procesados, ["rollout-fresco.jsonl"])

    def test_ejecutar_backfill_flag_restaura_comportamiento_previo(self):
        _rollout_de_un_turno(
            self.sessions_dir / "rollout-viejo.jsonl",
            "t-bf", "historico", timestamp="2026-01-01T00:00:00.000Z",
        )
        ciclos_vistos = []
        ejecutar(
            self.sessions_dir,
            coleccion=self.coleccion,
            intervalo=0,
            max_ciclos=1,
            on_ciclo=ciclos_vistos.append,
            backfill=True,
            analizar=self._analizar_fake,
        )
        self.assertEqual(ciclos_vistos[0][0].estado, "guardado")


if __name__ == "__main__":
    unittest.main()
