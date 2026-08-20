# P-002: ajuste del ciclo de precondiciones para multi-CLI

Estado: **aprobada por el dueño en canal (2026-08-20).** Ejecución
según `docs/planes/plan-ciclo-precondiciones.md`; los actos 🔒 de este
documento siguen requiriendo autorización explícita del dueño, una vez
por operación (`AGENTS.md`).
Fecha: 2026-08-20.
Origen: análisis crítico del encargo contra código (`skopos@124d31c`),
P-001 v4, visión final firmada y actas X-1/X-2, Y-1..Y-7. El encargo de
origen está en
`/Users/krisnova/www/pinax/rondas/2026-08-20-vision-skopos-ektel/instruccion-agente-skopos.md`
y conserva íntegra su gobernanza.

## 1. Qué ajusta y por qué

El encargo acierta en gobernanza: restaura el orden real de P-001 §5
(X-1), marca 🔒 los actos de autoridad, fecha las métricas como snapshot
(X-2), nombra ADR-005 y la decisión 8 (Y-4), y gatea el contrato de
parser tras las precondiciones. Verificado contra el código y los
documentos del repo, tiene ocho defectos de ejecución. Este documento los
ajusta; no reabre P-001 ni contradice ADR-001..006.

| # | Hallazgo (verificado) | Ajuste |
|---|---|---|
| 1 | La premisa multi-CLI llega sólo vía Pinax; el acta de Codex declara "sin autenticar al dueño" | Acto 0: el dueño confirma en este canal antes de cualquier edición (§2) |
| 2 | Hoja de ruta: Hito 12 declara multi-CLI "explícitamente fuera de alcance"; Hito 8 pendiente; README con el orden viejo de próximos pasos | Acto 0 incluye sincronizar `hoja-de-ruta.md` y `README.md` (§2) |
| 3 | C-9 es más que "un campo": fuente de verdad sin evidencia registrada, política de legacy indefinida, índices faltantes, hardcode duplicado | §3.1 |
| 4 | C-8 se justifica con la consolidación AN-KLA — superada por la misma decisión que motiva el ciclo | §3.2: re-justificación multi-CLI + alternativa intermedia |
| 5 | C-10 empaqueta tres decisiones separables (política de arranque, ADR de lectura incremental, backfill) | §3.3: desempaquetado; la decisión 8 no requiere tocar ADR-005 |
| 6 | C-5 correría contra un corpus de 0 documentos: está bloqueado por C-10, no "último" | §3.5: piloto de una sesión + composición del corpus declarada |
| 7 | C-6: "marcar como no-instrucción" es sólo declarativa; falta la palanca límite/presupuesto (motor del eco, P-001 §4.5) | §3.4: cinco palancas, no cuatro |
| 8 | El ensayo escrubery ejercitaría un subprocess por turno (`analisis.py:194-197`) sin registrar el costo | §3.6: el ensayo mide y produce el hallazgo, no lo implementa |

## 2. Acto 0 — compuerta de confirmación (pendiente 🔒)

Todo lo demás espera a esto. La decisión multi-CLI existe hoy sólo en el
canal Pinax; el repo no la registra y el acta de Codex explicita que no
autenticó al dueño. La confirmación del dueño **en este canal** (una
línea) es la evidencia citable que desbloquea, en el mismo acto
documental:

1. **Anotar P-001** — una línea de estado y fecha, nada más (lo permite
   el encargo; no se reabre, no se rediseña):
   > Superada por decisión del dueño (2026-08-20): Skopos será multi-CLI
   > con parsers propios; la pregunta 3 de §7 queda resuelta por decisión,
   > no por ronda. Ver P-002.
2. **Sincronizar `docs/hoja-de-ruta.md`** — Hito 12 reencuadrado (de
   "fuera de alcance" a "gated tras las precondiciones, P-002"); Hito 8
   reencuadrado como C-10(a) de este ciclo; Hito 9 (`skopos read`)
   diferido explícitamente —no cancelado—; los ítems de este ciclo
   entran como hitos nuevos.
3. **Sincronizar `README.md` § "Próximos pasos"** — hoy lista otro orden;
   sin esto el repo contradice su propia dirección.

Si el dueño no confirma, este documento queda como propuesta y no se
toca nada más.

## 3. Ítems del ciclo, ajustados

### 3.1 C-9 · Eje de proyecto (y eje CLI de verdad)

Alcance real, más allá de "añadir un campo":

- **Fuente de verdad con evidencia.** EV-1 (2026-08-20): el evento
  `turn_context` de los rollouts de Codex trae `payload.cwd` y
  `payload.workspace_roots`, **por turno** (incluye `turn_id`). El
  proyecto es derivable en captura para ingesta nueva, incluso si el
  directorio cambia a mitad de sesión. `captura.py` hoy ignora
  `turn_context` por completo; `Turno` gana un campo `proyecto` y la
  SPEC-001/CONTRATO rollout-jsonl-de-codex se enmiendan para documentar
  la fuente.
