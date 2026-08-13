"""Conecta captura → análisis → almacenamiento para un rollout completo.

Implementa la máquina de estados de un turno (docs/f1-maquina-estados.md):
detectado → analizado → guardado, con "fallido" explícito si el análisis o
la persistencia fallan. Nunca se llega a "guardado" sin pasar por
"analizado", y un fallo nunca se confunde con un guardado silencioso.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from skopos.almacenamiento import existe_turn_id, guardar_analisis
from skopos.analisis import Analisis, AnalisisFallido, analizar_turno
from skopos.captura import extraer_turnos

ESTADOS_TERMINALES = {"guardado", "fallido", "omitido"}


@dataclass(frozen=True)
class ResultadoTurno:
    turn_id: str
    estado: str  # "guardado" | "fallido" | "omitido"
    motivo: str | None = None


def procesar_rollout(
    path: Path | str,
    *,
    coleccion: Collection,
    analizar: Callable[..., Analisis] = analizar_turno,
    guardar: Callable[..., dict] = guardar_analisis,
    ya_guardado: Callable[..., bool] = existe_turn_id,
    **kwargs_analisis,
) -> list[ResultadoTurno]:
    """Procesa todos los turnos cerrados de un rollout, uno por uno."""
    resultados: list[ResultadoTurno] = []
    for turno in extraer_turnos(path):
        if ya_guardado(turno.turn_id, coleccion=coleccion):
            resultados.append(ResultadoTurno(turno.turn_id, "omitido"))
            continue

        try:
            analisis = analizar(turno, **kwargs_analisis)
        except AnalisisFallido as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            continue

        try:
            guardar(analisis, coleccion=coleccion)
        except PyMongoError as exc:
            resultados.append(ResultadoTurno(turno.turn_id, "fallido", str(exc)))
            continue

        resultados.append(ResultadoTurno(turno.turn_id, "guardado"))
    return resultados
