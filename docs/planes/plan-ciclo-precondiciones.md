# Plan de acción — ciclo de precondiciones multi-CLI

Estado: **activo** — plan de ejecución de P-002
(`docs/propuestas/P-002-ajuste-ciclo-precondiciones.md`), aprobado por el
dueño en este canal el 2026-08-20.
Fecha: 2026-08-20.
Revisión: v3 — incorpora el protocolo de cierre por fase (ronda
adversarial + ajuste + commit, autorizado por el dueño el 2026-08-20) y
las once correcciones (H1–H11) de la ronda adversarial sobre el plan
(acta en `docs/rondas/2026-08-20-ronda-0-plan.md`).
Traza: hitos 8, 10 y 13–17 de `docs/hoja-de-ruta.md`; encargo de origen
en `/Users/krisnova/www/pinax/rondas/2026-08-20-vision-skopos-ektel/instruccion-agente-skopos.md`.

Este documento es el **cómo y cuándo**; P-002 es el **por qué y con qué
forma**. Si un paso de aquí contradice P-002, gana P-002 hasta que
alguno de los dos se corrija con evidencia.

## Reglas transversales (aplican a toda fase)

- 🔒 = requiere autorización explícita del dueño, una vez por operación
  (`AGENTS.md`). El agente prepara la decisión, nunca la toma.
- Toda métrica citada va fechada como snapshot (regla nacida de X-2).
- Sin dependencias nuevas sin autorización explícita; sin placeholders;
  un módulo por frontera de SPEC; español; `unittest` de stdlib.
- Ninguna fase se cierra sin pasar el protocolo completo de la sección
  siguiente.
- Push sigue requiriendo autorización explícita, cada vez.

## Protocolo de cierre de fase (obligatorio, autorizado por el dueño 2026-08-20)

Ninguna fase se declara cerrada sin los cinco pasos, en este orden:

1. **Verificación base**: `python3 -m unittest discover -s tests` en
   verde; diff leído completo; specs/contratos/implementación/tests
   consistentes; métricas fechadas.
2. **Ronda adversarial** sobre lo producido en la fase: revisor con
   **contexto fresco** (subagente separado, que no vivió la
   implementación), instruido a refutar y a verificar cada cita contra
   código y docs. La autocrítica del mismo contexto es sólo piso de
   calidad, nunca ronda de cierre — lección registrada en P-001 §10
   frente a §11.
3. **Ajuste**: cada hallazgo se corrige, o se registra con su razón si
   se rechaza; un BLOCKER bloquea el cierre.
4. **Re-verificación**: tests en verde otra vez tras los ajustes.
5. **Commit**: uno por fase — docs + código + tests del mismo golpe —
   con mensaje en el estilo del repo, más el **acta de la ronda** en
   `docs/rondas/` (hallazgos y destino de cada uno), para que el
   historial de correcciones tenga la misma trazabilidad que P-001 §1.

**Operativa de la ronda** (ronda 0, corrección H8): la lanza el agente
del ciclo como subagente con contexto fresco; si no vuelve o tarda
desproporcionadamente, se relanza una vez y la segunda falla escala al
dueño sin cerrar la fase. El agente implementador puede rebatir un
hallazgo **con evidencia**, registrada en el acta; una disputa sin
resolver escala al dueño, y sólo el dueño retira un BLOCKER.

**Fases que esperan una decisión 🔒:** si una fase se detiene a la
espera del dueño, lo producido hasta ahí se commitea como propuesta
pendiente (ej. `docs: ADR-007 propuesto, decisión 🔒 pendiente`); el
cierre definitivo de la fase llega con su ronda, ajuste y commit.

**Ronda 0 (2026-08-20):** este plan pasó por su propia ronda adversarial
antes de empezar. Acta con los once hallazgos y su destino:
`docs/rondas/2026-08-20-ronda-0-plan.md`. Esa acta es también el
registro no autoreferencial de la autorización de este protocolo
(corrección H4) y de la decisión multi-CLI del dueño.

**Mapa fase → hito** (corrección H10): F1→Hito 13 · F2→Hito 14 ·
F3(a)→Hito 8 · F3(b)→Hito 15 (el ADR) · F4→Hito 16 · F5→Hito 17 ·
F6→Hito 10 · F7→Hito 12.

