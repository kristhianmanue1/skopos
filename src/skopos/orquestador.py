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

from skopos.almacenamiento import DocumentoInvalido, existe_turn_id, guardar_analisis
from skopos.analisis import Analisis, AnalisisFallido, analizar_turno
from skopos.captura import Turno
from skopos.parseo import ResultadoParseo, parsear

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
    """
    parseo = parsear(path)
    if on_diagnostico is not None:
        on_diagnostico(Path(path), parseo)
    if parseo.diagnostico != "ok":
        return []

    resultados: list[ResultadoTurno] = []
    for turno in parseo.turnos:
        if not _cerrado_desde(turno, desde):
            continue

        try:
            visto = ya_guardado(turno.turn_id, coleccion=coleccion)
        except PyMongoError as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", f"dedup falló: {exc}"))
            continue
        if visto:
            resultados.append(ResultadoTurno(turno.turn_id, "omitido"))
            continue

        if _contenido_insuficiente(turno):
            resultados.append(
                ResultadoTurno(turno.turn_id, "omitido", "sin contenido significativo")
            )
            continue

        try:
            analisis = analizar(turno, **kwargs_analisis)
        except AnalisisFallido as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            continue

        try:
            guardar(analisis, coleccion=coleccion)
        except DuplicateKeyError:
            # otro proceso guardó este turn_id entre el chequeo y esta escritura
            resultados.append(ResultadoTurno(turno.turn_id, "omitido", "duplicado concurrente"))
            continue
        except (PyMongoError, DocumentoInvalido) as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            continue

        resultados.append(ResultadoTurno(turno.turn_id, "guardado"))
    return resultados
