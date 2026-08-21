# Evidencia · predicado de identidad Codex para ADR-010 (corrección 2 de Pinax)

Snapshot: **2026-08-20**, corpus `~/.codex/sessions/` completo + formatos
de sesión reales de otros CLIs de esta máquina (regla X-2). Método:
escaneo del primer evento `session_meta` de cada archivo; controles
negativos con el predicado cuádruple y con el predicado de identidad.

## Muestras positivas (corpus Codex, 616 archivos)

- **616/616** tienen `session_meta` como primer evento de metadatos
  (0 archivos sin él).
- `payload.originator` observado: `codex-tui` (51), `codex_exec` (63),
  `Codex Desktop` (502) — **todos** cumplen `^codex` case-insensitive.
- `payload.cli_version` presente (ej. `0.146.0-alpha.3.1`, `0.147.0`):
  **la versión del CLI está disponible en el propio archivo** —
  alimenta la referencia de obsolescencia de ADR-010 §9 sin consultar
  escrubery.
- Predicado cuádruple (`session_meta` + `turn_context` + `event_msg` +
  `response_item` en las primeras 200 líneas): 40/40 en muestra
  aleatoria (semilla 42) — válido como **marca de estructura**, no de
  identidad (un archivo vivo recién creado aún no tiene los cuatro).

## Controles negativos (otros formatos reales, 11 archivos, 2 formatos ajenos)

- `~/.claude/projects/**/*.jsonl` (10 archivos muestreados, Claude
  Code): sin `session_meta` — **no-match**. El claim operativo no
  depende del primer tipo de evento de la muestra (que fue
  `queue-operation`; la población completa de 253 archivos varió:
  queue-operation 119, user 81, mode 51…): lo verificado con código
  sobre la **población completa** es que **0/253 archivos Claude tienen
  `session_meta` en las primeras 10 líneas** (verificación de la ronda
  12, H-6).
- `~/.codex/history.jsonl` (artefacto propio de Codex que NO es
  rollout): sin `session_meta` — **no-match**: el predicado distingue
  rollouts de otros JSONL del mismo producto.

*(Corregido en ronda 11b: este documento decía "3 formatos distintos";
los formatos ajenos representados son **2** — sesiones de Claude Code y
`history.jsonl` de Codex. Nota de drift intradía, ronda 12 H-5: los
conteos de la reproducción 11c (world_state 3,540 / compacted 1,016 /
inter_agent 1,256; 84/616) son de una corrida del 2026-08-20; un
recount posterior el mismo día dio 3,541/1,017 (+1/+1, corpus vivo que
creció entre corridas) — los números se citan como snapshot de su
corrida, no como constantes.)*

## Predicado adoptado (ADR-010 §1, ficha parser-codex v1; frontera endurecida en ronda 11b)

**Identidad**: primer evento `type == "session_meta"` dentro de las
primeras 10 líneas, con `payload.originator` que case
`(?i)^codex([ _-]|$)` — frontera de palabra completa: `codexfoo` NO
casa; fin de cadena o separador (`_`, `-`, espacio) sí. Enum observado
en el corpus: `codex-tui`, `codex_exec`, `Codex Desktop` (616/616).
Ausencia de `session_meta` o de match ⇒ `formato_desconocido` para este
adaptador. Exclusividad no afirmada como verdad absoluta: afirmada
**con evidencia** (616 positivos, 11 controles negativos de 2 formatos
ajenos). *(Corregido en ronda 13, F-2: este documento decía que una
coincidencia ajena produciría `deteccion_ambigua` sin calificar — lo
correcto, según ADR-010 §1 vigente: ambigüedad sólo si el otro
producto está registrado y su predicado también casa; un formato no
registrado que imite la identidad es límite residual de la detección
heurística. Toda ficha declara su predicado con muestras y controles
fechados.)*

**Estructura** (versión declarada v1): eventos `type ∈ {"turn_context",
"response_item", "event_msg"}` con cierre por `event_msg.payload.type ==
"task_complete"`. **Un archivo vivo puede no contenerlas todavía**: eso
NO es `version_no_soportada` (corrección 1 de Pinax) — ver regla de
decisión en ADR-010 §1.