## Fase 0 — Acto 0 · CERRADA (2026-08-20)

Hecho: dueño confirmó multi-CLI en canal; P-001 anotada como superada;
`hoja-de-ruta.md` y `README.md` sincronizados; P-002 escrita.
Trazabilidad entre sesiones: estado del ciclo guardado en AN-KLA local
(`.an-kla/`, gitignorado — patrón de ektel) el 2026-08-20, transacción
`7ba725a4`, hecho `f-ciclo-multi-cli-2026-08-20`; recuperable con
`retrieve --query "ciclo multi-CLI"`.

## Fase 1 · C-9 — eje de proyecto y eje CLI real (Hito 13)

Objetivo: el documento Mongo identifica proyecto y CLI de verdad; la
búsqueda se puede acotar por proyecto.

Pasos:
1. **Contratos primero.** Enmendar en `docs/contratos/f1-contratos.md`:
   - `rollout-jsonl-de-codex`: documentar `turn_context` como fuente de
     `proyecto` (`payload.cwd`/`payload.workspace_roots`, por turno —
     EV-1 de P-002, snapshot 2026-08-20).
   - `documento-analisis-mongo`: agregar `proyecto` (string, opcional;
     ausente = desconocido pre-C-9). Enmienda compatible según el propio
     contrato v1.
   - **`cli-skopos-query`**: agregar `--proyecto` como filtro opcional a
     la Entrada (corrección H6 de la ronda 0 — sin esto, la fase falla
     su propia barra de consistencia).
2. **Regla de derivación con evidencia** (corrección H5): antes de
   codificar, muestrear la distribución real de `cwd`/`workspace_roots`
   en el corpus (snapshot fechado en el acta de la fase) y diseñar la
   regla con esos datos. Modo de fallo obligatorio: cuando el valor no
   identifique un proyecto (ej. `cwd = /Users/krisnova/www`, medido en
   ronda 0), el campo queda **ausente**, nunca un valor presente pero
   sin significado — para el filtro `--proyecto`, un valor basura es
   peor que ninguno.
3. **Specs.** Ajustar SPEC-001 (captura extrae `proyecto`), SPEC-003
   (persistencia + índices), SPEC-004 (`skopos query --proyecto`).
4. **Código** (`captura.py`, `analisis.py`, `almacenamiento.py`,
   `cli.py`):
   - `Turno.proyecto` derivado del `turn_context` del turno según la
     regla del paso 2 (no de una constante ni del nombre de archivo).
   - `analisis.py`: la ficha de escrubery usa `turno.cli`; se elimina el
     default hardcodeado `escrubery_cli="codex-cli"` (EV-4 de P-002).
   - Índices nuevos: `proyecto`, `cli`, `ocurrido_en` (EV-2; este último
     prepara el `skopos read` diferido).
   - `skopos query` gana filtro opcional `--proyecto`.
5. **Tests**: uno por comportamiento nuevo (extracción de proyecto,
   ausencia legítima en legacy y en valor sin significado, filtro por
   proyecto, índices creados).

Entregables: contratos/specs enmendados + código + tests.
Verificación: reglas transversales; además una corrida real de
`skopos query` con y sin `--proyecto` contra el Mongo local — con la
colección probablemente vacía hoy (0 documentos, snapshot 2026-08-19)
esa corrida prueba el canal (JSON válido, lista vacía, exit 0), no la
semántica; la verificación semántica llega con el corpus piloto de la
Fase 5.

## Fase 2 · C-8 — superficie de mutación o retención (Hito 14) 🔒

Objetivo: que la vigencia del store tenga reparación posible.

Pasos:
1. Redactar ADR nuevo con **tres** alternativas y consecuencias:
   retención (TTL/borrado), supersede blanda (`reemplazado_por`, mantiene
   insert-only), mutación plena. Justificación multi-CLI (la de P-001
   murió con P-001). Nota obligatoria: la opción 4 retroactiva de C-6 y
   el cierre del legacy de C-9 dependen de lo que aquí se decida.
