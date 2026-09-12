# Hoja de ruta

> Hitos reales, con commit de cierre. No es un plan a futuro especulativo:
> los primeros siete ya pasaron y quedan como registro; de ahí en
> adelante son próximos pasos, no promesas de fecha.

| Hito | Qué entrega | Estado | Commit |
|---|---|---|---|
| 0 | F0 — análisis, requisitos, evidencia | Cerrado | `7f032b7` |
| 1 | F1 — specs, ADR, contratos, máquina de estados | Cerrado | `40812c5` |
| 1.1 | REQ-10 — escrubery como fuente opcional | Cerrado | `797aaf1` |
| 2 | F2 — cascarón (captura, sin dependencias nuevas) | Cerrado | `8c14455` |
| 3 | Análisis (Ollama) + almacenamiento (Mongo) | Cerrado | `cdd5367` |
| 4 | Orquestador + `skopos query` (pipeline completo) | Cerrado | `647412d` |
| 5 | Vigilante en vivo (`skopos watch`) | Cerrado | `896959a` |
| 6 | Metadata vital: `cli`, `modelo_analisis`, `ocurrido_en` | Cerrado | `863e2ee` |
| 6.1 | Ayuda de comandos (`--help`) + próximos pasos por escrito | Cerrado | `7fa01f2` |
| 7 | Ronda adversarial de arquitectura + 7 correcciones | Cerrado | `ab9f51b` |
| 8 | Política de arranque del vigilante (backfill opt-in vs "desde ahora") — hoy C-10(a) del ciclo P-002 | Cerrado (ADR-008, 🔒 2026-08-20) | `4f7900a` |
| 9 | Herramienta de lectura por sesión/fecha/rango (`skopos read`) — diferido explícito (2026-08-20, P-002 §2); lo prepara el índice `ocurrido_en` de C-9 | Diferido | — |
| 10 | Ensayo del canal escrubery contra el repo real (P-002 §3.6) | Cerrado | `8d68ed1` |
| 11 | Búsqueda semántica (embeddings) — condicional a que `$text` (ADR-006) resulte insuficiente en uso real | Futuro, no decidido | — |
| 12 | Soporte multi-CLI (más allá de Codex) — confirmado por el dueño el 2026-08-20; precondiciones C-9..C-5 cerradas; **ADR-010 + SPEC-006 aceptados 🔒 2026-08-21** (rondas 10–18; 17 = gate final) | Cerrado documentalmente; implementación **autorizada 🔒 2026-08-28** con alcance A+B vía P-003 (hito 18) | `fc37a90` |
| 13 | C-9: eje de proyecto + eje CLI real + índices (P-002 §3.1) | Cerrado | `811e58c` |
| 14 | C-8: ADR superficie de mutación o retención (P-002 §3.2) — ADR-007, alternativa B (supersede con versiones), decisión 🔒 2026-08-20 | Cerrado | `f0f6134` |
| 15 | C-10: cursor de ingesta — decisión 8 + ADR de lectura incremental (P-002 §3.3) 🔒 | **Cerrado** — gate con remedición fechada (`remedicion-ciclo-c10-2026-08-28.md`), **ADR-011 aceptado 🔒 2026-08-28** e implementado tras la ronda 23 (4 hallazgos corregidos): ciclo de 13.9 s a **3.7–4.9 s** con carga normal, dentro del intervalo de 5 s; 159 tests (`cursor-incremental-2026-08-28.md`) | `7761607` |
| 16 | C-6: decisión sobre `fragmento_completo` — ADR-009, P4a+P5+P3, decisión 🔒 2026-08-20 | Cerrado | `21ce77a` |
| 17 | C-5: detector de eco sobre corpus piloto (P-002 §3.5) — 6/6 sellados, 0 hits, control positivo 3/3 | Cerrado | `27c1332` |
| 18 | Implementación multi-CLI, fases A+B de `docs/propuestas/P-003-colector-conversation-event.md` (aceptada 🔒 2026-08-28 tras la ronda 22; fases C/D de exportación **aplazadas** por no tener consumidor). A: parser codex → adaptador tras `parser-contrato/v1`. B: adaptadores claude-code, opencode, cline, kimi-code — Hito 15 ya cerrado, B destrabada. `qwen-code`: **diferido** por decisión del dueño 2026-08-28, con el reconocimiento hecho y guardado en `docs/evidencia/reconocimiento-qwen-2026-08-28.md` (no hay marca de cierre de turno; exigiría derivar la frontera y construir el predicado de identidad) | **A cerrada** (evidencia: `docs/evidencia/fase-a-adaptador-codex-2026-08-28.md` — 131 tests, 643/643 identidad, 0/394 falsos positivos, 45/45 archivos equivalentes al extractor previo); pipeline **enrutado por `parsear()`**; **B CERRADA: los 5 CLIs** — claude-code, cline, kimi-code y opencode (este último vía ADR-012, origen de filas) (`docs/evidencia/ficha-claude-code-2026-08-28.md` — 205/205 detectados, 0 falsos positivos sobre 2,187 ajenos, 1,800 turnos, 173 tests); opencode resuelto con **ADR-012 aceptado 🔒 2026-08-28** (localizador de origen: filas en vez de offsets, instantánea = transacción de lectura, fragmento = serialización canónica sellada; `docs/evidencia/ficha-opencode-2026-08-28.md`) | `4dd10f4` |
| 19 | opencode al vigilante — cursor incremental para orígenes de filas (**ADR-013, 🔒 2026-09-06**, revoca §d de ADR-012 con medición completa: extracción completa 18.3 s vs delta por `time_created` 91.8 ms/24 h con índice cubriente existente; sellos de la delta byte-idénticos a la completa — 45/45 re-verificados tras el fix). `skopos-cursores/v2` aditivo, marca de agua con abridor previo y segmento completo del turno abierto, `procesar_base_filas` con la regla de congelamiento de ADR-011, fuente de filas en `watch` (cold start = pasada completa degradada, nunca pérdida; dedup en Mongo manda, ADR-005). Ronda adversarial del cierre: `fix-and-retry` — BLOCKER corregido (los turnos que cruzaban 2+ ciclos se perdían enteros; test de regresión incluido) | Cerrado | `31ba387` |
| 20 | Análisis multi-proveedor (**ADR-014, 🔒 2026-09-06**; enmienda parcial de ADR-001 y del manifest): adaptador compatible-OpenAI en stdlib (`_llamar_openai_compat`, parseo tolerante de cercados), proveedor por entorno `SKOPOS_LLM_API/BASE_URL/MODELO/API_KEY` — Ollama local sigue siendo el default byte-idéntico; remoto sólo por decreto (la key vive en el entorno, jamás en el repo). Precedencia argumento > entorno > default; `modelo_analisis` registra el proveedor real. Watch reiniciado el mismo día con las 5 fuentes (opencode en vivo desde ADR-013) | Cerrado | `c1579bc` |
| 21 | Gate de Skevi adoptado (**ADR-015, 🔒 2026-09-06**): `scripts/check_sizes.py` + `check_plans.py` copiados verbatim desde skevi (HEAD `910cdc4`, clon sincronizado), canon propio en `skevi-gate.json` (`required` reemplaza; límites 800/200/300 heredados sin redeclarar). Primera corrida: 118 archivos en límites, 0 incumplimientos. Gate de planes E1-E5 inactivo (clave `plans` ausente, fail-closed): el único plan existente es registro de ciclo cerrado; el primer plan nuevo deberá conformarlo y declarar la clave. AGENTS/README/guía actualizados — la verificación exige el gate en verde junto a la suite | Cerrado | `7eb1922` |
| 22 | Idioma por audiencia (**ADR-016, 🔒 2026-09-12**): inglés en comandos, flags, campos e ids de contrato; español en módulos, funciones, comentarios, `docs/` y commits. Los 25,909 campos almacenados **no** se migran hoy: se renombran dentro del `v3` que exigirá la ampliación a conversaciones de cualquier origen, para no pagar dos migraciones. Alias en inglés para `reanalizar`/`indexar`/`buscar`, sin retirar los actuales | **Implementado** — `analyze`/`reanalyze`/`index`/`search` vivos, alias viejos avisan por stderr | — |
| 23 | Puerta índice→análisis, `skopos analyze` (**ADR-017, 🔒 2026-09-12**, sobre P-006 §7): los turnos indexados eran inalcanzables para el análisis —`indexar` no llama al modelo, `watch` sólo cubre su ventana, `reanalizar` supersede uno existente—, con 25,909 observados y **8 interpretados**. Primer corpus: las **560 anclas `commit-write-plan`** (~3 h serial, local con `qwen3:8b`). No toca turnos con análisis previo; la ventana de ADR-008 queda acotada a `watch` | **Implementado** — 19 tests nuevos (272 en total), `analyze` corrido contra el corpus real y `skopos query` sirviendo resultados por primera vez; primera corrida acotada a **ventana de 7 días** por decisión del dueño (2026-09-12): 129 anclas en vez de 608, y —por P-007— las únicas con offsets sanos, así que el piloto evalúa la capa interpretada con su evidencia cruda. Ritmo real medido: ~90 s/turno, no 19.6 (las anclas son turnos grandes; la constante de `--dry-run` quedó mal calibrada) | — |
| 23.1 | **Hallazgo P-007** — offsets irrecuperables en la parte del índice construida el 2026-08-29: el desfase crece turno a turno (firma de un acumulador que no se reinició por archivo) y el 78 % de una muestra cae fuera del EOF, así que `fragmento_completo` (ADR-009 P3, hito 16) se niega. **No es pérdida de contenido ni duplicados** (595 textos distintos de 608): el índice está segmentado distinto, no inflado. La ingesta con el parser de hoy nace sana (0/400 rotos). Registrado sin corregir: reparar exige decidir qué pasa con 25,909 documentos | Propuesta abierta | — |
| 24 | P-005 reformulada como contrato (`curated-anchor`, `context-block`) en vez de tercer proyecto — se escribe **después** de la primera corrida del hito 23, por la regla que siguió ADR-010: el contrato generaliza una instancia viva, no la precede | Pendiente del hito 23 | — |
| 25 | Ampliación a conversaciones de cualquier origen (prime, agentes en runtimes y sandboxes), más allá de CLIs con rollout en disco — anunciada por el dueño el 2026-09-12. **Sin diseñar**: exige su propio análisis. Fuerza `documento-turno-mongo v3`, que nacerá en inglés por ADR-016 | Anunciado, sin análisis | — |

