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

    def _avanzar(turno: Turno) -> None:
        nonlocal avance
        if not congelado:
            avance = turno.offset_fin

    for turno in parseo.turnos:
        if not _cerrado_desde(turno, desde):
            # histórico no invitado (ADR-008): no se procesa, pero
            # tampoco hay nada que reintentar en él
            _avanzar(turno)
            continue

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
            _avanzar(turno)
            continue

        try:
            visto = ya_guardado(turno.turn_id, coleccion=coleccion)
        except PyMongoError as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", f"dedup falló: {exc}"))
            congelado = True
            continue
        if visto:
            resultados.append(ResultadoTurno(turno.turn_id, "omitido"))
            _avanzar(turno)
            continue

        if _contenido_insuficiente(turno):
            resultados.append(
                ResultadoTurno(turno.turn_id, "omitido", "sin contenido significativo")
            )
            _avanzar(turno)
            continue

        try:
            analisis = analizar(turno, **kwargs_analisis)
        except AnalisisFallido as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            congelado = True
            continue

        try:
            guardar(analisis, coleccion=coleccion)
        except DuplicateKeyError:
            # otro proceso guardó este turn_id entre el chequeo y esta escritura
            resultados.append(ResultadoTurno(turno.turn_id, "omitido", "duplicado concurrente"))
            _avanzar(turno)
            continue
        except (PyMongoError, DocumentoInvalido) as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            congelado = True
            continue

        resultados.append(ResultadoTurno(turno.turn_id, "guardado"))
        _avanzar(turno)

    if on_cursor is not None and avance is not None and parseo.instantanea is not None:
        on_cursor(Path(path), Cursor(avance, sellar_prefijo(parseo.instantanea, avance)))
    return resultados