2. 🔒 El dueño elige.
3. Implementar lo decidido + tests; cerrar la política de legacy de C-9
   (backfill de `proyecto` si la superficie lo permite).

## Fase 3 · C-10 — cursor de ingesta desempaquetado (Hito 15) 🔒

**(a) Decisión 8 — política de arranque.**
1. Preparar diseño concreto de la opción recomendada: "desde ahora" por
   defecto (filtro por mtime en el arranque) + `--backfill` opt-in.
   ADR-005 intacto: la dedup sigue viviendo en Mongo.
2. **Remedir el ciclo del vigilante al cerrar (a)** (corrección H9):
   duración de un ciclo completo vs intervalo, snapshot fechado. El
   disparador de (b) parece ya cumplido por el snapshot 2026-08-19
   (~8 s > 5 s), pero se decide con la remedición, no con memoria.
3. 🔒 El dueño decide.
4. Implementar + tests (el vigilante no reprocesa historia por defecto).

**(b) ADR de lectura incremental** — sólo con **evidencia medible y
fechada** de que (a) no alcanza: un ciclo completo del vigilante tarda
más que su intervalo (criterio objetivo; hoy ~8 s de parseo por ciclo
contra intervalo de 5 s sería disparador, snapshot 2026-08-19 — a
remedir). Encuadre: extensión pre-registrada por el propio ADR-005; el
cursor es caché inofensiva, la dedup autoritativa sigue en Mongo. 🔒
aceptación del dueño.

**(c) Backfill por pilotos** — el piloto 1 (una sesión) sirve a Fase 5.
Cada piloto publica su snapshot fechado. No se decide 40–100 h
(snapshot 2026-08-19) de una vez.

**Riesgo conocido para 3c/5 (exigencia 1 de la firma del ADR-008,
2026-08-20):** el timeout de análisis de 120 s quedó marginal — 2 de 7
llamadas reales del snapshot 2026-08-20 cayeron en él con el entorno
bajo carga (`docs/evidencia/remedicion-ciclo-c10-2026-08-20.md`,
lectura 3). Antes de correr cualquier piloto de backfill se decide si
se sube el timeout o se troza el trabajo; no se lanza un piloto con el
timeout marginal sin tratar.

**Decisión 🔒 del dueño (2026-08-20), tratamiento del timeout para
pilotos:** opción **(a)+(b)** — subir el timeout del piloto a 300 s vía
el parámetro existente de `analizar_turno` (sin tocar código), y
reportar los fallos que queden como dato con conteo explícito
éxitos/fallos. Opción (c) (esperar carga baja) descartada: la evidencia
debe ser reproducible, no afortunada.

## Fase 4 · C-6 — `fragmento_completo` (Hito 16) 🔒

1. Brief de decisión con las **cinco** palancas de P-002 §3.4 (servir /
   redactar / marcar no-instrucción [declarativa] / persistir o sellar
   [requiere Fase 2 si es retroactiva] / **límite-presupuesto en la
   salida**) con costo estimado y fechado por opción.
2. 🔒 El dueño elige combinación.
3. Implementar + tests (incluye el fallo silencioso de `cli.py:20-27`,
   hallazgo Y-5: ninguna opción lo deja abierto).

## Fase 5 · C-5 — detector de eco sobre corpus piloto (Hito 17)

Requiere: Fase 3(a) cerrada.
1. Backfill piloto de una sesión (~28 turnos ≈ 10 min al ritmo medido de
   19.6 s/turno, snapshot 2026-08-19).
2. Ejecutar el detector corregido de P-001 §4.5 (regex sobre `resumen`)
   **acotado al piloto** — filtro por `session_id`/turn_ids del piloto,
   no la colección entera, para no mezclar corpus si el vigilante "desde
   ahora" ya ingiere en vivo (corrección H11).
3. Reporte fechado en `docs/evidencia/detector-eco-piloto-1.md` con la
   composición del corpus declarada (fracción de turnos que hablan de
   Skopos — sesgo auto-referencial).

## Fase 6 · escrubery — ensayo del canal (Hito 10) · PARALELA

