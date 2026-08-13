"""Analiza un turno con un modelo de IA local (SPEC-002).

Implementa SPEC-002 (docs/specs/f1-specs.md): llama a Ollama vía su API
HTTP local (ADR-001) para extraer tema/resumen/entidades, y opcionalmente
enriquece el resultado con una ficha de escrubery (ADR-004) — sin bloquear
si escrubery falla o no está disponible.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from skopos.captura import Turno

MODELO_POR_DEFECTO = "qwen3:8b"
URL_OLLAMA_POR_DEFECTO = "http://localhost:11434"

_ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "tema": {"type": "string"},
        "resumen": {"type": "string"},
        "entidades": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tema", "resumen"],
}


@dataclass(frozen=True)
class Analisis:
    tema: str
    resumen: str
    turn_id: str
    session_id: str
    ruta_origen: str
    offset_inicio: int
    offset_fin: int
    cli: str
    modelo_analisis: str
    ocurrido_en: str | None = None
    entidades: list[str] = field(default_factory=list)
    dominio: str | None = None
    metadata_cli: dict | None = None


class AnalisisFallido(Exception):
    """El modelo local no respondió o respondió sin campos válidos."""


def _construir_prompt(turno: Turno, dominio_config: dict | None) -> str:
    instrucciones = [
        "Analiza el siguiente turno de una conversación entre un usuario y "
        "un agente de IA. Responde únicamente con JSON: tema (string corto), "
        "resumen (una o dos frases) y entidades (lista de nombres propios o "
        "términos clave, puede ser vacía).",
    ]
    if dominio_config:
        dominio = dominio_config.get("domain")
        if dominio:
            instrucciones.append(f"Dominio de referencia: {dominio}.")
        keywords = dominio_config.get("keywords")
        if keywords:
            instrucciones.append(
                "Términos relevantes en este dominio: " + ", ".join(keywords) + "."
            )
        extra = dominio_config.get("prompt_adicional")
        if extra:
            instrucciones.append(extra)
    instrucciones.append(f"Usuario: {turno.texto_usuario}")
    instrucciones.append(f"Agente: {turno.texto_agente}")
    return "\n".join(instrucciones)


def _llamar_ollama(
    prompt: str, *, modelo: str, base_url: str, timeout: float
) -> dict:
    """Llama a POST /api/generate de Ollama en modo de salida estructurada."""
    payload = json.dumps(
        {
            "model": modelo,
            "prompt": prompt,
            "format": _ESQUEMA_RESPUESTA,
            "stream": False,
            # qwen3 activa "thinking" por defecto: para extracción
            # estructurada simple eso multiplica la latencia sin aportar
            # nada (medido: ~26s de razonamiento vs ~0.5s sin él).
            "think": False,
        }
    ).encode("utf-8")
    peticion = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            cuerpo = json.loads(respuesta.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AnalisisFallido(f"Ollama no respondió: {exc}") from exc
    try:
        return json.loads(cuerpo["response"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise AnalisisFallido(f"respuesta de Ollama no es JSON válido: {exc}") from exc


def _ficha_escrubery(cli: str, *, script: str, timeout: float) -> dict | None:
    """Consulta escrubery para el CLI observado; None si falla (ADR-004)."""
    try:
        resultado = subprocess.run(
            [script, "ficha", "cli", cli],
            capture_output=True,
            timeout=timeout,
            text=True,
            check=True,
        )
        return json.loads(resultado.stdout)
    except (
        subprocess.SubprocessError,
        OSError,
        json.JSONDecodeError,
    ):
        return None


def analizar_turno(
    turno: Turno,
    *,
    modelo: str = MODELO_POR_DEFECTO,
    base_url: str = URL_OLLAMA_POR_DEFECTO,
    dominio_config: dict | None = None,
    escrubery_script: str | None = None,
    escrubery_cli: str = "codex-cli",
    # medido en el entorno real: ~90s si Ollama tuvo que recargar el
    # modelo en memoria (descargado por inactividad o por otro proceso
    # usando la GPU); ~1-7s con el modelo ya caliente.
    timeout: float = 120.0,
    llamar_modelo: Callable[..., dict] | None = None,
) -> Analisis:
    """Produce un Analisis a partir de un Turno (SPEC-002)."""
    prompt = _construir_prompt(turno, dominio_config)
    invocar = llamar_modelo or _llamar_ollama
    resultado = invocar(prompt, modelo=modelo, base_url=base_url, timeout=timeout)

    if not isinstance(resultado, dict):
        raise AnalisisFallido("la respuesta del modelo no es un objeto JSON")
    tema = resultado.get("tema")
    resumen = resultado.get("resumen")
    if not tema or not resumen:
        raise AnalisisFallido("el modelo no devolvió tema/resumen no vacíos")

    metadata_cli = None
    if escrubery_script:
        metadata_cli = _ficha_escrubery(
            escrubery_cli, script=escrubery_script, timeout=timeout
        )

    entidades_crudas = resultado.get("entidades")
    entidades = (
        [str(e) for e in entidades_crudas] if isinstance(entidades_crudas, list) else []
    )

    return Analisis(
        tema=tema,
        resumen=resumen,
        entidades=entidades,
        turn_id=turno.turn_id,
        session_id=turno.session_id,
        ruta_origen=turno.ruta_origen,
        offset_inicio=turno.offset_inicio,
        offset_fin=turno.offset_fin,
        cli=turno.cli,
        modelo_analisis=modelo,
        ocurrido_en=turno.timestamp_cierre,
        dominio=(dominio_config or {}).get("domain"),
        metadata_cli=metadata_cli,
    )