- **Política de legacy.** Los documentos pre-C-9 no llevan `proyecto` y
  el store es insert-only: no se falsifican. Campo ausente =
  "desconocido (pre-C-9)". Recuperarlos por backfill releyendo
  `ruta_origen` hereda el riesgo de integridad de Y-5 y **requiere** la
  superficie de C-8 — por eso C-8 va después y la política de legacy se
  cierra con C-8, no aquí.
- **Índices.** `proyecto`, `cli` y `ocurrido_en` (este último prepara el
  Hito 9 diferido). Hoy sólo existen `turn_id` único y `$text`
  (`almacenamiento.py:106-107`).
- **Eje CLI.** `cli` ya es campo obligatorio del documento (CONTRATO
  documento-analisis-mongo v1); lo que falta es que deje de ser
  constante: `CLI_ORIGEN` (`captura.py:18`) pasa al adaptador, y la
  ficha de escrubery debe usar `turno.cli` en vez del default
  hardcodeado `escrubery_cli="codex-cli"` (`analisis.py:172`).
- **Contrato.** Agregar `proyecto` como opcional es enmienda compatible
  hacia atrás según el propio CONTRATO v1 ("agregar campos opcionales es
  compatible"); exige actualizar SPEC-003, SPEC-004 y ambos contratos.
  `skopos query` gana filtro opcional `--proyecto`.

### 3.2 C-8 · Superficie de mutación o retención (ADR nuevo, 🔒)

- **Re-justificación obligatoria.** El argumento de P-001 ("la vigencia
  consolidada se pudre") hablaba de consolidar AN-KLA — superada. En el
  mundo multi-CLI, el ADR se justifica por: análisis malos petrificados
  (no determinismo de Ollama sin reanálisis posible), redacciones
  mejorables (patrones de secretos nuevos), sellado retroactivo de
  orígenes (C-6 opción 4), retención/privacidad (rutas absolutas del
  usuario persistidas — riesgo ya declarado en README).
- **Tres alternativas, no dos:** (1) política de retención (TTL/borrado
  por antigüedad), (2) **supersede blanda** — insertar una versión nueva
  y marcar la vieja (`reemplazado_por`); la lectura filtra las
  reemplazadas; conserva auditoría y **mantiene el insert-only**;
  (3) mutación plena (`update`/`delete`). 🔒 la elección es del dueño; el
  agente prepara el ADR con las tres.
- **Dependencia explícita con C-6:** la opción 4 de C-6 aplicada a
  documentos existentes requiere la superficie que aquí se decida.

### 3.3 C-10 · Cursor de ingesta, desempaquetado en tres decisiones

- **(a) Decisión 8 — política de arranque (🔒), sin ADR nuevo.** Un
  filtro por mtime en el arranque ("desde ahora" por defecto, `--backfill`
  opt-in) no es un cursor persistente: ADR-005 queda intacto (la dedup
  sigue viviendo en Mongo). El agente prepara la decisión con esta
  opción concreta; el dueño elige.
- **(b) ADR de lectura incremental — extensión, no reversión.** El propio
  ADR-005 pre-registró el camino ("si el volumen… ese es un ADR nuevo
  sobre lectura incremental"). Encuadre propuesto: el cursor es una
  **caché inofensiva** — su desync peor caso es reprocesar archivos, que
  la dedup autoritativa en Mongo absorbe. Disuelve la objeción de
  "segunda fuente de verdad" que motivó el ADR original. 🔒 aceptación
  del dueño.
- **(c) Backfill por pilotos, no binario.** No hace falta decidir
  40–100 h (snapshot 2026-08-19) de una vez: el primer piloto es una
  sesión y sirve a C-5 (§3.5). Cada piloto mide y publica su propio
  snapshot fechado.

### 3.4 C-6 · `fragmento_completo` — cinco palancas (🔒)

Las cuatro del encargo más la que falta:

1. Servir crudo (status quo; `cli.py:20-27`, `cli.py:38-41`).
2. Redactar en la salida.
3. Marcar como no-instrucción en el contrato del CLI — **declarativa**:
   Skopos sólo puede declararla, no exigirla; que conste así en la
   decisión.
4. Persistir el fragmento o sellar el origen (hash+tamaño). Notas: la
   variante retroactiva requiere C-8; si gana, el ADR incluye estimación
   de tamaño fechada (los fragmentos son fracción del corpus de 2.1 GB,
   snapshot 2026-08-19).
5. **Presupuesto/límite en `skopos query`** — transversal a las
   anteriores: hoy no hay `limit` ni tope de fragmento
   (`almacenamiento.py:79-82`) y P-001 §4.5 identificó la recuperación
   sin tope como **motor del eco**, no sólo víctima.

Las palancas no son excluyentes: (5) puede combinarse con cualquiera de
(1)–(4). 🔒 el dueño elige la combinación.

### 3.5 C-5 · Detector de eco sobre corpus poblado (piloto)

Hoy la colección tiene 0 documentos: ejecutar el detector "al final" sin
más produciría cero por construcción. Pasos:

1. Requiere C-10(a) cerrada (el piloto ES backfill).
2. Piloto: backfill de **una sesión** (~28 turnos ≈ 10 min al ritmo
   medido de 19.6 s/turno, snapshot 2026-08-19).
3. Ejecutar el detector corregido de P-001 §4.5 (regex sobre `resumen`).
4. Reporte fechado con la **composición del corpus declarada**: qué
   fracción de los turnos piloto son conversaciones *sobre* Skopos
   (incluido este ciclo) — sin eso, el sesgo auto-referencial contamina
   la lectura del número.

### 3.6 Ensayo escrubery (paralelo a 3.1–3.5, independiente)

Ejecutar contra el repo real (`/Users/krisnova/www/aria/escrubery`) con
`escrubery_script` explícito, como está implementado y nunca ejercitado
(REQ-10; ADR-004: opcional, nunca bloqueante). El ensayo registra:

- resultado funcional (ficha / sin ficha / fallo tolerado),
- latencia por llamada,
- y el hallazgo de diseño: hoy se consulta **un subprocess por turno**
  (`analisis.py:194-197`) cuando la ficha no cambia por turno — la
  memoización por CLI queda como recomendación del ensayo, no se
  implementa en el ensayo.

Límite del encargo original sin cambio: escrubery aporta la verdad
versionada del CLI; los parsers los escribe Skopos.

### 3.7 Contrato de parser por CLI (gateado)

Sólo con 3.1–3.5 cerrados: ADR nuevo + SPEC nueva por la frontera nueva
(`detectar formato → turnos normalizados`), Codex como adaptador de
referencia, indexado por `(cli, versión)` vía fichas de escrubery. El
diseño debe decidir, por CLI, de dónde salen `proyecto` y `cli` — la
trampa de fuente de verdad de §3.1, generalizada a la familia.

## 4. Dependencias y paralelismo

```text
Acto 0 (confirmación 🔒)
  └─> C-9 (§3.1) ──> C-8 (§3.2) 🔒 ──> C-6 (§3.4) 🔒   [secuenciales:
        legacy de C-9 se cierra con C-8; opción 4 retroactiva de C-6
        requiere C-8]
  └─> C-10(a) (§3.3) 🔒 ──> C-5 piloto (§3.5)
  └─> escrubery (§3.6)          [paralelo, independiente]
  └─> parser contract (§3.7)    [gateado: C-9..C-5 cerrados]
      C-10(b) ADR lectura incremental (§3.3) [cuando la evidencia lo pida]
```

## 5. Decisiones 🔒 del dueño (consolidadas)

1. Confirmación multi-CLI en este canal (Acto 0, §2).
2. C-8: retención / supersede blanda / mutación plena (§3.2).
3. Decisión 8: "desde ahora" por defecto vs backfill opt-in (§3.3a).
4. ADR lectura incremental: aceptación como extensión de ADR-005 (§3.3b).
5. C-6: combinación de palancas (§3.4).

## 6. Fuera de alcance (sin cambio respecto del encargo)

- Reabrir o rediseñar P-001 (superada; sólo la línea de estado de §2).
- Integración con AN-KLA en cualquier dirección.
- Búsqueda semántica/embeddings (sigue como evaluación pendiente).
- Cambios fuera de `/Users/krisnova/www/aria/skopos`.

## 7. Reglas de verificación por ítem

Métricas siempre fechadas como snapshot (regla X-2). Cada ítem de código
se declara terminado sólo con: `python3 -m unittest discover -s tests` en
verde, diff leído completo, y specs/contratos/implementación/tests
consistentes entre sí. Sin dependencias nuevas sin autorización explícita.

## 8. Evidencia

```text
EV-1: turn_context trae cwd y workspace_roots por turno | muestreo de un
rollout real en ~/.codex/sessions (2026-08-20): payload con turn_id, cwd,
workspace_roots, approval_policy, etc.
EV-2: índices actuales | almacenamiento.py:106-107 — turn_id único y $text
sobre tema+resumen; sin índice de proyecto/cli/ocurrido_en
EV-3: búsqueda sin límite | almacenamiento.py:79-82 — find sin limit
EV-4: hardcode duplicado del CLI | captura.py:18 (CLI_ORIGEN) y
analisis.py:172 (escrubery_cli="codex-cli" por defecto)
EV-5: métricas de volumen y ritmo | P-001 §4.9 y README — 609 rollouts /
2.1 GB / intervalo 5 s / 19.6 s/turno / backfill 40–100 h — todas
snapshot 2026-08-19
EV-6: colección analisis con 0 documentos | P-001 §9 (2026-08-19); el
detector de C-5 no puede correr sin poblarla
```
