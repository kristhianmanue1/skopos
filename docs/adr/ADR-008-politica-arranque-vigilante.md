# ADR-008: política de arranque del vigilante (decisión 8)

Estado: **aceptado** — decisión 8 🔒 firmada por el dueño el 2026-08-20
(Fase 3 / C-10(a), Hito 8), tras revisión aprobatoria de Pinax contra
código y corpus (conteo independiente bit a bit: 612/2,281,708,113;
intervalo 5.0 y timeout 120 s verificados; restricción Python ≥3.9
confirmada). Sometido a ronda adversarial pre-decisión (ronda 4,
`docs/rondas/2026-08-20-ronda-4-adr008.md`): 12 hallazgos incorporados
antes de la firma. Remedición fresca en
`docs/evidencia/remedicion-ciclo-c10-2026-08-20.md`.

## Contexto

`skopos watch` no distingue turnos históricos de nuevos: cada ciclo
descubre **todos** los rollouts del directorio y procesa todo turno que
no esté en Mongo (dedup ADR-005). En la práctica (dueño, 2026-08-13):
la primera corrida real analiza TODO el histórico sin feedback ni
límite — se detuvo a mano.

Remedición 2026-08-20 (método y advertencia de comparabilidad en la
evidencia): **612 rollouts / 2.28 GB / 14,822 turnos**; barrido de ~12 s
en reposo a ~123 s bajo carga alta, contra intervalo de 5 s; análisis de
90–126 s/turno en el estado del entorno de hoy (cota con carga y tamaños
de turno mayores que la línea base del 2026-08-19; 2 de 7 llamadas
cayeron al timeout por defecto). Backfill completo estimado: **~81 h a
~474 h** según ritmo.

Nota de forma (ronda 4, H7): P-002 §3.3(a) caracterizaba esta decisión
como "sin ADR nuevo" bajo el supuesto de que no tocaría ADR-005; la
exigencia del dueño (2026-08-20) de acotación explícita con enmienda
actada promovió el acto a ADR. Corrección de P-002 registrada aquí y en
el acta de la ronda.

## Decisión propuesta

**`skopos watch` arranca "desde ahora" por defecto; el backfill es
opt-in explícito (`--backfill`).**

- Al arrancar, el vigilante registra un corte `t0` y sólo procesa
  **turnos cerrados a partir de `t0`** (`timestamp_cierre >= t0`).
  Prefiltro de archivo por mtime (`mtime >= t0`, salvo archivos vivos
  que se siguen escribiendo: se procesan filtrando por turno) —
  optimización de descubrimiento, no semántica.
- `--backfill` restaura el comportamiento actual: procesa todo turno no
  guardado, sin distinción histórica. Es el modo de los pilotos de
  sesión única (Fase 3c/5: apuntar `--sessions-dir` a una copia
  aislada de la sesión piloto, o vía programática
  `procesar_rollout`).
- Alternativas descartadas:
  - **Backfill por defecto** (status quo): inviable a cualquier punto
    de la horquilla remedida (81–474 h), sin feedback, ya detenido a
    mano una vez.
  - **Backfill acotado por fecha/presupuesto** (`--backfill --desde` /
    `--max-turnos`): extensión natural del opt-in, no una alternativa a
    la política de arranque; se difiere hasta que un uso real la pida
    (los pilotos de sesión única la cubren con `--sessions-dir`).
  - **`t0` persistente entre reinicios**: cierra el hueco de reinicio
    sin ser el cursor de 3(b), pero introduce un estado persistido que
    hay que gobernar (escrituras, corrupción, desincronización) — una
    segunda pieza de estado para ganar poco mientras la vigilancia
    corra de forma sostenida. Se difiere; 3(b) lo cierra de raíz.
  - **Cursor persistente ahora** (lectura incremental): es la Fase
    3(b), gated a evidencia y con su propio ADR; mezclarla aquí
    agranda el acto de decisión. Este ADR no la prejuzga.

## Convivencia con ADR-005 (acotación explícita, exigida por el dueño)

ADR-005 decide: **la deduplicación vive en Mongo** (`existe_turn_id`
antes de analizar), no en un cursor local; sus consecuencias aceptan
releer archivos completos por ciclo.

- **Se mantiene íntegro**: Mongo sigue siendo la única autoridad de
  "ya procesado". No hay set local de turn_ids vistos, no hay cursor de
  offsets, y cada archivo descubierto se sigue leyendo completo. El
  corte `t0` nunca decide "esto ya está guardado" — eso lo sigue
  decidiendo Mongo.
