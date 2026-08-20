# P-001 v4: integración Skopos ↔ AN-KLA por cobertura de observación

Estado: **propuesta — no decidida. Insumo para rondas de consenso y
adversariales entre varios modelos.**
Fecha: 2026-08-19
Revisión: v4 — v3 sometida a ronda adversarial **independiente, con
contexto fresco** (§11). Cuatro BLOCKER. La tesis central de v2/v3 cayó.
Autoría: v1–v3 y §10 por Claude Opus 5 (mismo contexto, autocrítica).
§11 por un revisor independiente con contexto fresco.

> El eje de esta propuesta cambió en v4. v2 y v3 sostenían un reparto
> **corto plazo / largo plazo**. La ronda independiente mostró, contra
> código, que ese no es el eje: el eje real es **observable / no
> observable**. Ver §2.

## 1. Historial de correcciones

Se conserva completo a propósito: para rondas entre modelos, saber *cómo*
falló un análisis vale tanto como su conclusión.

**v1 → v2.** v1 recomendaba promoción manual Skopos → AN-KLA con firma
humana por registro. Retirada: esta es memoria de agentes para agentes.

**v2 → v3.** Autocrítica (§10). Dos BLOCKER contra la tesis de v2 de que
"la consolidación es el `decay` que le falta a AN-KLA".

**v3 → v4.** Ronda independiente (§11). Lo que cayó:

| Afirmación de v3 | Veredicto |
|---|---|
| "AN-KLA no puede olvidar"; `decay` es la única operación sin implementar | **Falsa.** `refute` está implementado y gobernado (§3) |
| El eje es corto plazo / largo plazo | **Eje equivocado.** Es cobertura de observación (§2) |
| La "señal de curaduría" justifica la integración | **No construible.** No existe clave de join (§2.2) |
| Skopos es "el destino mutable y barato" | **Falsa.** Skopos es insert-only; AN-KLA es el más mutable (§4.2) |
| Detector de C-5 sobre `fragmento_completo` | **Roto.** Ese campo no existe en Mongo (§4.5) |
| C-6 mitigado: "sólo summary redactado cruza" | **Falsa, y la severidad sube** (§4.4) |
| H-3: la prueba de amputación descarta reemplazar Mongo | **Mal aplicada** (§4.6) |
| §5: "falta implementar `decay`" | **Contra un ADR.** Rechazado deliberadamente (§3.2) |

Sobrevivieron: C-4 (presupuesto), C-7 (concurrencia), A-1 (prohibición de
`supersede` para `derived_from_retrieval`), y la conclusión "ordenar
Skopos antes de conectar" — aunque **la lista de qué ordenar era
equivocada** (§5).

## 2. El eje correcto: cobertura de observación

### 2.1 Skopos sólo puede ver Codex

Verificado: `vigilante.py:27` (`~/.codex/sessions`), `captura.py:18`
(`CLI_ORIGEN = "codex-cli"`), `captura.py:61-88` (el parser depende del
esquema propietario de Codex: `response_item`, `payload.type=="message"`,
cierre por `event_msg/task_complete`).

Este proyecto se evalúa con **rondas de varios modelos**. Para todos los
que no son Codex, Skopos ve **cero**. No hay rollout crudo que leer.

Eso invalida la premisa de la pregunta que v3 designó como sostén de todo
("¿qué gana Skopos observando AN-KLA, si ya lee el rollout crudo?") y da
la respuesta que v3 buscaba sin encontrar:

> **Lo que Skopos gana observando AN-KLA es cobertura de los agentes que
> estructuralmente no puede observar.**

Esa justificación no depende de ningún campo nuevo, sobrevive al ataque
de "ya tengo el rollout", y es independiente del horizonte temporal.

### 2.2 Por qué la "señal de curaduría" no servía

v3 propuso que el valor era saber *qué turnos produjeron hechos que un
agente juzgó durables*. No es construible hoy:

- No hay clave de join. `grep -rn "turn_id|rollout|session_id|codex"` en
  `an_kla/` y `docs/schemas/` → cero.
- `lineage.refs` admite `kind ∈ {artifact, event, fact, episode,
  revision, external}` con `id` libre: nada obliga ni valida un `turn_id`.
