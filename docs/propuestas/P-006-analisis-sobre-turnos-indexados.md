# P-006: análisis sobre turnos ya indexados (y el ancla curada)

Estado: **propuesta — no decidida. Insumo para rondas de consenso y
adversariales.** No implementa nada: pide decisiones (§7) y registra
evidencia medida hoy (§1).
Fecha: 2026-09-12.
Origen: sesión del 2026-09-12 con el dueño. Análisis de estado del
proyecto que destapó un hueco no registrado (§2) y una reformulación de
P-005 propuesta por el dueño: **syndesmos como contrato, no como
proyecto** (§5).
Relación: destraba P-005, que hoy no puede decidirse porque no puede
fallar ni acertar.

## 1. Evidencia de la sesión (todo medido hoy, nada especulado)

| Medida | Valor | Fuente |
|---|---|---|
| Suite de tests | 253 en verde, 34.7 s | `unittest discover` |
| Gate de Skevi (ADR-015) | verde — 120 archivos en límites; planes fail-closed | `check_sizes` + `check_plans` |
| Turnos indexados (antes de la sesión) | 23,041 | Mongo |
| Documentos en `skopos.analisis` | **8**, el último del 2026-08-22 | Mongo |
| Vigilante | **caído**; último turno indexado 2026-09-07T21:49Z (5 días de cola) | `pgrep` + Mongo |
| Cola recuperada en esta sesión | 1,542 turnos codex + 449 claude-code | `skopos indexar` |
| Turnos indexados (después) | **25,032** | Mongo |
| Anclas `commit-write-plan` | **560** (eran 448 el 2026-09-06 — el corpus crece) | regex sobre `texto_usuario`/`texto_agente` |
| Anclas por CLI | codex-cli 400, opencode 115, claude-code 45 | Mongo |
| Anclas por proyecto | an-kla-memory 82, argos 64, pinax 63, kratos 47, eduEMD 45, … | Mongo |
| Costo de interpretación | ~19.6 s/turno con `qwen3:8b` → 560 ≈ **3.0 h serial** | README + ADR-014 |

## 2. El hueco: los turnos indexados son inalcanzables para el análisis

Hoy **no existe camino para analizar un turno que ya está en el
índice**. Verificado sobre la superficie de comandos real:

- `indexar` no llama al modelo — por diseño (P-004).
- `watch` analiza sólo lo nuevo y dentro de su ventana (ADR-008).
- `reanalizar` hace **supersede** de un análisis existente (ADR-007):
  necesita que ya haya uno, no crea el primero.

Consecuencia: 25,032 turnos observados y 8 interpretados. `skopos
query` —SPEC-004, la razón de ser declarada del proyecto— no tiene qué
servir. **Esto no es un defecto de implementación: es una consecuencia
no escrita de haber separado índice y análisis en el hito 18.** La
separación fue correcta (indexar es barato y evita perder conversación;
analizar es caro). Lo que falta es la puerta entre las dos mitades.

Nadie lo registró porque cada decisión aislada fue buena. El estado
agregado es el que no se revisó.

## 3. Qué propone

Un comando que **seleccione turnos del índice y los mande al análisis**,
sin tocar la política de `watch` ni la de `reanalizar`.

Forma de trabajo (nombre tentativo `skopos analizar`):

```
skopos analizar [--proyecto P] [--cli C] [--ancla PATRON]
                [--desde FECHA] [--hasta FECHA] [--limite N] [--dry-run]
```

- Selecciona sobre `skopos.turnos` por los ejes que ya existen
  (`proyecto`, `cli`, `ocurrido_en` — C-9, hito 13).
- Para cada turno seleccionado **sin análisis previo**, corre la misma
  ruta de análisis que el orquestador y guarda en `skopos.analisis`.
- Un turno que ya tiene análisis **no se toca**: eso es territorio de
  `reanalizar` y de ADR-007. Sin ambigüedad de autoridad.
- `--dry-run` cuenta y estima el costo antes de comprometer horas de
  GPU, igual que hace `indexar`.

## 4. Por qué el primer corpus son las anclas curadas

Los 560 turnos con `commit-write-plan` son **turnos en los que alguien
se detuvo y decidió deliberadamente que eso merecía preservarse**. Es un
conjunto curado que ya existe y no costó etiquetar: el ~2 % del corpus,
marcado por intención humana real, sin coste de anotación.

Esa es la diferencia con "analizar los 25,032": 3 horas locales contra
semanas, y el subconjunto con la mayor densidad de señal por turno.

Se propone llamarlo **ancla curada**: *un turno que lleva evidencia de
preservación deliberada*. Hoy la evidencia es un patrón de escritura a
AN-KLA; la definición **no debe atarse a ese patrón ni a AN-KLA** (§6).

## 5. Relación con P-005: el contrato va después de la primera instancia

