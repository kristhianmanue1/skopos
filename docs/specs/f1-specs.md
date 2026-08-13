# F1 — Specs

## SPEC-001 [cubre: REQ-1]

Comportamiento: Skopos detecta el cierre de cada turno en un rollout de
Codex y extrae el texto real intercambiado en ese turno.

Entradas: ruta a un archivo `rollout-*.jsonl` (JSON Lines, UTF-8), leído
incrementalmente desde la última posición conocida (offset) — mismo
mecanismo de polling del prototipo `conversation_observer`.

Salidas: un objeto `Turno` con: `turn_id`, `session_id`, `texto_usuario`,
`texto_agente`, `timestamp_cierre`, `ruta_origen`, `offset_inicio`,
`offset_fin` (estos dos últimos permiten recuperar el fragmento exacto
después, sin releer todo el archivo).

Errores:
  - archivo no encontrado en un ciclo de poll: no es fatal, se reintenta
    en el siguiente ciclo;
  - línea JSON corrupta: se descarta esa línea, se sigue procesando el
    resto (igual que `_process_line` en el prototipo);
  - evento `task_complete` sin `turn_id`: se ignora.

Casos:
  - DADO un rollout con un `task_complete` nuevo y sus `response_item`
    previos CUANDO Skopos hace poll ENTONCES produce un `Turno` con
    `texto_usuario` y `texto_agente` no vacíos para ese `turn_id`.
  - DADO un `turn_id` ya visto (deduplicación acotada, igual que
    `SeenTurns` en el prototipo) CUANDO reaparece en el archivo ENTONCES
    no se produce un `Turno` duplicado.
  - DADO una línea JSON corrupta en medio del archivo CUANDO se hace poll
    ENTONCES se descarta esa línea y se sigue procesando el resto sin
    fallar.

Invariantes: un `turn_id` ya emitido nunca se vuelve a emitir (dentro del
límite de deduplicación acotada); el offset de lectura nunca retrocede
salvo que el archivo se trunque.

## SPEC-002 [cubre: REQ-2, REQ-5, REQ-10]

Comportamiento: dado un `Turno` (SPEC-001) y opcionalmente una
configuración de dominio (ADR-003), un modelo de IA local (ADR-001)
produce un análisis estructurado. Opcionalmente, se enriquece con
metadata de referencia sobre el CLI observado, consultando escrubery
(ADR-004) — ese paso nunca bloquea ni condiciona el resto del análisis.

Entradas: `Turno` (`texto_usuario`, `texto_agente`); configuración de
dominio opcional (`docs/contratos/f1-contratos.md`, contrato de config);
ficha de escrubery opcional (mismo archivo, contrato
`consulta-escrubery-cli`).

Salidas: `Analisis` con `tema`, `resumen`, `entidades` (opcional),
`referencia_origen` (`turn_id` + `ruta_origen` + offsets del `Turno`),
`metadata_cli` (opcional, presente sólo si escrubery respondió con
ficha).

Errores: si el modelo local no responde o responde vacío, el turno queda
en estado `fallido` (ver máquina de estados) — nunca se guarda un
`Analisis` vacío como si fuera válido.

Casos:
  - DADO un `Turno` con contenido reconocible sobre un tema CUANDO se
    analiza sin configuración de dominio ENTONCES el `Analisis` tiene
    `tema` y `resumen` no vacíos.
  - DADO el mismo `Turno` CUANDO se analiza con una configuración de
    dominio (ej. `arquitectura-software`) ENTONCES el resultado puede
    diferir en precisión o etiquetas respecto al análisis sin configurar,
    verificable comparando ambas salidas.
  - DADO que el modelo local no responde (timeout) CUANDO se intenta el
    análisis ENTONCES el turno pasa a `fallido`, nunca se infiere éxito.
  - DADO que escrubery no está disponible o no tiene ficha para el CLI
    observado CUANDO se analiza un `Turno` ENTONCES el `Analisis` se
    produce igual, sin `metadata_cli`, y el turno no pasa a `fallido` por
    esa causa.

Invariantes: ningún `Analisis` se guarda sin `referencia_origen`; un
análisis fallido nunca se confunde con uno vacío exitoso; un fallo de
escrubery nunca produce un `Analisis` fallido (ADR-004).

## SPEC-003 [cubre: REQ-3]

Comportamiento: el `Analisis` de un turno se persiste en MongoDB local,
con una referencia recuperable al fragmento completo original.

Entradas: `Analisis` (SPEC-002) + `Turno` (SPEC-001, para el fragmento
completo).

Salidas: un documento insertado en la colección Mongo (esquema en
`docs/contratos/f1-contratos.md`).

Errores: si Mongo no está disponible (conexión rechazada), la operación
falla explícitamente; el turno no se descarta silenciosamente (mecanismo
de reintento/cola se define en implementación, no en F1).

Casos:
  - DADO un `Analisis` válido con su `Turno` CUANDO se persiste ENTONCES
    existe un documento en Mongo consultable por `tema` que referencia el
    fragmento original completo.
  - DADO que Mongo no responde CUANDO se intenta persistir ENTONCES la
    operación falla explícitamente y queda registrada, no se descarta en
    silencio.

Invariantes: todo documento guardado tiene una `referencia_origen`
resoluble a un fragmento real, nunca huérfana.

## SPEC-004 [cubre: REQ-4]

Comportamiento: dado un tema, el CLI `skopos query <tema>` devuelve JSON
con todos los registros relevantes guardados, cada uno con acceso al
fragmento completo de origen.

Entradas: `tema` (string, argumento posicional de línea de comandos).

Salidas: JSON a stdout — lista de resultados, cada uno con `tema`,
`resumen`, `turn_id`, `ruta_origen`, `fragmento_completo`.

Errores:
  - tema sin resultados: JSON con lista vacía, exit code 0 (no es error);
  - Mongo no disponible: exit code distinto de cero, mensaje a stderr,
    nada en stdout.

Casos:
  - DADO documentos guardados sobre "arquitectura de software" CUANDO se
    ejecuta `skopos query "arquitectura de software"` ENTONCES la salida
    JSON incluye todos esos documentos con su fragmento completo
    accesible.
  - DADO un tema sin coincidencias CUANDO se consulta ENTONCES la salida
    es JSON con lista vacía y exit code 0.

Invariantes: la salida en stdout es siempre JSON válido cuando el exit
code es 0; los errores van a stderr, nunca mezclados con stdout.
