# ADR-005: el vigilante deduplica contra MongoDB, no contra un cursor local

Estado: aceptado

Contexto: el vigilante en vivo (REQ-1, REQ-6) tiene que recorrer
periódicamente `~/.codex/sessions/` sin volver a analizar (llamada cara a
Ollama) ni volver a guardar un turno que ya se procesó en un ciclo
anterior. El prototipo original (`conversation_observer`) resolvía esto
con un cursor de offsets y un `set` de `turn_id` vistos, en memoria.

Decisión: antes de analizar un turno, el vigilante consulta si su
`turn_id` ya existe en la colección de Mongo (`skopos.almacenamiento`,
nueva función `existe_turn_id`); si existe, el turno pasa a estado
`omitido` (`docs/f1-maquina-estados.md`) sin llamar a Ollama ni a
`guardar_analisis`.

Alternativas descartadas:
  - Cursor de offsets + `set` en memoria (como el prototipo): se pierde
    en cada reinicio del proceso, así que tras cualquier caída se
    reprocesarían todos los turnos ya guardados — exactamente lo que se
    quiere evitar. Persistirlo a disco duplicaría un mecanismo de verdad
    que Mongo ya resuelve.
  - Cursor persistido en un archivo propio (JSON/SQLite local): funciona,
    pero introduce una segunda fuente de verdad que puede desincronizarse
    de Mongo (ej. si se borra un documento a mano). Mongo ya es la fuente
    de verdad de qué se guardó; consultarla es más simple y no puede
    desincronizarse de sí misma.

Consecuencias: cada ciclo del vigilante vuelve a leer y parsear los
archivos `.jsonl` completos (SPEC-001 no hace lectura incremental
todavía), pero sólo paga el costo caro (Ollama, Mongo) para turnos
nuevos. Si el volumen de rollouts crece lo suficiente para que releer
archivos completos sea un problema medido, ese es un ADR nuevo sobre
lectura incremental — no se anticipa aquí sin evidencia de que haga falta.
