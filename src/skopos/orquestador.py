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
from pymongo.errors import DuplicateKeyError, PyMongoError

from skopos.almacenamiento import DocumentoInvalido, existe_turn_id, guardar_analisis
from skopos.analisis import Analisis, AnalisisFallido, analizar_turno
from skopos.captura import Turno, extraer_turnos

ESTADOS_TERMINALES = {"guardado", "fallido", "omitido"}

LONGITUD_MINIMA_CONTENIDO = 1  # 0 = turno totalmente vacío; no vale una llamada a Ollama


@dataclass(frozen=True)
class ResultadoTurno:
    turn_id: str
    estado: str  # "guardado" | "fallido" | "omitido"
    motivo: str | None = None


def _contenido_insuficiente(turno: Turno) -> bool:
    return len(turno.texto_usuario) + len(turno.texto_agente) < LONGITUD_MINIMA_CONTENIDO


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
