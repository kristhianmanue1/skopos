"""Comando `skopos analyze` — la puerta del índice al análisis (ADR-017).

El hito 18 separó indexar de analyze, y la separación fue correcta:
indexar es barato y evita perder conversación; analyze cuesta ~19.6 s
por turn. Lo que nadie escribió es que esa separación dejó los turnos
ya indexados **sin ninguna vía hacia el análisis**: `indexar` no llama
al modelo (P-004), `watch` sólo cubre su ventana (ADR-008) y
`reanalizar` supersede un análisis existente (ADR-007), no crea el
primero. Este módulo es esa vía.

Lee de `skopos.turnos` y escribe en `skopos.analysis`. No vuelve a
tocar el archivo de origen: el document indexado guarda todo lo que
compone un Turno, así que reconstruirlo since Mongo funciona igual para
orígenes de archivo y de filas (ADR-012), donde no hay offsets que
releer.

Identificadores en inglés por ADR-018, que sustituyó el §(b) de ADR-016
para código nuevo. Comentarios y docstrings siguen en español, como fija
el mismo ADR.

Excepción razonada (ADR-018 permite conservar nombres con razón
documentada): las cadenas de outcome que devuelve `analyze_document`
—"analizado", "ya_analizado", "fallido_modelo"…— se quedan en español
porque son **el texto que el summary imprime al humano**, no claves de
un contrato, y `indexar` ya imprime "turno:indexado"/"archivo:ok" con la
misma forma. Traducirlas partiría en dos la salida de dos comandos
hermanos sin ganar nada.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from typing import Callable, Iterable, Iterator

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from skopos.almacenamiento import (
    DocumentoInvalido,
    coleccion_local,
    coleccion_turnos,
    existe_turn_id,
    guardar_analisis,
)
from skopos.analisis import (
    Analisis,
    AnalisisFallido,
    ErrorInfraestructura,
    analizar_turno,
)
from skopos.captura import Turno

# Medido en el entorno real con qwen3:8b (README, ADR-014). Sólo se usa
# para estimar el costo en --dry-run: nada del comportamiento depende.
SECONDS_PER_TURN = 19.6

TEXT_FIELDS = ("texto_usuario", "texto_agente")

# `analysis.py` ya distingue lo reintentable (ErrorInfraestructura: red,
# timeout, 429 del proveedor) de lo que no lo es (ErrorModelo: respondió
# pero sin campos válidos). Honrar esa distinción es del llamador, y no
# hacerlo costó 37 de 133 anclas en la primera corrida del piloto — todas
# por HTTP 429, todas recuperables con esperar.
DEFAULT_RETRIES = 3
BASE_BACKOFF_SECONDS = 5.0

# Pausa proactiva entre peticiones. Por defecto 0: el endpoint del plan
# aguantó 135 seguidas sin un solo rechazo, así que imponer espera a todo
# el mundo sería pagar por un problema que ese camino no tiene. Se sube
# cuando el proveedor cobra por tasa — molestarlo menos termina antes que
# reintentar a ciegas.
DEFAULT_PAUSE = 0.0


class Summary(Counter):
    """Conteos de una corrida, por outcome de cada turn."""


def turn_from_document(document: dict) -> Turno:
    """Reconstruye el Turno que se indexó, sin releer el origen.

    `ocurrido_en` vuelve a ser `timestamp_cierre`: son el mismo dato con
    el nombre que le toca a cada lado de la frontera (`_documento_turno`
    hace la conversión inversa).
    """
    origen_ids = document.get("origen_ids")
    return Turno(
        turn_id=document["turn_id"],
        session_id=document.get("session_id", ""),
        texto_usuario=document.get("texto_usuario", ""),
        texto_agente=document.get("texto_agente", ""),
        timestamp_cierre=document.get("ocurrido_en"),
        ruta_origen=document.get("ruta_origen", ""),
        offset_inicio=document.get("offset_inicio"),
        offset_fin=document.get("offset_fin"),
        cli=document.get("cli", ""),
        proyecto=document.get("proyecto"),
        fragmento_sha256=document.get("fragmento_sha256"),
        origen_tipo=document.get("origen_tipo", "archivo"),
        origen_tabla=document.get("origen_tabla"),
        origen_ids=tuple(origen_ids) if origen_ids else None,
    )


def build_filter(
    *,
    project: str | None = None,
    cli: str | None = None,
    anchor: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> dict:
    """Filtro de Mongo sobre los ejes que ya existen con índice (C-9).

    `since`/`until` comparan `ocurrido_en` como cadena: los timestamps se
    guardan en ISO 8601 con `Z`, donde el orden lexicográfico coincide
    con el cronológico. Un turn sin `ocurrido_en` queda fuera de
    cualquier time_range — no se le inventa una fecha.
    """
    query_filter: dict = {}
    if project:
        query_filter["proyecto"] = project
    if cli:
        query_filter["cli"] = cli
    if anchor:
        pattern = re.escape(anchor)
        query_filter["$or"] = [{field: {"$regex": pattern}} for field in TEXT_FIELDS]
    time_range = {}
    if since:
        time_range["$gte"] = since
    if until:
        time_range["$lte"] = until
    if time_range:
        query_filter["ocurrido_en"] = time_range
    return query_filter


def select_turns(
    query_filter: dict, *, index: Collection, limit: int | None = None
) -> Iterator[dict]:
    """Turnos del índice que cumplen el query_filter, ordenados por antigüedad.

    El orden estable importa en una corrida larga: si se interrumpe y se
    repite, se retoma por donde iba en vez de barajar lo ya hecho.
    """
    cursor = index.find(query_filter).sort("ocurrido_en", 1)
    if limit is not None:
        cursor = cursor.limit(limit)
    return cursor


def _analyze_with_retries(
    turn,
    *,
    analyze: Callable[..., Analisis],
    retries: int,
    sleep_for: Callable[[float], None],
    **analysis_kwargs,
) -> Analisis:
    """Reintenta sólo lo reintentable, con espera creciente.

    `ErrorModelo` no se reintenta: el contrato de `analysis.py` dice que
    volver a preguntar lo mismo probablemente falle igual, y gastar tres
    llamadas para confirmarlo es quemar cuota ajena.
    """
    for attempt in range(retries + 1):
        try:
            return analyze(turn, **analysis_kwargs)
        except ErrorInfraestructura:
            if attempt == retries:
                raise
            sleep_for(BASE_BACKOFF_SECONDS * (3 ** attempt))
    raise AssertionError("inalcanzable")


def analyze_document(
    document: dict,
    *,
    analysis_collection: Collection,
    analyze: Callable[..., Analisis] = analizar_turno,
    save: Callable[..., dict] = guardar_analisis,
    already_analyzed: Callable[..., bool] = existe_turn_id,
    retries: int = DEFAULT_RETRIES,
    sleep_for: Callable[[float], None] = time.sleep,
    **analysis_kwargs,
) -> str:
    """El outcome de UN turn del índice. Devuelve el conteo que le toca.

    ADR-017 (b): un turn que ya tiene análisis se omite y no se toca.
    Crear la segunda versión de un análisis es territorio exclusivo de
    `reanalizar` (ADR-007) — si dos superficies pudieran hacerlo, la
    traza de por qué existe cada versión dejaría de ser reconstruible.
    """
    turn_id = document.get("turn_id")
    if not turn_id:
        return "invalido"

    try:
        if already_analyzed(turn_id, coleccion=analysis_collection):
            return "ya_analizado"
    except PyMongoError:
        return "fallido"

    turn = turn_from_document(document)
    if not (turn.texto_usuario or turn.texto_agente):
        return "sin_contenido"

    try:
        analysis = _analyze_with_retries(
            turn, analyze=analyze, retries=retries, sleep_for=sleep_for,
            **analysis_kwargs,
        )
    except ErrorInfraestructura:
        # agotó los retries: el proveedor sigue sin responder
        return "fallido_infraestructura"
    except AnalisisFallido:
        return "fallido_modelo"

    try:
        save(analysis, coleccion=analysis_collection)
    except DuplicateKeyError:
        # otro proceso lo guardó entre el chequeo y esta escritura
        return "ya_analizado"
    except (PyMongoError, DocumentoInvalido):
        return "fallido"
    return "analizado"


def analyze_selection(
    documents: Iterable[dict],
    *,
    analysis_collection: Collection,
    on_progress: Callable[[int, dict, str], None] | None = None,
    pause: float = DEFAULT_PAUSE,
    sleep_for: Callable[[float], None] = time.sleep,
    **kwargs,
) -> Summary:
    """Corre la selección completa. Una corrida larga se puede interrumpir.

    `KeyboardInterrupt` no se traga: se devuelve lo hecho until ahí para
    que el summary sea verdadero, y se marca la corrida como partial.
    Lo ya guardado en Mongo queda guardado — la próxima corrida lo saltará
    por la regla de (b).
    """
    summary = Summary()
    for index, document in enumerate(documents, start=1):
        if pause and index > 1:
            sleep_for(pause)
        try:
            outcome = analyze_document(
                document, analysis_collection=analysis_collection,
                sleep_for=sleep_for, **kwargs
            )
        except KeyboardInterrupt:
            summary["interrumpido"] = 1
            break
        summary[outcome] += 1
        if on_progress:
            on_progress(index, document, outcome)
    return summary


def analyze_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="skopos analyze",
        description=(
            "Analiza turnos ya indexados que no tienen análisis todavía "
            "(ADR-017). No toca los que ya lo tienen: eso es reanalizar."
        ),
    )
    parser.add_argument("--project", default=None, help="filtra por eje de project")
    parser.add_argument("--cli", default=None, help="filtra por CLI de origen")
    parser.add_argument(
        "--anchor", default=None,
        help="sólo turnos cuyo texto contiene este literal (p. ej. commit-write-plan)",
    )
    parser.add_argument("--since", default=None, help="ocurrido_en >= (ISO 8601)")
    parser.add_argument("--until", default=None, help="ocurrido_en <= (ISO 8601)")
    parser.add_argument("--limit", type=int, default=None,
                        help="máximo de turnos a procesar")
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE,
                        help="seconds de espera entre peticiones; súbelo si "
                             "el proveedor cobra por tasa")
    parser.add_argument("--dry-run", action="store_true",
                        help="cuenta y estima el costo sin llamar al modelo")
    args = parser.parse_args(argv)

    query_filter = build_filter(
        project=args.project, cli=args.cli, anchor=args.anchor,
        since=args.since, until=args.until,
    )

    try:
        index = coleccion_turnos()
        analysis_collection = coleccion_local()
    except PyMongoError as exc:
        print(f"no se pudo conectar a Mongo: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        return _dry_run(query_filter, index=index, limit=args.limit)

    started = time.time()
    summary = analyze_selection(
        select_turns(query_filter, index=index, limit=args.limit),
        analysis_collection=analysis_collection,
        on_progress=_progress,
        pause=args.pause,
    )
    _print_summary(summary, time.time() - started)
    failures = summary["fallido_infraestructura"] + summary["fallido_modelo"]
    return 1 if failures else 0


def _dry_run(query_filter: dict, *, index: Collection, limit: int | None) -> int:
    total = index.count_documents(query_filter, **({"limit": limit} if limit else {}))
    hours = total * SECONDS_PER_TURN / 3600
    print(f"skopos analyze (dry-run): {total} turno(s) seleccionado(s)",
          file=sys.stderr)
    print(f"  costo estimado: {hours:.1f} h serial "
          f"(a {SECONDS_PER_TURN:.1f} s/turno)", file=sys.stderr)
    print("  nota: no descuenta los que ya tengan análisis; ésos se omiten "
          "al correr de verdad", file=sys.stderr)
    return 0


def _progress(index: int, document: dict, outcome: str) -> None:
    if outcome == "analizado" or index % 10 == 0:
        print(f"  [{index}] {document.get('turn_id', '?')}: {outcome}",
              file=sys.stderr)


def _print_summary(summary: Summary, seconds: float) -> None:
    partial = " — INTERRUMPIDA" if summary.get("interrumpido") else ""
    print(f"skopos analyze ({seconds:.1f}s){partial}:", file=sys.stderr)
    for key in sorted(summary):
        if key != "interrumpido":
            print(f"  {key}: {summary[key]}", file=sys.stderr)
