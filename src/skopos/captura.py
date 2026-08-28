"""Adaptador parser-codex/v1: extrae turnos de un rollout de Codex.

Implementa SPEC-001 (docs/specs/f1-specs.md) y el CONTRATO
rollout-jsonl-de-codex v1 (docs/contratos/f1-contratos.md), y es el
**adaptador de referencia** del contrato parser-contrato/v1 (ADR-010):
declara aquí, como constantes, la ficha que el §8 del ADR registra —
identidad, marcas de estructura, alcance del escaneo, fuentes de
`session_id`/`turn_id`/`timestamp_cierre` y estrategia de identidad.
La selección de este adaptador NO vive aquí (sería fallback por
defecto, ADR-010 §4): vive en la frontera de SPEC-006, `parseo.py`.

Este módulo opera sobre la **instantánea materializada** de bytes que
esa frontera produce (ADR-010 §5): una sola lectura, offsets y sello
sobre el mismo buffer. `extraer_turnos(path)` se conserva como entrada
directa de SPEC-001 (orquestador, `skopos reanalizar`) y materializa la
instantánea por su cuenta.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# --- Ficha del adaptador (ADR-010 §2 y §8; constantes declaradas) ------

ID_FICHA = "parser-codex/v1"
CLI_PRODUCTO = "codex-cli"  # nombre tal como lo identifica escrubery (EV-7 de F0)
CLI_ORIGEN = CLI_PRODUCTO  # nombre histórico del campo `cli` del Turno
VERSION_PARSER = "parser-codex/v1"
VERSION_FORMATO = "codex-rollout/v1"

# Identidad: primer `session_meta` dentro de las primeras 10 líneas con
# `payload.originator` de frontera cerrada (`codexfoo` no casa).
# Evidencia: docs/evidencia/predicado-identidad-codex-2026-08-20.md
# (616/616 positivos, 11/11 controles negativos sobre 2 formatos ajenos).
LINEAS_ESCANEO_IDENTIDAD = 10
EVENTO_IDENTIDAD = "session_meta"
PATRON_ORIGINATOR = re.compile(r"^codex([ _-]|$)", re.IGNORECASE)

# Marcas de estructura (rol: extracción y cierre — NO reconocen versión;
# v1 es perfil base por ausencia de firma incompatible, ronda 13 F-4).
EVENTOS_DECLARADOS = frozenset(
    {EVENTO_IDENTIDAD, "turn_context", "response_item", "event_msg"}
)
EVENTO_CIERRE = "event_msg"
PAYLOAD_CIERRE = "task_complete"

# Roles excluidos del texto conversacional (decisión de ficha, ADR-010 §6).
ROLES_CONVERSACION = {"user": "usuario", "assistant": "agente"}


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
    cli: str = CLI_PRODUCTO
    proyecto: str | None = None
    fragmento_sha256: str | None = None  # sello P4a (ADR-009)


@dataclass(frozen=True)
class Extraccion:
    """Lo que el adaptador produce de una instantánea (ADR-010 §3).

    Los conteos son disjuntos por definición: `eventos_no_reconocidos`
    cuenta JSON válido de tipo no declarado por la ficha (evolución
    aditiva, nunca incompatibilidad); `descartes_linea`, líneas que no
    son JSON válido dentro de una instantánea que sí lo es.
    """

    turnos: list[Turno]
    eventos_no_reconocidos: int
    descartes_linea: int
    version_cli_observada: str | None


def _sellar_fragmento(instantanea: bytes, offset_inicio: int, offset_fin: int) -> str:
    """sha256 de los bytes [inicio, fin) de la instantánea (ADR-009 P4a).

    Sello fragmento-only sobre la MISMA instantánea de la que salieron
    los offsets (ADR-010 §5): antes se releía el archivo por rango, lo
    que el ADR declaró no conforme — dos lecturas podían no ver los
    mismos bytes. El tamaño no se sella aparte: es `fin - inicio` por
    construcción, y los turnos teselan el archivo.
    """
    return hashlib.sha256(instantanea[offset_inicio:offset_fin]).hexdigest()


def _proyecto_de_cwd(cwd: str) -> str | None:
    """basename(cwd) sólo si cwd identifica un subdirectorio de trabajo.

    Regla C-9 con muestreo del corpus real detrás
    (docs/evidencia/muestreo-cwd-c9-2026-08-20.md): un cwd genérico
    (~/www, ~/Documents, $HOME) o fuera de $HOME produce None — para el
    filtro por proyecto, un valor presente sin significado es peor que
    ninguno.
    """
    if not cwd:
        return None
    home = os.path.expanduser("~")
    try:
        rel = Path(cwd).relative_to(home)
    except ValueError:
        return None
    partes = rel.parts
    if len(partes) < 2 or partes[-1] in {".", ".."}:
        return None
    return partes[-1]


def _proyecto_de_turn_context(evento: object) -> str | None | type(...) :
    """Deriva el proyecto del turn_context; (...) si el evento no es
    turn_context (para no resetear el proyecto heredado en ese caso) y
    None si es turn_context cuyo cwd no deriva proyecto (reset explícito
    — ronda adversarial de Fase 1, hallazgo H1: un cwd que deja de
    identificar proyecto nunca hereda el del turno anterior).
    """
    if not isinstance(evento, dict) or evento.get("type") != "turn_context":
        return ...
    payload = evento.get("payload")
    if not isinstance(payload, dict):
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        return None
    return _proyecto_de_cwd(cwd)


def iter_lineas(instantanea: bytes, desde: int = 0) -> Iterator[tuple[bytes, int, int]]:
    """(línea, offset_inicio, offset_fin) en bytes de la instantánea.

    Corta **sólo** por `\n`, igual que iterar el descriptor de archivo:
    `bytes.splitlines()` cortaría también por `\r`, `\v`, `\f` y otros
    separadores, y eso movería offsets y sellos respecto de lo ya
    guardado (JSON válido no lleva esos bytes crudos, pero la
    equivalencia no debe depender de esa suposición).
    """
    offset = desde
    total = len(instantanea)
    while offset < total:
        salto = instantanea.find(b"\n", offset)
        fin = total if salto == -1 else salto + 1
        yield instantanea[offset:fin], offset, fin
        offset = fin


def _iter_eventos_con_offsets(
    instantanea: bytes, desde: int = 0
) -> Iterator[tuple[object | None, int, int]]:
    """Eventos JSON con sus offsets; `None` marca una línea descartada.

    Las líneas en blanco no son ni evento ni descarte: no llevan
    contenido que contar (SPEC-001 las ignora desde F2).
    """
    for raw_line, inicio, fin in iter_lineas(instantanea, desde):
        line = raw_line.strip()
        if not line:
            continue
        try:
            yield json.loads(line), inicio, fin
        except (UnicodeDecodeError, json.JSONDecodeError):
            yield None, inicio, fin


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
    rol = ROLES_CONVERSACION.get(payload.get("role"))
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


def calificar(session_id: str, turn_id_bruto: str) -> str:
    """`{cli_producto}:{session_id}:{turn_id}` — identidad calificada.

    ADR-010 §7 permitió a este adaptador el **id crudo** como excepción
    probabilística, "revisable a calificada si aparece un
    contraejemplo". Apareció: sobre el corpus real, 16,301 turnos dan
    sólo 10,441 `turn_id` distintos —el id se repite entre sesiones, con
    texto distinto— así que la dedup descartaría el 35 % de los turnos
    (`docs/evidencia/colision-turn-id-codex-2026-08-28.md`). Calificar
    con la sesión da 16,301 ids únicos y 0 colisiones.

    La gramática es la del §7: el **primer** dos puntos delimita el
    producto, que por construcción no lleva ninguno; lo de después es el
    id bruto tal cual, sin escapes.
    """
    return f"{CLI_PRODUCTO}:{session_id}:{turn_id_bruto}"


def _turn_id_si_cierre(evento: object) -> str | None:
    """Devuelve el turn_id crudo sólo para el marcador task_complete.

    La calificación la aplica el extractor, que es quien conoce la
    sesión.
    """
    if not isinstance(evento, dict) or evento.get("type") != EVENTO_CIERRE:
        return None
    payload = evento.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != PAYLOAD_CIERRE:
        return None
    turn_id = payload.get("turn_id")
    return turn_id if isinstance(turn_id, str) and turn_id else None


def casa_identidad(instantanea: bytes) -> bool:
    """Predicado de identidad de la ficha (ADR-010 §1, alcance: 10 líneas).

    Frontera de palabra completa por construcción del patrón; un
    originator futuro que no la respete cae en `formato_desconocido`
    (observable), nunca en un match por parecido.
    """
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
        if not isinstance(evento, dict) or evento.get("type") != EVENTO_IDENTIDAD:
            continue
        payload = evento.get("payload")
        if not isinstance(payload, dict):
            return False
        originator = payload.get("originator")
        return isinstance(originator, str) and bool(PATRON_ORIGINATOR.match(originator))
    return False


def es_incompatible(instantanea: bytes) -> bool:
    """Predicados positivos de incompatibilidad de la ficha v1: ninguno.

    Declarado así en ADR-010 §8 y verificado (ronda 12, H-3):
    `session_meta.payload` no declara versión del formato, no existe
    firma de otra versión registrada y v1 no declara estructuras
    obligatorias. `version_no_soportada` es inalcanzable para este
    adaptador salvo por retiro (§8). Sin predicado positivo, no hay
    incompatibilidad: devolver siempre False es la ficha, no un atajo.
    """
    return False


def _cli_version(evento: object) -> str | None:
    if not isinstance(evento, dict) or evento.get("type") != EVENTO_IDENTIDAD:
        return None
    payload = evento.get("payload")
    if not isinstance(payload, dict):
        return None
    version = payload.get("cli_version")
    return version if isinstance(version, str) and version else None


def _proyecto_heredado(instantanea: bytes, desde: int) -> str | None:
    """El `proyecto` vigente al llegar al offset `desde`.

    Estado que cruza la frontera incremental (ADR-011): `proyecto` no
    viene del turno, viene del último `turn_context` que lo precede — y
    ése puede estar antes del cursor. Sin esto, toda lectura incremental
    produciría `proyecto=None` y el eje de proyecto de C-9 se degradaría
    en silencio, que es peor que no tener cursor.

    Se busca hacia atrás la última línea con la marca, sin parsear el
    prefijo entero: es una búsqueda de bytes, no un parseo de JSON.
    """
    marca = b'"turn_context"'
    fin = desde
    while True:
        pos = instantanea.rfind(marca, 0, fin)
        if pos == -1:
            return None
        inicio_linea = instantanea.rfind(b"\n", 0, pos) + 1
        fin_linea = instantanea.find(b"\n", pos)
        if fin_linea == -1 or fin_linea > desde:
            fin_linea = desde
        try:
            evento = json.loads(instantanea[inicio_linea:fin_linea].strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            fin = inicio_linea
            continue
        proyecto = _proyecto_de_turn_context(evento)
        if proyecto is not ...:
            return proyecto
        fin = inicio_linea


def version_cli_de_instantanea(instantanea: bytes) -> str | None:
    """`cli_version` del `session_meta` de cabecera (ADR-010 §1).

    Vive en el mismo alcance de escaneo que la identidad (10 líneas), no
    en el tramo que toque leer: en una lectura incremental (ADR-011) el
    `session_meta` queda por debajo del cursor, y sin esto la versión
    observada se degradaría a `None` en cuanto el cursor avanzara.
    """
    for indice, (raw_line, _inicio, _fin) in enumerate(iter_lineas(instantanea)):
        if indice >= LINEAS_ESCANEO_IDENTIDAD:
            return None
        line = raw_line.strip()
        if not line:
            continue
        try:
            evento = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        version = _cli_version(evento)
        if version is not None:
            return version
    return None


def extraer_de_instantanea(
    instantanea: bytes, path: Path, desde: int = 0
) -> Extraccion:
    """Extrae los turnos cerrados de una instantánea ya materializada.

    `desde` (ADR-011) arranca la extracción en un byte offset ya
    procesado: los turnos teselan el archivo, así que empezar en el
    `offset_fin` del último turno cerrado no parte ninguno por la mitad.
    Los offsets producidos siguen siendo de la instantánea completa —
    el sello P4a y el fragmento servido no cambian de semántica— y los
    conteos (`eventos_no_reconocidos`, `descartes_linea`) son los de
    **este tramo**, no los del archivo entero: cuentan lo observado en
    esta lectura, que es lo que el ciclo puede afirmar.
    """
    session_id = path.stem  # decisión de ficha v1 por compatibilidad (ADR-010 §8)
    turnos: list[Turno] = []
    vistos: set[str] = set()
    texto_usuario_partes: list[str] = []
    texto_agente_partes: list[str] = []
    offset_inicio_turno = desde
    proyecto: str | None = _proyecto_heredado(instantanea, desde) if desde else None
    eventos_no_reconocidos = 0
    descartes_linea = 0
    version_cli_observada = version_cli_de_instantanea(instantanea)

    for evento, _inicio, fin in _iter_eventos_con_offsets(instantanea, desde):
        if evento is None:
            descartes_linea += 1
            continue

        tipo = evento.get("type") if isinstance(evento, dict) else None
        if isinstance(tipo, str) and tipo not in EVENTOS_DECLARADOS:
            # Evolución aditiva del formato: se ignora para la extracción
            # y se cuenta (ADR-010 §1, ronda 11c). Un evento sin `type` o
            # con `type` no-string no cuenta: no se arbitra sobre formas
            # corruptas de campo.
            eventos_no_reconocidos += 1
            continue

        nuevo_proyecto = _proyecto_de_turn_context(evento)
        if nuevo_proyecto is not ...:
            # turn_context: asigna (incluido None explícito = reset — el
            # cwd dejó de identificar proyecto, no se hereda el anterior)
            proyecto = nuevo_proyecto
            continue

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
                turn_id=calificar(session_id, turn_id),
                session_id=session_id,
                texto_usuario="".join(texto_usuario_partes),
                texto_agente="".join(texto_agente_partes),
                timestamp_cierre=evento.get("timestamp"),
                ruta_origen=str(path),
                offset_inicio=offset_inicio_turno,
                offset_fin=fin,
                proyecto=proyecto,
                fragmento_sha256=_sellar_fragmento(instantanea, offset_inicio_turno, fin),
            )
        )
        texto_usuario_partes = []
        texto_agente_partes = []
        offset_inicio_turno = fin

    return Extraccion(
        turnos=turnos,
        eventos_no_reconocidos=eventos_no_reconocidos,
        descartes_linea=descartes_linea,
        version_cli_observada=version_cli_observada,
    )


def extraer_turnos(path: Path | str) -> list[Turno]:
    """Extrae los turnos cerrados de un rollout completo, en orden.

    Entrada directa de SPEC-001: parsea lo que se le da, sin detección
    (la selección por predicados es de SPEC-006, `parseo.parsear`). Un
    error de I/O propaga, como antes de ADR-010; la traducción a
    `entrada_corrupta` la hace la frontera.
    """
    path = Path(path)
    from skopos.parseo import materializar_instantanea

    return extraer_de_instantanea(materializar_instantanea(path), path).turnos
