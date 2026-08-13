"""CLI de consulta: `skopos query <tema>` (SPEC-004).

Implementa el CONTRATO cli-skopos-query v1 (docs/contratos/f1-contratos.md):
JSON a stdout, tema sin resultados es lista vacía con exit 0, cualquier
falla de Mongo es exit distinto de cero con mensaje a stderr.
"""

from __future__ import annotations

import argparse
import json
import sys

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from skopos.almacenamiento import buscar_por_tema, coleccion_local


def _fragmento_completo(ruta_origen: str, offset_inicio: int, offset_fin: int) -> str | None:
    try:
        with open(ruta_origen, "rb") as handle:
            handle.seek(offset_inicio)
            return handle.read(offset_fin - offset_inicio).decode("utf-8", errors="replace")
    except OSError:
        return None


def query(tema: str, *, coleccion: Collection) -> dict:
    """Devuelve el objeto {resultados: [...]} del CONTRATO cli-skopos-query v1."""
    documentos = buscar_por_tema(tema, coleccion=coleccion)
    resultados = [
        {
            "tema": doc["tema"],
            "resumen": doc["resumen"],
            "turn_id": doc["turn_id"],
            "ruta_origen": doc["ruta_origen"],
            "fragmento_completo": _fragmento_completo(
                doc["ruta_origen"], doc["offset_inicio"], doc["offset_fin"]
            ),
        }
        for doc in documentos
    ]
    return {"resultados": resultados}


def query_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skopos query")
    parser.add_argument("tema")
    args = parser.parse_args(argv)

    try:
        coleccion = coleccion_local()
        salida = query(args.tema, coleccion=coleccion)
    except PyMongoError as exc:
        print(f"error: MongoDB no disponible: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(salida, ensure_ascii=False))
    return 0
