# Ronda adversarial — planes activos multiproyecto y prime-agent — 2026-10-13

Objetos: `docs/planes/activos/contrato-multiproyecto-v0.3-2026-10-13.md` (v1)
y `docs/planes/activos/adaptador-prime-agent-2026-10-13.md` (v1). Método:
revisor adversarial sin contexto de autoría (subagente) + verificación propia
con sondas de solo lectura. Veredicto: **fix-and-retry** para el plan
multiproyecto (H1 estructural), **corrige** para el de prime-agent. Aplicado
el mismo día: el plan multiproyecto fue reescrito como v2 y renombrado a
`contrato-multiproyecto-2026-10-13.md` (el contrato pasa a ser nuevo,
`source-consumer-access-v0.1`, no una enmienda v0.3 de CTIM); el de
prime-agent recibió las correcciones H7–H14 en el sitio.

| # | Severidad | Hallazgo | Veredicto | Disposición |
|---|---|---|---|---|
| H1 | BLOQUEANTE | El plan v1 mezclaba dos pilas: `source_not_allowed` vive en `ctim_source_access.py:263,426` (pasarela CTIM, un solo proyecto de custodia fijado en `pdf_document_store.py:85`), no en los archivos que T2 consumía; en la pila runtime, donde el eje proyecto es real (identidad `(project_id, source_id, revision)`), no hay loader que extender sino un control que crear; T3 era imposible en la pasarela (no sirve pilot-cedro/olmo) | Refuta la v1 | v2 reescrita: contrato nuevo para la superficie del almacén; pasarela CTIM intocable (redundante); Consumes corregidos |
| H2 | MEDIO | T3 suponía «instancia de laboratorio del piloto» viva: no existe mongod alguno; sólo el tarball de la serie | Corrige | T3 v2 rehidrata desde el tarball (SHA cotejado) en instancia dedicada que se crea y destruye |
| H3 | MEDIO | «Fail-closed» vs «compatibilidad v0.2» contradictorios: `load_access_policy` exige conjunto exacto de campos y un `allowed_projects` obligatorio rompería toda política v0.2 | Corrige | Contrato nuevo con esquema propio: no hay políticas previas que romper |
| H4 | MEDIO | `allowed_projects` redundante en la pasarela (lista de fuentes con SHA ya más fina) y novedoso en el almacén — la v1 no distinguía | Corrige | v2 declara ambas pilas y elige el almacén; pasarela fuera de alcance |
| H5 | BAJO | «104/108 éxitos respetando alcance» presentaba como control técnico lo que fue conducta de tarea bajo rúbrica | Afina | v2 lo declara conducta, no evidencia de frontera |
| H6 | BAJO | La invocación de ADR-010 se apoyaba en una instancia que no era lo contratado | Afina | v2 ancla el contrato a la instancia correcta (consumo del piloto y corridas Ágora) |
| H7 | MEDIO | La «ronda 2026-09-02» y su ~35% no tienen acta en `docs/rondas/` ni registro en AN-KLA: número decisivo inverificable | Corrige | El plan cita el issue #1 como origen, declara el hueco archivístico y T1 remide la colisión sobre las sesiones vivas |
| H8 | MEDIO | T1 consumía `docs/contratos/f1-contratos.md`, que no contiene `parser-contrato/v1` (vive en `docs/adr/ADR-010-contrato-parser-por-cli.md`, `VERSION_CONTRATO` en `parseo.py:29`) | Corrige | Consumes corregido al ADR |
| H9 | MEDIO | `toolResult` es un `message.role` con texto (612 en el corpus, segundo depósito por volumen) y el vocabulario de exclusión no lo nombraba | Corrige | Ficha lo declara frontera, no contenido; exclusión pens/toolCall/toolResult |
| H10 | BAJO | En 1 de 8 archivos el id de cabecera ≠ nombre de archivo: la fuente de `session_id` cambia todos los turn_id | Afina | Ficha fija cabecera como identidad; caso documentado |
| H11 | BAJO | «Salvo sesión activa» infalsable (un archivo termina en stopReason error con session_state active) | Afina | Criterio reescrito a falsifiable: turno abierto registrado con posición física, sin invocar actividad |
| H12 | BAJO | El filtro rlmDepth no tiene gancho en `FUENTES_POR_DEFECTO` y hoy no existen sesiones hijo en disco | Afina | El filtro vive en la ficha como incompatibilidad tipada; decisión T0 redimensionada |
| H13 | NIT | Atribuciones deslizadas a ADR-013 (es ADR-011; el 45/45 es de la evidencia codex fase-a) | Afina | Corregidas ambas citas |
| H14 | NIT | La verificación de publicación de T4 omitía la suite | Afina | `unittest discover` añadido a T4 |

## Afirmaciones que resistieron el ataque

- El plan respeta la decisión monousuario (hoja-de-ruta ~línea 251); «ni
  metadatos de existencia» es coherente con el filtrado vigente a nivel fuente.
- Prime: las 8 sesiones existen, directorio plano, patrón `*.jsonl` limpio; el
  histograma (~79-80% no conversacional, `child_usage_attributed`) es
  reproducible; el cursor ADR-011 es genérico y sirve sin adaptación; el
  namespace `prime:` está libre y almacenamiento no valida formato; el cierre
  user→user es derivable sin ambigüedad (0 usuarios consecutivos medidos); sin
  credenciales máquina (`sk-`/`Bearer`/`api_key` → 0 coincidencias) y el
  tratamiento de sensible queda igual que codex/claude hoy.

## Sondas propias

`grep source_not_allowed src/` (confirma ubicación), `runtime_store.py:48`
(identidad con project_id), nombres exactos de `ADR-010-contrato-parser-por-cli.md`,
`import_corpus.py`/`backend.py`, `pdf_document_store.py:85` (proyecto fijado)
y `parseo.py:29` (`VERSION_CONTRATO`). Nada mutado.
