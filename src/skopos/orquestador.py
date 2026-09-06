"""Conecta captura → análisis → almacenamiento para un rollout completo.

Implementa la máquina de estados de un turno (docs/f1-maquina-estados.md):
detectado → analizado → guardado, con "fallido" explícito si el análisis o
la persistencia fallan. Nunca se llega a "guardado" sin pasar por
"analizado", y un fallo nunca se confunde con un guardado silencioso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from skopos.almacenamiento import (
    DocumentoInvalido,
    existe_turn_id,
    guardar_analisis,
    indexar_turno,
)
from skopos.analisis import Analisis, AnalisisFallido, analizar_turno
from skopos.captura import Turno
from skopos.cursor import Cursor
from skopos.parseo import ResultadoParseo, parsear, sellar_prefijo

ESTADOS_TERMINALES = {"guardado", "fallido", "omitido"}

LONGITUD_MINIMA_CONTENIDO = 1  # 0 = turno totalmente vacío; no vale una llamada a Ollama


@dataclass(frozen=True)
class ResultadoTurno:
    turn_id: str
    estado: str  # "guardado" | "fallido" | "omitido"
    motivo: str | None = None


def _parsear_timestamp(valor: object) -> datetime | None:
    """Parsea el timestamp ISO 8601 del evento (con `Z`); None si no se puede.

    Python 3.9 no parsea `Z` con `fromisoformat` (nota de implementación
    del ADR-008): se sustituye por `+00:00`.
    """
    if not isinstance(valor, str) or not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def _cerrado_desde(turno: Turno, desde: datetime | None) -> bool:
    """ADR-008: corte por timestamp_cierre. Sin timestamp se trata como
    histórico (conservador — documentado en el ADR); `desde=None`
    (backfill) procesa todo. Un timestamp tz-naive (parseable pero sin
    offset) también es histórico: compararlo contra `desde` (aware)
    revienta el ciclo completo, y la promesa es "no parseable →
    histórico" (ronda 5, H1)."""
    if desde is None:
        return True
    ts = _parsear_timestamp(turno.timestamp_cierre)
    return ts is not None and ts.tzinfo is not None and ts >= desde


def _contenido_insuficiente(turno: Turno) -> bool:
    return len(turno.texto_usuario) + len(turno.texto_agente) < LONGITUD_MINIMA_CONTENIDO


def _ejecutar_pipeline(
    turno: Turno,
    *,
    coleccion: Collection,
    analizar: Callable[..., Analisis],
    guardar: Callable[..., dict],
    ya_guardado: Callable[..., bool],
    desde: datetime | None,
    indice: Collection | None,
    on_indexado: Callable[[Turno, bool | None], None] | None,
    solo_indice: bool,
    **kwargs_analisis,
) -> tuple[ResultadoTurno | None, bool]:
    """El destino de UN turno: ventana → índice → dedup → análisis → guardado.

    Devuelve `(resultado, avanzar)`. `resultado=None` significa "no hay
    nada que reportar" (fuera de ventana, u observación en solo_indice).
    `avanzar=False` exactamente cuando el turno terminó en `fallido`:
    lo que falló debe ofrecerse de nuevo (ADR-011). El avance concreto
    es cosa de cada llamada: byte offset en archivos, marca de agua en
    orígenes de filas (ADR-013).
    """
    if not _cerrado_desde(turno, desde):
        # histórico no invitado (ADR-008): no se procesa, pero
        # tampoco hay nada que reintentar en él
        return None, True

    if indice is not None:
        # una escritura del índice que falle no puede tumbar el
        # análisis: se reporta y se sigue (el índice es aditivo)
        try:
            insertado = indexar_turno(turno, coleccion=indice)
        except (PyMongoError, DocumentoInvalido):
            insertado = None
        if on_indexado is not None:
            on_indexado(turno, insertado)

    if solo_indice:
        return None, True

    try:
        visto = ya_guardado(turno.turn_id, coleccion=coleccion)
    except PyMongoError as exc:
        return ResultadoTurno(turno.turn_id, "fallido", f"dedup falló: {exc}"), False
    if visto:
        return ResultadoTurno(turno.turn_id, "omitido"), True

    if _contenido_insuficiente(turno):
        return (
            ResultadoTurno(turno.turn_id, "omitido", "sin contenido significativo"),
            True,
        )

    try:
        analisis = analizar(turno, **kwargs_analisis)
    except AnalisisFallido as exc:
        return ResultadoTurno(turno.turn_id, "fallido", str(exc)), False

    try:
        guardar(analisis, coleccion=coleccion)
    except DuplicateKeyError:
        # otro proceso guardó este turn_id entre el chequeo y esta escritura
        return ResultadoTurno(turno.turn_id, "omitido", "duplicado concurrente"), True
    except (PyMongoError, DocumentoInvalido) as exc:
        return ResultadoTurno(turno.turn_id, "fallido", str(exc)), False

    return ResultadoTurno(turno.turn_id, "guardado"), True


