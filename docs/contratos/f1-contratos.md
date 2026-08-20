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
  - [C-9, 2026-08-20] el evento `turn_context` es fuente del campo
    `proyecto`: `basename(cwd)` cuando `cwd` tiene al menos dos niveles
    bajo `$HOME`; ausente en cualquier otro caso (regla completa y
    muestreo en `docs/evidencia/muestreo-cwd-c9-2026-08-20.md`).
    `workspace_roots` NO se usa: arrastra rutas de visualización de
    Codex ajenas al proyecto (contaminación medida). Un turno sin
    `turn_context` previo produce `proyecto` ausente, no vacío. Un
    `turn_context` cuyo cwd no deriva proyecto resetea el valor —
    nunca se hereda el proyecto de un `turn_context` anterior (H1,
    ronda adversarial de Fase 1, 2026-08-20).

Compatibilidad: el formato de los rollouts es externo, de Codex, y no
versionado por Skopos. Un cambio de Codex que rompa el parseo se detecta
como fallo de extracción (SPEC-001), no como una versión propia de este
contrato — Skopos no controla esa frontera, sólo la observa.

## CONTRATO: documento-analisis-mongo v2

> v2 (2026-08-20, ADR-007, decisión 🔒 del dueño — alternativa B): el
> documento gana `version`; la unicidad pasa de `turn_id` a
> `(turn_id, version)`; la versión vigente de un turno es la de número
> mayor y es la única que se sirve; existe la operación de supersede
> (inserción de versión nueva, con reintento). v1 queda sustituida; los
> cambios están marcados [v2].

Entrada (esquema del documento insertado en la colección):
  `tema`: string [obligatorio]
  `resumen`: string [obligatorio]
  `turn_id`: string [obligatorio]
  `version`: int [obligatorio, v2] — primera versión = 1; la vigente es
  la de número mayor
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
  `proyecto`: string [opcional, C-9 2026-08-20] — nombre del proyecto
  derivado de `turn_context.cwd` (regla en el CONTRATO
  rollout-jsonl-de-codex); ausente = desconocido. Con supersede [v2], un
  documento vigente sin `proyecto` puede completarse insertando versión
  nueva que lo traiga — la vieja no se toca
  `dominio`: string [opcional] — presente si se usó configuración de
  dominio (ADR-003)
  `entidades`: lista de string [opcional, saldado en v2 — siempre se
  escribieron cuando el análisis las trajo, sin estar listadas aquí]
  `creado_en`: string (ISO 8601) [obligatorio] — cuándo Skopos guardó el
  documento (puede ser mucho después de `ocurrido_en` si hubo backfill);
  cada versión lleva su propio `creado_en`

Salida: la **versión vigente** del documento, recuperable mediante
búsqueda de texto sobre `tema`/`resumen` (ver CONTRATO cli-skopos-query
v1 — cambió de igualdad exacta a `$text` en la ronda adversarial
2026-08-13). Versiones superseded no se sirven por las lecturas
públicas, pero permanecen en la colección como auditoría.

Errores:
  inserción sin `turn_id` o sin `ruta_origen`: rechazada explícitamente
  por `guardar_analisis` (`DocumentoInvalido`), no se persiste —
  aplicado en el borde desde la ronda adversarial 2026-08-13; antes de
  eso la garantía era sólo "por construcción" del resto del pipeline, no
  una barrera real
  `(turn_id, version)` duplicado (dos escrituras concurrentes de la
  MISMA versión): rechazada por el índice único compuesto. En ingesta
  (versión 1), el orquestador la trata como "omitido", no como fallo; en
  supersede explícito, se re-computa max(versión) y se reintenta —
  nunca se omite en silencio [v2, H2 de la ronda 2 del ADR-007]

Operación de supersede [v2]: `superseder_documento(turn_id, cambios)`
copia la versión vigente completa y sustituye sólo los campos de
`cambios`, insertando `version = max + 1`. Disparadores: comando
`skopos reanalizar <turn_id>` (re-análisis completo) o
`skopos reanalizar <turn_id> --solo-redaccion` (re-aplicar patrones de
secretos vigentes, sin Ollama). El vigilante jamás dispara supersede.

Índices: único compuesto `(turn_id, version)` [v2 — sustituye al único
simple de `turn_id`, que el bootstrap debe retirar]; texto sobre
`tema`+`resumen`; `proyecto`, `cli`, `ocurrido_en` [C-9, 2026-08-20].