El dueño propuso reformular syndesmos como **contrato publicado** en vez
de tercer proyecto. La propuesta es correcta y el proyecto tiene el
precedente: ADR-010 convirtió "un parser por CLI" en `parser-contrato/v1`
y hoy sostiene 5 adaptadores; el manifiesto publica 8 contratos. Un
contrato no tiene uptime, ni almacén, ni proceso que se caiga un martes
—como acaba de pasar con `watch`, descubierto 5 días tarde (§1)— y si
nadie lo implementa, el costo hundido es un documento.

**Pero ADR-010 no se escribió antes de tener un parser vivo.** Se
aceptó después de cerrar C-9..C-5, con los ejes puestos, el fragmento
sellado y un corpus piloto ya ingestado: **generalizó algo que ya
funcionaba una vez**. Esa es la regla que el proyecto sigue de hecho.

Hoy `skopos.analisis` tiene 8 documentos: nadie ha visto la capa
interpretada funcionar un solo día. Escribir `bloque-de-contexto/v1`
ahora sería congelar la forma de algo sin experiencia operativa — v1
nacería para ser superseded.

Por eso se propone partir el contrato en dos mitades de madurez distinta:

| Contrato | Madurez | Cuándo |
|---|---|---|
| `skopos/ancla-curada/v1` — qué hace que un mensaje sea ancla, y qué se publica de él | semántica casi asentada; la evidencia está medida (§1) | puede escribirse con lo que hay |
| `skopos/bloque-de-contexto/v1` — presupuesto, frescura, referencia viva, redacción, qué pasa cuando la fuente cambió debajo | **sin experiencia operativa** | después de que este comando corra y se use |

Riesgo honesto de la vía contractual: **un contrato sin consumidor de
referencia es un monólogo.** Exige que AN-KLA (u otro) acepte
consumirlo — decisión de la contraparte. P-005 como proyecto tenía la
virtud inversa: arranca unilateralmente, pero se mantiene para siempre.

## 6. Restricción de diseño: la ampliación de skopos ya anunciada

El dueño anunció en esta misma sesión que **skopos se ampliará para
almacenar conversaciones de cualquier origen**, no sólo CLIs oficiales:
prime, agentes en runtimes/sandboxes, y otros que no dejan rollout en
disco. Eso merece su propio análisis y **no se diseña aquí**.

Pero impone una restricción que es gratis ahora y cara después:

- `ancla-curada` se define sobre **un mensaje o turno observado**, no
  sobre un rollout de CLI. Nada en el contrato puede presuponer
  archivo, offsets ni `cli_producto`.
- El localizador de origen ya tiene los dos casos resueltos —archivo
  con offsets (ADR-009) y filas (ADR-012)— y el campo `origen_tipo` ya
  existe en el documento. Un tercer tipo de origen debe caber sin
  romper el contrato.
- La evidencia de "preservación deliberada" debe poder venir de otra
  señal que no sea un patrón de texto de AN-KLA.

Si `ancla-curada` nace atada a CLIs, la ampliación la supersedará antes
de usarla.

## 7. Preguntas para las rondas (decisión del dueño)

1. ¿Se autoriza el comando nuevo (`skopos analizar` o el nombre que se
   decida)? Es superficie de CLI nueva: contrato `cli-skopos-analizar v1`
   a publicar en el manifiesto.
2. ¿Confirma la regla "no toca turnos con análisis previo", dejando el
   supersede como territorio exclusivo de `reanalizar` (ADR-007)?
3. ¿El primer corpus son las 560 anclas `commit-write-plan`, o se
   amplía a `plan-write` (587) desde el arranque?
4. ¿Se corre en local con `qwen3:8b` (~3 h, nada sale de la máquina) o
   se decreta proveedor remoto vía ADR-014? **Recomendado: local.**
5. ¿`ancla-curada` se escribe como contrato en esta ronda, o se espera
   a tener las 560 interpretadas y se escribe describiendo lo que se
   vio? (recomendado: escribirlo **después**, por §5).
6. ¿Se registra ADR para la puerta índice→análisis? Toca un supuesto de
   ADR-008 (el análisis ocurre sólo en la ventana del vigilante), y ese
   supuesto quedaría explícitamente acotado a `watch`.

## 8. Relación con decisiones cerradas

- **No contradice ADR-008**: `watch` conserva su política de arranque
  intacta. Este comando es una ruta manual y explícita, fuera de la
  ventana — lo que sí exige es escribir que la ventana gobierna a
  `watch`, no al análisis en general (§7.6).
- **No contradice ADR-007**: el supersede sigue siendo de `reanalizar`.
  Aquí sólo se crea el primer análisis de un turno que no tiene ninguno.
- **No contradice P-004**: `indexar` sigue sin llamar al modelo. La
  separación índice/análisis se mantiene; se le agrega una puerta.
- **Usa C-9 (hito 13)**: la selección se apoya en los ejes `proyecto`,
  `cli` e `ocurrido_en` y sus índices, ya existentes.
- **Destraba P-005**: le da la primera instancia viva que el contrato
  necesita generalizar, y convierte su decisión en un experimento con
  resultado — incluido el resultado nulo, que también cierra.
