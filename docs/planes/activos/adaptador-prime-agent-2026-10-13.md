# Plan — adaptador prime-agent (frente de fuentes) — 2026-10-13

Estado: **CANCELADO por decisión del Operador el 2026-10-13**
([acta](../../evidencia/acta-decisiones-operador-2026-10-13.md), decisión 7):
prime no se utilizará y la integración queda cancelada — Skopos
es independiente y celebra contratos con proyectos de ARIA (Ágora, AN-KLA) o
con terceros como expertoGobernanza, **no** con prime agents. De la
conversación con Prime sólo se toma lo que conviene a Skopos. Ninguna tarea se
ejecutó: no se creó adaptador, registro ni prueba; las T0-T4 quedan sin
efecto y el archivo se conserva como registro del análisis de viabilidad
(premisas verificadas el 2026-10-13) por si la decisión se revisara algún día.

Estado previo: ACTIVO, sin ejecutar; T0 resuelta (rlmDepth 0) y luego
cancelada sin llegar a T1.

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
  (verificado en ronda: `AlmacenCursores` es genérico por ruta y `ciclo()` lo
  aplica a toda fuente de archivo — claude/kimi/cline lo usan igual que
  codex), no el de filas de ADR-013.
- La cifra «sin namespace la dedup pierde ~35%» proviene del texto del issue #1
  (ronda del dueño 2026-09-02, **sin acta en `docs/rondas/`** — hueco
  archivístico detectado por la ronda adversarial): T1 la **remide** sobre
  las sesiones vivas en vez de heredarla.
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
- [x] Decidir el filtro rlmDepth; recomendación del agente: sólo sesiones padre (rlmDepth 0) — los sub-agentes ya llegan resumidos vía child_usage_attributed e indexarlos duplica el corpus con eco. Nota de ronda: hoy las 8 sesiones en disco son todas rlmDepth 0 (la hija referida en un custom_message no existe en disco), y `FUENTES_POR_DEFECTO` es (dir, glob) sin gancho de filtro: el filtro vive en la ficha, como incompatibilidad tipada (rlmDepth>0 → diagnóstico propio), no en el registro de fuentes.
  **Decisión del Operador (2026-10-13): sólo rlmDepth 0** — [acta](../../evidencia/acta-decisiones-operador-2026-10-13.md).
  Verificación: decisión explícita del Operador en el acta de la sesión; cumplida.

TAREA T1 — ficha y adaptador
Consumes: T0; src/skopos/kimi_code.py; docs/adr/ADR-010-contrato-parser-por-cli.md.
Produce: se crea src/skopos/prime_agent.py con ficha parser-prime-agent/v1 bajo parser-contrato/v1.
Steps:
- [ ] Declarar la ficha: identidad, marcas de estructura, alcance de escaneo, fuentes de session_id/turn_id/timestamp_cierre; turn_id namespaced prime:<session>:<id>. session_id se toma de la cabecera `session` del archivo, no del nombre — en 1 de 8 archivos difieren (verificado en ronda); el namespace `prime:` está libre y almacenamiento no valida formato más allá de no-vacío.
  Verificación: ficha válida contra ADR-010 §8; remedición de colisiones de dedup sobre las 8 sesiones (el ~35% del issue #1 es referencia, no dato); cero extracción de thinking/toolCall/toolResult — toolResult es un rol de message con texto (612 en el corpus, el segundo depósito por volumen) y queda declarado frontera, no contenido.
- [ ] Derivar el cierre de turno user→user sobre las sesiones reales (8 disponibles; 0 casos de usuarios consecutivos medidos en ronda).
  Verificación: contraste sobre archivos vivos; sin turnos cruzando sesiones; criterio de final falsifiable: si el archivo termina sin mensaje de usuario que cierre, el último turno queda registrado en estado abierto con su posición física — sin invocar «sesión activa» (indistinguible de abandonada en disco; ronda: un archivo termina en stopReason error con session_state active).

TAREA T2 — registro y pruebas
Consumes: T1; src/skopos/vigilante.py; src/skopos/parseo.py; tests/test_kimi_code.py.
Produce: fuente registrada en el vigilante, selección en parsear() y suite en verde con tests dedicados.
Steps:
- [ ] Registrar (~/.prime/agent/sessions, *.jsonl) en FUENTES_POR_DEFECTO y el despacho en parsear() (frontera SPEC-006, un módulo por frontera).
  Verificación: extracción completa vs delta idénticas por archivo (patrón ADR-011, cursor genérico); dedup Mongo manda (ADR-005); sellos verificados byte a byte (patrón 45/45 de la evidencia codex, fase-a 2026-08-28).
- [ ] Tests dedicados con fixtures derivados de las sesiones reales, sin datos privados en el repo.
  Verificación: suite completa en verde; cero falsos positivos sobre archivos ajenos (patrón de las fichas previas: 2.187 ajenos para claude-code).

TAREA T3 — corrida viva y evidencia
Consumes: T2; docs/evidencia/.
Produce: se crea docs/evidencia/ficha-prime-agent-2026-10-XX.md con medición de ingesta real.
Steps:
- [ ] Ingerir las 8 sesiones reales y medir: turnos detectados, dedup, tiempo por delta.
  Verificación: números exactos en la evidencia; sellos verificados byte a byte (patrón 45/45 de la evidencia codex, fase-a 2026-08-28); sin tocar corpus operativo sin autorización.

TAREA T4 — ronda adversarial y publicación
Consumes: T3; docs/rondas/.
Produce: ronda adversarial documentada; push reportado.
Steps:
- [ ] Ronda adversarial con revisor sin contexto de autoría (patrón del plan multiproyecto).
  Verificación: tabla de hallazgos con veredicto; correcciones aplicadas antes de publicar.
- [ ] Publicar con suite y gates en verde.
  Verificación: python3 -m unittest discover -s tests en verde; python3 scripts/check_sizes.py y python3 scripts/check_plans.py en verde; git ls-remote == main local.
```

## Riesgos y abortos

- Si el formato v3 de las sesiones cambia sin aviso (campo `version`), el
  adaptador debe fallar con `version_no_soportada` (modo de fallo de SPEC-006),
  nunca ingerir a ciegas.
- Si T1 no logra cierre derivado estable sobre las 8 sesiones, abortar y
  documentar: no forzar marcas inexistentes.
