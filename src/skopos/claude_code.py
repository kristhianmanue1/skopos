"""Adaptador parser-claude-code/v1 (fase B de P-003, contrato ADR-010).

Ficha del adaptador: identidad, marcas, fuentes de cada campo y —lo que
distingue a este formato— un **predicado de cierre derivado**, porque
claude-code no emite una marca de cierre fiable.

Evidencia del reconocimiento y de las dos decisiones de ficha:
`docs/evidencia/ficha-claude-code-2026-08-28.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

from skopos.captura import (  # tipos normalizados del contrato (ADR-010 §5)
    Extraccion,
    Turno,
    _proyecto_de_cwd,
    _sellar_fragmento,
    iter_lineas,
)


# --- Ficha del adaptador (ADR-010 §2 y §8; constantes declaradas) ------

ID_FICHA = "parser-claude-code/v1"
CLI_PRODUCTO = "claude-code"
VERSION_PARSER = "parser-claude-code/v1"
VERSION_FORMATO = "claude-code-transcript/v1"

# Identidad: una línea de la cabecera con la forma propia del harness —
# `sessionId`+`uuid`+`version` más al menos una marca suya. Evidencia:
# 205/205 positivos y 0 falsos positivos sobre 2,187 archivos ajenos
# (codex 643, kimi 1,494, qwen 47, cline 3).
LINEAS_ESCANEO_IDENTIDAD = 10
CLAVES_IDENTIDAD = frozenset({"sessionId", "uuid", "version"})
MARCAS_HARNESS = frozenset({"isSidechain", "userType", "entrypoint"})

# Tipos declarados por la ficha (lo demás se cuenta como aditivo).
EVENTOS_DECLARADOS = frozenset(
    {"user", "assistant", "system", "attachment", "queue-operation", "mode"}
)

ROLES_CONVERSACION = {"user": "usuario", "assistant": "agente"}


def _es_linea_de_identidad(evento: object) -> bool:
    if not isinstance(evento, dict):
        return False
    if not CLAVES_IDENTIDAD.issubset(evento.keys()):
        return False
    return bool(MARCAS_HARNESS & evento.keys())


def casa_identidad(instantanea: bytes) -> bool:
    """Predicado de identidad de la ficha (ADR-010 §1, alcance: 10 líneas)."""
    for indice, (raw_line, _inicio, _fin) in enumerate(iter_lineas(instantanea)):
        if indice >= LINEAS_ESCANEO_IDENTIDAD:
            return False
        line = raw_line.strip()
        if not line:
            continue
        try:
            evento = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if _es_linea_de_identidad(evento):
            return True
    return False


def es_incompatible(instantanea: bytes) -> bool:
    """Predicados positivos de incompatibilidad declarados en v1: ninguno.

    El corpus observado abarca 16 versiones del harness (2.1.187 →
    2.1.237) con la misma forma de línea; no hay marcador de versión del
    **formato** ni firma de otra versión registrada. Igual que en
    parser-codex/v1, `version_no_soportada` es inalcanzable para este
    adaptador salvo por retiro (ADR-010 §8).
    """
    return False


def _texto_de_mensaje(evento: dict) -> tuple[str, str] | None:
    """(rol, texto) de un mensaje conversacional real.

    Excluye lo que no es conversación con la persona: `isSidechain`
    (transcripciones de subagentes), `isMeta`, y —crítico— los eventos
    `type: "user"` cuyo contenido es sólo `tool_result`: en este formato
    los resultados de herramienta vuelven como mensajes de usuario, y
    son el **90 %** de ellos (7,167 de 7,965 en el reconocimiento).
    Tratarlos como voz del usuario multiplicaría los turnos por nueve.
    """
    if evento.get("isSidechain") or evento.get("isMeta"):
        return None
    rol = ROLES_CONVERSACION.get(evento.get("type"))
    if rol is None:
        return None
    mensaje = evento.get("message")
    if not isinstance(mensaje, dict):
        return None
    contenido = mensaje.get("content")
    if isinstance(contenido, str):
        return (rol, contenido) if contenido.strip() else None
    if not isinstance(contenido, list):
        return None
    partes = [
        bloque.get("text", "")
        for bloque in contenido
        if isinstance(bloque, dict) and bloque.get("type") == "text"
    ]
    texto = "".join(partes)
    return (rol, texto) if texto.strip() else None


def _abre_turno(evento: dict) -> bool:
    """Un turno empieza en un mensaje real de la persona.

    **Cierre derivado, declarado**: claude-code no emite marca fiable de
    fin de turno — `subtype: turn_duration` existe pero sólo en 68 de
    205 archivos y, donde existe, cuenta MENOS turnos que los reales
    (9 usuarios vs 4 marcas en un archivo del corpus): usarlo perdería
    turnos en silencio. Por eso el turno va de un mensaje de usuario al
    siguiente, y **el último turno de una sesión viva no cierra** hasta
    que llegue el mensaje siguiente — se observa en el ciclo siguiente,
    igual que un rollout de Codex sin `task_complete` todavía.
    """
    texto = _texto_de_mensaje(evento)
    return texto is not None and texto[0] == "usuario"


def _identidad_calificada(uuid: object) -> str | None:
    """`{cli_producto}:{id_bruto}` — ID calificado por defecto (ADR-010 §7).

    El id crudo es la excepción que Codex se ganó con evidencia de
    unicidad; todo adaptador nuevo califica. El `uuid` del mensaje que
    abre el turno es estable entre relecturas del mismo archivo.
    """
    if not isinstance(uuid, str) or not uuid:
        return None
    return f"{CLI_PRODUCTO}:{uuid}"


def extraer_de_instantanea(
    instantanea: bytes, path: Path, desde: int = 0
) -> Extraccion:
    """Extrae los turnos cerrados de una instantánea (contrato SPEC-006)."""
    session_id = path.stem
    turnos: list[Turno] = []
    eventos_no_reconocidos = 0
    descartes_linea = 0
    version_cli_observada: str | None = None

    # turno en curso
    turn_id: str | None = None
    inicio: int = desde
    usuario: list[str] = []
    agente: list[str] = []
    proyecto: str | None = None
    timestamp: str | None = None

    def cerrar(fin: int) -> None:
        nonlocal turn_id, usuario, agente, proyecto, timestamp
        if turn_id is None:
            return
        turnos.append(
            Turno(
                turn_id=turn_id,
                session_id=session_id,
                texto_usuario="".join(usuario),
                texto_agente="".join(agente),
                timestamp_cierre=timestamp,
                ruta_origen=str(path),
                offset_inicio=inicio,
                offset_fin=fin,
                cli=CLI_PRODUCTO,
                proyecto=proyecto,
                fragmento_sha256=_sellar_fragmento(instantanea, inicio, fin),
            )
        )
        turn_id = None
        usuario = []
        agente = []

    for raw_line, ini, fin in iter_lineas(instantanea, desde):
        line = raw_line.strip()
        if not line:
            continue
        try:
            evento = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            descartes_linea += 1
            continue
        if not isinstance(evento, dict):
            continue

        if version_cli_observada is None and isinstance(evento.get("version"), str):
            version_cli_observada = evento["version"]

        tipo = evento.get("type")
        if isinstance(tipo, str) and tipo not in EVENTOS_DECLARADOS:
            eventos_no_reconocidos += 1
            continue

        if _abre_turno(evento):
            cerrar(ini)  # el turno anterior termina donde empieza este
            nuevo = _identidad_calificada(evento.get("uuid"))
            if nuevo is None:
                continue
            turn_id = nuevo
            inicio = ini
            proyecto = (
                _proyecto_de_cwd(evento["cwd"])
                if isinstance(evento.get("cwd"), str)
                else None
            )
            timestamp = evento.get("timestamp")

        if turn_id is None:
            continue
        texto = _texto_de_mensaje(evento)
        if texto is not None:
            rol, contenido = texto
            (usuario if rol == "usuario" else agente).append(contenido)
        if isinstance(evento.get("timestamp"), str):
            timestamp = evento["timestamp"]

    # el turno en curso NO se cierra: sin marca de fin, sólo lo cierra el
    # mensaje siguiente (se verá en el ciclo siguiente)
    return Extraccion(
        turnos=turnos,
        eventos_no_reconocidos=eventos_no_reconocidos,
        descartes_linea=descartes_linea,
        version_cli_observada=version_cli_observada,
    )
