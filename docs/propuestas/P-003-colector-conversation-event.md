# P-003: colector multi-CLI que emite conversation-event/v0 — primer consumidor del contrato de escrubery

Estado: **aceptada con alcance recortado** — decisión 🔒 del dueño,
**2026-08-28**: se aprueban las **fases A y B** (multi-CLI puro, la
implementación que ADR-010 dejó "pendiente de autorización y plan
propios"); **las fases C y D quedan aplazadas** sin fecha (opción (c) de
§6.4). Ver "Firma de decisión" al final. No reabre
P-002 ni contradice ADR-001..010; **es la implementación autorizada por
ADR-010** (la implementación multi-CLI "pendiente de autorización y
plan de fase propios": esta propuesta es ese plan).
Fecha: 2026-08-22. **Revisada por la ronda 22 (2026-08-28,
`docs/rondas/2026-08-28-ronda-22-p003.md`): correcciones R2–R5
incorporadas en §3.3, §4 y §6; R1 (ALTO) resuelto por la vía del
aplazamiento — ver §6.4 y la firma.**
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
3. **Fases A y B no añaden dependencias**: son parseo de JSONL con la
   biblioteca estándar, igual que `captura.py` hoy. **La fase C sí exige
   una decisión de dependencia** (corrección R2, ronda 22): validar el
   schema en Python pide `jsonschema` —presente en el entorno (4.25.1)
   pero **no declarado** en `pyproject.toml`, que hoy sólo lista
   `pymongo`—, y declararla es una operación de autoridad separada que
   requiere autorización explícita del dueño (AGENTS.md). Alternativa
   sin dependencia: validar el subconjunto del schema a mano en la fase
   C y declarar en la evidencia qué cláusulas no se verifican.

## 4. Fases propuestas (cada una cierra con evidencia)

| Fase | Entrega | Gate |
|---|---|---|
| A | Refactor del parser codex incrustado → adaptador tras el contrato parser-contrato/v1 (ya aceptado; extracción desde `captura.py`, constantes declaradas, registro §8 del ADR) | Tests actuales en verde; detección por marcas idéntica (616/616, 11/11 negativos) |
| B | Adaptadores de los CLIs restantes del mapa de escrubery. El mapa cubre **5**: codex-cli (ya cubierto por la fase A), claude-code, opencode, cline y kimi-code (35 celdas = 5 CLIs × 7 tipos de evento; corrección R3, ronda 22 — la redacción previa decía «3 CLIs» y proponía `qwen-code`, que sólo aparece en el `listar` de candidatos del ensayo 2026-08-20 y **no tiene adaptador mapeado**) | Muestras positivas + controles negativos fechados en `docs/evidencia/`, como el predicado codex |
| C | Emisor `conversation-event/v0`: turnos normalizados → eventos validados contra una **copia local congelada** del schema en `docs/contratos/` (citada por hash), para que el gate sea ejecutable sin `npm` ni el canal de escrubery. **Precondición: R1 resuelto** (herencia de P4a+P5+P3 de ADR-009, §6.4) y decisión de dependencia tomada (§3.3) | Corpus piloto re-ingestado → eventos 100% válidos contra schema; tabla de cobertura por CLI que **nombra los huecos ya conocidos** —`turno_fallido` transversal, `sesion_cerrada` sólo en cline (corrección R5, ronda 22)— además de los que aparezcan |
| D | `skopos export --format conversation-event` (CLI) **más su contrato `cli-skopos-export v1`** en `docs/contratos/f1-contratos.md` — es la tercera superficie CLI y ADR-002 gobierna su forma JSON-a-stdout, como `cli-skopos-query v1` y `cli-skopos-reanalizar v1` (corrección R4, ronda 22) | Contrato escrito y un comando real ejecutado end-to-end sobre el corpus piloto, verificado contra ese contrato |

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
   opencode → cline → kimi-code, por madurez del mapa de escrubery;
   `qwen-code` queda fuera por no tener adaptador mapeado — corrección
   R3, ronda 22).
4. **Decisión de dependencia de la fase C** (§3.3): autorizar
   `jsonschema` en `pyproject.toml`, o validar a mano sin dependencia.

### 6.4 · R1 — cómo hereda la exportación las mitigaciones de ADR-009

