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
| 15 | C-10: cursor de ingesta — decisión 8 + ADR de lectura incremental (P-002 §3.3) 🔒 | **Cerrado** — gate con remedición fechada (`remedicion-ciclo-c10-2026-08-28.md`), **ADR-011 aceptado 🔒 2026-08-28** e implementado tras la ronda 23 (4 hallazgos corregidos): ciclo de 13.9 s a **3.7–4.9 s** con carga normal, dentro del intervalo de 5 s; 159 tests (`cursor-incremental-2026-08-28.md`) | pendiente |
| 16 | C-6: decisión sobre `fragmento_completo` — ADR-009, P4a+P5+P3, decisión 🔒 2026-08-20 | Cerrado | `21ce77a` |
| 17 | C-5: detector de eco sobre corpus piloto (P-002 §3.5) — 6/6 sellados, 0 hits, control positivo 3/3 | Cerrado | `27c1332` |
| 18 | Implementación multi-CLI, fases A+B de `docs/propuestas/P-003-colector-conversation-event.md` (aceptada 🔒 2026-08-28 tras la ronda 22; fases C/D de exportación **aplazadas** por no tener consumidor). A: parser codex → adaptador tras `parser-contrato/v1`. B: adaptadores claude-code, opencode, cline, kimi-code — Hito 15 ya cerrado, B destrabada. `qwen-code`: **diferido** por decisión del dueño 2026-08-28, con el reconocimiento hecho y guardado en `docs/evidencia/reconocimiento-qwen-2026-08-28.md` (no hay marca de cierre de turno; exigiría derivar la frontera y construir el predicado de identidad) | **A cerrada** (evidencia: `docs/evidencia/fase-a-adaptador-codex-2026-08-28.md` — 131 tests, 643/643 identidad, 0/394 falsos positivos, 45/45 archivos equivalentes al extractor previo); pipeline **enrutado por `parsear()`**; **B CERRADA: los 5 CLIs** — claude-code, cline, kimi-code y opencode (este último vía ADR-012, origen de filas) (`docs/evidencia/ficha-claude-code-2026-08-28.md` — 205/205 detectados, 0 falsos positivos sobre 2,187 ajenos, 1,800 turnos, 173 tests); opencode resuelto con **ADR-012 aceptado 🔒 2026-08-28** (localizador de origen: filas en vez de offsets, instantánea = transacción de lectura, fragmento = serialización canónica sellada; `docs/evidencia/ficha-opencode-2026-08-28.md`) | pendiente |

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
`f-ciclo-multi-cli-2026-08-28` → **`f-skopos-cierre-2026-08-28`**
(vigente; transacción `6aa9579f-2761-43d8-a84a-9f5fe6580a51`, revisión 3
`sha256:2c7dd9af073cdeb3263547f74625a78ec028e5d405fbdd17de4fc503459ba38b`).
Recoge avances, **limitaciones vivas** y los dos patrones aprendidos del
día. Recuperable con
`an-kla retrieve --query "estado skopos limitaciones" --budget 6000`.

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
