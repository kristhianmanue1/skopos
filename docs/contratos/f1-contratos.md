# F1 — Contratos de interfaz

## CONTRATO: rollout-jsonl-de-codex v1

Entrada:
  `ruta`: string [obligatorio] — ruta a un archivo `*.jsonl` bajo
  `~/.codex/sessions/`

Salida:
  eventos: lista de objetos JSON, uno por línea válida — Skopos no valida
  ni controla el esquema interno completo de Codex, sólo filtra los tipos
  relevantes: `response_item` (texto) y `event_msg` con
  `payload.type == "task_complete"` (cierre de turno)

Errores:
  `archivo inexistente`: se ignora en ese ciclo de poll, no es fatal
  `línea corrupta`: se descarta esa línea, se continúa con el resto

Invariantes:
  - el archivo se lee completo en cada llamada, desde el byte 0 — no hay
    lectura incremental ni parámetro `offset`/`baseline` (a diferencia
    del prototipo original). Decisión consciente, ver ADR-005: la
    deduplicación entre ciclos vive en Mongo, no en el punto de lectura
    del archivo. Corrección de la v1 original de este contrato, que
    prometía un `offset` que nunca se implementó (ronda adversarial
    2026-08-13) — si el volumen de rollouts hace que releer archivos
    completos sea un problema medido, eso es un ADR nuevo, no un ajuste
    silencioso aquí.

Compatibilidad: el formato de los rollouts es externo, de Codex, y no
versionado por Skopos. Un cambio de Codex que rompa el parseo se detecta
como fallo de extracción (SPEC-001), no como una versión propia de este
contrato — Skopos no controla esa frontera, sólo la observa.

## CONTRATO: documento-analisis-mongo v1

Entrada (esquema del documento insertado en la colección):
  `tema`: string [obligatorio]
  `resumen`: string [obligatorio]
  `turn_id`: string [obligatorio]
  `session_id`: string [obligatorio]
  `ruta_origen`: string [obligatorio] — ruta al `rollout-*.jsonl` de origen
  `offset_inicio`: int [obligatorio]
  `offset_fin`: int [obligatorio]
  `cli`: string [obligatorio] — CLI de origen del turno (ej.
  `"codex-cli"`, mismo nombre que usa escrubery)
  `modelo_analisis`: string [obligatorio] — modelo que produjo este
  análisis (ej. `"qwen3:8b"`); necesario para comparar CLIs/modelos entre
  sí más adelante
  `ocurrido_en`: string (ISO 8601) [opcional] — cuándo pasó la
  conversación de verdad (del evento `task_complete` original), NO cuándo
  Skopos la procesó; puede faltar si el CLI de origen no trae timestamp
  `dominio`: string [opcional] — presente si se usó configuración de
  dominio (ADR-003)
  `creado_en`: string (ISO 8601) [obligatorio] — cuándo Skopos guardó el
  documento (puede ser mucho después de `ocurrido_en` si hubo backfill)

Salida: el mismo documento, recuperable mediante búsqueda de texto sobre
`tema`/`resumen` (ver CONTRATO cli-skopos-query v1 — cambió de igualdad
exacta a `$text` en la ronda adversarial 2026-08-13).

Errores:
  inserción sin `turn_id` o sin `ruta_origen`: rechazada explícitamente
  por `guardar_analisis` (`DocumentoInvalido`), no se persiste —
  aplicado en el borde desde la ronda adversarial 2026-08-13; antes de
  eso la garantía era sólo "por construcción" del resto del pipeline, no
  una barrera real
  `turn_id` duplicado (dos escrituras concurrentes para el mismo turno):
  rechazada por el índice único de Mongo (`DuplicateKeyError`), el
  orquestador lo trata como "omitido", no como fallo

Invariantes:
  - todo documento es resoluble a un fragmento real vía `ruta_origen` +
    `offset_inicio` + `offset_fin`
  - `turn_id` es único en la colección (índice único, cierra la
    condición de carrera entre `existe_turn_id` e `insert_one`)

Compatibilidad: agregar campos opcionales es compatible hacia atrás;
quitar o renombrar `tema`, `resumen`, `turn_id`, `ruta_origen`,
`offset_inicio` u `offset_fin` exige v2 y un ADR que sustituya a éste.

## CONTRATO: config-dominio v1

Entrada (archivo JSON, ruta configurable):
  `domain`: string [obligatorio] — nombre del dominio (ej.
  `"arquitectura-software"`)
  `keywords`: lista de string [opcional] — términos que orientan la
  extracción
  `prompt_adicional`: string [opcional] — instrucción extra para el
  modelo de análisis (SPEC-002)

Salida: usado como entrada opcional de SPEC-002; no produce salida propia.

Errores:
  archivo declarado pero inexistente o JSON inválido: falla explícita al
  arrancar, no se ignora en silencio (evita analizar sin el dominio que
  el humano pidió, sin avisar)

Compatibilidad: agregar campos opcionales es compatible; quitar o
renombrar `domain` exige v2.

## CONTRATO: consulta-escrubery-cli v1

Entrada:
  `cli`: string [obligatorio] — nombre del CLI tal como lo identifica
  escrubery (confirmado con datos reales: `"codex-cli"`, ver
  `scripts/consultar listar` en EV-7 de F0)

Salida:
  `ficha`: objeto JSON con metadata y bloque de `procedencia` (fuente,
  fecha, hash) por dato, tal como lo devuelve
  `scripts/consultar ficha cli <cli>`; ausente si escrubery no tiene
  ficha para ese CLI

Errores:
  escrubery no disponible (proceso falla, timeout, clon local ausente o
  desactualizado): se trata como "sin ficha" — nunca produce un error
  fatal ni bloquea el análisis (ADR-004, REQ-10)

Invariantes:
  - una consulta fallida a escrubery nunca detiene el pipeline de Skopos

Compatibilidad: escrubery es un proyecto externo con su propio ciclo de
vida y su propio contrato (`CONTRATO_API_v0.md` en ese repo); Skopos no
fija ese contrato, sólo declara cómo tolera su ausencia o cambio.

## CONTRATO: cli-skopos-query v1

Entrada:
  `tema`: string [obligatorio] — primer argumento posicional de
  `skopos query <tema>`; se usa como término de búsqueda de texto
  completo (`$text`) sobre `tema`+`resumen`, no como igualdad exacta —
  corregido en la ronda adversarial 2026-08-13: la igualdad exacta
  fallaba contra temas que el LLM redacta con palabras distintas para
  la misma idea (verificado con datos reales)

Salida (JSON a stdout):
  `resultados`: lista de objetos `{tema, resumen, turn_id, ruta_origen,
  fragmento_completo}`, ordenados por relevancia de texto (`textScore`)

Errores:
  tema sin resultados: exit 0, `{"resultados": []}`
  Mongo no disponible: exit distinto de cero, mensaje a stderr, nada en
  stdout

Invariantes:
  - stdout es siempre JSON válido cuando el exit code es 0
  - `$text` es coincidencia por palabra, no semántica: sinónimos o
    reformulaciones sin palabras en común no se recuperan (búsqueda por
    embeddings queda para un ADR futuro si la evidencia lo justifica)

Compatibilidad: agregar campos al objeto de resultado es compatible;
quitar o renombrar campos exige v2.
