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


class _DerivadorTurnos:
    """Máquina de estados de turno (única para ambas lecturas).

    El turno va de un mensaje de usuario al siguiente (cierre derivado,
    como claude-code y cline): opencode no marca el fin de turno. El
    último de cada sesión queda abierto hasta que llegue el siguiente
    mensaje de usuario. La misma máquina sirve a la lectura completa
    (extraer_de_base) y a la delta (extraer_delta, ADR-013) — dos
    derivadores serían dos máquinas que derivan.
    """

    def __init__(self, ruta: Path, directorios: dict[str, str | None]):
        self._ruta = ruta
        self._directorios = directorios
        self.turnos: list[Turno] = []
        self.no_reconocidos = 0
        self._abierto: dict | None = None
        self._sesion_actual: str | None = None

    def cerrar(self) -> None:
        """Emite el turno abierto, si lo hay."""
        abierto = self._abierto
        if abierto is None:
            return
        self.turnos.append(
            Turno(
                turn_id=f"{CLI_PRODUCTO}:{abierto['id']}",
                session_id=abierto["session_id"],
                texto_usuario=abierto["usuario"],
                texto_agente=abierto["agente"],
                timestamp_cierre=abierto["timestamp"],
                ruta_origen=str(self._ruta),
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
        self._abierto = None

    def alimentar(self, mensaje_id: str, sid: str, creado: object,
                  datos: object, partes: list[dict]) -> None:
        """Procesa una fila `message` (ya con su partes resueltas)."""
        try:
            mensaje = json.loads(datos)
        except (TypeError, json.JSONDecodeError):
            self.no_reconocidos += 1
            return
        rol = ROLES_CONVERSACION.get(mensaje.get("role"))
        if rol is None:
            self.no_reconocidos += 1
            return
        if sid != self._sesion_actual:
            self.cerrar()  # un turno nunca cruza de sesión
            self._sesion_actual = sid
        texto = _texto(partes)
        fila = {"id": mensaje_id, "session_id": sid, "data": mensaje,
                "parts": partes}

        if rol == "usuario":
            self.cerrar()
            directorio = self._directorios.get(sid)
            self._abierto = {
                "id": mensaje_id,
                "session_id": sid,
                "usuario": texto,
                "agente": "",
                "timestamp": _timestamp_iso(creado),
                "proyecto": _proyecto_de_cwd(directorio) if directorio else None,
                "filas": [fila],
                "ids": [mensaje_id],
            }
            return
        if self._abierto is None:
            return
        self._abierto["agente"] += texto
        self._abierto["filas"].append(fila)
        self._abierto["ids"].append(mensaje_id)
        marca = _timestamp_iso(creado)
        if marca:
            self._abierto["timestamp"] = marca


def _cargar_sesiones(con: sqlite3.Connection) -> tuple[dict[str, str | None], str | None]:
    """Mapa session_id → directory, y la versión del CLI observada."""
    directorios: dict[str, str | None] = {}
    version_cli: str | None = None
    for sid, directorio, version in con.execute(
        "SELECT id, directory, version FROM session"
    ):
        directorios[sid] = directorio
        if version and version_cli is None:
            version_cli = version
    return directorios, version_cli


def _partes_de(con: sqlite3.Connection, ids: list[str]) -> tuple[dict[str, list[dict]], int]:
    """Partes agrupadas por message_id, y cuántas venían rotas.

    Con `ids` vacío lee TODAS las partes (lectura completa); con ids,
    lote `IN` sobre `part_message_id_id_idx` — `time_created` no tiene
    índice en `part` (SCAN de 732 ms medido), así que la delta nunca
    consulta partes por tiempo sino por los mensajes de su ventana.
    """
    partes: dict[str, list[dict]] = {}
    rotas = 0
    if ids:
        cursor_sql = con.execute(
            "SELECT message_id, data FROM part WHERE message_id IN "
            f"({','.join('?' * len(ids))}) ORDER BY time_created, id", ids)
    else:
        cursor_sql = con.execute(
            "SELECT message_id, data FROM part ORDER BY time_created, id")
    for mensaje_id, datos in cursor_sql:
        try:
            partes.setdefault(mensaje_id, []).append(json.loads(datos))
        except (TypeError, json.JSONDecodeError):
            rotas += 1
    return partes, rotas


def extraer_de_base(path: Path, session_id: str | None = None) -> Extraccion:
    """Extrae los turnos cerrados de la base, en una transacción de lectura.

    Lectura completa: recorre todas las filas (el costo completo de
    18.3 s está medido en ADR-013 — es el camino de cold start, no el
    recurrente). El turno en curso al final NO se cierra: sin marca de
    fin, lo cierra el mensaje de usuario siguiente.
    """
    con = _conectar(path)
    try:
        con.execute("BEGIN")  # snapshot consistente (ADR-012)
        directorios, version_cli = _cargar_sesiones(con)
        derivador = _DerivadorTurnos(path, directorios)
        partes, rotas = _partes_de(con, [])
        derivador.no_reconocidos += rotas
        filas = con.execute(
            "SELECT id, session_id, time_created, data FROM message "
            "{filtro} ORDER BY session_id, time_created, id".format(
                filtro="WHERE session_id = ?" if session_id else ""),
            (session_id,) if session_id else (),
        )
        for mensaje_id, sid, creado, datos in filas:
            derivador.alimentar(mensaje_id, sid, creado, datos,
                                partes.get(mensaje_id, []))
        return Extraccion(
            turnos=derivador.turnos,
            eventos_no_reconocidos=derivador.no_reconocidos,
            descartes_linea=0,
            version_cli_observada=version_cli,
        )
    finally:
        con.close()


MAX_BUSQUEDA_ABRIDOR = 200  # filas hacia atrás por sesión, acotado


def _abridor_previo(con: sqlite3.Connection, sid: str,
                    marca_ms: int) -> tuple | None:
    """Último mensaje de usuario ANTERIOR a la marca de agua en una sesión.

    Es el abridor del turno que pudo quedar abierto cruzando la ventana:
    sin él, la delta no podría sellar ese turno al cerrar. Recorre hacia
    atrás con el índice cubriente y resuelve el rol en Python (JSON1 no
    se da por supuesto). SOLO usuario: un assistant previo no abre turno
    (hallazgo BLOCKER de la ronda adversarial del 2026-09-06). None si en
    las últimas MAX_BUSQUEDA_ABRIDOR filas no hay usuario — caso
    degenerado que la delta cuenta como no reconocido en lugar de
    perderlo en silencio.
    """
    filas = con.execute(
        "SELECT id, session_id, time_created, data FROM message "
        "WHERE session_id = ? AND time_created < ? "
        "ORDER BY time_created DESC, id DESC LIMIT ?",
        (sid, marca_ms, MAX_BUSQUEDA_ABRIDOR),
    )
    for mensaje_id, sid_f, creado, datos in filas:
        try:
            mensaje = json.loads(datos)
        except (TypeError, json.JSONDecodeError):
            continue
        if mensaje.get("role") == "user":
            return (mensaje_id, sid_f, creado, datos)
    return None


def _segmento_previo(con: sqlite3.Connection, sid: str, t_abridor: int,
                     marca_ms: int) -> list[tuple]:
    """TODAS las filas del turno abierto entre su abridor y la marca.

    La marca avanza (max_visto+1) pero el turno abierto se re-deriva
    completo: sin este segmento, las filas del turno que quedaron bajo
    la marca faltarian del sello (hallazgo BLOCKER de la ronda
    adversarial del 2026-09-06: respuestas que cruzan 2+ ciclos). El
    rango va por el índice cubriente (session_id, time_created, id).
    """
    return con.execute(
        "SELECT id, session_id, time_created, data FROM message "
        "WHERE session_id = ? AND time_created >= ? AND time_created < ? "
        "ORDER BY time_created, id",
        (sid, t_abridor, marca_ms),
    ).fetchall()


def extraer_delta(path: Path,
                  marca_ms: int | None) -> tuple[Extraccion, int | None]:
    """Lectura incremental de un origen de filas (ADR-013).

    Lee sólo `message.time_created >= marca_ms` (índice cubriente;
    7.2 ms por 24 h medidos) más el abridor previo de cada sesión
    activa, y deriva turnos con la MISMA máquina de la lectura completa.
    Devuelve `(extraccion, nueva_marca)`: la nueva marca es
    `max_visto + 1` — la ventana siguiente re-deriva el turno abierto
    desde su abridor (buscado hacia atrás), de modo que el sello
    canónico se computa siempre sobre las filas completas del turno.

    `marca_ms=None` es cold start o backfill: delega en la lectura
    completa (18 s medidos) pero SÍ propone marca — `max(time_created)+1`
    — para que el siguiente ciclo ya sea delta. Las filas con
    `time_created` nulo son invisibles para cualquier ventana acotada:
    se cuentan como no reconocidas para que esa pérdida potencial
    nunca sea silenciosa.
    """
    if marca_ms is None:
        completa = extraer_de_base(path)
        con = _conectar(path)
        try:
            maximo = con.execute(
                "SELECT MAX(time_created) FROM message").fetchone()[0]
        finally:
            con.close()
        nueva = int(maximo) + 1 if isinstance(maximo, (int, float)) and maximo > 0 else None
        return completa, nueva

    con = _conectar(path)
    try:
        con.execute("BEGIN")  # snapshot consistente (ADR-012)
        directorios, version_cli = _cargar_sesiones(con)
        derivador = _DerivadorTurnos(path, directorios)

        ventana = con.execute(
            "SELECT id, session_id, time_created, data FROM message "
            "WHERE time_created >= ? ORDER BY session_id, time_created, id",
            (marca_ms,),
        ).fetchall()
        if not ventana:
            return (Extraccion(turnos=[], eventos_no_reconocidos=0,
                               descartes_linea=0,
                               version_cli_observada=version_cli),
                    marca_ms)

        nulos = con.execute(
            "SELECT COUNT(*) FROM message WHERE time_created IS NULL"
        ).fetchone()[0]
        derivador.no_reconocidos += int(nulos or 0)

        sesiones_ventana = sorted({fila[1] for fila in ventana})
        filas_por_sesion: dict[str, list[tuple]] = {s: [] for s in sesiones_ventana}
        for fila in ventana:
            filas_por_sesion[fila[1]].append(fila)

        abridores: list[tuple] = []
        for sid in sesiones_ventana:
            primera = filas_por_sesion[sid][0]
            try:
                rol_primera = json.loads(primera[3]).get("role")
            except (TypeError, json.JSONDecodeError):
                rol_primera = None
            if rol_primera == "usuario" or rol_primera == "user":
                continue  # abre turno propio: no necesita abridor
            abridor = _abridor_previo(con, sid, marca_ms)
            if abridor is None:
                # filas de agente sin abridor derivable: no se pierden
                # en silencio (ADR-013 §b)
                derivador.no_reconocidos += len(filas_por_sesion[sid])
            else:
                # el turno abierto se re-deriva COMPLETO: todas sus filas
                # desde el abridor, incluidas las que quedaron bajo la
                # marca (fix del BLOCKER de la ronda adversarial)
                segmento = _segmento_previo(con, sid, int(abridor[2]), marca_ms)
                filas_por_sesion[sid] = segmento + filas_por_sesion[sid]

        ids: list[str] = [fila[0] for filas in filas_por_sesion.values()
                          for fila in filas]
        partes, rotas = _partes_de(con, ids)
        derivador.no_reconocidos += rotas

        max_visto = max(fila[2] for fila in ventana)
        for sid in sesiones_ventana:
            for mensaje_id, sid_f, creado, datos in filas_por_sesion[sid]:
                derivador.alimentar(mensaje_id, sid_f, creado, datos,
                                    partes.get(mensaje_id, []))

        nueva_marca = int(max_visto) + 1
        return (Extraccion(
            turnos=derivador.turnos,
            eventos_no_reconocidos=derivador.no_reconocidos,
            descartes_linea=0,
            version_cli_observada=version_cli,
        ), nueva_marca)
    finally:
        con.close()
