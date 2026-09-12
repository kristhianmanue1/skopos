# Skopos

Skopos (Σκοπός)

Significado: Observador, meta, objetivo o vigilante. Aunque tiene una 'k' intermedia, la cadencia y el inicio suave le dan cierta similitud.

Observa turnos de un CLI de IA (Codex, para empezar), analiza lo dicho y
lo guarda de forma recuperable por tema, con acceso al fragmento completo
de origen cuando hace falta.

Construido siguiendo el método de
[Skevi](https://github.com/kristhianmanue1/Skevi) (F0→F3). Las decisiones
de diseño están en `docs/`, no aquí — este README es el contrato de
arranque: cómo se construye, corre y prueba.

**Estado:** F3 — pipeline completo funcionando de punta a punta con datos
reales: captura (SPEC-001) → análisis con LLM (SPEC-002; Ollama local
por defecto, multi-proveedor vía ADR-014) →
almacenamiento en MongoDB local (SPEC-003) → consulta por CLI (SPEC-004) →
vigilante en vivo (SPEC-005). Verificado contra rollouts reales de Codex,
no sólo fixtures sintéticos.

```bash
python3 -m skopos query "<tema>"
python3 -m skopos watch [--sessions-dir DIR] [--intervalo SEGUNDOS] [--backfill]
python3 -m skopos reanalyze <turn_id> [--solo-redaccion]    # supersede (ADR-007)
python3 -m skopos analyze [--project P] [--anchor PATRON] [--limit N] [--dry-run]
                                                            # analiza turnos ya
                                                            # indexados (ADR-017)
```

`watch` arranca "desde ahora" por defecto (ADR-008): sólo procesa turnos
cerrados a partir de su arranque; el histórico exige `--backfill`
explícito.

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

- `docs/guia-rapida.md` — arrancar contexto en 5 minutos (empieza aquí).
- `docs/hoja-de-ruta.md` — hitos, qué está cerrado y qué falta.
- `docs/f0-analisis-y-requerimientos.md` — problema, REQ-*, restricciones,
  evidencia.
- `docs/adr/` — decisiones con alternativas (motor de IA, interfaz de
  recuperación, config de dominio, escrubery como fuente opcional).
- `docs/specs/f1-specs.md` — comportamiento observable por componente.
- `docs/contratos/f1-contratos.md` — fronteras: formato de Codex, esquema
  de Mongo, config de dominio, CLI de consulta, consulta a escrubery.
- `docs/f1-maquina-estados.md` — ciclo de vida de un turno.
- `docs/propuestas/` — propuestas con estado explícito por documento:
  P-001 (integración con AN-KLA) quedó **superada** por la decisión
  multi-CLI del dueño (2026-08-20); P-002 (ajuste del ciclo de
  precondiciones) fue **aprobada** y materializada en el ciclo
  Fases 0–7. No toda propuesta está "abierta, sin decidir" — el estado
  vive en cada archivo.

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
- **Modelo de análisis:** proveedor configurable por entorno (ADR-014) —
  **Ollama local por defecto** vía su API HTTP (`urllib` de stdlib, sin
  cliente HTTP nuevo como dependencia), modelo `qwen3:8b`. Cualquier API
  compatible-OpenAI (LM Studio, vLLM, z.ai, OpenRouter…) entra por
  `SKOPOS_LLM_*` — proveedor remoto sólo con decreto explícito (la key
  vive en el entorno, jamás en el repo; ver `docs/adr/adr-014`).
- **Estructura:** `src/skopos/` por paquete instalable
  (`pyproject.toml`, `setuptools`), `tests/` con `unittest` de la
  biblioteca estándar — sin dependencias de testing nuevas.
- **Linter/CI:** ninguno todavía. Se decide cuando el proyecto tenga más
  de un módulo implementado y valga la pena automatizarlo.
- **Adopción de Skevi:** por referencia (este README y `docs/`), no
  vendorizada — no se copió el estándar/guía completos de Skevi a este
  repo. Límites de tamaño de archivo: se heredan los valores por defecto
  del estándar de Skevi (800 líneas genérico, 200 `AGENTS.md`, 300
  `README.md`) y se comprueban con el **gate de Skevi** (ADR-015):
  `python3 scripts/check_sizes.py && python3 scripts/check_plans.py`,
  configurado en `skevi-gate.json` (canon propio de skopos; gate de
  planes E1-E5 inactivo hasta que haya un plan nuevo que lo conforme).

## Próximos pasos

**Estado (2026-09-06):** el ciclo multi-CLI de P-002 está CERRADO — los
5 CLIs (codex, claude-code, cline, kimi-code, opencode) se capturan,
indexan y vigilan en vivo (hitos 13–19). El análisis es multi-proveedor
(ADR-014, hito 20). El mapa completo, en `docs/hoja-de-ruta.md`; el
detalle de decisiones, en `docs/adr/` (14 ADRs).

**Cola viva (en orden sugerido):**

1. **Analizar desde el índice** — interpretar turnos del índice P-004
   sin re-leeer archivos; habilita re-análisis masivo (con ADR-014, un
   proveedor rápido lo baja de años a horas) y el salto de
   `documento-analisis-mongo` a v3.
2. **LaunchAgent para `watch`** — sobrevivir reinicios (hoy es proceso
   suelto, ver ADR-013/hoja-de-ruta hito 19).
3. **`skopos read`** (hito 9, diferido) y **embeddings** (hito 11,
   condicional a que `$text` se quede corto).
4. **Parser qwen-code** — diferido por el dueño: sin marca de cierre de
   turno (ver `docs/evidencia/reconocimiento-qwen-2026-08-28.md`).

Diferidos: `skopos read` por sesión/fecha/rango (lo prepara el índice
`ocurrido_en` de C-9); precargar `qwen3:8b` antes de uso interactivo
(latencia percibida, no corrección); búsqueda semántica si `$text`
(ADR-006) resulta insuficiente en uso real.

## Riesgos conocidos, aceptados por ahora (no resueltos en esta ronda)

- **Sin retención ni borrado.** Los documentos guardados no expiran ni
  hay comando para borrarlos selectivamente (más allá de vaciar la
  colección a mano, como se hizo hoy). Las conversaciones capturadas
  quedan indefinidamente en Mongo, incluidas rutas absolutas del sistema
  de archivos del usuario. Aceptado explícitamente por ahora — todo
  corre local, sin exposición externa; se revisita si `metadata_cli`/otro
  consumidor externo (REQ-10, F0) se activa de verdad.
- **Redacción de secretos es defensa por patrón, no garantía.** Cubre
  formatos conocidos (API keys de OpenAI/Anthropic, AWS, GitHub, Slack,
  JWT) en `tema`/`resumen`/`entidades`; no cubre secretos con formato
  desconocido, ni protege `fragmento_completo` (que siempre expone el
  texto original sin redactar, por diseño — es la evidencia cruda).

## Ronda adversarial de arquitectura (2026-08-13)

Ejecutada con contexto fresco (subagente separado, sin haber escrito el
código) enfocada en buenas prácticas para software que produce/consume
salida de agentes de IA. Encontró y se corrigieron: 3 BLOCKER (fallo de
Mongo en el chequeo de deduplicación tumbaba `watch` entero; inyección de
prompt reproducida contra Ollama real que filtró un secreto falso a
Mongo; CONTRATO que prometía lectura incremental nunca implementada) y 4
HIGH (condición de carrera sin índice único sobre `turn_id`; búsqueda por
tema con igualdad exacta que fallaba contra reformulaciones del LLM;
ítems no-string en `entidades` coercionados en vez de descartados;
validación de borde ausente pese a que el contrato la prometía). Detalle
completo en los ADR/CONTRATO/SPEC actualizados y en `tests/` (8 tests
nuevos de regresión, uno por hallazgo corregido).

## Datos operativos medidos (para dimensionar lo anterior)

- Sesión real de hoy (28 turnos, 1.2MB, 42,958 caracteres, ~13min de
  conversación real): 548.8s de procesamiento total, ~19.6s/turno, 0
  fallos.
- La sesión más grande del entorno de desarrollo tiene ~23,700 líneas —
  a ese ritmo, un backfill completo del historial tomaría horas, no
  minutos. Esto es lo que hace urgente el punto 1 de arriba.
