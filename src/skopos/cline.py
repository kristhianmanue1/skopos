"""Adaptador parser-cline/v1 (fase B de P-003, contrato ADR-010).

Primer adaptador cuyo origen **no es JSONL**: cline guarda cada sesión
como un único objeto JSON con un array `messages`. El contrato se honra
igual —offsets de bytes reales dentro del archivo y sello P4a sobre
ellos— calculando el rango de cada mensaje con un decodificador
incremental, no partiendo por líneas.

Evidencia y decisiones de ficha:
`docs/evidencia/ficha-cline-2026-08-28.md`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from skopos.captura import Extraccion, Turno, _proyecto_de_cwd, _sellar_fragmento


# --- Ficha del adaptador (ADR-010 §2 y §8; constantes declaradas) ------

ID_FICHA = "parser-cline/v1"
CLI_PRODUCTO = "cline"
VERSION_PARSER = "parser-cline/v1"
VERSION_FORMATO = "cline-messages/v1"

# Identidad: objeto JSON único (no una línea completa, como en los
# formatos JSONL) con `sessionId` y `messages` en la cabecera.
# Evidencia: 176/176 positivos, 0 falsos positivos sobre 1,902 ajenos.
ALCANCE_ESCANEO_IDENTIDAD = 4096
MARCAS_IDENTIDAD = (b'"sessionId"', b'"messages"')

# `version` de la raíz es la versión del FORMATO (no del CLI): hoy 1 en
# 176/176. Es el primer adaptador con predicado positivo de
# incompatibilidad (ADR-010 §1, regla 5 del Nivel B).
VERSION_FORMATO_SOPORTADA = 1

# Bloques que son conversación. Se excluyen `tool_use`, `tool_result`
# (vuelven como mensajes de usuario, 1,538 contra 239 de texto real) y
# `thinking` (razonamiento del modelo, no diálogo) — decisión de ficha,
# igual que Codex excluye `developer` (ADR-010 §6).
BLOQUES_CONVERSACION = frozenset({"text"})
ROLES_CONVERSACION = {"user": "usuario", "assistant": "agente"}

# Sólo el agente principal produce turnos: `subagent`/`teammate` son
# conversaciones derivadas, como `isSidechain` en claude-code.
AGENTE_PRINCIPAL = "lead"


def casa_identidad(instantanea: bytes) -> bool:
    """Predicado de identidad de la ficha (alcance: primeros 4 KiB).

    Descarta los formatos JSONL sin parsear el archivo: allí la primera
    línea es un objeto JSON **completo**; aquí es la apertura de uno
    repartido en varias líneas.
    """
    cabecera = instantanea[:ALCANCE_ESCANEO_IDENTIDAD]
    recortado = cabecera.lstrip()
    if not recortado.startswith(b"{"):
        return False
    primera = recortado.split(b"\n", 1)[0].strip()
    try:
        json.loads(primera)
        return False  # línea completa ⇒ es JSONL, no este formato
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return all(marca in cabecera for marca in MARCAS_IDENTIDAD)


def es_incompatible(instantanea: bytes) -> bool:
    """`version` de raíz distinta de la soportada ⇒ incompatible.

    Marcador explícito del propio formato (ADR-010 §1, predicado positivo
    tipo (i)): a diferencia de codex y claude-code, aquí el archivo SÍ
    declara la versión de su esquema, así que `version_no_soportada` es
    alcanzable sin retirar el parser.
    """
    documento = _documento(instantanea)
    if documento is None:
        return False  # ilegible: no es incompatibilidad, lo decide el parseo
    version = documento.get("version")
    return isinstance(version, int) and version != VERSION_FORMATO_SOPORTADA


def _documento(instantanea: bytes) -> dict | None:
    try:
        documento = json.loads(instantanea)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return documento if isinstance(documento, dict) else None


def _timestamp_iso(marca: object) -> str | None:
    """`ts` en milisegundos epoch → ISO 8601 UTC con `Z`.

    El Turno promete `timestamp_cierre` en el formato que ADR-008 sabe
    parsear; dejarlo como entero lo volvería ilegible para el corte
    "desde ahora" y **todo turno de cline sería histórico**, es decir,
    nunca se ingeriría fuera de `--backfill`. La conversión es de la
    ficha, no del contrato.
    """
    if isinstance(marca, str) and marca:
        return marca
    if isinstance(marca, (int, float)) and marca > 0:
        try:
            momento = datetime.fromtimestamp(marca / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return momento.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return None


def _rangos_de_mensajes(instantanea: bytes) -> list[tuple[int, int]]:
    """Rango de bytes `[inicio, fin)` de cada elemento de `messages`.

    El contrato exige offsets sobre los bytes crudos (ADR-010 §5) y aquí
    no hay líneas que contarlos: se recorre el array con `raw_decode`,
    que devuelve dónde termina cada elemento, y se convierte a bytes
    acumulando la longitud codificada — un solo paso, sin volver atrás.
    """
    try:
        texto = instantanea.decode("utf-8")
    except UnicodeDecodeError:
        return []
    marca = texto.find('"messages"')
    if marca == -1:
        return []
    corchete = texto.find("[", marca)
    if corchete == -1:
        return []

    decodificador = json.JSONDecoder()
    rangos: list[tuple[int, int]] = []
    indice = corchete + 1
    bytes_hasta = len(texto[:indice].encode("utf-8"))
    while indice < len(texto):
        while indice < len(texto) and texto[indice] in " \t\r\n,":
            bytes_hasta += len(texto[indice].encode("utf-8"))
            indice += 1
        if indice >= len(texto) or texto[indice] == "]":
            break
        try:
            _valor, fin = decodificador.raw_decode(texto, indice)
        except json.JSONDecodeError:
            break
        bytes_elemento = len(texto[indice:fin].encode("utf-8"))
        rangos.append((bytes_hasta, bytes_hasta + bytes_elemento))
        bytes_hasta += bytes_elemento
        indice = fin
    return rangos


def _texto_de_mensaje(mensaje: dict) -> tuple[str, str] | None:
    rol = ROLES_CONVERSACION.get(mensaje.get("role"))
    if rol is None:
        return None
    contenido = mensaje.get("content")
    if isinstance(contenido, str):
        return (rol, contenido) if contenido.strip() else None
    if not isinstance(contenido, list):
        return None
    texto = "".join(
        bloque.get("text", "")
        for bloque in contenido
        if isinstance(bloque, dict) and bloque.get("type") in BLOQUES_CONVERSACION
    )
    return (rol, texto) if texto.strip() else None


def extraer_de_instantanea(
    instantanea: bytes, path: Path, desde: int = 0
) -> Extraccion:
    """Extrae los turnos cerrados (contrato SPEC-006).

    `desde` se honra descartando los mensajes que quedan por debajo del
    cursor, pero el archivo se reparsea entero de todos modos: un objeto
    JSON se reescribe al crecer, así que la lectura incremental no ahorra
    trabajo aquí (declarado en la ficha; ADR-011 lo tolera porque el
    cursor es caché, no obligación).
    """
    documento = _documento(instantanea)
    if documento is None:
        return Extraccion([], 0, 0, None)

    mensajes = documento.get("messages")
    if not isinstance(mensajes, list):
        return Extraccion([], 0, 0, None)
    if documento.get("agent") not in (None, AGENTE_PRINCIPAL):
        # subagent/teammate: conversación derivada, no turnos propios
        return Extraccion([], 0, 0, _version(documento))

    rangos = _rangos_de_mensajes(instantanea)
    session_id = path.stem.replace(".messages", "")
    proyecto = (
        _proyecto_de_cwd(documento["cwd"]) if isinstance(documento.get("cwd"), str) else None
    )

    turnos: list[Turno] = []
    no_reconocidos = 0
    turn_id: str | None = None
    inicio = 0
    usuario: list[str] = []
    agente: list[str] = []
    timestamp: str | None = None

    def cerrar(fin: int) -> None:
        nonlocal turn_id, usuario, agente
        if turn_id is None or fin <= inicio or inicio < desde:
            turn_id = None
            usuario, agente = [], []
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
        usuario, agente = [], []

    for mensaje, (ini, fin) in zip(mensajes, rangos):
        if not isinstance(mensaje, dict):
            no_reconocidos += 1
            continue
        texto = _texto_de_mensaje(mensaje)
        if texto is not None and texto[0] == "usuario":
            cerrar(ini)
            identificador = mensaje.get("id")
            if not isinstance(identificador, str) or not identificador:
                continue
            turn_id = f"{CLI_PRODUCTO}:{identificador}"
            inicio = ini
        if turn_id is None:
            continue
        if texto is not None:
            rol, contenido = texto
            (usuario if rol == "usuario" else agente).append(contenido)
        marca = _timestamp_iso(mensaje.get("ts"))
        if marca is not None:
            timestamp = marca

    # el turno en curso queda abierto: sin marca de fin, lo cierra el
    # mensaje de usuario siguiente (mismo criterio que claude-code)
    return Extraccion(turnos, no_reconocidos, 0, _version(documento))


def _version(documento: dict) -> str | None:
    version = documento.get("version")
    return str(version) if version is not None else None