Invariantes:
  - todo documento es resoluble a un fragmento real vía `ruta_origen` +
    `offset_inicio` + `offset_fin`, en cualquier versión
  - `(turn_id, version)` es único en la colección (índice único
    compuesto); un mismo `turn_id` puede tener N versiones
  - ninguna versión existente se modifica ni se borra: insert-only
    físico (ADR-007); "reemplazado" es implícito (existe versión mayor)
  - las lecturas que sirven datos devuelven sólo la vigente; el filtro
    de vigencia es una **carga de seguridad** (una lectura que lo
    olvide sirve, p.ej., secretos pre-redacción — H1 de la ronda 2 del
    ADR-007)

Compatibilidad: documentos v1 (sin `version`) legibles como legado;
toda escritura nueva produce v2. Con 0 documentos al momento del cambio
(verificado 2026-08-20), no hay migración de datos — sí del índice
(retirar el único simple), con el riesgo documentado de que un proceso
con código viejo lo resucite.

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
  `--proyecto`: string [opcional, C-9 2026-08-20] — filtra los
  resultados por el campo `proyecto` del documento; los documentos sin
  `proyecto` (pre-C-9 o desconocido) quedan fuera cuando el filtro está
  presente, nunca se inventa una coincidencia para ellos

Salida (JSON a stdout):
  `resultados`: lista de objetos `{tema, resumen, turn_id, ruta_origen,
  proyecto, fragmento_completo}` — `proyecto` añadido por C-9
  (2026-08-20): valor del campo del documento o `null` si no lo tiene —
  ordenados por relevancia de texto (`textScore`)

Errores:
  tema sin resultados: exit 0, `{"resultados": []}`
  Mongo no disponible: exit distinto de cero, mensaje a stderr, nada en
  stdout

Invariantes:
  - stdout es siempre JSON válido cuando el exit code es 0
  - `$text` es coincidencia por palabra, no semántica: sinónimos o
    reformulaciones sin palabras en común no se recuperan (búsqueda por
    embeddings queda para un ADR futuro si la evidencia lo justifica)

Compatibilidad: agregar campos opcionales es compatible hacia atrás;
en el resultado de `skopos query`, quitar o renombrar campos exige v2.

## CONTRATO: cli-skopos-reanalizar v1

> v1 (2026-08-20, ADR-007, ronda 3 F5): superficie del supersede
> explícito — salida JSON, exit codes y el no-op `cambiado: false`
> quedan prometidos aquí, no sólo viviendo en el código.

Entrada:
  `turn_id`: string [obligatorio] — argumento posicional de
  `skopos reanalizar <turn_id>`
  `--solo-redaccion`: flag [opcional] — re-aplicar los patrones de
  secretos vigentes (SPEC-002) a la versión actual, sin llamar a Ollama

Salida (JSON a stdout, exit 0):
  éxito: `{"turn_id", "cambiado": true, "version_anterior",
  "version_nueva"}` — se insertó una versión nueva (la vieja permanece
  como auditoría)
  no-op: `{"turn_id", "cambiado": false, "motivo"}` — p.ej.
  `--solo-redaccion` sin patrones nuevos que redactar; **no se inserta
  versión**

Errores (exit distinto de cero, mensaje a stderr, nada en stdout):
  turn_id sin ninguna versión guardada; rollout de origen ilegible o sin
  el turno (lección Y-5: nunca supersede a ciegas desde una referencia
  rota); `AnalisisFallido` del modelo (Ollama caído o respuesta inválida,
  ronda 3 F1); Mongo no disponible

Invariantes:
  - el vigilante jamás dispara supersede: sólo este comando o la API
    programática (`superseder_documento`)
  - modo completo recomputa las referencias de origen desde el `Turno`
    re-extraído (offsets, `ocurrido_en`, `proyecto`); `ruta_origen` no
    se toca (misma ruta por construcción)
  - `--solo-redaccion` redacta exactamente `tema`/`resumen`/`entidades`
    (lo que SPEC-002 redacta, ni más ni menos)
  - las claves de identidad (`turn_id`, `version`, `_id`,
    `ruta_origen`) nunca viajan en los cambios (validado en el borde)

Compatibilidad: agregar campos a la salida es compatible; quitar o
renombrar exige v2.
