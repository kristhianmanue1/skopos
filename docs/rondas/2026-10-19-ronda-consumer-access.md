# Ronda adversarial — contrato source-consumer-access v0.1 — 2026-10-19

T4 del [plan multiproyecto](../planes/activos/contrato-multiproyecto-2026-10-13.md).
Revisor independiente sin contexto de autoría, sobre contrato, código,
pruebas y evidencia T3. Once hallazgos, **ninguno bloqueante**; ninguno
filtraba contenido ni metadatos de existencia.

| ID | Severidad | Hallazgo | Disposición |
|---|---|---|---|
| H1 | MEDIO | URI multi-host (`mongodb://127.0.0.1:x,10.0.0.5:y`) o con `replicaSet=` pasaba el `startswith` y el descubrimiento de topología podía contactar hosts fuera de loopback | **Corregido**: `URI_RE` fullmatch de un solo host loopback, sin coma ni `replicaSet=` (`consumer_access.py`); contrato reescrito; cuatro casos nuevos de prueba |
| H2 | BAJO | Líneas CLI de la tabla T0 desfasadas +4 tras la integración | **Corregido**: tabla actualizada a 33/37/39/41 |
| H3 | BAJO | Límite de 64 KiB rechazaba políticas sin estar declarado en el contrato | **Corregido**: declarado en la lista de violaciones |
| H4 | BAJO | Huecos de prueba: ids subcadena/caso, camino feliz de CLI bajo política, URI multi-host | **Corregido**: `test_unlisted_project_rejects_uniformly…` ahora cubre subcadenas/prefijos/mayúsculas/no-texto; `test_cli_policy_serves_over_real_store` sirve por la CLI sobre Mongo real bajo el runner (la conexión material va al host redirigido; el argumento recibido acredita que la URI salió de la política); casos multi-host en el loader |
| H5 | NIT | Código más estricto que el contrato en cadenas de sólo espacios | **Corregido**: el contrato ahora promete «contenido distinto de espacios» |
| H6 | NIT | Banderas vacías (`--database ''`, `--uri ''`) eludían los errores de exclusividad | **Corregido**: semántica `is None` en `source_cli.py` |
| H7 | NIT | `project_id` no hashable (lista/dict) reventaba con `TypeError` vía API Python | **Corregido**: comprobación de tipo antes del conjunto; no-texto también es «no listado»; casos en prueba |
| H8 | NIT | Precedencia `operation_not_allowed` sobre `policy_unavailable` sin especificar | **Corregido**: el contrato declara que `import` bajo política se rechaza antes de conectar y antes de cargar la política |
| H9 | NIT | Ambigüedad sobre los `.held` en la evidencia T3 | **Corregido con verificación**: la conjetura del revisor («son los tres decoys») resultó falsa al contrastarla con el manifiesto: los retenidos son `s009-r1` de cada proyecto, dos de ellos dentro de las 42 importadas. La evidencia ahora lo dice así |
| H10 | NIT | Loader sin disciplina `O_NOFOLLOW/O_NONBLOCK` de `read_source` | **Tolerable**: perfil local monousuario; sin cambio |
| H11 | NIT | Claves duplicadas en el JSON de política pasaban (última-gana) | **Corregido**: `object_pairs_hook` que rechaza `duplicate_json_key` (precedente ADR-021), con prueba |

Verificación tras correcciones: suite aislada **581 pruebas OK sin
omisiones** (Mongo temporal 37035, Ollama `qwen3:8b`), gates `check_sizes`
(839 archivos) y `check_plans` (5 planes) en verde.

Nota de método: H9 se corrigió contrastando la conjetura del revisor contra
el manifiesto real antes de escribirla — la ronda adversarial propone, el
código y los datos vivos deciden.
