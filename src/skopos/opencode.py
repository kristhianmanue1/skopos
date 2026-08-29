"""Adaptador parser-opencode/v1 — primer origen de FILAS (ADR-012).

opencode guarda la conversación en SQLite (`opencode.db`), no en
archivos de texto. Este adaptador implementa lo que ADR-012 decidió para
esa forma de origen:

- la **instantánea** es una transacción de lectura (SQLite da un snapshot
  consistente aunque la base cambie por debajo);
- el **fragmento** de un turno es la serialización canónica de las filas
  que lo componen, y `fragmento_sha256` se sella sobre esos bytes;
- **no hay offsets**: una fila no tiene rango de bytes estable, y
  fingirlo sería mentir en un campo que otros componentes usan.

Evidencia y decisiones de ficha:
`docs/evidencia/ficha-opencode-2026-08-28.md`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from skopos.captura import ORIGEN_FILAS, Extraccion, Turno, _proyecto_de_cwd


# --- Ficha del adaptador (ADR-010 §2 y §8; constantes declaradas) ------

ID_FICHA = "parser-opencode/v1"
CLI_PRODUCTO = "opencode"
VERSION_PARSER = "parser-opencode/v1"
VERSION_FORMATO = "opencode-sqlite/v1"

# Identidad: cabecera de SQLite + el conjunto de tablas propio de
# opencode. Se comprueba sin materializar la base (4.4 GB en el corpus
# real): primero 16 bytes, luego una consulta al catálogo.
CABECERA_SQLITE = b"SQLite format 3\x00"
TABLAS_IDENTIDAD = frozenset({"session", "message", "part"})
TABLA_ORIGEN = "message"

# Tipos de parte que son conversación. `reasoning` queda fuera
# (razonamiento del modelo, no diálogo — misma decisión que en cline y
# kimi); `tool`, `step-start`, `step-finish`, `patch` y `file` tampoco.
PARTES_CONVERSACION = frozenset({"text"})
ROLES_CONVERSACION = {"user": "usuario", "assistant": "agente"}


def _conectar(path: Path) -> sqlite3.Connection:
    """Conexión de sólo lectura; nunca escribe en la base del otro CLI."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)


