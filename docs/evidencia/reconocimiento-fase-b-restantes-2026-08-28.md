# Evidencia · los tres CLIs que quedan de la fase B no caben en el contrato tal como está

**Fecha:** 2026-08-28. **Estado: BLOQUEADO a decisión del dueño** — no se
escribió adaptador para ninguno. **Motivo:** ninguno de los tres guarda
la conversación como *un evento por línea en un archivo estable*, que es
el supuesto sobre el que descansan ADR-010 §5 (offsets de bytes, sello
P4a sobre el archivo original, instantánea materializada) y ADR-011
(cursor por digest de prefijo).

De los cinco CLIs del mapa, **dos caben y están hechos** (codex-cli,
claude-code). Los otros tres exigen decidir antes de codificar.

## opencode — SQLite, no archivos

`~/.local/share/opencode/opencode.db`, **4.4 GB**, más `-wal` y `-shm`
vivos. Esquema (leído en modo `ro`): `session` (753 secuencias),
`message` **52,705 filas**, `part` **227,712 filas**, `project` 34,
`event` 737,118. La conversación está en columnas `data`, no en líneas.

**Con qué choca:**
- **ADR-010 §5** promete que *"todo turno normalizado es resoluble a
  bytes sellados de su archivo original"*. Una fila de SQLite no tiene
  rango de bytes estable: el `.db` se reescribe en sitio y el WAL mueve
  páginas. `offset_inicio`/`offset_fin` pierden sentido.
- **El protocolo de instantánea** (una apertura, `fstat`, leer N bytes)
  es inviable sobre 4.4 GB que cambian mientras se lee.
- **El cursor de ADR-011** (digest del prefijo) no aplica: no hay prefijo
  estable que sellar.

**Qué haría falta decidir:** cómo se sella y se recupera un fragmento
cuando el origen es una fila y no un rango de bytes. Eso es **un ADR**,
no una ficha.

## kimi-code — JSONL, pero partido en dos y sin tiempo

`~/.kimi/sessions/<workspace>/<sesión>/`, con dos archivos por sesión:

| Archivo | Nº | Líneas (muestra) | Qué tiene | Timestamp |
|---|---|---|---|---|
| `context.jsonl` | 387 | 12,945 | La conversación: `role ∈ {user, assistant, tool, _checkpoint, _usage, _system_prompt}`, `content`, `tool_calls` | **0 %** |
| `wire.jsonl` | 381 | 34,383 | El log del protocolo: `timestamp`, `message`, `protocol_version` | 99 % |

**Con qué choca:**
- **El contenido no tiene tiempo y el tiempo no tiene contenido.** El
  turno vive en `context.jsonl`, que **no trae ni un timestamp**. Y eso
  colisiona de frente con **ADR-008**: un turno sin `timestamp_cierre`
  se trata como histórico, así que en el modo por defecto ("desde
  ahora") **ningún turno de kimi se ingeriría jamás** — sólo con
  `--backfill`. Un adaptador que "funciona" pero cuyos turnos nunca
  entran es peor que no tenerlo.
- Correlacionar `context` con `wire` para recuperar el tiempo significa
  **dos archivos por turno**, y la frontera de SPEC-006 es **por
  archivo** ("frontera por archivo", entradas: una ruta).
- Sin marca de cierre: haría falta cierre derivado, como en claude-code.
- La forma de línea de `context.jsonl` es mínima (`{role, content}`):
  un predicado de identidad sobre eso es débil y arriesga falsos
  positivos.

## cline — un array JSON, no JSONL

`~/.cline/data/sessions/<sesión>/<sesión>.messages.json` — **176
archivos**, cada uno un **array JSON completo**, no una línea por
evento. (Los `.jsonl` que hay son `hooks.jsonl` y
`user_input_history.jsonl`: telemetría y prompts sueltos, no la
conversación.)

**Con qué choca:** un array JSON se **reescribe entero** al crecer, así
que el digest de prefijo del cursor (ADR-011) fallaría en cada ciclo y
el archivo se reparsearía siempre. Los offsets y el sello sí son
posibles —es un archivo con bytes estables mientras no cambie—, pero la
lectura incremental no aporta nada aquí.

## Lo que esto significa para la fase B

La fase B se aprobó como "adaptadores para los CLIs del mapa". El mapa
decía **qué** CLIs guardan historial local; no decía **en qué forma**, y
la forma es justo lo que el contrato asume. Con los datos de hoy:

- **codex-cli** ✅ y **claude-code** ✅ — JSONL por línea, contrato
  intacto, ambos entregados.
- **cline** — cabe con una decisión menor (declarar que no usa cursor).
- **kimi-code** — exige decidir la fuente del tiempo, y de paso resolver
  la colisión con ADR-008; posiblemente una frontera de dos archivos.
- **opencode** — exige un ADR sobre orígenes que no son archivos de
  líneas. Es el más caro con diferencia y el que más contenido tiene.

Nada de esto se decide aquí: queda para el dueño, con los números
delante.
