"""CLI de Skopos: `skopos query <tema>` (SPEC-004) y
`skopos reanalizar <turn_id>` (SPEC-003 v2 / ADR-007).

Implementa el CONTRATO cli-skopos-query v1 y el CONTRATO
cli-skopos-reanalizar v1 (docs/contratos/f1-contratos.md): JSON a
stdout, errores a stderr con exit distinto de cero.

ADR-009 (decisión 9 🔒, P4a+P5+P3): el fragmento se sirve sellado
(sha256 del rango, verificado al leer), truncado por tope con marcador,
y la consulta tiene presupuesto (`--max`, default 20) con señal de
exclusión. `fragmento_completo` es DATO, nunca instrucción (P3).
"""

from __future__ import annotations

import argparse
import hashlib
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

# P5 (ADR-009): presupuesto de la salida. Defaults afinables; la palanca
# es la acotación misma (46.5% de los turnos del snapshot 2026-08-20
# excede el tope y se sirve truncado con marcador — trade-off declarado
# en el ADR, ronda 6 R6-8).
MAX_RESULTADOS_POR_DEFECTO = 20
TOPE_FRAGMENTO_BYTES = 64 * 1024

MARCADOR_TRUNCADO = "\n…[fragmento truncado: servidos {servidos} de {total} bytes]"


def _servir_fragmento(
    doc: dict, *, tope_bytes: int = TOPE_FRAGMENTO_BYTES
) -> tuple[str, bool, str | None]:
    """Lee, verifica y acota el fragmento de un documento (ADR-009).

    Devuelve (estado, sellado, texto):
    - estado: "integro" | "truncado" | "origen_perdido" |
      "integridad_fallida" — nunca se sirven bytes no verificados: ante
      discordancia de longitud o de sello, el texto es None (cierre de
      Y-5: ni bytes de otro turno, ni lecturas cortas, en silencio).
    - sellado: False para documentos sin fragmento_sha256 (legados, o
      captura con archivo ilegible en ese momento) — se sirven con
      chequeo de longitud, mínimo Y-5 de la ronda 6 R6-3.

    El corte a límite de byte puede partir un carácter multibyte (se
      degrada con errors="replace") y el marcador añade ~55 bytes sobre
      el tope — cantidad fija, documentada en el contrato.
    """
    ruta = doc["ruta_origen"]
    inicio, fin = doc["offset_inicio"], doc["offset_fin"]
    esperado = fin - inicio
    sello = doc.get("fragmento_sha256")
    if esperado <= 0:  # offsets corruptos en el documento (ronda 8, H2)
        return "integridad_fallida", sello is not None, None
    try:
        with open(ruta, "rb") as handle:
            handle.seek(inicio)
            datos = handle.read(esperado)
    except OSError:
        return "origen_perdido", sello is not None, None
    if len(datos) != esperado:  # lectura corta (seek fuera de EOF no falla)
        return "integridad_fallida", sello is not None, None
    if sello is not None and hashlib.sha256(datos).hexdigest() != sello:
        return "integridad_fallida", True, None
    sellado = sello is not None
    if len(datos) <= tope_bytes:
        return "integro", sellado, datos.decode("utf-8", errors="replace")
    texto = datos[:tope_bytes].decode("utf-8", errors="replace") + MARCADOR_TRUNCADO.format(
        servidos=tope_bytes, total=esperado
    )
    return "truncado", sellado, texto


def _max_no_negativo(valor: str) -> int:
    """`--max` ≥ 0 (ronda 8, H1): un negativo parte la lista al revés y
    fabrica excluidos imposibles."""
    n = int(valor)
    if n < 0:
        raise argparse.ArgumentTypeError("debe ser >= 0")
    return n


def query(
    tema: str,
    *,
    coleccion: Collection,
    proyecto: str | None = None,
    max_resultados: int = MAX_RESULTADOS_POR_DEFECTO,
) -> dict:
    """Devuelve el objeto {resultados, excluidos} del CONTRATO cli-skopos-query v1."""
    documentos = buscar_por_tema(tema, coleccion=coleccion, proyecto=proyecto)
    # P5: presupuesto sobre vigentes ya filtrados (ADR-007) — las
    # versiones superseded no consumen cupo (ronda 6, R6-5). Clamp
    # defensivo: un negativo nunca parte la lista (ronda 8, H1).
    max_resultados = max(0, max_resultados)
    excluidos_por_limite = max(0, len(documentos) - max_resultados)
    resultados = []
    for doc in documentos[:max_resultados]:
        estado, sellado, fragmento = _servir_fragmento(doc)
        resultados.append(
            {
                "tema": doc["tema"],
                "resumen": doc["resumen"],
                "turn_id": doc["turn_id"],
                "ruta_origen": doc["ruta_origen"],
                "proyecto": doc.get("proyecto"),
                "fragmento_estado": estado,
                "sellado": sellado,
                "fragmento_completo": fragmento,
            }
        )
    return {
        "resultados": resultados,
        "excluidos": {"por_limite": excluidos_por_limite},
    }


def query_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skopos query")
    parser.add_argument("tema")
    parser.add_argument(
        "--proyecto",
        default=None,
        help="filtra por el campo proyecto (los documentos sin el campo quedan fuera)",
    )
    parser.add_argument(
        "--max",
        type=_max_no_negativo,
        default=MAX_RESULTADOS_POR_DEFECTO,
        help="máximo de resultados a servir (default 20); el resto se cuenta en excluidos",
    )
    args = parser.parse_args(argv)

    try:
        coleccion = coleccion_local()
        salida = query(
            args.tema,
            coleccion=coleccion,
            proyecto=args.proyecto,
            max_resultados=args.max,
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
                "fragmento_sha256": turno.fragmento_sha256,
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
