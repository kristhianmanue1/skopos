# Plan — adaptador prime-agent (frente de fuentes) — 2026-10-13

Estado: **ACTIVO, sin ejecutar**. Deriva del issue #1 (propuesta del dueño
2026-09-06) tras la verificación contra código y datos vivos del 2026-10-13.
Cierra el punto ciego del ciclo ARIA: el agente que integra el ecosistema no
es observable por Skopos.

## Contexto verificado (2026-10-13)

- `~/.prime/agent/sessions/` existe con 8 sesiones JSONL reales; cabecera
  `session` versión 3 con `rlmDepth`; ~79% de líneas no conversacionales
  (`agent_status` 1394 vs `message` 380 en una sesión medida) — el cierre de
  turno debe derivarse user→user, como analizó la ronda 2026-09-02.
- Eventos `child_usage_attributed` presentes: los sub-agentes existen y su
  uso ya llega resumido a la sesión padre.
- `src/skopos/vigilante.py` registra 4 fuentes por rollout + opencode por
  filas; prime ausente. Patrón de adaptador: `src/skopos/kimi_code.py`
  (242 líneas) y `src/skopos/claude_code.py` (236), con ficha
  `parser-X/v1` bajo ADR-010/SPEC-006 y tests dedicados.
- JSONL append-only por archivo: aplica el cursor incremental de ADR-011
  (mismo frente que codex), no el de filas de ADR-013.
- Descarte verificado: la ruta runtime v3 (`import_file` con
  `dsh-session-v0-jsonl` o texto) NO absorbe a prime-agent — importar como
  texto perdería la estructura de turnos y es custodia explícita por archivo,
  no observación continua.

## Objetivo y no-objetivos

**Objetivo**: adaptador `parser-prime-agent/v1` con ficha bajo contrato
`parser-contrato/v1` (ADR-010 §8), registro en el vigilante y selección en
`parsear()`, con turnos cerrados derivados y deduplicación con namespace.

**No-objetivos**: indexar sub-agentes (ver T0); exportación (fases C/D de
P-003, aplazadas); cambios a SPEC-006 o ADR-010.

```text
TAREA T0 — decisión de alcance sobre sub-agentes
Consumes: este plan; issue #1; AGENTS.md.
Produce: decisión registrada del Operador sobre rlmDepth.
Steps:
- [ ] Decidir el filtro rlmDepth; recomendación del agente: sólo sesiones padre (rlmDepth 0) — los sub-agentes ya llegan resumidos vía child_usage_attributed e indexarlos duplica el corpus con eco.
  Verificación: decisión explícita del Operador en el acta de la sesión; sin ella no iniciar T1.

TAREA T1 — ficha y adaptador
Consumes: T0; src/skopos/kimi_code.py; docs/contratos/f1-contratos.md.
Produce: se crea src/skopos/prime_agent.py con ficha parser-prime-agent/v1 bajo parser-contrato/v1.
Steps:
- [ ] Declarar la ficha: identidad, marcas de estructura, alcance de escaneo, fuentes de session_id/turn_id/timestamp_cierre; turn_id namespaced prime:<session>:<id> (sin namespace la dedup de ADR-005 pierde ~35% según la ronda 2026-09-02).
  Verificación: ficha válida contra el contrato; cero extracción de thinking/toolCall (exclusión de la ronda).
- [ ] Derivar el cierre de turno user→user sobre las sesiones reales (8 disponibles).
  Verificación: contraste sobre archivos vivos; sin turnos cruzando sesiones; sin turno abierto al final de archivo salvo sesión activa.

TAREA T2 — registro y pruebas
Consumes: T1; src/skopos/vigilante.py; src/skopos/parseo.py; tests/test_kimi_code.py.
Produce: fuente registrada en el vigilante, selección en parsear() y suite en verde con tests dedicados.
Steps:
- [ ] Registrar (~/.prime/agent/sessions, *.jsonl) en FUENTES_POR_DEFECTO y el despacho en parsear() (frontera SPEC-006, un módulo por frontera).
  Verificación: detección idéntica entre extracción completa y delta (patrón ADR-013); dedup Mongo manda (ADR-005).
- [ ] Tests dedicados con fixtures derivados de las sesiones reales, sin datos privados en el repo.
  Verificación: suite completa en verde; cero falsos positivos sobre archivos ajenos (patrón de las fichas previas: 2.187 ajenos para claude-code).

TAREA T3 — corrida viva y evidencia
Consumes: T2; docs/evidencia/.
Produce: se crea docs/evidencia/ficha-prime-agent-2026-10-XX.md con medición de ingesta real.
Steps:
- [ ] Ingerir las 8 sesiones reales y medir: turnos detectados, dedup, tiempo por delta.
  Verificación: números exactos en la evidencia; sellos verificados byte a byte (patrón 45/45 de ADR-013); sin tocar corpus operativo sin autorización.

TAREA T4 — ronda adversarial y publicación
Consumes: T3; docs/rondas/.
Produce: ronda adversarial documentada; push reportado.
Steps:
- [ ] Ronda adversarial con revisor sin contexto de autoría (patrón del plan multiproyecto).
  Verificación: tabla de hallazgos con veredicto; correcciones aplicadas antes de publicar.
- [ ] Publicar con suite y gates en verde.
  Verificación: python3 scripts/check_sizes.py y python3 scripts/check_plans.py en verde; git ls-remote == main local.
```

## Riesgos y abortos

- Si el formato v3 de las sesiones cambia sin aviso (campo `version`), el
  adaptador debe fallar con `version_no_soportada` (modo de fallo de SPEC-006),
  nunca ingerir a ciegas.
- Si T1 no logra cierre derivado estable sobre las 8 sesiones, abortar y
  documentar: no forzar marcas inexistentes.