Puede correr desde ya; no bloquea ni depende de nada.
1. Ensayo funcional con `escrubery_script` explícito contra
   `/Users/krisnova/www/aria/escrubery` (REQ-10; ADR-004: opcional, no
   bloqueante).
2. Registrar: resultado (ficha/sin ficha/fallo tolerado), latencia por
   llamada, y el hallazgo subprocess-por-turno (`analisis.py:194-197`)
   como recomendación de memoización — no se implementa aquí.

## Fase 7 · contrato de parser por CLI (Hito 12) · GATED

Sólo con Fases 1–5 cerradas **y Fase 6 cerrada** (corrección H7: el
canal escrubery debe estar ejercitado o explícitamente invalidado antes
de diseñar un contrato que se indexa "vía fichas de escrubery" — si el
ensayo resulta en fallo tolerado, el diseño de esta fase lo declara y no
depende del canal): ADR nuevo + SPEC nueva
(`detectar formato → turnos normalizados`), Codex como adaptador de
referencia, indexado por `(cli, versión)` vía fichas de escrubery. El
diseño decide, por CLI, de dónde salen `proyecto` y `cli` (la trampa de
fuente de verdad de Fase 1, generalizada a la familia).

## Dependencias

```text
Fase 0 ✅
  ├─> Fase 1 (C-9) ──> Fase 2 (C-8) 🔒 ──> Fase 4 (C-6) 🔒
  ├─> Fase 3a (decisión 8) 🔒 ──> Fase 3c (pilotos) ──> Fase 5 (C-5)
  ├─> Fase 6 (escrubery)                [paralela; gate de Fase 7]
  └─> Fase 7 (parser)                   [gated: Fases 1-6 cerradas]
        Fase 3b (ADR incremental)       [disparo por remedición en 3a]
```

## Progreso

| Fase | Estado | Ronda | Commit |
|---|---|---|---|
| 0 · Acto 0 | ✅ Cerrada | ronda 0 (sobre el plan, 2026-08-20, acta en `docs/rondas/2026-08-20-ronda-0-plan.md`) | apertura del ciclo (2026-08-20) |
| 1 · C-9 | ✅ Cerrada | ronda 1 (2026-08-20, 6 hallazgos corregidos, acta en `docs/rondas/2026-08-20-ronda-1-fase1-c9.md`) | `811e58c` |
| 2 · C-8 | ✅ Cerrada | ronda 2 (ADR, pre-decisión) + ronda 3 (implementación; 10 hallazgos corregidos, acta en `docs/rondas/2026-08-20-ronda-3-fase2-c8.md`) | `f0f6134` |
| 3 · C-10 | 3(a) ✅ Cerrada — decisión 8 🔒 firmada 2026-08-20 (ADR-008, tras revisión aprobatoria de Pinax); ronda 5 sobre la implementación (4 hallazgos corregidos, acta en `docs/rondas/2026-08-20-ronda-5-fase3a-c10.md`). (b) gated a evidencia (remedición en `docs/evidencia/remedicion-ciclo-c10-2026-08-20.md`). (c) pilotos pendientes | 3a: ronda 5 / `—` |
| 4 · C-6 | ✅ Cerrada | ronda 6 (ADR, pre-decisión) + ronda 8 (implementación; 8 hallazgos corregidos, acta en `docs/rondas/2026-08-20-ronda-8-fase4-c6.md`) | `21ce77a` |
| 5 · C-5 | ✅ Cerrada | ronda 9 (7 hallazgos de redacción/trazabilidad corregidos, incl. control positivo del detector 3/3; acta en `docs/rondas/2026-08-20-ronda-9-fase5-c5.md`; reporte en `docs/evidencia/detector-eco-piloto-1.md`: 6/6 éxitos sellados, detector 0 hits, composición 3/6 declarada) | `—` |
| 6 · escrubery | ✅ Cerrada | ronda 7 (verificación empírica, aprobado; acta en `docs/rondas/2026-08-20-ronda-7-escrubery.md`; ensayo en `docs/evidencia/ensayo-escrubery-2026-08-20.md`) | `8d68ed1` |
| 7 · parser | Pendiente (gated: 1–5) | — | — |
