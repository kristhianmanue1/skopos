# P-003: colector multi-CLI que emite conversation-event/v0 — primer consumidor del contrato de escrubery

Estado: **propuesta** — pendiente de decisión 🔒 del dueño. No reabre
P-002 ni contradice ADR-001..010; **es la implementación autorizada por
ADR-010** (la implementación multi-CLI "pendiente de autorización y
plan de fase propios": esta propuesta es ese plan).
Fecha: 2026-08-22.
Origen: sesión de trabajo escrubery (cierre H7-T4 + definición de la
ruta del supervisor multi-proyecto). Redactada por el agente de escrubery
a petición del dueño; conservando la gobernanza de P-002 (actos 🔒 una
por operación).

## 1. Qué propone

Construir el **colector multi-CLI** de skopos: la familia de parsers
(ADR-010/SPEC-006) extendida con una **salida de eventos normalizada**
al contrato `conversation-event/v0` que escrubery diseñó y congeló en
su ciclo H6 (2026-08-21: schema ajv estricto, 4 probes read-only sobre
historiales reales de los 5 CLIs, decisión de adaptadores; ver
`insumo-escrubery-2026-08-22.md` en este directorio).

**Por qué ahora:** (a) las precondiciones de ADR-010 están cerradas y
el propio ADR exige "plan de fase propio" para implementar — esto lo
surtre; (b) el dueño definió hoy la ruta del supervisor multi-proyecto
(docker + agentes preconfigurados + inyección de contexto + recolección
de resultados): el supervisor **necesita observar conversaciones**,
y ese es exactamente el trabajo de skopos; (c) escrubery cerró hoy su
verificación activa (H7-T4) — las fichas de assurance certifican qué
paredes son reales, y este colector es la contraparte de observación.

## 2. Frontera de responsabilidades (lo que NO es esta propuesta)

- **escrubery** es dueño del **contrato** (`conversation-event/v0`:
  schema, semántica, versionado) y de las fichas de referencia
  (assurance, mapa de superficies). No escribirá parsers ni colectores.
  Frontera idéntica a la del ADR-010 §9: referencia con procedencia,
  nunca autoridad.
- **skopos** es dueño de la **implementación**: detectar formato →
  seleccionar parser → producir turnos normalizados (SPEC-006) →
  **y opcionalmente emitir eventos conversation-event/v0** como formato
  de exportación/intercambio.
- La emisión de eventos es un **adaptador de salida** del pipeline de
  skopos, no un cambio del almacén ni de los turnos normalizados: el
  evento se deriva del turno ya normalizado. Si el dueño prefiere no
  emitir eventos aún, la propuesta se reduce a §4 sin la fase C.

## 3. Por qué conviene a skopos (no solo al supervisor)

1. **El contrato ya está probado contra sus formatos**: los 4 probes de
   escrubery (H6) validaron que los almacenes de los 5 CLIs exponen lo
   que el schema necesita — el riesgo de diseño ya está pagado.
2. **Portabilidad**: con eventos normalizados, `skopos query`/`watch`
   ganan una superficie de exportación estándar (cualquier consumidor
   futuro del supervisor, dashboards, análisis cross-CLI) sin exponer
   el almacén interno.
3. **No añade dependencias nuevas**: el schema es JSON + ajv
   (equivalente Python: jsonschema); regla de P-002 intacta.

## 4. Fases propuestas (cada una cierra con evidencia)

| Fase | Entrega | Gate |
|---|---|---|
| A | Refactor del parser codex incrustado → adaptador tras el contrato parser-contrato/v1 (ya aceptado; extracción desde `captura.py`, constantes declaradas, registro §8 del ADR) | Tests actuales en verde; detección por marcas idéntica (616/616, 11/11 negativos) |
| B | Adaptadores claude-code + opencode (los 3 CLIs con historiales locales ya mapeados por los probes de escrubery; kimi/qwen después) | Muestras positivas + controles negativos fechados en `docs/evidencia/`, como el predicado codex |
| C | Emisor `conversation-event/v0`: turnos normalizados → eventos validados contra el schema ajv de escrubery (verificador oficial: escrubery expone `npm run` o spec Python equivalente — mini-ticket en escrubery si el dueño lo pide) | Corpus piloto re-ingestado → eventos 100% válidos contra schema; redondeo de pérdida declarado (qué campo no llena cada CLI) |
| D | `skopos export --format conversation-event` (CLI) | Un comando real ejecutado end-to-end sobre el corpus piloto |

Orden A→B→C→D sin paralelismo; B puede iterar CLI por CLI.
Presupuesto LLM: 0 (parseo local de historiales existentes).

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Formatos que cambian bajo los pies (lección H6 de escrubery) | `version_formato` por marcas (ADR-010); nada se parsea "por parecido" |
| Eventos con campos que un CLI no llena | Schema ajv fail-closed + tabla de cobertura por CLI en la evidencia de fase C |
| Acoplamiento a escrubery | El contrato es un artefacto versionado congelado (v0), citado con hash; skopos puede congelar su copia local (`docs/contratos/`) — dependencia blanda, igual que REQ-10 |
| Duplicar trabajo si el supervisor nunca se construye | Fases A+B valen por sí solas (multi-CLI puro, ya aceptado); C+D son aditivas y pequeñas |

## 6. Decisión 🔒 que se pide al dueño

1. ¿Se aprueba P-003 como plan de fase de la implementación ADR-010?
2. ¿Con o sin la fase C/D (emisión de eventos) en esta primera pasada?
3. Confirmación del orden CLI de fase B (propuesta: claude-code →
   opencode → kimi-code → qwen-code, por orden de madurez del mapa de
   escrubery).

## Referencias

- ADR-010 + SPEC-006: `docs/adr/ADR-010-contrato-parser-por-cli.md`,
  `docs/specs/f1-specs.md` (aceptados 🔒 2026-08-21).
- Contrato conversation-event/v0: repo escrubery, `datos/schemas/conversation-event-v0.schema.json`
  + decisión de adaptadores `docs/investigacion/probes/DECISION_ADAPTADORES.md`
  (insumo notificado: `docs/evidencia/insumo-escrubery-2026-08-22.md`).
- Verificación activa de assurance (contexto del supervisor):
  `docs/evidencia/insumo-escrubery-verificacion-2026-08-22.md` +
  repo escrubery `docs/investigacion/hra/reporte-verificacion-2026-08-22.md`.
- Ruta del supervisor (origen de la necesidad): sesión del dueño
  2026-08-22 (docker + agentes preconfigurados + inyección AN-KLA +
  recolección de resultados; escrubery H8 demostró la inyección viva).
