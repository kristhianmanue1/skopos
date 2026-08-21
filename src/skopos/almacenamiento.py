"""Persiste el análisis de un turno en MongoDB local.

Implementa SPEC-003 (docs/specs/f1-specs.md) y el CONTRATO
documento-analisis-mongo v2 (docs/contratos/f1-contratos.md — versionado
por supersede, ADR-007). El esquema del documento se garantiza por
construcción: skopos.analisis.Analisis exige turn_id, ruta_origen y
offsets, así que nunca se puede llamar a guardar_analisis con un registro
huérfano.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pymongo
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from skopos.analisis import Analisis

COLECCION_POR_DEFECTO = "analisis"

# supersede: reintentos al chocar con un supersede concurrente por la
# misma versión (ADR-007, H2 de su ronda 2) — nunca omitido en silencio
INTENTOS_SUPERSEDE = 3


class DocumentoInvalido(ValueError):
    """turn_id/ruta_origen faltantes: el CONTRATO exige rechazar, no persistir."""


class TurnoInexistente(LookupError):
    """supersede sobre un turn_id sin ninguna versión guardada."""


def _documento(analisis: Analisis) -> dict:
    documento = {
        "tema": analisis.tema,
        "resumen": analisis.resumen,
        "turn_id": analisis.turn_id,
        "version": 1,  # ADR-007: primera versión; supersede inserta N+1
        "session_id": analisis.session_id,
        "ruta_origen": analisis.ruta_origen,
        "offset_inicio": analisis.offset_inicio,
        "offset_fin": analisis.offset_fin,
        "cli": analisis.cli,
        "modelo_analisis": analisis.modelo_analisis,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    }
    if analisis.ocurrido_en:
        documento["ocurrido_en"] = analisis.ocurrido_en
    if analisis.proyecto:
        documento["proyecto"] = analisis.proyecto
    if analisis.fragmento_sha256:
        # sello P4a (ADR-009): sha256 de los bytes del fragmento; el
        # tamaño no se sella aparte (offsets por construcción)
        documento["fragmento_sha256"] = analisis.fragmento_sha256
    if analisis.entidades:
        documento["entidades"] = analisis.entidades
    if analisis.dominio:
        documento["dominio"] = analisis.dominio
    if analisis.metadata_cli:
        documento["metadata_cli"] = analisis.metadata_cli
    return documento


def guardar_analisis(
    analisis: Analisis, *, coleccion: Collection
) -> dict:
    """Inserta el análisis y devuelve el documento insertado (con _id).

    Rechaza explícitamente un registro huérfano en el borde de persistencia
    (CONTRATO documento-analisis-mongo v1) en vez de confiar únicamente en
    que Analisis/captura.py nunca produzcan uno.
    """
    if not analisis.turn_id or not analisis.ruta_origen:
        raise DocumentoInvalido(
            f"turn_id y ruta_origen son obligatorios: turn_id={analisis.turn_id!r} "
            f"ruta_origen={analisis.ruta_origen!r}"
        )
    documento = _documento(analisis)
    resultado = coleccion.insert_one(documento)
    documento["_id"] = resultado.inserted_id
    return documento


def buscar_por_tema(
    tema: str, *, coleccion: Collection, proyecto: str | None = None
) -> list[dict]:
    """Devuelve documentos relacionados con el tema, por texto completo.

    Antes usaba igualdad exacta de string, lo que fallaba contra temas
    generados libremente por el LLM que describen lo mismo con palabras
    distintas (ronda adversarial 2026-08-13). $text sobre tema+resumen es
    la mejora mínima: coincide por palabra, no por frase exacta. Búsqueda
    semántica real (embeddings) queda para un ADR futuro si hace falta.

    C-9 (2026-08-20): `proyecto`, si está presente, filtra por el campo
    homónimo — los documentos sin el campo (pre-C-9 o desconocido)
    quedan fuera, nunca se les inventa una coincidencia.
    """
    filtro: dict = {"$text": {"$search": tema}}
    if proyecto is not None:
        filtro["proyecto"] = proyecto
    cursor = coleccion.find(
        filtro, {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})])
    documentos = list(cursor)
    return _solo_vigentes(documentos)


def _solo_vigentes(documentos: list[dict]) -> list[dict]:
    """Deja, por turn_id, sólo la versión de número mayor (ADR-007).

    Carga de seguridad, no sólo filtrado: una lectura que olvide esta
    pasada sirve versiones viejas — incluidos secretos pre-redacción
    (H1 de la ronda 2 del ADR-007). Conserva el orden de llegada.
    """
    mejor: dict[str, dict] = {}
    for doc in documentos:
        turn_id = doc["turn_id"]
        actual = mejor.get(turn_id)
        if actual is None or doc.get("version", 0) > actual.get("version", 0):
            mejor[turn_id] = doc
    # conserva el orden (por relevancia) de la versión vigente
    return [doc for doc in documentos if doc is mejor.get(doc["turn_id"])]


def version_vigente(turn_id: str, *, coleccion: Collection) -> dict | None:
    """Devuelve la versión de número mayor de un turn_id (o None si no existe)."""
    return coleccion.find_one(
        {"turn_id": turn_id}, sort=[("version", -1)]
    )


def superseder_documento(
    turn_id: str, cambios: dict, *, coleccion: Collection
) -> dict:
    """Inserta versión N+1 copiando la vigente y sustituyendo `cambios`.

    ADR-007 (alternativa B): ninguna versión existente se modifica. Si un
    supersede concurrente gana la misma versión, re-computa max(versión)
    y reintenta (H2 de la ronda 2 del ADR) — nunca omite en silencio.
    Las claves de identidad (`turn_id`, `version`, `_id`, `ruta_origen`)
    están prohibidas en `cambios` (ronda 3, F3): el supersede repara un
    análisis, nunca re-apunta la referencia de origen.
    """
    prohibidas = {"turn_id", "version", "_id", "ruta_origen"} & set(cambios)
    if prohibidas:
        raise DocumentoInvalido(
            f"supersede no puede tocar claves de identidad: {sorted(prohibidas)}"
        )
    ultimo_error: Exception | None = None
    for _ in range(INTENTOS_SUPERSEDE):
        vigente = version_vigente(turn_id, coleccion=coleccion)
        if vigente is None:
            raise TurnoInexistente(f"no hay versión guardada de {turn_id!r}")
        nueva = dict(vigente)
        nueva.pop("_id", None)
        nueva.update(cambios)
        # legado sin `version` cuenta como 0: su primer supersede es la
        # versión 1 (ronda 3, F6 — el contrato promete legado legible)
        nueva["version"] = vigente.get("version", 0) + 1
        nueva["creado_en"] = datetime.now(timezone.utc).isoformat()
        try:
            resultado = coleccion.insert_one(nueva)
        except DuplicateKeyError as exc:  # supersede concurrente: misma versión
            ultimo_error = exc
            continue
        nueva["_id"] = resultado.inserted_id
        return nueva
    raise PyMongoError(
        f"supersede de {turn_id!r}: {INTENTOS_SUPERSEDE} choques por la misma "
        f"versión — concurrente real, o un índice único simple pre-v2 "
        f"resucitado por un proceso viejo (H5): {ultimo_error}"
    )


def existe_turn_id(turn_id: str, *, coleccion: Collection) -> bool:
    """True si ya hay un documento guardado para ese turn_id (ADR-005)."""
    return coleccion.find_one({"turn_id": turn_id}, {"_id": 1}) is not None


def coleccion_local(
    *,
    uri: str = "mongodb://localhost:27017",
    db: str = "skopos",
    nombre: str = COLECCION_POR_DEFECTO,
    timeout_ms: int = 2000,
) -> Collection:
    """Conecta a la instancia local de Mongo (REQ-8) y devuelve la colección.

    Asegura los índices que el resto del módulo asume: único compuesto
    `(turn_id, version)` [ADR-007 v2 — sustituye al único simple sobre
    turn_id, que se retira aquí mismo si un despliegue viejo lo dejó],
    texto completo sobre tema+resumen (para buscar_por_tema) y, desde
    C-9 (2026-08-20), proyecto/cli/ocurrido_en para consultas por eje
    sin collection scan (ocurrido_en prepara el `skopos read` diferido).
    create_index es idempotente — no falla si el índice ya existe.
    Riesgo documentado (H5 de la ronda 2 del ADR-007): un proceso con
    código pre-v2 corriendo en paralelo resucita el índice único simple.
    """
    cliente = pymongo.MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
    coleccion = cliente[db][nombre]
    coleccion.create_index(
        [("turn_id", 1), ("version", 1)], unique=True
    )
    # retirar el índice único simple pre-v2 si un despliegue viejo lo dejó
    # (H5 de la ronda 2 del ADR-007). Sin try/except ciego (ronda 3, F4):
    # se comprueba existencia y se deja pasar cualquier otro error.
    if "turn_id_1" in {i["name"] for i in coleccion.list_indexes()}:
        coleccion.drop_index("turn_id_1")
    coleccion.create_index([("tema", "text"), ("resumen", "text")])
    coleccion.create_index("proyecto")
    coleccion.create_index("cli")
    coleccion.create_index("ocurrido_en")
    return coleccion
