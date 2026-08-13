"""Extrae turnos completos de un rollout de Codex.

Implementa SPEC-001 (docs/specs/f1-specs.md) y el CONTRATO
rollout-jsonl-de-codex v1 (docs/contratos/f1-contratos.md): lee un
rollout-*.jsonl línea por línea, descarta líneas corruptas sin detenerse,
y produce un Turno completo por cada cierre (event_msg/task_complete) no
visto antes, con el texto real de usuario y agente de ese turno.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Turno:
    turn_id: str
    session_id: str
    texto_usuario: str
    texto_agente: str
    timestamp_cierre: str | None
    ruta_origen: str
    offset_inicio: int
    offset_fin: int


def _iter_eventos_con_offsets(path: Path) -> Iterator[tuple[object, int, int]]:
    offset = 0
    with path.open("rb") as handle:
        for raw_line in handle:
            inicio = offset
            offset += len(raw_line)
            line = raw_line.strip()
            if not line:
                continue
            try:
                evento = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            yield evento, inicio, offset


_ROLES_CONVERSACION = {"user": "usuario", "assistant": "agente"}


def _texto_de_response_item(evento: object) -> tuple[str, str] | None:
    """Devuelve (rol, texto) para un mensaje real de usuario o agente.

    payload.type == "message" también aparece con role == "developer"
    (instrucciones de sistema/permisos inyectadas por Codex, no
    conversación) — se excluye deliberadamente, igual que cualquier otro
    rol que no sea user/assistant.
    """
    if not isinstance(evento, dict) or evento.get("type") != "response_item":
        return None
    payload = evento.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return None
    rol = _ROLES_CONVERSACION.get(payload.get("role"))
    if rol is None:
        return None
    partes = payload.get("content")
    if not isinstance(partes, list):
        return None
    contenido = "".join(
        parte.get("text", "")
        for parte in partes
        if isinstance(parte, dict) and parte.get("type") in {"input_text", "output_text"}
    )
    return rol, contenido


def _turn_id_si_cierre(evento: object) -> str | None:
    """Devuelve el turn_id sólo para el marcador empírico task_complete."""
    if not isinstance(evento, dict) or evento.get("type") != "event_msg":
        return None
    payload = evento.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "task_complete":
        return None
    turn_id = payload.get("turn_id")
    return turn_id if isinstance(turn_id, str) and turn_id else None


def extraer_turnos(path: Path | str) -> list[Turno]:
    """Extrae los turnos cerrados de un rollout completo, en orden."""
    path = Path(path)
    session_id = path.stem
    turnos: list[Turno] = []
    vistos: set[str] = set()
    texto_usuario_partes: list[str] = []
    texto_agente_partes: list[str] = []
    offset_inicio_turno = 0

    for evento, inicio, fin in _iter_eventos_con_offsets(path):
        texto = _texto_de_response_item(evento)
        if texto is not None:
            rol, contenido = texto
            if rol == "usuario":
                texto_usuario_partes.append(contenido)
            else:
                texto_agente_partes.append(contenido)
            continue

        turn_id = _turn_id_si_cierre(evento)
        if turn_id is None:
            continue
        if turn_id in vistos:
            # Cierre duplicado: el límite ya se registró antes. Se
            # descarta cualquier contenido acumulado desde entonces para
            # que no se filtre hacia el siguiente turno real.
            texto_usuario_partes = []
            texto_agente_partes = []
            offset_inicio_turno = fin
            continue
        vistos.add(turn_id)
        turnos.append(
            Turno(
                turn_id=turn_id,
                session_id=session_id,
                texto_usuario="".join(texto_usuario_partes),
                texto_agente="".join(texto_agente_partes),
                timestamp_cierre=evento.get("timestamp"),
                ruta_origen=str(path),
                offset_inicio=offset_inicio_turno,
                offset_fin=fin,
            )
        )
        texto_usuario_partes = []
        texto_agente_partes = []
        offset_inicio_turno = fin

    return turnos
