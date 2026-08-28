"""Adaptador parser-kimi-code/v1 (fase B de P-003, contrato ADR-010).

Fuente: `~/.kimi/sessions/<workspace>/<sesión>/wire.jsonl` — el log del
protocolo, que es el **único** archivo con la conversación y el tiempo
juntos. El `context.jsonl` de la misma carpeta tiene el contenido pero
**cero** timestamps, y correlacionar ambos rompería la frontera por
archivo de SPEC-006: se descarta como fuente (ver evidencia).

Es el único adaptador del registro con **marcas explícitas de turno**
(`TurnBegin`/`TurnEnd`), como el `task_complete` de Codex.

Evidencia y decisiones de ficha:
`docs/evidencia/ficha-kimi-code-2026-08-28.md`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from skopos.captura import Extraccion, Turno, _sellar_fragmento, iter_lineas


# --- Ficha del adaptador (ADR-010 §2 y §8; constantes declaradas) ------

ID_FICHA = "parser-kimi-code/v1"
CLI_PRODUCTO = "kimi-code"
VERSION_PARSER = "parser-kimi-code/v1"
VERSION_FORMATO = "kimi-wire/v1"

# Identidad: línea de cabecera `{"type":"metadata","protocol_version":…}`.
# Evidencia: 381/381 positivos; 0 falsos positivos sobre 1,523 ajenos,
# incluidos los 452 `context*.jsonl` del propio kimi.
LINEAS_ESCANEO_IDENTIDAD = 10
EVENTO_IDENTIDAD = "metadata"

# `protocol_version` es la versión del FORMATO del wire. Observadas en el
# corpus: 1.3, 1.7, 1.9, 1.10 — todas con el mismo vocabulario de turno,
# así que v1 del parser las soporta y no declara incompatibilidad; el
# día que una versión rompa el vocabulario, la ficha la excluye aquí.
VERSIONES_SOPORTADAS = ("1.3", "1.7", "1.9", "1.10")

MENSAJE_INICIO = "TurnBegin"
MENSAJE_FIN = "TurnEnd"
MENSAJE_CONTENIDO = "ContentPart"
TIPOS_DECLARADOS = frozenset(
    {MENSAJE_INICIO, MENSAJE_FIN, MENSAJE_CONTENIDO, "ToolCall", "ToolResult",
     "ToolCallPart", "StepBegin", "StepInterrupted", "StatusUpdate",
     "SubagentEvent", "Notification", "ApprovalRequest", "ApprovalResponse",
     "CompactionBegin"}
)
# `think` es razonamiento del modelo, no diálogo (19,364 partes contra
# 3,629 de texto) — misma decisión de ficha que en cline (ADR-010 §6).
PARTES_CONVERSACION = frozenset({"text"})


def _evento(raw_line: bytes) -> dict | None:
    line = raw_line.strip()
    if not line:
        return None
    try:
        evento = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return evento if isinstance(evento, dict) else None


def casa_identidad(instantanea: bytes) -> bool:
    """Predicado de identidad de la ficha (alcance: 10 líneas)."""
    for indice, (raw_line, _ini, _fin) in enumerate(iter_lineas(instantanea)):
        if indice >= LINEAS_ESCANEO_IDENTIDAD:
            return False
        evento = _evento(raw_line)
        if evento is None:
            continue
        if evento.get("type") == EVENTO_IDENTIDAD and isinstance(
            evento.get("protocol_version"), str
        ):
            return True
    return False


def es_incompatible(instantanea: bytes) -> bool:
    """Marcador explícito de versión del formato fuera de las soportadas.

    Predicado positivo del tipo (i) de ADR-010 §1: el archivo declara su
    `protocol_version`. Una versión no listada se diagnostica
    `version_no_soportada` en vez de parsearse a ciegas.
    """
    for indice, (raw_line, _ini, _fin) in enumerate(iter_lineas(instantanea)):
        if indice >= LINEAS_ESCANEO_IDENTIDAD:
            return False
        evento = _evento(raw_line)
        if evento is None or evento.get("type") != EVENTO_IDENTIDAD:
            continue
        version = evento.get("protocol_version")
        return isinstance(version, str) and version not in VERSIONES_SOPORTADAS
    return False


def _timestamp_iso(marca: object) -> str | None:
    """`timestamp` epoch en segundos (float) → ISO 8601 UTC con `Z`.

    Igual que en cline: servido como número, ADR-008 no lo parsea y
    trata el turno como histórico, con lo que **ningún turno de kimi
    entraría** fuera de `--backfill`. La conversión es de la ficha.
    """
    if isinstance(marca, str) and marca:
        return marca
    if isinstance(marca, (int, float)) and marca > 0:
        try:
            momento = datetime.fromtimestamp(float(marca), timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return momento.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return None


def _texto_de_usuario(payload: object) -> str:
    """Texto del `user_input` que abre el turno.

    `user_input` aparece en dos formas en el corpus: lista de partes
    (523 observadas) y **string suelto** (99) — típicamente la
    instrucción inicial del agente. Se aceptan ambas; ignorar la segunda
    dejaba 363 turnos con `texto_usuario` vacío.
    """
    if not isinstance(payload, dict):
        return ""
    entradas = payload.get("user_input")
    if isinstance(entradas, str):
        return entradas
    if not isinstance(entradas, list):
        return ""
    return "".join(
        parte.get("text", "")
        for parte in entradas
        if isinstance(parte, dict) and parte.get("type") in PARTES_CONVERSACION
    )


def _texto_de_agente(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("type") not in PARTES_CONVERSACION:
        return ""
    return payload.get("text", "") or ""


def extraer_de_instantanea(
    instantanea: bytes, path: Path, desde: int = 0
) -> Extraccion:
    """Extrae los turnos cerrados por `TurnEnd` (contrato SPEC-006).

    `session_id` es el nombre de la carpeta de la sesión, no el del
    archivo: todos los wire se llaman `wire.jsonl`.
    """
    session_id = path.parent.name or path.stem
    turnos: list[Turno] = []
    eventos_no_reconocidos = 0
    descartes_linea = 0
    version_cli_observada: str | None = None

    turn_id: str | None = None
    inicio = desde
    usuario: list[str] = []
    agente: list[str] = []
    timestamp: str | None = None
    ordinal = 0

    for raw_line, ini, fin in iter_lineas(instantanea, desde):
        if not raw_line.strip():
            continue
        evento = _evento(raw_line)
        if evento is None:
            descartes_linea += 1
            continue

        if evento.get("type") == EVENTO_IDENTIDAD:
            version = evento.get("protocol_version")
            if isinstance(version, str):
                version_cli_observada = version
            continue

        mensaje = evento.get("message")
        if not isinstance(mensaje, dict):
            continue
        tipo = mensaje.get("type")
        if isinstance(tipo, str) and tipo not in TIPOS_DECLARADOS:
            eventos_no_reconocidos += 1
            continue

        marca = _timestamp_iso(evento.get("timestamp"))
        if marca is not None:
            timestamp = marca

        if tipo == MENSAJE_INICIO:
            ordinal += 1
            # identidad calificada (ADR-010 §7). El wire no da id de
            # turno: se usa el ordinal dentro del archivo, estable
            # porque el log es de sólo-anexado — declarado en la ficha.
            turn_id = f"{CLI_PRODUCTO}:{session_id}:{ordinal}"
            inicio = ini
            usuario = [_texto_de_usuario(mensaje.get("payload"))]
            agente = []
            continue

        if turn_id is None:
            continue

        if tipo == MENSAJE_CONTENIDO:
            agente.append(_texto_de_agente(mensaje.get("payload")))
            continue

        if tipo == MENSAJE_FIN:
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
                    # `proyecto` ausente por declaración de ficha: el wire
                    # no expone cwd, y deducirlo de la ruta del archivo
                    # está prohibido (ADR-010 §2)
                    proyecto=None,
                    fragmento_sha256=_sellar_fragmento(instantanea, inicio, fin),
                )
            )
            turn_id = None
            usuario, agente = [], []

    return Extraccion(
        turnos=turnos,
        eventos_no_reconocidos=eventos_no_reconocidos,
        descartes_linea=descartes_linea,
        version_cli_observada=version_cli_observada,
    )
