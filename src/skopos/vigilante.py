"""Vigila ~/.codex/sessions/ y procesa turnos nuevos (REQ-1, REQ-6).

Reutiliza el mecanismo de descubrimiento del prototipo original
(kratos/prototypes/conversation_observer/codex_rollout_watcher.py) pero,
a diferencia de él, sí analiza y persiste el contenido de cada turno — el
prototipo detectaba el cierre y deliberadamente no leía el texto.

La deduplicación entre ciclos vive en Mongo, no en un cursor local
(ADR-005): cada ciclo relee los rollouts completos, pero
`procesar_rollout` omite los turnos cuyo turn_id ya está guardado.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import Callable

from pymongo.collection import Collection

from skopos.almacenamiento import coleccion_local
from skopos.orquestador import ResultadoTurno, procesar_rollout

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
    **kwargs_procesar,
) -> list[ResultadoTurno]:
    """Un barrido completo: procesa los turnos nuevos de todos los rollouts."""
    resultados: list[ResultadoTurno] = []
    for path in sorted(descubrir(sessions_dir)):
        resultados.extend(procesar_rollout(path, coleccion=coleccion, **kwargs_procesar))
    return resultados


def ejecutar(
    sessions_dir: Path = SESSIONS_DIR_POR_DEFECTO,
    *,
    coleccion: Collection,
    intervalo: float = INTERVALO_POR_DEFECTO,
    on_ciclo: Callable[[list[ResultadoTurno]], None] | None = None,
    max_ciclos: int | None = None,
    **kwargs_procesar,
) -> None:
    """Corre el vigilante hasta SIGTERM/SIGINT (o max_ciclos, para pruebas)."""
    detener = False

    def _parar(_signum: int, _frame: object) -> None:
        nonlocal detener
        detener = True

    anterior_term = signal.signal(signal.SIGTERM, _parar)
    anterior_int = signal.signal(signal.SIGINT, _parar)
    try:
        ciclos = 0
        while not detener:
            resultados = ciclo(sessions_dir, coleccion=coleccion, **kwargs_procesar)
            if on_ciclo:
                on_ciclo(resultados)
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


def watch_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skopos watch")
    parser.add_argument("--sessions-dir", type=Path, default=SESSIONS_DIR_POR_DEFECTO)
    parser.add_argument("--intervalo", type=float, default=INTERVALO_POR_DEFECTO)
    args = parser.parse_args(argv)

    coleccion = coleccion_local()
    print(
        f"skopos watch: vigilando {args.sessions_dir} cada {args.intervalo}s "
        "(Ctrl+C para detener)",
        file=sys.stderr,
    )
    ejecutar(
        args.sessions_dir,
        coleccion=coleccion,
        intervalo=args.intervalo,
        on_ciclo=_reportar_ciclo,
    )
    return 0
