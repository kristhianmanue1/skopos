"""Comando `skopos indexar` — llena el índice de turnos sin llamar al modelo.

Implementa la fase de ingesta de P-004: recorre archivos de sesión por la
frontera de SPEC-006 y persiste los turnos observados en
`skopos.turnos` (CONTRATO documento-turno-mongo v1). No usa Ollama:
indexar es observar, no interpretar.

Va en comando propio y no dentro de `watch` a propósito (recomendación
aceptada 🔒 2026-08-28): el histórico es una operación masiva de una sola
vez, que hay que poder lanzar acotada, medir, parar y repetir.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from skopos.almacenamiento import DocumentoInvalido, coleccion_turnos, indexar_turno
from skopos.parseo import parsear
from skopos.vigilante import SESSIONS_DIR_POR_DEFECTO


class Resumen(Counter):
    """Conteos de una corrida: archivos por diagnóstico y turnos por destino."""


def indexar_ruta(path: Path, *, coleccion: Collection, resumen: Resumen) -> None:
    """Indexa los turnos de un archivo. Todo descarte queda contabilizado."""
    parseo = parsear(path)
    resumen[f"archivo:{parseo.diagnostico}"] += 1
    if parseo.diagnostico != "ok":
        return
    for turno in parseo.turnos:
        try:
            insertado = indexar_turno(turno, coleccion=coleccion)
        except DocumentoInvalido:
            resumen["turno:invalido"] += 1
            continue
        except PyMongoError as exc:
            resumen["turno:fallido"] += 1
            resumen[f"error:{type(exc).__name__}"] += 1
            continue
        resumen["turno:indexado" if insertado else "turno:ya_estaba"] += 1


def indexar(
    rutas: list[Path],
    *,
    coleccion: Collection,
    limite: int | None = None,
    on_progreso=None,
) -> Resumen:
    """Indexa una lista de archivos, opcionalmente acotada.

    `limite` corta por número de ARCHIVOS, no de turnos: un corte a mitad
    de archivo dejaría el índice con un prefijo arbitrario de una sesión,
    y el objetivo del piloto es medir sobre unidades completas.
    """
    resumen = Resumen()
    for indice, path in enumerate(rutas):
        if limite is not None and indice >= limite:
            resumen["archivo:no_visitado"] = len(rutas) - indice
            break
        indexar_ruta(path, coleccion=coleccion, resumen=resumen)
        if on_progreso:
            on_progreso(indice + 1, path, resumen)
    return resumen


def descubrir(directorios: list[Path], patron: str) -> list[Path]:
    encontrados: list[Path] = []
    for directorio in directorios:
        if directorio.is_dir():
            encontrados.extend(sorted(directorio.rglob(patron)))
        elif directorio.is_file():
            encontrados.append(directorio)
    return encontrados


def indexar_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="skopos indexar",
        description="Indexa turnos observados en skopos.turnos, sin llamar al modelo.",
    )
    parser.add_argument(
        "rutas", nargs="*", type=Path, default=[SESSIONS_DIR_POR_DEFECTO],
        help="archivos o directorios de sesión (por defecto: ~/.codex/sessions)",
    )
    parser.add_argument("--patron", default="*.jsonl",
                        help="patrón de archivos al recorrer directorios")
    parser.add_argument("--limite", type=int, default=None,
                        help="máximo de ARCHIVOS a visitar (para pilotos acotados)")
    parser.add_argument("--dry-run", action="store_true",
                        help="cuenta lo que haría sin escribir en Mongo")
    args = parser.parse_args(argv)

    rutas = descubrir(args.rutas or [SESSIONS_DIR_POR_DEFECTO], args.patron)
    if not rutas:
        print("no se encontró ningún archivo de sesión", file=sys.stderr)
        return 1

    if args.dry_run:
        resumen = Resumen()
        for path in rutas[: args.limite] if args.limite else rutas:
            parseo = parsear(path)
            resumen[f"archivo:{parseo.diagnostico}"] += 1
            resumen["turno:observado"] += len(parseo.turnos)
        _imprimir(resumen, len(rutas), 0.0, seco=True)
        return 0

    coleccion = coleccion_turnos()
    inicio = time.time()
    resumen = indexar(rutas, coleccion=coleccion, limite=args.limite)
    _imprimir(resumen, len(rutas), time.time() - inicio, seco=False)
    return 0


def _imprimir(resumen: Resumen, total: int, segundos: float, *, seco: bool) -> None:
    cabecera = "dry-run" if seco else f"{segundos:.1f}s"
    print(f"skopos indexar ({cabecera}): {total} archivo(s) descubierto(s)",
          file=sys.stderr)
    for clave in sorted(resumen):
        print(f"  {clave}: {resumen[clave]}", file=sys.stderr)