def procesar_rollout(
    path: Path | str,
    *,
    coleccion: Collection,
    analizar: Callable[..., Analisis] = analizar_turno,
    guardar: Callable[..., dict] = guardar_analisis,
    ya_guardado: Callable[..., bool] = existe_turn_id,
    desde: datetime | None = None,
    on_diagnostico: Callable[[Path, ResultadoParseo], None] | None = None,
    cursor: Cursor | None = None,
    on_cursor: Callable[[Path, Cursor], None] | None = None,
    indice: Collection | None = None,
    on_indexado: Callable[[Turno, bool | None], None] | None = None,
    solo_indice: bool = False,
    **kwargs_analisis,
) -> list[ResultadoTurno]:
    """Procesa los turnos cerrados de un rollout, uno por uno.

    La entrada pasa por la frontera de SPEC-006 (`parsear`), no por el
    parser de Codex directamente: un archivo cuya identidad no casa se
    descarta con diagnóstico, nunca se parsea "por parecido" (ADR-010
    §4). `on_diagnostico` recibe SIEMPRE el `ResultadoParseo` del
    archivo —incluido el `ok`— para que todo descarte sea contabilizable
    y atribuible (ADR-010 §3); sin él, el descarte sigue siendo correcto
    pero silencioso, así que el vigilante lo pasa siempre.

    `desde` (ADR-008, decisión 8): si está presente, sólo se procesan los
    turnos cerrados a partir de ese instante; los anteriores quedan fuera
    de la ventana sin producir resultado (no son "omitidos" — nunca se
    les consultó a la dedup; son históricos no invitados).

    `cursor`/`on_cursor` (ADR-011): lectura incremental. **El cursor sólo
    avanza sobre turnos que llegaron a un desenlace que no exige
    reintento**: se detiene en el primer `fallido`, porque un turno cuyo
    análisis falló no está en Mongo, y adelantarlo significaría no
    volver a verlo nunca — el cursor pasaría de caché inofensiva a
    pérdida silenciosa de datos.

    `indice` (P-004): si está presente, cada turno **dentro de la
    ventana** se indexa antes de analizarse. Indexar no llama al modelo y
    no depende de que el análisis funcione: un Ollama caído deja el turno
    guardado como observación aunque no llegue a interpretarse. Los
    turnos fuera de la ventana de ADR-008 **no** se indexan aquí — el
    histórico es trabajo de `skopos indexar`, no un backfill encubierto
    del vigilante.

    `solo_indice`: observa sin interpretar — indexa y no llama al modelo
    ni a la dedup de análisis. El cursor **sí avanza**: el turno quedó
    guardado como observación, así que no hay nada que reintentar. La
    consecuencia se declara: esos turnos no volverán a ofrecerse al
    análisis por relectura; analizarlos será trabajo de una pasada sobre
    el índice, que es la forma que P-004 eligió (recordar todo,
    interpretar lo que haga falta).
    """
    parseo = parsear(path, cursor=cursor)
    if on_diagnostico is not None:
        on_diagnostico(Path(path), parseo)
    if parseo.diagnostico != "ok":
        return []

    resultados: list[ResultadoTurno] = []
    avance: int | None = None  # hasta dónde puede avanzar el cursor (ADR-011)
    congelado = False  # un fallido congela el avance: hay que reintentarlo

    for turno in parseo.turnos:
        resultado, avanzar = _ejecutar_pipeline(
            turno,
            coleccion=coleccion,
            analizar=analizar,
            guardar=guardar,
            ya_guardado=ya_guardado,
            desde=desde,
            indice=indice,
            on_indexado=on_indexado,
            solo_indice=solo_indice,
            **kwargs_analisis,
        )
        if resultado is not None:
            resultados.append(resultado)
            if resultado.estado == "fallido":
                congelado = True
        if avanzar and not congelado:
            avance = turno.offset_fin

    if on_cursor is not None and avance is not None and parseo.instantanea is not None:
        on_cursor(Path(path), Cursor(avance, sellar_prefijo(parseo.instantanea, avance)))
    return resultados


def procesar_base_filas(
    path: Path | str,
    *,
    coleccion: Collection,
    marca: int | None,
    analizar: Callable[..., Analisis] = analizar_turno,
    guardar: Callable[..., dict] = guardar_analisis,
    ya_guardado: Callable[..., bool] = existe_turn_id,
    desde: datetime | None = None,
    indice: Collection | None = None,
    on_indexado: Callable[[Turno, bool | None], None] | None = None,
    solo_indice: bool = False,
    **kwargs_analisis,
) -> tuple[list[ResultadoTurno], int | None]:
    """Procesa los turnos cerrados que aporta una pasada delta de filas.

    Es el gemelo de `procesar_rollout` para orígenes de filas (ADR-013):
    mismo pipeline por turno (`_ejecutar_pipeline`), distinto mecanismo
    de avance — la **marca de agua** (`marca` → `extraer_delta`) en vez
    del byte offset. La marca que se devuelve es la nueva propuesta de
    la delta, **salvo que algún turno haya fallado**: entonces se
    devuelve la marca recibida, para que la ventana completa se vuelva a
    ofrecer en el siguiente ciclo y lo fallido no se pierda nunca (la
    misma regla de congelamiento de ADR-011, con otra unidad de avance).
    El dedup en Mongo hace idempotente el re-tránsito de lo ya guardado
    (ADR-005): re-ofrecer cuesta consultas, jamás duplicados.

    `marca=None` es cold start o backfill: la lectura completa (18 s
    medidos), que es exactamente lo que el encargo pide releer.
    """
    from skopos.opencode import extraer_delta

    extraccion, marca_propuesta = extraer_delta(Path(path), marca)

    resultados: list[ResultadoTurno] = []
    congelado = False
    for turno in extraccion.turnos:
        resultado, _avanzar = _ejecutar_pipeline(
            turno,
            coleccion=coleccion,
            analizar=analizar,
            guardar=guardar,
            ya_guardado=ya_guardado,
            desde=desde,
            indice=indice,
            on_indexado=on_indexado,
            solo_indice=solo_indice,
            **kwargs_analisis,
        )
        if resultado is not None:
            resultados.append(resultado)
            if resultado.estado == "fallido":
                congelado = True

    return resultados, (marca if congelado else marca_propuesta)
