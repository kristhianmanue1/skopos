"""Frontera multi-CLI: detectar formato, seleccionar parser, normalizar.

Implementa SPEC-006 (docs/specs/f1-specs.md) y el contrato
`parser-contrato/v1` del ADR-010: materializa una instantánea única de
bytes (§5), selecciona en dos niveles por predicados declarados (§1) y
devuelve un `ResultadoParseo` con vocabulario cerrado de diagnósticos
(§3). Nunca hay fallback al parser de Codex ni selección por orden del
registro (§4): si la identidad no casa, el archivo se descarta con
diagnóstico, no se parsea "por parecido".

Este módulo NO conoce el formato de ningún CLI: cada adaptador declara
su ficha (identidad, incompatibilidad, extracción) y aquí sólo se
registra — `captura.py` es el adaptador de referencia (parser-codex/v1).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from skopos import captura
from skopos.captura import Turno
from skopos.cursor import Cursor


VERSION_CONTRATO = "parser-contrato/v1"

# Precedencia total y testeable (ADR-010 §3): ningún archivo puede
# recibir dos diagnósticos, y el orden de evaluación es este.
PRECEDENCIA = (
    "entrada_corrupta",
    "deteccion_ambigua",
    "formato_desconocido",
    "version_no_soportada",
    "ok",
)

# Códigos de `detalle` (unión cerrada, ADR-010 §3). `candidatos` es
# obligatorio sólo para los dos de ambigüedad y prohibido en el resto.
CODIGOS_CON_CANDIDATOS = frozenset(
    {"identidades_producto_multiples", "versiones_formato_multiples"}
)
CODIGOS_SIN_CANDIDATOS = frozenset(
    {"identidad_reconocida_sin_cierres", "parser_retirado", "lectura_corta"}
)


class InstantaneaCorrupta(Exception):
    """La instantánea no pudo materializarse bajo el protocolo del §5."""

    def __init__(self, codigo: str | None = None):
        super().__init__(codigo or "entrada_corrupta")
        self.codigo = codigo


@dataclass(frozen=True)
class Detalle:
    """`null | {codigo} | {codigo, candidatos}` — nada más (ADR-010 §3)."""

    codigo: str
    candidatos: tuple[str, ...] | None = None

    def __post_init__(self):
        if self.codigo in CODIGOS_CON_CANDIDATOS:
            if not self.candidatos or len(self.candidatos) < 2:
                raise ValueError(f"{self.codigo} exige >= 2 candidatos")
            if list(self.candidatos) != sorted(set(self.candidatos)):
                raise ValueError("candidatos: orden lexicográfico y sin duplicados")
        elif self.codigo in CODIGOS_SIN_CANDIDATOS:
            if self.candidatos is not None:
                raise ValueError(f"{self.codigo} prohíbe candidatos")
        else:
            raise ValueError(f"codigo fuera de la unión cerrada: {self.codigo}")


@dataclass(frozen=True)
class ResultadoParseo:
    diagnostico: str
    turnos: list[Turno] = field(default_factory=list)
    cli_producto: str | None = None
    version_formato: str | None = None
    version_cli_observada: str | None = None
    detalle: Detalle | None = None
    eventos_no_reconocidos: int = 0
    descartes_linea: int = 0
    # ADR-011: la instantánea de la que salieron estos turnos, para que
    # el llamador pueda sellar el prefijo hasta donde decida avanzar su
    # cursor. `None` cuando no hubo instantánea (entrada_corrupta).
    instantanea: bytes | None = None
    # True si esta lectura se apoyó en un cursor válido (sólo se parseó
    # la cola nueva); False si se parseó el archivo entero.
    incremental: bool = False


@dataclass(frozen=True)
class Ficha:
    """Ficha de adaptador registrada (ADR-010 §2 y §8).

    `activa=False` es la forma stub del §8: un parser retirado conserva
    su identidad registrada para que sus archivos sigan diagnosticándose
    `version_no_soportada` (`parser_retirado`) en vez de degradar a
    `formato_desconocido`.
    """

    id_ficha: str
    cli_producto: str
    version_parser: str
    version_formato: str
    casa_identidad: Callable[[bytes], bool]
    es_incompatible: Callable[[bytes], bool]
    extraer: Callable[[bytes, Path], captura.Extraccion]
    activa: bool = True


FICHA_CODEX = Ficha(
    id_ficha=captura.ID_FICHA,
    cli_producto=captura.CLI_PRODUCTO,
    version_parser=captura.VERSION_PARSER,
    version_formato=captura.VERSION_FORMATO,
    casa_identidad=captura.casa_identidad,
    es_incompatible=captura.es_incompatible,
    extraer=captura.extraer_de_instantanea,
)

# Registro de adaptadores (ADR-010 §8). Agregar uno es aditivo; retirar
# uno exige ADR propio y deja su ficha con activa=False, nunca la borra.
REGISTRO: tuple[Ficha, ...] = (FICHA_CODEX,)


def materializar_instantanea(path: Path | str) -> bytes:
    """Instantánea única de bytes bajo el protocolo del ADR-010 §5.

    Una apertura, N por `fstat` del mismo descriptor, lectura exacta de
    N bytes desde ese descriptor. Lo que crezca después queda fuera y se
    observa en el siguiente ciclo. Short read o UTF-8 inválido ⇒
    `InstantaneaCorrupta`; los errores de I/O propagan como `OSError`.
    """
    with open(path, "rb") as handle:
        esperados = os.fstat(handle.fileno()).st_size
        datos = handle.read(esperados)
    if len(datos) < esperados:
        raise InstantaneaCorrupta("lectura_corta")
    try:
        datos.decode("utf-8")
    except UnicodeDecodeError:
        raise InstantaneaCorrupta() from None
    return datos


def _candidatos_por_producto(
    instantanea: bytes, registro: tuple[Ficha, ...]
) -> dict[str, list[Ficha]]:
    """Nivel A: predicados de identidad agrupados por `cli_producto`.

    Dos versiones del mismo producto no son dos identidades (§1): por eso
    el agrupamiento es por producto y no por ficha.
    """
    candidatos: dict[str, list[Ficha]] = {}
    for ficha in registro:
        if ficha.casa_identidad(instantanea):
            candidatos.setdefault(ficha.cli_producto, []).append(ficha)
    return candidatos


def _ids(fichas: list[Ficha]) -> tuple[str, ...]:
    return tuple(sorted({ficha.id_ficha for ficha in fichas}))


def sellar_prefijo(instantanea: bytes, offset: int) -> str:
    """sha256 de `bytes[0:offset]` — el sello que valida un cursor (ADR-011)."""
    return hashlib.sha256(instantanea[:offset]).hexdigest()


def _cursor_aplicable(instantanea: bytes, cursor: Cursor | None) -> bool:
    """El cursor sirve sólo si su prefijo sigue siendo byte a byte el mismo.

    Rotación, edición o truncación hacen que el sello no case y el
    archivo se reparsea entero (ADR-011): la discrepancia es observable,
    nunca un salto silencioso. `tamaño+mtime` está prohibido como
    comparación (ADR-010 §5), por eso se verifica por contenido.
    """
    if cursor is None or cursor.offset <= 0:
        return False
    if len(instantanea) < cursor.offset:
        return False  # el archivo encogió: truncado o sustituido
    return sellar_prefijo(instantanea, cursor.offset) == cursor.digest_prefijo


def parsear(
    path: Path | str,
    registro: tuple[Ficha, ...] = REGISTRO,
    cursor: Cursor | None = None,
) -> ResultadoParseo:
    """Detecta, selecciona y extrae; un diagnóstico por archivo.

    Con `cursor` (ADR-011) y si su sello sigue casando, sólo se parsea la
    cola nueva; los offsets de los turnos siguen siendo de la instantánea
    completa, así que el sello P4a y `fragmento_completo` no cambian de
    semántica. La detección de identidad se evalúa siempre sobre la
    instantánea entera: un cursor jamás sustituye a la frontera.
    """
    path = Path(path)
    try:
        instantanea = materializar_instantanea(path)
    except InstantaneaCorrupta as exc:
        detalle = Detalle(exc.codigo) if exc.codigo else None
        return ResultadoParseo(diagnostico="entrada_corrupta", detalle=detalle)
    except OSError:
        return ResultadoParseo(diagnostico="entrada_corrupta")

    incremental = _cursor_aplicable(instantanea, cursor)

    candidatos = _candidatos_por_producto(instantanea, registro)

    if len(candidatos) > 1:  # Nivel A regla 3
        todas = [ficha for fichas in candidatos.values() for ficha in fichas]
        return ResultadoParseo(
            diagnostico="deteccion_ambigua",
            detalle=Detalle("identidades_producto_multiples", _ids(todas)),
        )
    if not candidatos:  # Nivel A regla 2
        return ResultadoParseo(diagnostico="formato_desconocido")

    cli_producto, fichas = next(iter(candidatos.items()))

    # Nivel B: versión de formato entre las fichas de ESE producto.
    compatibles = [f for f in fichas if not f.es_incompatible(instantanea)]
    if len(compatibles) > 1:  # regla 4
        return ResultadoParseo(
            diagnostico="deteccion_ambigua",
            cli_producto=cli_producto,
            detalle=Detalle("versiones_formato_multiples", _ids(compatibles)),
        )
    if not compatibles:  # regla 5: marcador positivo incompatible
        return ResultadoParseo(
            diagnostico="version_no_soportada", cli_producto=cli_producto
        )

    ficha = compatibles[0]
    if not ficha.activa:  # regla 3: ficha stub de parser retirado
        return ResultadoParseo(
            diagnostico="version_no_soportada",
            cli_producto=cli_producto,
            version_formato=ficha.version_formato,
            detalle=Detalle("parser_retirado"),
        )

    desde = cursor.offset if incremental else 0
    extraccion = ficha.extraer(instantanea, path, desde)
    # `identidad_reconocida_sin_cierres` describe el ARCHIVO, no la cola:
    # en una lectura incremental sin turnos nuevos no se afirma que el
    # archivo no tenga cierres — ya se sabía que los tenía.
    detalle = (
        Detalle("identidad_reconocida_sin_cierres")
        if not extraccion.turnos and not incremental
        else None
    )
    return ResultadoParseo(
        diagnostico="ok",
        turnos=extraccion.turnos,
        cli_producto=cli_producto,
        version_formato=ficha.version_formato,
        version_cli_observada=extraccion.version_cli_observada,
        detalle=detalle,
        eventos_no_reconocidos=extraccion.eventos_no_reconocidos,
        descartes_linea=extraccion.descartes_linea,
        instantanea=instantanea,
        incremental=incremental,
    )