## Criterio de cierre por hito

Igual que en F3 de Skevi: un hito no se cierra por declaración, se cierra
con evidencia — tests en verde, comando real ejecutado, o documento
actualizado. Los hitos 0-7 tienen commit porque ya pasaron esa barra.

## Detalle de los pendientes

El **por qué y la forma** del ciclo vigente está en
`docs/propuestas/P-002-ajuste-ciclo-precondiciones.md`; el **cómo y el
orden de ejecución**, en `docs/planes/plan-ciclo-precondiciones.md`. No
se duplica aquí para no tener dos lugares que puedan desincronizarse.

## Trazabilidad entre sesiones

Estado guardado en AN-KLA local (`.an-kla/`, gitignorado — patrón de
ektel), como cadena de supersedes: `f-ciclo-multi-cli-2026-08-20` →
`f-ciclo-multi-cli-2026-08-28` → `f-skopos-cierre-2026-08-28` →
`f-skopos-cierre-2026-09-06` → `f-skopos-cierre-p005-2026-09-06` →
**`f-skopos-cierre-h2-2026-09-10`**
(vigente; transacción escrita con AN-KLA b22 el 2026-09-10, revisión
`sha256:3699363dba8f78278594830475b9805ca02c0fcdcdd0eead63b4042b46aa6851`,
autoridad `tool_observed` vía `attest`).
Recoge la sesión del 2026-09-10: corrección H-2 de ARIA F0.1 (baseline
sanitation) — `project-manifest.yaml` era YAML inválido (`:` sin
proteger en la línea 12, reproducido antes del cambio con PyYAML y
Psych); corrección mínima con escalar bloque `>-`, semántica
byte-idéntica verificada; `pinax.py validate` OK y `pinax build` vuelve
a cosechar a skopos (commit `def9bb9`). Hallazgos incidentales no
corregidos: 9 proyectos de Aria sin manifiesto (`missing_manifest`) y
el venv de pinax sin PyYAML instalado.
Recoge el cierre de la sesión del 2026-09-05/06: propuesta **P-005
"syndesmos"** (plugin independiente tejedor de contexto skopos ↔
AN-KLA; commit `a4a74ea`, issue de seguimiento
`kristhianmanue1/skopos#2`), las dos hipótesis de memoria refutadas
con medición (AN-KLA insuficiente y perecedera; la memoria de skopos
sin capa de análisis y sin el presente) y el dato que destraba la
integración: 448 turnos con `commit-write-plan` como anclas curadas.
Recuperable con
`an-kla retrieve --query "syndesmos p-005 tejedor" --budget 1500`.
Nota de versión: la instalación de AN-KLA para skopos quedó en
**0.1.0b22** (venv local); los almacenes de otros proyectos y el PATH
siguen en versiones anteriores por decisión del dueño.

