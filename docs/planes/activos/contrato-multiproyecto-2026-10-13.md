# Plan — contrato multiproyecto para consumidores — 2026-10-13 (v2)

Estado: **ACTIVO, sin ejecutar**. Autorizado por el Operador el 2026-10-13.
La v1 fue refutada en su estructura por la
[ronda adversarial](../../rondas/2026-10-13-ronda-planes-activos.md) (hallazgo
H1): mezclaba dos pilas de servicio y consumía archivos que no contienen lo
que prometía extender. Esta v2 corrige el mapa y nombra las cosas por lo que
son: en la pila donde el eje proyecto es real **no hay loader que extender —
hay un control que crear**.

## Contexto verificado (corregido por ronda, 2026-10-13)

Skopos sirve contenido por **dos pilas distintas**, y la crítica
«no es multiproyecto» cae en una sola de ellas:

1. **Pasarela CTIM** (`src/skopos/ctim_source_access.py`, error
   `source_not_allowed` en las líneas 263 y 426): sirve siete originales bajo
   **un único** proyecto de custodia fijado en `src/skopos/pdf_document_store.py`
   (`expertogobernanza`). Ahí una lista de proyectos sería **redundante**: la
   lista exacta de fuentes con SHA ya es más fina que cualquier eje proyecto.
   El contrato `ctim-source-access-v0.2` no se toca.
2. **Almacén de fuentes runtime/source** (`src/skopos/runtime_store.py`,
   identidad `(project_id, source_id, source_revision)` — el mismo `source_id`
   puede existir en proyectos distintos con contenido distinto): aquí el eje
   proyecto es real y **no existe control de acceso por consumidor** — el
   piloto de consulta filtró por `project_id` a nivel de consulta
   (`experiments/agent-query-pilot/backend.py`), no por lista de permitidos.

La conducta del piloto (104/108 éxitos respetando alcance) fue **instrucción
de tarea bajo rúbrica**, no aplicación de una frontera; no cuenta como
evidencia de control. La decisión monousuario del 2026-10-06 queda intacta:
esto es alcance bajo la cuenta vigente, no multiusuario.

## Objetivo y no-objetivos

**Objetivo**: contrato nuevo de acceso por consumidor para la superficie de
servicio del almacén de fuentes, con lista exacta `allowed_projects` y error
tipado `project_not_allowed` (fail-closed: proyecto no listado no recibe
contenido ni metadatos de existencia — coherente con el filtrado ya vigente a
nivel fuente en la pasarela CTIM).

**No-objetivos**: modificar la pasarela CTIM ni su contrato v0.2 (redundante);
autenticación entre usuarios (decisión monousuario vigente); instancias por
proyecto; renombrado de campos almacenados.

```text
TAREA T0 — preflight: mapear la superficie real de servicio
Consumes: este plan; AGENTS.md; src/skopos/runtime_store.py; src/skopos/source_cli.py; src/skopos/ctim_source_access.py.
Produce: manifiesto con los puntos exactos de entrada/salida por donde un consumidor obtiene contenido del almacén (CLI y puente MCP), y confirmación del Operador del alcance.
Steps:
- [ ] Enumerar cada operación que sirve contenido (search/fetch/receipt y equivalentes) con archivo:línea, y decidir el punto único (o los puntos) donde el control debe vivir.
  Verificación: cada operación citada existe en código; sin operaciones huérfanas ni rutas que esquiven el control.
- [ ] Confirmar con el Operador: sólo eje proyecto bajo la cuenta vigente, sin multiusuario.
  Verificación: respuesta explícita registrada; si no llega, no iniciar T1.

TAREA T1 — contrato documental nuevo
Consumes: T0; docs/contratos/ctim-source-access-v0.2-local.md; docs/contratos/source-store-v3.md.
Produce: se crea docs/contratos/source-consumer-access-v0.1-local.md: esquema de política con allowed_projects (lista exacta, obligatoria), error tipado project_not_allowed, y límites declarados.
Steps:
- [ ] Redactar el contrato desde la instancia viva: las corridas de consumo reales (piloto de consulta con tres proyectos; corridas Ágora p18/p21) son lo que generaliza, conforme a la regla ADR-010.
  Verificación: cada afirmación del contrato anclada a esa instancia; cero promesas de aislamiento multiusuario; compatibilidad de esquema resuelta por ser contrato nuevo (sin políticas previas que romper).

TAREA T2 — control nuevo con pruebas (creación, no extensión)
Consumes: T1; src/skopos/source_cli.py; src/skopos/runtime_store.py.
Produce: se crea src/skopos/consumer_access.py (loader fail-closed de la política y rechazo project_not_allowed en la superficie que T0 mapeó); suite en verde con casos nuevos.
Steps:
- [ ] Implementar el loader: política con conjunto exacto de campos (patrón de ctim_source_access.py), allowed_projects obligatorio, política ausente o inválida = nada se sirve.
  Verificación: pruebas nuevas: proyecto listado sirve; no listado rechaza project_not_allowed sin filtrar contenido ni existencia; política malformada se rechaza en carga, no en uso.
- [ ] Correr la suite completa y los gates.
  Verificación: python3 -m unittest discover -s tests en verde; python3 scripts/check_sizes.py y python3 scripts/check_plans.py en verde.

TAREA T3 — ensayo de dos proyectos con corpus rehidratado
Consumes: T2; experiments/agent-query-pilot/artifacts/series-v0.4.tar.gz; experiments/agent-query-pilot/import_corpus.py.
Produce: evidencia con recibo: proyecto permitido sirve, proyecto ajeno rechazado, sobre corpus pilot-cedro/pilot-olmo rehidratado en instancia de laboratorio dedicada.
Steps:
- [ ] Rehidratar el corpus del tarball con verificación de manifiesto (comprobar SHA del tarball contra su evidencia) e importar cedro+olmo a un Mongo de laboratorio dedicado; no hay instancia viva del piloto (verificado en ronda) — la del drill se crea y se destruye.
  Verificación: conteos por proyecto coinciden con el manifiesto interno del tarball (21+21 fuentes); instancia en puerto de laboratorio, nunca el operativo.
- [ ] Ejecutar el ensayo espejo: consumidor con allowed_projects=[pilot-cedro] consulta cedro (sirve) y olmo (project_not_allowed).
  Verificación: recibos de ambas llamadas archivados; ninguna fuga de contenido ni de existencia del proyecto ajeno; instancia destruida al terminar.

TAREA T4 — ronda adversarial propia y publicación
Consumes: T3; docs/rondas/.
Produce: ronda adversarial del contrato implementado; correcciones; push reportado.
Steps:
- [ ] Ronda adversarial con revisor sin contexto de autoría sobre contrato+código.
  Verificación: tabla de hallazgos con veredicto; correcciones aplicadas antes de publicar.
- [ ] Publicar con suite y gates en verde.
  Verificación: python3 -m unittest discover -s tests en verde; gates en verde; git ls-remote origin refs/heads/main == main local; árbol limpio.
```

## Riesgos y abortos

- Si T0 encuentra más de una superficie de servicio sin punto común de
  control, abortar y proponer consolidación de la superficie antes del
  contrato (no parches múltiples).
- Si T3 filtra contenido o existencia del proyecto ajeno, BLOCKER: no publicar
  y registrar el fallo.
- Si el tarball del piloto no coincide con su SHA registrado, rehidratar nada
  y reportar la discrepancia.