- **Se acota una consecuencia, no la decisión**: la frase de
  consecuencias "cada ciclo del vigilante vuelve a leer y parsear los
  archivos .jsonl completos" queda acotada a "los archivos con
  actividad posterior al arranque". Es un filtro de **descubrimiento**
  (qué archivos mirar), ortogonal a dónde vive la dedup (Mongo).
- **No es el ADR que ADR-005 anticipó** (ronda 4, H4): el ADR
  pre-registrado por ADR-005 es el de **lectura incremental** (Fase
  3(b)). Éste responde al mismo disparador medido (volumen/ciclo) por
  otra vía — una política de arranque — y no sustituye a aquél.
- **Enmienda con acta, con mecánica explícita** (ronda 4, H5): al
  aceptarse este ADR, el agente implementador escribe una nota de
  enmienda fechada en el propio ADR-005 (qué se mantiene, qué se acota,
  puntero a este ADR y a la firma del dueño), registrada en el commit
  de aceptación/implementación — no en el acta de una ronda
  pre-decisión. Sin omisión.

## Consecuencias (si se acepta)

- (+) El arranque nunca dispara horas de Ollama invisibles; el
  comportamiento por defecto es vigilancia, no excavación.
- (+) `--backfill` explícito hace del backfill una decisión visible,
  acotable por directorio, apta para pilotos.
- (−) **Hueco en reinicio** (honesto): si el vigilante muere y
  reinicia, los turnos cerrados entre la caída y el nuevo `t0` quedan
  sin procesar hasta un `--backfill`. Con la vigilancia corriendo como
  servicio el hueco es mínimo; el cursor de la Fase 3(b) lo cerraría de
  raíz — otra razón para no cerrar esa puerta.
- (−) **El corpus histórico queda invisible por defecto** (ronda 4,
  H3): con "desde ahora", los 14,822 turnos previos nunca entran a
  Mongo salvo `--backfill` explícito — `skopos query` nace vacío
  respecto de todo el pasado. Es la cara operativa de la decisión: la
  memoria por defecto mira hacia adelante; la excavación del pasado es
  siempre un acto deliberado, acotable por directorio/fecha.
- (−) El corte por `timestamp_cierre` depende del reloj de Codex
  (evento `task_complete`; medido: 14,822/14,822 turnos con timestamp,
  skew 0.0 s contra mtime local en los archivos recientes — misma
  máquina). Un turno **sin** timestamp (0 medidos) se trata como
  histórico (no procesado por defecto) — conservador, y aplica también
  a un eventual turno futuro sin timestamp. Nota de implementación
  (ronda 4, H11): los timestamps terminan en `Z` y el entorno corre
  Python 3.9.6, donde `datetime.fromisoformat` no parsea `Z` — el
  parser debe reemplazarlo o usar `strptime`.
- Cambios de superficie: `skopos watch [--backfill]`; SPEC-005 y su
  contrato se enmiendan al implementar; no se toca ADR-005 más allá de
  la nota de enmienda descrita.

## Firma de decisión

- Dueño: firma 🔒 comunicada en canal del agente y confirmada con
  revisión aprobatoria de Pinax (2026-08-20) · Alternativa: **"desde
  ahora" por defecto + `--backfill` opt-in**
- Exigencias de la firma, registradas: (1) la marginalidad del timeout
  de 120 s (2/7 llamadas del snapshot 2026-08-20) queda como riesgo
  conocido del plan para las Fases 3c/5 — fuera del alcance de este
  ADR, no olvidada; (2) la nota de enmienda de ADR-005 va en este
  mismo commit de aceptación, fechada, con puntero a esta firma.

## Decisiones de implementación (cerradas al implementar, 2026-08-20)

- **Filtro semántico por turno** en `procesar_rollout(desde=…)`
  (`orquestador.py`): turnos cerrados antes de `desde` quedan fuera de
  la ventana **sin producir resultado** (no son `omitido`: nunca se les
  consultó a la dedup). Turno sin timestamp o no parseable → histórico.
- **Prefiltro de archivo por mtime** en `vigilante.ciclo(t0=…)`:
  archivo con `mtime < t0` no se parsea (optimización de descubrimiento;
  skew mtime↔evento medido 0.0 s, ronda 4). `OSError` al hacer `stat`
  → se salta el archivo en ese ciclo (mismo criterio que SPEC-001 para
  archivo inexistente).
- **`ciclo()` mantiene `t0=None` por defecto** (sin corte): la política
  vive en `ejecutar`/`watch_command` (`t0 = now` al arrancar salvo
  `backfill=True`), que es la frontera de SPEC-005; `ciclo` y
  `procesar_rollout` quedan como primitivas explícitas.
- **Timestamps `Z` en Python 3.9**: `_parsear_timestamp` sustituye `Z`
  por `+00:00` antes de `fromisoformat` (nota de la ronda 4, H11).