def casa_identidad_ruta(path: Path) -> bool:
    """Predicado de identidad sobre la ruta, sin materializar la base."""
    try:
        with open(path, "rb") as handle:
            if handle.read(len(CABECERA_SQLITE)) != CABECERA_SQLITE:
                return False
    except OSError:
        return False
    try:
        con = _conectar(path)
        try:
            tablas = {
                fila[0]
                for fila in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        finally:
            con.close()
    except sqlite3.Error:
        return False
    return TABLAS_IDENTIDAD.issubset(tablas)


def es_incompatible(path: Path) -> bool:
    """Sin marcador de versión del esquema declarado en v1.

    `session.version` es la versión del **CLI**, no del formato de la
    base (ADR-010 §1 distingue las cinco versiones). Sin predicado
    positivo, no hay incompatibilidad.
    """
    return False


def _canonico(filas: list[dict]) -> bytes:
    """Serialización canónica de las filas de un turno (ADR-012).

    Claves ordenadas, sin espacios, UTF-8 — el mismo `canonical-json/v1`
    que usa AN-KLA. Es lo que se sella: el fragmento de un origen de
    filas es su contenido, no un rango de bytes.
    """
    return json.dumps(filas, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _timestamp_iso(marca: object) -> str | None:
    """`time_created` en milisegundos epoch → ISO 8601 UTC con `Z`."""
    if isinstance(marca, (int, float)) and marca > 0:
        try:
            momento = datetime.fromtimestamp(float(marca) / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return momento.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return None


def _texto(partes: list[dict]) -> str:
    return "".join(
        parte.get("text") or ""
        for parte in partes
        if isinstance(parte, dict) and parte.get("type") in PARTES_CONVERSACION
    )


def extraer_de_base(path: Path, session_id: str | None = None) -> Extraccion:
    """Extrae los turnos cerrados de la base, en una transacción de lectura.

    El turno va de un mensaje de usuario al siguiente (cierre derivado,
    como claude-code y cline): opencode no marca el fin de turno. El
    último de cada sesión queda abierto hasta que llegue el siguiente.
    """
    turnos: list[Turno] = []
    no_reconocidos = 0
    version_cli: str | None = None
    con = _conectar(path)
    try:
        con.execute("BEGIN")  # snapshot consistente (ADR-012)
        directorios = {}
        for sid, directorio, version in con.execute(
            "SELECT id, directory, version FROM session"
        ):
            directorios[sid] = directorio
            if version and version_cli is None:
                version_cli = version

        partes: dict[str, list[dict]] = {}
        for mensaje_id, datos in con.execute(
            "SELECT message_id, data FROM part ORDER BY time_created, id"
        ):
            try:
                partes.setdefault(mensaje_id, []).append(json.loads(datos))
            except (TypeError, json.JSONDecodeError):
                no_reconocidos += 1

        consulta = (
            "SELECT id, session_id, time_created, data FROM message "
            "{filtro} ORDER BY session_id, time_created, id"
        ).format(filtro="WHERE session_id = ?" if session_id else "")
        filas = con.execute(consulta, (session_id,) if session_id else ())

        abierto: dict | None = None
        sesion_actual: str | None = None

        def cerrar() -> None:
            nonlocal abierto
            if abierto is None:
                return
            turnos.append(
                Turno(
                    turn_id=f"{CLI_PRODUCTO}:{abierto['id']}",
                    session_id=abierto["session_id"],
                    texto_usuario=abierto["usuario"],
                    texto_agente=abierto["agente"],
                    timestamp_cierre=abierto["timestamp"],
                    ruta_origen=str(path),
                    offset_inicio=None,
                    offset_fin=None,
                    cli=CLI_PRODUCTO,
                    proyecto=abierto["proyecto"],
                    fragmento_sha256=hashlib.sha256(
                        _canonico(abierto["filas"])
                    ).hexdigest(),
                    origen_tipo=ORIGEN_FILAS,
                    origen_tabla=TABLA_ORIGEN,
                    origen_ids=tuple(abierto["ids"]),
                )
            )
            abierto = None

        for mensaje_id, sid, creado, datos in filas:
            try:
                mensaje = json.loads(datos)
            except (TypeError, json.JSONDecodeError):
                no_reconocidos += 1
                continue
            rol = ROLES_CONVERSACION.get(mensaje.get("role"))
            if rol is None:
                no_reconocidos += 1
                continue
            if sid != sesion_actual:
                cerrar()  # un turno nunca cruza de sesión
                sesion_actual = sid
            texto = _texto(partes.get(mensaje_id, []))
            fila = {"id": mensaje_id, "session_id": sid, "data": mensaje,
                    "parts": partes.get(mensaje_id, [])}

            if rol == "usuario":
                cerrar()
                directorio = directorios.get(sid)
                abierto = {
                    "id": mensaje_id,
                    "session_id": sid,
                    "usuario": texto,
                    "agente": "",
                    "timestamp": _timestamp_iso(creado),
                    "proyecto": _proyecto_de_cwd(directorio) if directorio else None,
                    "filas": [fila],
                    "ids": [mensaje_id],
                }
                continue
            if abierto is None:
                continue
            abierto["agente"] += texto
            abierto["filas"].append(fila)
            abierto["ids"].append(mensaje_id)
            marca = _timestamp_iso(creado)
            if marca:
                abierto["timestamp"] = marca
        # el turno en curso NO se cierra: sin marca de fin, lo cierra el
        # mensaje de usuario siguiente
    finally:
        con.close()

    return Extraccion(
        turnos=turnos,
        eventos_no_reconocidos=no_reconocidos,
        descartes_linea=0,
        version_cli_observada=version_cli,
    )
