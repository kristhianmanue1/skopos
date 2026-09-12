"""Comando `skopos analyze` — la puerta del índice al análisis (ADR-017).

El hito 18 separó indexar de analizar, y la separación fue correcta:
indexar es barato y evita perder conversación; analizar cuesta ~19.6 s
por turno. Lo que nadie escribió es que esa separación dejó los turnos
ya indexados **sin ninguna vía hacia el análisis**: `indexar` no llama
al modelo (P-004), `watch` sólo cubre su ventana (ADR-008) y
`reanalizar` supersede un análisis existente (ADR-007), no crea el
primero. Este módulo es esa vía.

Lee de `skopos.turnos` y escribe en `skopos.analisis`. No vuelve a
tocar el archivo de origen: el documento indexado guarda todo lo que
compone un Turno, así que reconstruirlo desde Mongo funciona igual para
orígenes de archivo y de filas (ADR-012), donde no hay offsets que
releer.

Nombre y flags en inglés por ADR-016 (frontera); el interior sigue en
español.
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
SEGUNDOS_POR_TURNO = 19.6

CAMPOS_DE_TEXTO = ("texto_usuario", "texto_agente")

# `analisis.py` ya distingue lo reintentable (ErrorInfraestructura: red,
# timeout, 429 del proveedor) de lo que no lo es (ErrorModelo: respondió
# pero sin campos válidos). Honrar esa distinción es del llamador, y no
# hacerlo costó 37 de 133 anclas en la primera corrida del piloto — todas
# por HTTP 429, todas recuperables con esperar.
REINTENTOS_POR_DEFECTO = 3
ESPERA_BASE_SEGUNDOS = 5.0

# Pausa proactiva entre peticiones. Por defecto 0: el endpoint del plan
# aguantó 135 seguidas sin un solo rechazo, así que imponer espera a todo
# el mundo sería pagar por un problema que ese camino no tiene. Se sube
# cuando el proveedor cobra por tasa — molestarlo menos termina antes que
# reintentar a ciegas.
PAUSA_POR_DEFECTO = 0.0


class Resumen(Counter):
    """Conteos de una corrida, por destino de cada turno."""


def turno_desde_documento(documento: dict) -> Turno:
    """Reconstruye el Turno que se indexó, sin releer el origen.

    `ocurrido_en` vuelve a ser `timestamp_cierre`: son el mismo dato con
    el nombre que le toca a cada lado de la frontera (`_documento_turno`
    hace la conversión inversa).
    """
    origen_ids = documento.get("origen_ids")
    return Turno(
        turn_id=documento["turn_id"],
        session_id=documento.get("session_id", ""),
        texto_usuario=documento.get("texto_usuario", ""),
        texto_agente=documento.get("texto_agente", ""),
        timestamp_cierre=documento.get("ocurrido_en"),
        ruta_origen=documento.get("ruta_origen", ""),
        offset_inicio=documento.get("offset_inicio"),
        offset_fin=documento.get("offset_fin"),
        cli=documento.get("cli", ""),
        proyecto=documento.get("proyecto"),
        fragmento_sha256=documento.get("fragmento_sha256"),
        origen_tipo=documento.get("origen_tipo", "archivo"),
        origen_tabla=documento.get("origen_tabla"),
        origen_ids=tuple(origen_ids) if origen_ids else None,
    )


def construir_filtro(
    *,
    proyecto: str | None = None,
    cli: str | None = None,
    ancla: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict:
    """Filtro de Mongo sobre los ejes que ya existen con índice (C-9).

    `desde`/`hasta` comparan `ocurrido_en` como cadena: los timestamps se
    guardan en ISO 8601 con `Z`, donde el orden lexicográfico coincide
    con el cronológico. Un turno sin `ocurrido_en` queda fuera de
    cualquier rango — no se le inventa una fecha.
    """
    filtro: dict = {}
    if proyecto:
        filtro["proyecto"] = proyecto
    if cli:
        filtro["cli"] = cli
    if ancla:
        patron = re.escape(ancla)
        filtro["$or"] = [{campo: {"$regex": patron}} for campo in CAMPOS_DE_TEXTO]
    rango = {}
    if desde:
        rango["$gte"] = desde
    if hasta:
        rango["$lte"] = hasta
    if rango:
        filtro["ocurrido_en"] = rango
    return filtro


def seleccionar(
    filtro: dict, *, indice: Collection, limite: int | None = None
) -> Iterator[dict]:
    """Turnos del índice que cumplen el filtro, ordenados por antigüedad.

    El orden estable importa en una corrida larga: si se interrumpe y se
    repite, se retoma por donde iba en vez de barajar lo ya hecho.
    """
    cursor = indice.find(filtro).sort("ocurrido_en", 1)
    if limite is not None:
        cursor = cursor.limit(limite)
    return cursor


def _analizar_con_reintentos(
    turno,
    *,
    analizar: Callable[..., Analisis],
    reintentos: int,
    dormir: Callable[[float], None],
    **kwargs_analisis,
) -> Analisis:
    """Reintenta sólo lo reintentable, con espera creciente.

    `ErrorModelo` no se reintenta: el contrato de `analisis.py` dice que
    volver a preguntar lo mismo probablemente falle igual, y gastar tres
    llamadas para confirmarlo es quemar cuota ajena.
    """
    for intento in range(reintentos + 1):
        try:
            return analizar(turno, **kwargs_analisis)
        except ErrorInfraestructura:
            if intento == reintentos:
                raise
            dormir(ESPERA_BASE_SEGUNDOS * (3 ** intento))
    raise AssertionError("inalcanzable")


def analizar_documento(
    documento: dict,
    *,
    analisis_coleccion: Collection,
    analizar: Callable[..., Analisis] = analizar_turno,
    guardar: Callable[..., dict] = guardar_analisis,
    ya_analizado: Callable[..., bool] = existe_turn_id,
    reintentos: int = REINTENTOS_POR_DEFECTO,
    dormir: Callable[[float], None] = time.sleep,
    **kwargs_analisis,
) -> str:
    """El destino de UN turno del índice. Devuelve el conteo que le toca.

    ADR-017 (b): un turno que ya tiene análisis se omite y no se toca.
    Crear la segunda versión de un análisis es territorio exclusivo de
    `reanalizar` (ADR-007) — si dos superficies pudieran hacerlo, la
    traza de por qué existe cada versión dejaría de ser reconstruible.
    """
    turn_id = documento.get("turn_id")
    if not turn_id:
        return "invalido"

    try:
        if ya_analizado(turn_id, coleccion=analisis_coleccion):
            return "ya_analizado"
    except PyMongoError:
        return "fallido"

    turno = turno_desde_documento(documento)
    if not (turno.texto_usuario or turno.texto_agente):
        return "sin_contenido"

    try:
        analisis = _analizar_con_reintentos(
            turno, analizar=analizar, reintentos=reintentos, dormir=dormir,
            **kwargs_analisis,
        )
    except ErrorInfraestructura:
        # agotó los reintentos: el proveedor sigue sin responder
        return "fallido_infraestructura"
    except AnalisisFallido:
        return "fallido_modelo"

    try:
        guardar(analisis, coleccion=analisis_coleccion)
    except DuplicateKeyError:
        # otro proceso lo guardó entre el chequeo y esta escritura
        return "ya_analizado"
    except (PyMongoError, DocumentoInvalido):
        return "fallido"
    return "analizado"


def analizar_seleccion(
    documentos: Iterable[dict],
    *,
    analisis_coleccion: Collection,
    on_progreso: Callable[[int, dict, str], None] | None = None,
    pausa: float = PAUSA_POR_DEFECTO,
    dormir: Callable[[float], None] = time.sleep,
    **kwargs,
) -> Resumen:
    """Corre la selección completa. Una corrida larga se puede interrumpir.

    `KeyboardInterrupt` no se traga: se devuelve lo hecho hasta ahí para
    que el resumen sea verdadero, y se marca la corrida como parcial.
    Lo ya guardado en Mongo queda guardado — la próxima corrida lo saltará
    por la regla de (b).
    """
    resumen = Resumen()
    for indice, documento in enumerate(documentos, start=1):
        if pausa and indice > 1:
            dormir(pausa)
        try:
            destino = analizar_documento(
                documento, analisis_coleccion=analisis_coleccion,
                dormir=dormir, **kwargs
            )
        except KeyboardInterrupt:
            resumen["interrumpido"] = 1
            break
        resumen[destino] += 1
        if on_progreso:
            on_progreso(indice, documento, destino)
    return resumen


def analyze_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="skopos analyze",
        description=(
            "Analiza turnos ya indexados que no tienen análisis todavía "
            "(ADR-017). No toca los que ya lo tienen: eso es reanalizar."
        ),
    )
    parser.add_argument("--project", default=None, help="filtra por eje de proyecto")
    parser.add_argument("--cli", default=None, help="filtra por CLI de origen")
    parser.add_argument(
        "--anchor", default=None,
        help="sólo turnos cuyo texto contiene este literal (p. ej. commit-write-plan)",
    )
    parser.add_argument("--since", default=None, help="ocurrido_en >= (ISO 8601)")
    parser.add_argument("--until", default=None, help="ocurrido_en <= (ISO 8601)")
    parser.add_argument("--limit", type=int, default=None,
                        help="máximo de turnos a procesar")
    parser.add_argument("--pause", type=float, default=PAUSA_POR_DEFECTO,
                        help="segundos de espera entre peticiones; súbelo si "
                             "el proveedor cobra por tasa")
    parser.add_argument("--dry-run", action="store_true",
                        help="cuenta y estima el costo sin llamar al modelo")
    args = parser.parse_args(argv)

    filtro = construir_filtro(
        proyecto=args.project, cli=args.cli, ancla=args.anchor,
        desde=args.since, hasta=args.until,
    )

    try:
        indice = coleccion_turnos()
        analisis_coleccion = coleccion_local()
    except PyMongoError as exc:
        print(f"no se pudo conectar a Mongo: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        return _dry_run(filtro, indice=indice, limite=args.limit)

    inicio = time.time()
    resumen = analizar_seleccion(
        seleccionar(filtro, indice=indice, limite=args.limit),
        analisis_coleccion=analisis_coleccion,
        on_progreso=_progreso,
        pausa=args.pause,
    )
    _imprimir(resumen, time.time() - inicio)
    fallos = resumen["fallido_infraestructura"] + resumen["fallido_modelo"]
    return 1 if fallos else 0


def _dry_run(filtro: dict, *, indice: Collection, limite: int | None) -> int:
    total = indice.count_documents(filtro, **({"limit": limite} if limite else {}))
    horas = total * SEGUNDOS_POR_TURNO / 3600
    print(f"skopos analyze (dry-run): {total} turno(s) seleccionado(s)",
          file=sys.stderr)
    print(f"  costo estimado: {horas:.1f} h serial "
          f"(a {SEGUNDOS_POR_TURNO:.1f} s/turno)", file=sys.stderr)
    print("  nota: no descuenta los que ya tengan análisis; ésos se omiten "
          "al correr de verdad", file=sys.stderr)
    return 0


def _progreso(indice: int, documento: dict, destino: str) -> None:
    if destino == "analizado" or indice % 10 == 0:
        print(f"  [{indice}] {documento.get('turn_id', '?')}: {destino}",
              file=sys.stderr)


def _imprimir(resumen: Resumen, segundos: float) -> None:
    parcial = " — INTERRUMPIDA" if resumen.get("interrumpido") else ""
    print(f"skopos analyze ({segundos:.1f}s){parcial}:", file=sys.stderr)
    for clave in sorted(resumen):
        if clave != "interrumpido":
            print(f"  {clave}: {resumen[clave]}", file=sys.stderr)