## Índice de turnos (P-004) e identidad de Codex

P-004 aceptada 🔒 2026-08-28 e **implementada**: `skopos.turnos` con
`documento-turno-mongo v1` y el comando `skopos indexar`. El piloto
destapó que el `turn_id` crudo de Codex se repite entre sesiones —la
dedup habría descartado el 35 % de los turnos
(`docs/evidencia/colision-turn-id-codex-2026-08-28.md`)—, así que **la
identidad de parser-codex pasó a calificada** (🔒 2026-08-28, ADR-010
§7/§8 actualizados: la excepción de id crudo queda revocada por
contraejemplo). Con eso, **índice lleno: 22,870 turnos de los 5 CLIs en
65.9 s, 213 MB, búsqueda en <10 ms**
(`docs/evidencia/indice-de-turnos-2026-08-28.md`).

Los tres pendientes quedaron cerrados el mismo día
(`docs/evidencia/superficie-busqueda-y-eco-2026-08-28.md`):
**`skopos buscar`** sirve el índice con P3, P5 y redacción de secretos
(contrato `cli-skopos-buscar v1`); el **detector de eco** pasó su control
positivo 3/3 sin falsos positivos y midió 29 turnos con firma (0.1 %)
sobre la colección real; y **`watch` ya indexa** por defecto, sólo dentro
de la ventana de ADR-008 y de forma independiente del análisis —
verificado con Ollama caído: el turno queda indexado aunque el análisis
falle.