> **Resuelto por la decisión 🔒 del 2026-08-28: opción (c)** — al
> aplazar C/D no existe superficie de exportación, así que no hay canal
> de eco que mitigar y **ADR-009 no se toca**. La opción (a) queda
> **preacordada** como la forma que tomará la exportación si algún día
> se desbloquea, para no reabrir el diseño desde cero. El texto de abajo
> se conserva como registro del hallazgo y de las alternativas
> evaluadas.

**Hallazgo ALTO de la ronda 22.** ADR-009
quedó cerrado 🔒 (2026-08-20) con **P4a + P5 + P3**: toda salida del CLI
que sirva fragmentos lleva sello de hash, límite de volumen (`--max`,
default 20) y la declaración *dato-nunca-instrucción* en el contrato. Un
emisor de `conversation-event/v0` es exactamente esa superficie, y la
redacción original de P-003 no la contemplaba: tal como estaba, las
fases C/D abrirían un canal de eco fuera de las mitigaciones que el
Hito 16 decidió y el Hito 17 midió. Tres salidas, ninguna elegida
todavía —**requiere decisión 🔒 del dueño porque toca el perímetro de un
ADR aceptado**:

- **(a) Eventos sin fragmento (recomendada por la ronda 22)** — el
  evento lleva metadata, `fragmento_sha256`, offsets y ruta, nunca el
  texto. Hereda P4a por construcción, P5 deja de aplicar (no hay volumen
  que acotar) y P3 es trivial. Quien quiera el texto usa `skopos query`,
  que ya tiene sus límites puestos. No modifica ADR-009.
- **(b) Eventos con fragmento bajo las mismas mitigaciones** — exige
  `--max` y la marca *dato-nunca-instrucción* dentro de
  `cli-skopos-export v1`. Más útil para el supervisor, más superficie de
  eco que vigilar. No modifica ADR-009, lo extiende a una superficie
  nueva.
- **(c) Aplazar C/D** — aprobar sólo A+B (multi-CLI puro, ya autorizado
  por ADR-010 y que vale por sí solo, §5). R1 desaparece hasta que exista
  un consumidor real del contrato.

Entre (a) y (c) la diferencia es cuánto se adelanta para el supervisor:
(a) si el supervisor es ruta firme, (c) si todavía es exploración.
Cualquier opción distinta de (a) y (c) que exporte fragmentos exige
sustituir o extender ADR-009 con un ADR propio, no una cláusula de esta
propuesta.

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

## Firma de decisión

- Dueño: decisión 🔒 comunicada en canal del agente · Fecha:
  **2026-08-28** · Tras la ronda 22
  (`docs/rondas/2026-08-28-ronda-22-p003.md`) y la incorporación de
  R2–R5.
- **Alcance aprobado: fases A y B.** A (extracción del parser codex a
  adaptador tras `parser-contrato/v1`) y B (adaptadores de los CLIs
  restantes del mapa: claude-code, opencode, cline, kimi-code), cada una
  con el gate de evidencia de §4.
- **Fases C y D aplazadas** sin fecha (opción (c) de §6.4). Motivo
  registrado: construyen un formato de exportación **sin consumidor
  existente** — el supervisor multi-proyecto es ruta definida, no sistema
  que pueda recibir eventos hoy; AGENTS.md prohíbe placeholders y
  dependencias especulativas, y §5 de esta propuesta ya concede que
  A+B valen por sí solas y que C+D son aditivas.
- **Consecuencias del recorte:** (i) R1 no se activa y ADR-009 queda
  intacto; (ii) la decisión de dependencia de §3.3 no se toma —
  `pyproject.toml` sigue con `pymongo` como única dependencia; (iii) el
  contrato `conversation-event/v0` (v0, de otro repo) **no se congela**
  en `docs/contratos/` todavía — no se adopta una versión que puede
  moverse sin tener quién la consuma.
- **Secuencia acordada:** cerrar **A primero** (refactor puro, gate ya
  medido: 616/616 positivos, 11/11 negativos); antes de arrancar **B**,
  revisar el estado del **Hito 15** (ADR de lectura incremental, fase 3b
  del plan de P-002), porque B multiplica por cinco las superficies que
  el vigilante lee y ese comportamiento aún no está decidido.
- **Reactivación de C/D:** exige propuesta o pasada propia cuando exista
  un consumidor real; la forma ya está preacordada (opción (a): eventos
  sin fragmento, con `fragmento_sha256`, offsets y ruta).
