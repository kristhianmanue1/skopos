# Skopos

Skopos (Σκοπός)

Significado: Observador, meta, objetivo o vigilante. Aunque tiene una 'k' intermedia, la cadencia y el inicio suave le dan cierta similitud.

Captura turnos de Codex, Claude Code, Cline, Kimi Code y OpenCode.
Los indexa en MongoDB y permite analizarlos con un LLM para recuperarlos
por tema. `query` comprueba longitud y sello del fragmento de origen cuando
el sello existe; acepta legado sin sello y lo marca `sellado:false`.
`search` devuelve texto indexado, redactado y acotado, sin releer el origen
ni verificar su sello. Hay una limitación histórica abierta en P-007.

Construido siguiendo el método de
[Skevi](https://github.com/kristhianmanue1/Skevi) (F0→F3). Las decisiones
de diseño están en `docs/`, no aquí — este README es el contrato de
arranque: cómo se construye, corre y prueba.

**Estado documental verificado el 2026-09-12:** implementados parsers
multi-CLI, índice, consultas, vigilancia incremental y `analyze` para crear
el primer análisis de turnos ya indexados. Ollama es el proveedor por
defecto; ADR-014 permite otro proveedor con autorización. Este estado del
código no certifica que Mongo/Ollama estén activos ni cierra corridas en vivo.

```bash
python3 -m skopos query "<tema>"                          # análisis temáticos
python3 -m skopos search "<texto>"                        # turnos indexados
python3 -m skopos index --help                            # indexación sin LLM
python3 -m skopos watch [--sessions-dir DIR] [--intervalo SEGUNDOS] [--backfill]
python3 -m skopos reanalyze <turn_id> [--solo-redaccion]    # supersede (ADR-007)
python3 -m skopos analyze --help                          # filtros y ventana
# analyze admite --project, --cli, --anchor, --since, --until, --limit, --dry-run
```

`watch` arranca "desde ahora" por defecto (ADR-008): sólo procesa turnos
cerrados a partir de su arranque; el histórico exige `--backfill`
explícito.

`analyze` omite los turnos que ya tienen análisis; `reanalyze` crea una
nueva versión explícita. `reanalyze`, `index` y `search` conservan los alias
`reanalizar`, `indexar` y `buscar`. Los flags legados españoles siguen
vigentes: consulta `<comando> --help` antes de invocar el comando.

**Limitación abierta:** P-007 registra offsets históricos que impiden releer
el fragmento original de parte del índice. La comprobación niega el fragmento
cuando falla su sello. La reparación y la causa siguen pendientes; esta
actualización no modifica los datos. Ver la propuesta en `docs/propuestas/`.

**Idioma:** ADR-018 establece identificadores nuevos en inglés y comunicación,
producto, documentación y comentarios en español por defecto. La persona
puede elegir el idioma de la conversación sin cambiar la política persistente.
Los nombres existentes se preservan por compatibilidad.

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
  vive en el entorno, jamás en el repo; ver `docs/adr/adr-014-analisis-multi-proveedor.md`).
- **Estructura:** `src/skopos/` por paquete instalable
  (`pyproject.toml`, `setuptools`), `tests/` con `unittest` de la
  biblioteca estándar — sin dependencias de testing nuevas.
- **Verificación:** unittest y gates locales de Skevi. No se introduce
  linter ni CI en esta revisión documental.
- **Adopción de Skevi:** por referencia (este README y `docs/`), no
  vendorizada — no se copió el estándar/guía completos de Skevi a este
  repo. Límites de tamaño de archivo: se heredan los valores por defecto
  del estándar de Skevi (800 líneas genérico, 200 `AGENTS.md`, 300
  `README.md`) y se comprueban con el **gate de Skevi** (ADR-015):
  `python3 scripts/check_sizes.py && python3 scripts/check_plans.py`,
  configurado en `skevi-gate.json` (canon propio de skopos; gate de
  planes E1-E5 inactivo hasta que haya un plan nuevo que lo conforme).

## Próximos pasos

El estado detallado y la procedencia de cada hito están en
`docs/hoja-de-ruta.md`; las decisiones viven en `docs/adr/`.

1. **P-007:** decidir y verificar una reparación del índice histórico.
   No se autoriza reindexar ni borrar documentos por leer esta lista.
2. **Evaluar la corrida de `analyze`:** el comando está implementado
   (ADR-017); la hoja de ruta registra un piloto acotado a siete días.
   Verificar su resultado antes de diseñar `curated-anchor`/`context-block`
   o dar por resuelta la propuesta P-005. No se declara aquí su finalización.
3. **Persistencia de `watch` tras reinicio:** seguimiento de LaunchAgent,
   sin configuración o activación en esta revisión.
4. **Ampliación de orígenes:** prime-agent y otras conversaciones requieren
   diseño propio; qwen-code permanece diferido por falta de cierre de turno.
5. **Lectura por sesión/rango y búsqueda semántica:** `read` sigue diferido;
   embeddings son condicionales a insuficiencia de `$text` en uso real.

## Riesgos conocidos, aceptados por ahora (no resueltos en esta ronda)

- **Sin retención ni borrado.** Los documentos guardados no expiran ni
  hay comando para borrarlos selectivamente (la
  manipulación manual de colecciones no constituye una política de retención). Las conversaciones capturadas
  quedan indefinidamente en Mongo, incluidas rutas absolutas del sistema
  de archivos del usuario. Riesgo registrado desde el diseño inicial. El proyecto
  usa almacenamiento local; la salida hacia un proveedor remoto o un
  consumidor externo exige revisar este riesgo (ADR-014, REQ-10).
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

## Mediciones históricas y límites de verificación

La medición inicial de 28 turnos registró 548.8 s, aproximadamente
19.6 s/turno. Es evidencia de ese caso, no capacidad actual garantizada.
La hoja de ruta del 2026-09-12 registra cerca de 90 s/turno para anclas
grandes. `analyze --dry-run` todavía usa la constante de 19.6 s/turno y
no descuenta análisis existentes: su estimación puede ser inadecuada para
ese corpus. Esta revisión documenta el límite; no recalibra el código.

Las pruebas dependientes de MongoDB/Ollama pueden saltarse si los servicios
no están disponibles; el runner informa los skips. Una corrida sin esas
integraciones no acredita el funcionamiento end-to-end. La verificación de
esta actualización queda en `docs/evidencia/reconciliacion-documental-2026-09-12.md`.
