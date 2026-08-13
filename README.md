# Skopos

Observa turnos de un CLI de IA (Codex, para empezar), analiza lo dicho y
lo guarda de forma recuperable por tema, con acceso al fragmento completo
de origen cuando hace falta.

Construido siguiendo el método de
[Skevi](https://github.com/kristhianmanue1/Skevi) (F0→F3). Las decisiones
de diseño están en `docs/`, no aquí — este README es el contrato de
arranque: cómo se construye, corre y prueba.

**Estado:** F3 — pipeline completo funcionando de punta a punta con datos
reales: captura (SPEC-001) → análisis vía Ollama local (SPEC-002) →
almacenamiento en MongoDB local (SPEC-003) → consulta por CLI (SPEC-004) →
vigilante en vivo (SPEC-005). Verificado contra rollouts reales de Codex,
no sólo fixtures sintéticos.

```bash
python3 -m skopos query "<tema>"
python3 -m skopos watch [--sessions-dir DIR] [--intervalo SEGUNDOS]
```

**Prueba de escala real** (sesión de hoy, 28 turnos, 1.2MB): 42,958
caracteres de conversación real (~13 min de conversación según
`ocurrido_en`) tardaron 548.8s (~9min, ~19.6s/turno) en procesarse
completos — captura + análisis con `qwen3:8b` + guardado en Mongo, 0
fallos. Referencia útil para estimar cuánto tardaría un backfill de
sesiones grandes (la mayor en este entorno tiene ~23,700 líneas).

Modelo de análisis confirmado: `qwen3:8b` (sucesor de `qwen2.5:7b`,
descargado y probado end-to-end). MongoDB local instalado vía Homebrew
(`mongodb-community`, tap `mongodb/brew`) y corriendo como servicio.

## Documentación de diseño

- `docs/f0-analisis-y-requerimientos.md` — problema, REQ-*, restricciones,
  evidencia.
- `docs/adr/` — decisiones con alternativas (motor de IA, interfaz de
  recuperación, config de dominio, escrubery como fuente opcional).
- `docs/specs/f1-specs.md` — comportamiento observable por componente.
- `docs/contratos/f1-contratos.md` — fronteras: formato de Codex, esquema
  de Mongo, config de dominio, CLI de consulta, consulta a escrubery.
- `docs/f1-maquina-estados.md` — ciclo de vida de un turno.

## Construcción

Requiere Python 3.9+ (confirmado en el entorno de desarrollo: 3.9.6).

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
```

## Ejecución

```bash
python3 -m skopos
```

## Pruebas

```bash
python3 -m unittest discover -s tests
```

## Decisiones de cascarón

- **Gestor de paquetes:** `pip` + `venv` estándar. Dependencia declarada:
  `pymongo>=4.17,<5` (confirmada contra MongoDB 8.3.7 local). Sin
  lockfile todavía — una sola dependencia directa no lo justifica aún.
- **Modelo de análisis:** Ollama local vía su API HTTP
  (`urllib` de stdlib, sin cliente HTTP nuevo como dependencia), modelo
  `qwen3:8b`.
- **Estructura:** `src/skopos/` por paquete instalable
  (`pyproject.toml`, `setuptools`), `tests/` con `unittest` de la
  biblioteca estándar — sin dependencias de testing nuevas.
- **Linter/CI:** ninguno todavía. Se decide cuando el proyecto tenga más
  de un módulo implementado y valga la pena automatizarlo.
- **Adopción de Skevi:** por referencia (este README y `docs/`), no
  vendorizada — no se copió el estándar/guía completos de Skevi a este
  repo. Límites de tamaño de archivo: se heredan los valores por defecto
  del estándar de Skevi (800 líneas genérico, 200 `AGENTS.md`, 300
  `README.md`) por declaración, sin gate automatizado propio todavía.

## Pendientes conocidos

- **Primer arranque del vigilante = backfill completo, sin aviso previo.**
  `skopos watch` no distingue turnos históricos de turnos nuevos: la
  primera vez que corre contra `~/.codex/sessions/` real, analiza (con
  Ollama, uno por uno) todo lo que nunca se guardó, sin feedback hasta
  terminar el ciclo completo — puede ser mucho volumen y mucho tiempo si
  hay historial acumulado. Confirmado al probarlo: lo detuve manualmente
  en vez de dejarlo terminar. Falta decidir (F1, con el humano): ¿arranca
  sólo "desde ahora" por defecto y el backfill es opt-in explícito?
- Integración con escrubery (REQ-10) implementada en `analisis.py` pero
  sin probar contra el repo real todavía (requiere pasar
  `escrubery_script` explícitamente al llamar `analizar_turno`).
- `qwen3:8b` con `think:false` responde en 1-7s con el modelo ya cargado
  en memoria, pero Ollama lo descarga tras inactividad — la primera
  llamada tras eso puede tardar hasta ~90s (medido). El timeout por
  defecto (120s) lo cubre; considerar precargar el modelo si esto importa
  para uso interactivo.
