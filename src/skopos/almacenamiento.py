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


class DocumentoInvalido(ValueError):
    """turn_id/ruta_origen faltantes: el CONTRATO exige rechazar, no persistir."""


def _documento(analisis: Analisis) -> dict:
    documento = {
        "tema": analisis.tema,
        "resumen": analisis.resumen,
        "turn_id": analisis.turn_id,
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
    return list(cursor)


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

    Asegura los índices que el resto del módulo asume: turn_id único
    (cierra la condición de carrera entre existe_turn_id e insert_one),
    texto completo sobre tema+resumen (para buscar_por_tema) y, desde
    C-9 (2026-08-20), proyecto/cli/ocurrido_en para consultas por eje
    sin collection scan (ocurrido_en prepara el `skopos read` diferido).
    create_index es idempotente — no falla si el índice ya existe.
    """
    cliente = pymongo.MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
    coleccion = cliente[db][nombre]
    coleccion.create_index("turn_id", unique=True)
    coleccion.create_index([("tema", "text"), ("resumen", "text")])
    coleccion.create_index("proyecto")
    coleccion.create_index("cli")
    coleccion.create_index("ocurrido_en")
    return coleccion
