"""Persiste el análisis de un turno en MongoDB local.

Implementa SPEC-003 (docs/specs/f1-specs.md) y el CONTRATO
documento-analisis-mongo v1 (docs/contratos/f1-contratos.md). El esquema
del documento se garantiza por construcción: skopos.analisis.Analisis
exige turn_id, ruta_origen y offsets, así que nunca se puede llamar a
guardar_analisis con un registro huérfano.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pymongo
from pymongo.collection import Collection

from skopos.analisis import Analisis

COLECCION_POR_DEFECTO = "analisis"


def _documento(analisis: Analisis) -> dict:
    documento = {
        "tema": analisis.tema,
        "resumen": analisis.resumen,
        "turn_id": analisis.turn_id,
        "session_id": analisis.session_id,
        "ruta_origen": analisis.ruta_origen,
        "offset_inicio": analisis.offset_inicio,
        "offset_fin": analisis.offset_fin,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    }
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
    """Inserta el análisis y devuelve el documento insertado (con _id)."""
    documento = _documento(analisis)
    resultado = coleccion.insert_one(documento)
    documento["_id"] = resultado.inserted_id
    return documento


def buscar_por_tema(tema: str, *, coleccion: Collection) -> list[dict]:
    """Devuelve todos los documentos cuyo tema coincide exactamente."""
    return list(coleccion.find({"tema": tema}))


def coleccion_local(
    *,
    uri: str = "mongodb://localhost:27017",
    db: str = "skopos",
    nombre: str = COLECCION_POR_DEFECTO,
    timeout_ms: int = 2000,
) -> Collection:
    """Conecta a la instancia local de Mongo (REQ-8) y devuelve la colección."""
    cliente = pymongo.MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
    return cliente[db][nombre]
