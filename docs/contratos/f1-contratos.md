# F1 — Contratos de interfaz

## CONTRATO: rollout-jsonl-de-codex v1

Entrada:
  `ruta`: string [obligatorio] — ruta a un archivo `*.jsonl` bajo
  `~/.codex/sessions/`
  `offset`: int [opcional] — posición de lectura desde la que continuar
  (por defecto 0, o el tamaño actual del archivo en modo "baseline" para
  ignorar histórico, igual que `RolloutWatcher.baseline()` del prototipo)

Salida:
  eventos: lista de objetos JSON, uno por línea válida — Skopos no valida
  ni controla el esquema interno completo de Codex, sólo filtra los tipos
  relevantes: `response_item` (texto) y `event_msg` con
  `payload.type == "task_complete"` (cierre de turno)

Errores:
  `archivo inexistente`: se ignora en ese ciclo de poll, no es fatal
  `línea corrupta`: se descarta esa línea, se continúa con el resto

Invariantes:
  - el offset de lectura nunca retrocede, salvo que el archivo se trunque
    (tamaño actual menor que el offset conocido)

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
  `dominio`: string [opcional] — presente si se usó configuración de
  dominio (ADR-003)
  `creado_en`: string (ISO 8601) [obligatorio]

Salida: el mismo documento, recuperable mediante consulta sobre `tema`.

Errores:
  inserción sin `turn_id`, `ruta_origen` u offsets: rechazada, no se
  persiste (invariante de SPEC-003: ningún documento queda huérfano)

Invariantes:
  - todo documento es resoluble a un fragmento real vía `ruta_origen` +
    `offset_inicio` + `offset_fin`

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
  `skopos query <tema>`

Salida (JSON a stdout):
  `resultados`: lista de objetos `{tema, resumen, turn_id, ruta_origen,
  fragmento_completo}`

Errores:
  tema sin resultados: exit 0, `{"resultados": []}`
  Mongo no disponible: exit distinto de cero, mensaje a stderr, nada en
  stdout

Invariantes:
  - stdout es siempre JSON válido cuando el exit code es 0

Compatibilidad: agregar campos al objeto de resultado es compatible;
quitar o renombrar campos exige v2.
