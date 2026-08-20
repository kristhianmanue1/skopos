"""CLI de Skopos: `skopos query <tema>` (SPEC-004) y
`skopos reanalizar <turn_id>` (SPEC-003 v2 / ADR-007).

Implementa el CONTRATO cli-skopos-query v1 y el CONTRATO
cli-skopos-reanalizar v1 (docs/contratos/f1-contratos.md): JSON a
stdout, errores a stderr con exit distinto de cero.
"""

from __future__ import annotations

import argparse
import json
import sys

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from skopos.almacenamiento import (
    buscar_por_tema,
    coleccion_local,
    superseder_documento,
    version_vigente,
)
from skopos.analisis import AnalisisFallido, analizar_turno, redactar_secretos
from skopos.captura import extraer_turnos


def _fragmento_completo(ruta_origen: str, offset_inicio: int, offset_fin: int) -> str | None:
    try:
        with open(ruta_origen, "rb") as handle:
            handle.seek(offset_inicio)
            return handle.read(offset_fin - offset_inicio).decode("utf-8", errors="replace")
    except OSError:
        return None


def query(tema: str, *, coleccion: Collection, proyecto: str | None = None) -> dict:
    """Devuelve el objeto {resultados: [...]} del CONTRATO cli-skopos-query v1."""
    documentos = buscar_por_tema(tema, coleccion=coleccion, proyecto=proyecto)
    resultados = [
        {
            "tema": doc["tema"],
            "resumen": doc["resumen"],
            "turn_id": doc["turn_id"],
            "ruta_origen": doc["ruta_origen"],
            "proyecto": doc.get("proyecto"),
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
    parser.add_argument(
        "--proyecto",
        default=None,
        help="filtra por el campo proyecto (los documentos sin el campo quedan fuera)",
    )
    args = parser.parse_args(argv)

    try:
        coleccion = coleccion_local()
        salida = query(
            args.tema, coleccion=coleccion, proyecto=args.proyecto
        )
    except PyMongoError as exc:
        print(f"error: MongoDB no disponible: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(salida, ensure_ascii=False))
    return 0


def reanalizar_command(argv: list[str]) -> int:
    """`skopos reanalizar <turn_id> [--solo-redaccion]` (ADR-007, SPEC-003 v2).

    Supersede explícito: inserta versión nueva; la vieja queda como
    auditoría. Nunca lo dispara el vigilante.
    """
    parser = argparse.ArgumentParser(prog="skopos reanalizar")
    parser.add_argument("turn_id")
    parser.add_argument(
        "--solo-redaccion",
        action="store_true",
        help="re-aplicar patrones de secretos vigentes sin llamar a Ollama",
    )
    args = parser.parse_args(argv)

    try:
        coleccion = coleccion_local()
        vigente = version_vigente(args.turn_id, coleccion=coleccion)
        if vigente is None:
            print(f"error: no hay versión guardada de {args.turn_id}", file=sys.stderr)
            return 1

        if args.solo_redaccion:
            cambios = {
                "tema": redactar_secretos(vigente.get("tema", "")),
                "resumen": redactar_secretos(vigente.get("resumen", "")),
            }
            entidades = vigente.get("entidades")
            if entidades:
                cambios["entidades"] = [redactar_secretos(e) for e in entidades]
            if all(vigente.get(k) == v for k, v in cambios.items()):
                print(
                    json.dumps(
                        {"turn_id": args.turn_id, "cambiado": False,
                         "motivo": "sin patrones nuevos que redactar"},
                        ensure_ascii=False,
                    )
                )
                return 0
        else:
            # re-análisis completo: re-extrae el turno del rollout de
            # origen — si el archivo ya no está o el turno no se halla,
            # fallo explícito, nunca supersede a ciegas (lección Y-5)
            try:
                turnos = {
                    t.turn_id: t for t in extraer_turnos(vigente["ruta_origen"])
                }
            except OSError as exc:
                print(
                    f"error: no se puede releer {vigente['ruta_origen']}: {exc}",
                    file=sys.stderr,
                )
                return 1
            turno = turnos.get(args.turn_id)
            if turno is None:
                print(
                    f"error: {args.turn_id} no se encuentra en "
                    f"{vigente['ruta_origen']} (¿rollout rotado o editado?)",
                    file=sys.stderr,
                )
                return 1
            try:
                analisis = analizar_turno(turno)
            except AnalisisFallido as exc:
                # la falla más probable del comando (Ollama caído) se
                # reporta, no se traza (ronda 3, F1)
                print(f"error: el análisis falló: {exc}", file=sys.stderr)
                return 1
            # referencias de origen recomputadas (ADR-007: "salvo en modo
            # completo" — ronda 3, F2): el Turno re-extraído manda
            cambios = {
                "tema": analisis.tema,
                "resumen": analisis.resumen,
                "entidades": analisis.entidades,
                "modelo_analisis": analisis.modelo_analisis,
                "offset_inicio": turno.offset_inicio,
                "offset_fin": turno.offset_fin,
                "ocurrido_en": turno.timestamp_cierre,
                "proyecto": turno.proyecto,
            }

        nueva = superseder_documento(args.turn_id, cambios, coleccion=coleccion)
    except PyMongoError as exc:
        print(f"error: MongoDB no disponible: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "turn_id": args.turn_id,
                "cambiado": True,
                "version_anterior": vigente.get("version"),
                "version_nueva": nueva["version"],
            },
            ensure_ascii=False,
        )
    )
    return 0
