"""Almacén local de cursores de lectura incremental (ADR-011).

El cursor es una **caché verificable**, nunca una fuente de verdad: la
dedup autoritativa sigue viviendo en Mongo (ADR-005). Por eso este
almacén vive fuera del repo, se puede borrar en cualquier momento y se
regenera solo — un cursor ausente cuesta un ciclo caro, jamás datos.

Cada entrada guarda hasta dónde se procesó un archivo y el sello de ese
prefijo. La validación por contenido es obligatoria: ADR-010 §5 prohíbe
volver a `tamaño+mtime` como comparación entre dos lecturas.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


RUTA_POR_DEFECTO = Path.home() / ".local" / "state" / "skopos" / "cursores.json"
VERSION_FORMATO_ALMACEN = "skopos-cursores/v2"  # v2 añade "filas" (ADR-013)


@dataclass(frozen=True)
class Cursor:
    """Hasta dónde se procesó un archivo, y el sello que lo prueba.

    `offset` es un byte offset de la instantánea; `digest_prefijo` es el
    sha256 de `bytes[0:offset]`. Si el sello no casa en la lectura
    siguiente, el cursor se descarta y el archivo se reparsea entero.
    """
    offset: int
    digest_prefijo: str


class AlmacenCursores:
    """Mapa ruta → Cursor, persistido en JSON con escritura atómica."""

    def __init__(self, ruta: Path | str = RUTA_POR_DEFECTO):
        self.ruta = Path(ruta)
        self._entradas: dict[str, Cursor] = {}
        # Marcas de agua de orígenes de filas (ADR-013): ruta → time_created
        # en milisegundos del turno abierto más antiguo. Misma jerarquía que
        # los cursores de archivo: caché que se puede borrar sin perder datos.
        self._marcas: dict[str, int] = {}
        self._sucio = False

    def cargar(self) -> "AlmacenCursores":
        """Lee el almacén; cualquier daño se trata como almacén vacío.

        Un archivo corrupto no es un error del que haya que recuperarse:
        es una caché que se rehace sola en el siguiente ciclo. La versión
        v1 (sólo archivos) se acepta: las marcas de filas simplemente no
        estaban, y el primer ciclo de filas arranca degradado (ADR-013 §b).
        """
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self
        if not isinstance(datos, dict) or datos.get("version") not in (
            "skopos-cursores/v1",
            VERSION_FORMATO_ALMACEN,
        ):
            return self
        entradas = datos.get("entradas")
        if not isinstance(entradas, dict):
            return self
        for ruta, valor in entradas.items():
            if (
                isinstance(valor, dict)
                and isinstance(valor.get("offset"), int)
                and isinstance(valor.get("digest_prefijo"), str)
            ):
                self._entradas[ruta] = Cursor(valor["offset"], valor["digest_prefijo"])
        filas = datos.get("filas")
        if isinstance(filas, dict):
            for ruta, marca in filas.items():
                if isinstance(marca, int) and marca > 0:
                    self._marcas[ruta] = marca
        return self

    def obtener(self, ruta: Path | str) -> Cursor | None:
        return self._entradas.get(str(ruta))

    def actualizar(self, ruta: Path | str, cursor: Cursor) -> None:
        clave = str(ruta)
        if self._entradas.get(clave) != cursor:
            self._entradas[clave] = cursor
            self._sucio = True

    def obtener_marca(self, ruta: Path | str) -> int | None:
        """Marca de agua de un origen de filas (ADR-013); None si no hay."""
        return self._marcas.get(str(ruta))

    def actualizar_marca(self, ruta: Path | str, marca: int) -> None:
        clave = str(ruta)
        if self._marcas.get(clave) != marca:
            self._marcas[clave] = marca
            self._sucio = True

    def podar(self, rutas_vivas) -> int:
        """Olvida las entradas de archivos que ya no existen.

        Sin esto el almacén crece para siempre: cada sesión archivada,
        renombrada o borrada dejaría su entrada dentro. Devuelve cuántas
        se eliminaron. Aplica a cursores de archivo y a marcas de filas.
        """
        vivas = {str(r) for r in rutas_vivas}
        muertas = [ruta for ruta in self._entradas if ruta not in vivas]
        for ruta in muertas:
            del self._entradas[ruta]
        marcas_muertas = [ruta for ruta in self._marcas if ruta not in vivas]
        for ruta in marcas_muertas:
            del self._marcas[ruta]
        if muertas or marcas_muertas:
            self._sucio = True
        return len(muertas) + len(marcas_muertas)

    def guardar(self) -> bool:
        """Persiste si hubo cambios. Devuelve si escribió.

        Escritura atómica (tmp + `os.replace`) para que un corte no deje
        un almacén a medias; si el disco falla, se pierde la caché y no
        pasa nada más — nunca se propaga el error al ciclo.
        """
        if not self._sucio:
            return False
        datos = {
            "version": VERSION_FORMATO_ALMACEN,
            "entradas": {
                ruta: {"offset": c.offset, "digest_prefijo": c.digest_prefijo}
                for ruta, c in sorted(self._entradas.items())
            },
        }
        if self._marcas:
            datos["filas"] = {ruta: marca for ruta, marca in sorted(self._marcas.items())}
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.ruta.parent, delete=False
            ) as tmp:
                json.dump(datos, tmp, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
                temporal = tmp.name
            os.replace(temporal, self.ruta)
        except OSError:
            return False
        self._sucio = False
        return True