- `subject_ref` está ligado a identidad de proyecto, sin eje de turno.
- AN-KLA **no registra autoría** (`README:338`: "no prueba identidad,
  autoría ni verdad"). "Un agente lo juzgó durable" no resuelve a *cuál*.

Construirla exigiría un campo nuevo obligatorio escrito por el agente en
cada write — la misma disciplina por-registro por la que se retiró v1.

### 2.3 El reparto que reemplaza al de v2/v3

- **Skopos = observador de un CLI concreto (Codex).** Su valor
  irreemplazable no es el horizonte temporal: es que ve lo que un agente
  hizo **sin que el agente decida escribirlo**.
- **AN-KLA = memoria escrita deliberadamente por cualquier agente,** con
  gobierno, traza, vigencia y olvido gobernado.

Son ortogonales al tiempo. Ambos pueden ser de corto o de largo plazo; lo
que los distingue es **quién decide que algo entre**.

## 3. Qué puede y qué no puede olvidar AN-KLA

### 3.1 Corrección: sí puede olvidar, en dos niveles

**v2 y v3 afirmaron que AN-KLA no puede olvidar. Es falso.** El error de
método: leí el contrato *para agentes* (`context_text.py:261`, "en esta
beta usa `add` y `supersede`") y concluí algo sobre *el sistema*.
`refute` vive en un subsistema separado.

Verificado:

- `an_kla/refute_policy.py:22-46` — perfil `refute-policy/v1`,
  `supported_operations: ["refute"]`, `resolver_required: True`.
- `docs/architecture/0026-governed-refute-v1.md:1-5` — **"Aceptada e
  implementada localmente… rondas pre-code e implementación cerradas en
  `proceed`"**.
- CLI real: `an_kla/__main__.py:235-247` (`refute plan|commit|inspect`).
- Efecto: `retrieval.py:161` excluye como `inactive` todo `status` fuera
  de `{vigente, active, None}`.

`refute` es **1:0**: saca el target de `retrieve` **sin escribir un
sucesor vigente**. Es exactamente la reducción de cardinalidad que A-2
(§10) declaró inexistente. Y `compact` (ADR-0028) borra físicamente.

### 3.2 Lo que realmente falta, y por qué no es un defecto

El vacío no es "no hay olvido". Es **no hay olvido automático por
antigüedad o desuso**, y eso fue **rechazado por ADR**, no omitido:

> "`decay` como operación gobernada o job en background: la evidencia de
> ADRC es que los mecanismos que requieren actor externo no corren nunca.
> Decay como scoring queda como investigación futura; **decay como
> mutación contradice la inmutabilidad CAS**."
> — `docs/architecture/0021-verified-at-freshness-v1.md:249-253`

v3 recomendaba "implementar `decay`, sigue haciendo falta". Eso
contradice una decisión registrada con razón arquitectónica. La
formulación correcta es **política de retención sobre `refute` + `compact`**,
no una operación nueva.

### 3.3 Consecuencia para la integración

La integración **ya no se justifica como sustituto del olvido**. AN-KLA
no la necesita para cumplir su rol. Se justifica sólo por cobertura
(§2.1). Es una justificación más débil que la de v2/v3, pero verdadera.

Nota semántica: consolidar y luego `refute` del original **no** es
legítimo. Las razones válidas de `refute` son
`evidence_contradicts_record | source_retracted | integrity_violation`;
"ya lo copié a otro lado" no es ninguna. El impedimento es de
**semántica**, no de inexistencia — v3 afirmaba inexistencia.

## 4. Análisis crítico como agente consumidor

### 4.1 C-4 (importante, intacto) — sin presupuesto no hay recuperación utilizable

AN-KLA recupera bajo presupuesto de bytes y devuelve `excluded_detail.ids`
con motivo (`retrieval.py:144-219`). Skopos devuelve documentos
completos, sin presupuesto y **sin `limit`** (`almacenamiento.py:79-82`).

Mi contexto es finito. Lo que más importa no es el recorte sino saber
**qué quedó fuera**: sin eso no distingo "no hay más" de "no cupo".

Único hallazgo del documento que sobrevivió las dos rondas sin una sola
objeción.

### 4.2 C-8 (crítico, nuevo) — Skopos no tiene superficie de mutación

`grep -rn "update_one|delete_one|replace_one|update_many" src/` → **cero**.
`almacenamiento.py` expone `insert_one`, `find`, `find_one`,
`coleccion_local`. Hay índice único en `turn_id` y `existe_turn_id` corta
antes de analizar (`orquestador.py:51-57`).

**Skopos es insert-only, primer-análisis-gana, irreversible.**

Tres consecuencias:

1. **La asimetría de costos de v2 no existe.** v2 corrigió la dirección
   del flujo argumentando "automatiza hacia el destino mutable y barato".
   No hay tal destino: ambos son append-only, y AN-KLA es *el más
   mutable* — tiene `supersede`, `refute` y `compact` gobernados.
   La dirección AN-KLA → Skopos sigue siendo correcta, pero **por
   cobertura (§2), no por mutabilidad**.
2. **La vigencia consolidada se pudre.** Un `fact` consolidado como
   `vigente` y refutado después queda en Skopos afirmando `vigente` para
   siempre. Es exactamente el peor modo de fallo que C-2 identificaba, y
   la corrección de v3 no lo evitaba.
3. **El no determinismo de Ollama queda petrificado.** Un turno mal
   analizado no se puede reanalizar nunca.

### 4.3 C-9 (crítico, nuevo) — Skopos no tiene eje de proyecto

`vigilante.py:31-34` recorre `rglob("*.jsonl")` sobre `~/.codex/sessions`:
**toda sesión de Codex de la máquina**, sin filtro por repo ni proyecto.
El documento persistido no tiene campo de proyecto
(`almacenamiento.py:26-47`). `session_id` es `path.stem`
(`captura.py:94`) — el nombre del archivo, no una identidad estable.

Del otro lado, cada memoria AN-KLA es **por proyecto** y `subject_ref`
deriva del digest de identidad del proyecto.

- Consolidar N memorias AN-KLA en un Mongo sin campo de proyecto **funde
  los namespaces**, y sin mutación (C-8) no hay reparación posible.
- `skopos query` ya devuelve hoy turnos de cualquier proyecto de la
  máquina, sin forma de acotarlo.

Esto responde la pregunta 5 de v3: no era una pregunta abierta, era un
defecto verificable.

### 4.4 C-6 (crítico — severidad SUBE en v4) — `fragmento_completo` se sirve crudo

v3 afirmó: "sólo `summary` redactado cruza… la evidencia cruda queda
auditable en Mongo sin entrar al circuito de recuperación". **Dos errores
en una frase.**

1. **La evidencia cruda no está en Mongo.** Está en
   `~/.codex/sessions/*.jsonl`, referenciada por ruta absoluta + offsets.
   Si Codex rota o borra ese archivo, `_fragmento_completo` devuelve
   `None` **en silencio** (`cli.py:25-26`), indistinguible de "no hay
   fragmento".
2. **Sí entra al circuito de recuperación, crudo.** `cli.py:38-40` lo
   incluye en cada resultado de `skopos query`. `_redactar_secretos`
   sólo toca `tema`, `resumen` y `entidades` (`analisis.py:190-191, 203`).
   El propio README lo dice (`README.md:131-133`): "siempre expone el
   texto original sin redactar, por diseño".

v3 confundió **"no se persiste en AN-KLA"** (H-2, cierto) con **"no se
entrega al agente"** (falso). El texto hostil que sobrevivió la ronda del
2026-08-13 no llega atenuado: llega **íntegro y sin redactar** a la
salida de `skopos query`, que es el canal por el que un agente consume
esta memoria.

C-6 no es "heredado y mitigado". Es un **hallazgo abierto**, y hay que
decidir si `fragmento_completo` se sirve, se redacta, o se marca como
no-instrucción en el contrato del CLI.

### 4.5 C-5 (hipótesis, detector corregido) — contaminación por eco

**El detector de v3 estaba roto:** consultaba `fragmento_completo` como
si fuera un campo de Mongo. No lo es (§4.4). Habría devuelto 0 siempre —
una falsificación falsa que archivaba la hipótesis por un artefacto de
esquema.

Detector corregido, sobre un campo que sí se persiste:

```python
col.count_documents({"resumen": {
    "$regex": r'"resumen"\s*:|"tema"\s*:|skopos query', "$options": "i"}})
```

Sigue sin ejecutarse contra datos: la colección `analisis` tiene 0
documentos. **Ejecutar esto antes de que nadie vuelva a discutir C-5.**

Agravante nuevo (§11): `skopos query` devuelve `fragmento_completo`
íntegro y sin `limit`. Cada consulta vuelca turnos enteros al rollout del
consultante, que Skopos reingerirá como observación fresca. **La
recuperación de Skopos es el motor del eco, no sólo su víctima.**

### 4.6 H-3 retirado — la prueba de amputación estaba mal aplicada

La prueba (`an-kla-memory/README.md:92-96`) decide **qué contenido
pertenece a la memoria del agente** vs. qué es estado del producto. No es
un criterio de elección de backend. v1 la usó para descartar "AN-KLA
reemplaza a Mongo" — error de categoría.

Aplicada bien: si el Mongo de Skopos desaparece, ningún producto deja de
funcionar. Por la lógica literal de la prueba, el contenido de Skopos
**es** memoria legítima de agente.

La coexistencia de ambos almacenamientos sigue siendo correcta, pero por
volumen, costo de escritura gobernada y cobertura — **no por H-3**.
Un hallazgo declarado "superviviente" sobre una prueba mal aplicada no
era un superviviente.

### 4.7 C-7 (crítico, intacto y agravado) — concurrencia entre varios modelos

AN-KLA declara "una sola memoria activa" y "el lock de escritura es local
y no coordina varias máquinas" (`README:336-337`). Cada commit mueve
`CURRENT`; un plan contra revisión vieja falla con
`write_plan_base_changed`.

Con varios modelos escribiendo: en una máquina serializan y cada commit
invalida los planes en vuelo → tormenta de replanificación con riesgo de
inanición para el más lento. Entre máquinas, no hay exclusión mutua.

**Agravante de §11:** AN-KLA tampoco registra autoría (`README:338`), así
que en una memoria compartida por un panel no se puede saber qué modelo
escribió qué. Toda esta propuesta, en sus cuatro revisiones, asumió **un
agente escritor**.

### 4.8 C-3 (importante, degradado dos veces)

`$text` es coincidencia por palabra. v2 lo declaró bloqueante; §10 lo
degradó (AN-KLA también es léxico: `sqlite-fts5/v1`, `index.py:18`); §11
mostró que el argumento de reemplazo también falla en parte: lo indexado
en Skopos es `tema`+`resumen`, **ambos generados por `qwen3:8b`**, nunca
texto humano. En vocabulario, el corpus recuperable de Skopos es *más*
homogéneo que el de AN-KLA.

Queda en pie por **tamaño y ventana temporal**, no por heterogeneidad de
vocabulario. Uno de los tres apoyos era falso.

### 4.9 C-10 (crítico, nuevo) — el vigilante ya no cierra su ciclo

Medido en el entorno real por la ronda independiente: **609 rollouts,
2.1 GB** en `~/.codex/sessions`. `vigilante.py:46-47` reparsea **todos**
los archivos en cada barrido, por diseño explícito (`vigilante.py:8-10`:
"la deduplicación entre ciclos vive en Mongo, no en un cursor local"). El
intervalo por defecto es **5 s** (`vigilante.py:28`).

~8 s de parseo por ciclo, antes de contar del orden de 10⁴
`existe_turn_id` por barrido. **Ya está por encima de su presupuesto con
la colección vacía.** El corpus crece monótonamente; el ciclo también.

Backfill: ~19.6 s/turno medidos × ~8k–19k turnos = **40–100 horas** de
Ollama serializado.

Ninguna de las cuatro revisiones preguntó por el costo de **ingesta**.
Razoné sobre el costo de recuperación (C-3, C-4) e ignoré el que ya está
roto y es medible.

## 5. Precondiciones, en orden

v3 decía "ordenar Skopos antes de conectar" — correcto — pero su lista
era equivocada. La lista real, de la ronda independiente, **y las tres
primeras no involucran a AN-KLA en absoluto**:

1. **Eje de proyecto** en el documento de Mongo (C-9). Sin él, consolidar
   funde namespaces de forma irreversible.
2. **Superficie de mutación** o retención (C-8). Sin ella, la vigencia
   consolidada se pudre sin reparación.
3. **Cursor de ingesta** (C-10). Hoy el vigilante no se mantiene al día
   ni consigo mismo.
4. **Decidir qué pasa con `fragmento_completo`** en la recuperación
   (C-6): hoy es simultáneamente el vector de inyección y el motor del
   eco.
5. **Ejecutar el detector corregido de C-5** (§4.5) antes de discutir más
   la hipótesis.

Después de eso: transporte de vigencia, presupuesto (C-4) y embeddings
(C-3). **Ninguna de las cinco primeras es sobre la integración.**

## 6. Dirección del flujo

**AN-KLA → Skopos.** Se mantiene, pero la razón cambió: **cobertura**
(§2.1), no asimetría de mutabilidad (que no existe, C-8) ni sustitución
del olvido (que AN-KLA no necesita, §3).

Precondición técnica de A-1: leer el sustrato (cadena de
revisiones/segmentos), no `retrieve`, o resolver autoridad `tool_observed`
por adaptador Python.

**Skopos → AN-KLA: probablemente innecesaria.** Choca con H-1, H-2 y el
volumen contra un historial inmutable.

**Retirado en v4:** v3 argumentaba además que reinyectar fabricaría el
eco de C-5. Es inválido — el lazo del eco se cierra a través del rollout
en `~/.codex/sessions`, **no** a través de AN-KLA, y ocurre igual sin
integración. Y "consultar Skopos directamente" no evita el eco: lo
**maximiza** (§4.5).

## 7. Preguntas para la siguiente ronda

1. **¿Hay uno o varios agentes escritores?** (C-7.) Sigue sin
   responderse y sigue cambiando todo lo demás.
2. **¿Vale la cobertura?** (§2.1.) Si el panel de modelos no necesita que
   sus turnos queden observados, la integración sobra — y ahora es la
   *única* justificación en pie.
3. **¿Skopos debe dejar de ser sólo-Codex?** Alternativa que ninguna
   ronda evaluó: en vez de que Skopos observe AN-KLA, **que Skopos
   aprenda a parsear otros formatos de rollout**. Resuelve la cobertura
   sin integrar nada. Merece evaluarse antes que esta propuesta.
4. **¿Un `fact` refutado se consolida o se descarta?** Sostengo que se
   consolida marcado: saber que algo se creyó y dejó de creerse es
   memoria legítima.

## 8. Posición de esta ronda

La integración **sigue siendo defendible, con una justificación mucho más
estrecha que la de v2/v3**: cobertura de los agentes que Skopos no puede
observar. Todo lo demás que la sostenía —sustituir el olvido, la señal de
curaduría, la asimetría de mutabilidad— cayó contra el código.

Y la conclusión operativa se refuerza: **ordenar Skopos antes de
conectar**, donde "ordenar" son cinco precondiciones de las cuales las
tres primeras no tienen nada que ver con AN-KLA. Skopos hoy no tiene eje
de proyecto, no puede corregir un registro, no cierra su ciclo de
ingesta, y sirve texto crudo sin redactar a quien lo consulte.

Antes de integrar dos memorias conviene que una de las dos esté sana.

## 9. Fuentes

- Skopos (`@42b94a7`): `README.md:120-133`, `AGENTS.md`,
  `src/skopos/almacenamiento.py:26-47,65-107`, `src/skopos/cli.py:18-42`,
  `src/skopos/captura.py:18,61-94`, `src/skopos/vigilante.py:8-10,27-34`,
  `src/skopos/orquestador.py:51-57`, `src/skopos/analisis.py:186-203`,
  `docs/contratos/f1-contratos.md:35-60`, `docs/adr/ADR-006`.
  Corpus: colección `analisis` con 0 documentos; 609 rollouts / 2.1 GB en
  `~/.codex/sessions` al 2026-08-19.
- AN-KLA (`/Users/krisnova/www/an-kla-memory` @ `b70561e`):
  `an_kla/refute_policy.py:22-46`, `an_kla/write_policy.py:25,54,414-421`,
  `an_kla/retrieval.py:38,144-219`, `an_kla/index.py:18`,
  `an_kla/__main__.py:235-247`, `an_kla/context_text.py:220-262`,
  `README.md:92-96,336-338`,
  `docs/architecture/0007-write-policy-v1.md:75-115,205-215`,
  `docs/architecture/0021-verified-at-freshness-v1.md:249-253`,
  `docs/architecture/0026-governed-refute-v1.md:1-5`,
  `docs/architecture/0028-governed-compaction-v1.md:20-30`,
  `docs/schemas/write-proposal-v1.schema.json`.

## 10. Ronda adversarial sobre v2 — autocrítica (2026-08-19)

Método: mismo modelo, mismo contexto. **No cumple la convención del
proyecto** (contexto fresco en agente separado). Piso de calidad, no
ronda de hito.

| Id | Nivel | Hallazgo | Estado tras §11 |
|---|---|---|---|
| A-1 | BLOCKER | `derived_from_retrieval` no puede `supersede` (`write_policy.py:414-421`) | **en pie**, verificado literal |
| A-2 | BLOCKER | `supersede` es 1:1 y no reduce cardinalidad | **derrumbado**: `refute` sí lo hace (§3.1) |
| A-4 | CRÍTICO | Concurrencia entre varios escritores no soportada | **en pie y agravado** (C-7) |
| A-3 | ALTO | C-3 probaba demasiado: AN-KLA también es léxico | en pie; §11 encontró un segundo error en la corrección |
| A-5 | MEDIO | C-2 era error de categoría | en pie, pero insuficiente (C-8) |
| A-6 | MEDIO | C-5 sin evidencia | en pie; **el detector propuesto estaba roto** (§4.5) |

Lección de método: esta ronda encontró errores reales pero **compartió el
punto ciego del documento** — leyó las mismas fuentes con el mismo sesgo.
Ninguno de los cuatro BLOCKER de §11 salió de aquí.

## 11. Ronda adversarial independiente, contexto fresco (2026-08-19)

Método: revisor independiente, sin acceso al razonamiento previo,
instruido para refutar y para verificar cada cita contra el código.
Duración ~7 min, 28 usos de herramienta. Ejecutó mediciones propias
(muestreo de parseo sobre el corpus real, conteo en Mongo vía `mongosh`).

| Id | Nivel | Hallazgo | Efecto en v4 |
|---|---|---|---|
| B-1 | BLOCKER | El detector de C-5 consulta `fragmento_completo`, que no es campo de Mongo. Devuelve 0 siempre. | §4.5, detector reescrito |
| B-2 | BLOCKER | `refute` está implementado, gobernado, con CLI, y es 1:0. "AN-KLA no puede olvidar" es falso. | §3 reescrito; A-2 derrumbado |
| B-3 | BLOCKER | No existe clave de join entre AN-KLA y Skopos. La señal de curaduría no es construible. | §2.2 |
| B-4 | BLOCKER | Skopos sólo parsea Codex. La premisa "ya lee el rollout crudo" es falsa. | §2.1, reencuadre completo |
| B-5 | CRÍTICO | `fragmento_completo` se sirve crudo y sin redactar en `skopos query`. | §4.4, severidad sube |
| B-6 | CRÍTICO | Skopos es insert-only: la asimetría de costos de v2 no existe. | §4.2 |
| B-7 | CRÍTICO | El vigilante reparsea 2.1 GB por ciclo con intervalo de 5 s. Backfill: 40–100 h. | §4.9 |
| B-8 | ALTO | Skopos no tiene eje de proyecto; recorre todas las sesiones de la máquina. | §4.3 |
| B-9 | ALTO | La prueba de amputación (H-3) estaba mal aplicada. | §4.6, H-3 retirado |
| B-10 | ALTO | El argumento del eco en §6 es inválido: el lazo no pasa por AN-KLA. | §6 |
| B-11 | MEDIO | Cita incompleta de `context_text.py`; explica el error de B-2. | §3.1 |
| B-12 | MEDIO | C-3: lo indexado en Skopos lo genera `qwen3:8b`, no humanos. | §4.8 |

**Lo que esta ronda validó sin objeción:** C-4 (presupuesto), C-7
(concurrencia), A-1.

**Lo que ninguna ronda ha hecho todavía:** ejecutar el detector de C-5
contra un corpus poblado; y responder la pregunta 3 de §7 —si Skopos
debería simplemente aprender a parsear otros CLIs, la integración entera
podría ser innecesaria.
