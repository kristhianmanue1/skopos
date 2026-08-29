"""Vigila ~/.codex/sessions/ y procesa turnos nuevos (REQ-1, REQ-6).

Reutiliza el mecanismo de descubrimiento del prototipo original
(kratos/prototypes/conversation_observer/codex_rollout_watcher.py) pero,
a diferencia de él, sí analiza y persiste el contenido de cada turno — el
prototipo detectaba el cierre y deliberadamente no leía el texto.

La deduplicación entre ciclos vive en Mongo, no en un cursor local
(ADR-005): cada ciclo relee los rollouts completos, pero
`procesar_rollout` omite los turnos cuyo turn_id ya está guardado.

Política de arranque (ADR-008, decisión 8, 🔒 2026-08-20): por defecto
arranca "desde ahora" — sólo procesa turnos cerrados a partir del
instante de arranque (`t0`); el histórico exige `--backfill` explícito.
`t0` es un filtro de descubrimiento; la dedup sigue viviendo en Mongo.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pymongo.collection import Collection

from skopos.almacenamiento import coleccion_local, coleccion_turnos
from skopos.cursor import AlmacenCursores
from skopos.orquestador import ResultadoTurno, procesar_rollout
from skopos.parseo import ResultadoParseo

SESSIONS_DIR_POR_DEFECTO = Path.home() / ".codex" / "sessions"
INTERVALO_POR_DEFECTO = 5.0


def descubrir_rollouts(sessions_dir: Path) -> set[Path]:
    if not sessions_dir.is_dir():
        return set()
    return set(sessions_dir.rglob("*.jsonl"))


def ciclo(
    sessions_dir: Path,
    *,
    coleccion: Collection,
    descubrir: Callable[[Path], set[Path]] = descubrir_rollouts,
    t0: datetime | None = None,
    on_diagnostico: Callable[[Path, ResultadoParseo], None] | None = None,
    cursores: AlmacenCursores | None = None,
    indice=None,
    on_indexado=None,
    **kwargs_procesar,
) -> list[ResultadoTurno]:
    """Un barrido completo: procesa los turnos nuevos de todos los rollouts.

    Con `t0` (ADR-008), los archivos sin actividad (mtime) posterior a
    `t0` se saltan sin parsear — optimización de descubrimiento: un
    archivo intacto desde antes de `t0` no puede contener turnos
    cerrados después (skew mtime↔evento medido en 0.0 s, ronda 4). El
    filtro semántivo por turno vive en `procesar_rollout(desde=…)`.

    `cursores` (ADR-011) evita reparsear lo ya procesado de cada archivo.
    Se pasa **sólo fuera de backfill**: un backfill es por definición
    "reléelo todo", y honrar cursores ahí saltaría precisamente el
    histórico que se pidió recuperar.
    """
    resultados: list[ResultadoTurno] = []
    descubiertos = sorted(descubrir(sessions_dir))
    if cursores is not None:
        cursores.podar(descubiertos)
    for path in descubiertos:
        if t0 is not None:
            try:
                if path.stat().st_mtime < t0.timestamp():
                    continue
            except OSError:
                continue
        resultados.extend(
            procesar_rollout(
                path,
                coleccion=coleccion,
                desde=t0,
                on_diagnostico=on_diagnostico,
                cursor=cursores.obtener(path) if cursores else None,
                on_cursor=cursores.actualizar if cursores else None,
                indice=indice,
                on_indexado=on_indexado,
                **kwargs_procesar,
            )
        )
    if cursores is not None:
        cursores.guardar()
    return resultados


def ejecutar(
    sessions_dir: Path = SESSIONS_DIR_POR_DEFECTO,
    *,
    coleccion: Collection,
    intervalo: float = INTERVALO_POR_DEFECTO,
    on_ciclo: Callable[[list[ResultadoTurno]], None] | None = None,
    on_diagnosticos: Callable[[Counter], None] | None = None,
    max_ciclos: int | None = None,
    backfill: bool = False,
    indice=None,
    **kwargs_procesar,
) -> None:
    """Corre el vigilante hasta SIGTERM/SIGINT (o max_ciclos, para pruebas).

    ADR-008: `backfill=False` (por defecto) arranca "desde ahora" — t0
    es el instante de arranque; `backfill=True` restaura el comportamiento
    previo (todo turno no guardado, sin distinción histórica).
    """
    t0 = None if backfill else datetime.now(timezone.utc)
    # ADR-011: sin cursores en backfill — releerlo todo es el encargo
    cursores = None if backfill else AlmacenCursores().cargar()
    detener = False

    def _parar(_signum: int, _frame: object) -> None:
        nonlocal detener
        detener = True

    anterior_term = signal.signal(signal.SIGTERM, _parar)
    anterior_int = signal.signal(signal.SIGINT, _parar)
    try:
        ciclos = 0
        while not detener:
            diagnosticos: Counter[str] = Counter()
            indexados: Counter[str] = Counter()

            def _contar(_path: Path, parseo: ResultadoParseo) -> None:
                diagnosticos[parseo.diagnostico] += 1

            def _contar_indice(_turno, insertado: bool | None) -> None:
                if insertado is None:
                    indexados["fallido"] += 1
                else:
                    indexados["indexado" if insertado else "ya_estaba"] += 1

            resultados = ciclo(
                sessions_dir,
                coleccion=coleccion,
                t0=t0,
                on_diagnostico=_contar,
                cursores=cursores,
                indice=indice,
                on_indexado=_contar_indice if indice is not None else None,
                **kwargs_procesar,
            )
            if on_ciclo:
                on_ciclo(resultados)
            if on_diagnosticos:
                on_diagnosticos(diagnosticos)
            if indice is not None and (indexados["indexado"] or indexados["fallido"]):
                print(
                    f"ciclo: índice — {indexados['indexado']} turno(s) nuevo(s)"
                    + (f", {indexados['fallido']} fallido(s)" if indexados["fallido"] else ""),
                    file=sys.stderr,
                )
            ciclos += 1
            if max_ciclos is not None and ciclos >= max_ciclos:
                break
            time.sleep(intervalo)
    finally:
        signal.signal(signal.SIGTERM, anterior_term)
        signal.signal(signal.SIGINT, anterior_int)


def _reportar_ciclo(resultados: list[ResultadoTurno]) -> None:
    if not resultados:
        return
    guardados = sum(1 for r in resultados if r.estado == "guardado")
    fallidos = [r for r in resultados if r.estado == "fallido"]
    print(f"ciclo: {guardados} guardado(s), {len(fallidos)} fallido(s)", file=sys.stderr)
    for r in fallidos:
        print(f"  fallido {r.turn_id}: {r.motivo}", file=sys.stderr)


def _reportar_diagnosticos(diagnosticos: Counter) -> None:
    """ADR-010 §3: todo descarte es contabilizable y atribuible.

    Un archivo que la frontera no acepta nunca baja en silencio; los
    `ok` no se reportan (son el caso normal, y su conteo por ciclo sería
    ruido en cada barrido).
    """
    descartes = {d: n for d, n in diagnosticos.items() if d != "ok"}
    if not descartes:
        return
    detalle = ", ".join(f"{d}: {n}" for d, n in sorted(descartes.items()))
    print(f"ciclo: archivos descartados — {detalle}", file=sys.stderr)


def watch_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skopos watch")
    parser.add_argument("--sessions-dir", type=Path, default=SESSIONS_DIR_POR_DEFECTO)
    parser.add_argument("--intervalo", type=float, default=INTERVALO_POR_DEFECTO)
    parser.add_argument(
        "--sin-indice",
        action="store_true",
        help="no indexa los turnos observados (P-004); por defecto sí lo hace, "
        "porque indexar no llama al modelo y es lo que evita perder conversación",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="procesa también el histórico no guardado (por defecto: sólo turnos "
        "cerrados desde el arranque — ADR-008)",
    )
    args = parser.parse_args(argv)

    coleccion = coleccion_local()
    indice = None if args.sin_indice else coleccion_turnos()
    modo = (
        "backfill: procesará TODO turno no guardado"
        if args.backfill
        else "desde ahora: sólo turnos cerrados a partir de este arranque (ADR-008); "
        "use --backfill para el histórico"
    )
    print(
        f"skopos watch: vigilando {args.sessions_dir} cada {args.intervalo}s "
        f"— {modo}"
        + ("" if indice is None else "; indexando turnos observados (P-004)")
        + " (Ctrl+C para detener)",
        file=sys.stderr,
    )
    ejecutar(
        args.sessions_dir,
        coleccion=coleccion,
        intervalo=args.intervalo,
        on_ciclo=_reportar_ciclo,
        on_diagnosticos=_reportar_diagnosticos,
        backfill=args.backfill,
        indice=indice,
    )
    return 0
