# Evidencia · ficha del adaptador parser-kimi-code/v1 (fase B, CLI 3 de 4)

**Fecha:** 2026-08-28. **Corpus:**
`~/.kimi/sessions/<workspace>/<sesión>/wire.jsonl`, **381 archivos**,
134,877 líneas.

## Corrección de un diagnóstico previo mío

El documento `reconocimiento-fase-b-restantes-2026-08-28.md` (de hoy
mismo) declaró kimi-code **bloqueado** porque "la conversación no tiene
tiempo y el tiempo no tiene contenido". **Ese diagnóstico era erróneo:
miré el archivo equivocado.** Me quedé en `context.jsonl` (conversación
sin timestamps) y no abrí el `message.payload` de `wire.jsonl`, que sí
trae **las dos cosas juntas** — y además marcas explícitas de turno.

Kimi no era el caso difícil: es **el mejor de los cinco**.

## Por qué `wire.jsonl` y no `context.jsonl`

| Archivo | Conversación | Tiempo | Marcas de turno |
|---|---|---|---|
| `context.jsonl` (387) | sí | **0 %** | no |
| **`wire.jsonl` (381)** | **sí** (`TurnBegin.user_input`, `ContentPart`) | **99 %** | **`TurnBegin`/`TurnEnd`** |

Un solo archivo basta: no hay que correlacionar dos, así que **la
frontera por archivo de SPEC-006 queda intacta** y no hace falta tocar
ningún ADR. La colisión con ADR-008 que temí no existe.

## Identidad

**Adoptado:** en las 10 primeras líneas, un objeto con
`type == "metadata"` y `protocol_version` string. Es la primera línea en
381/381 archivos.

| Población | Resultado |
|---|---|
| `wire.jsonl` de kimi | **381/381 casan** |
| codex | 0 falsos positivos de 643 |
| claude-code | 0 falsos positivos de 205 |
| cline (`.messages.json`) | 0 falsos positivos de 176 |
| qwen | 0 falsos positivos de 47 |
| **`context*.jsonl` del propio kimi** | 0 falsos positivos de 452 |

1,523 ajenos, cero falsos positivos — incluidos los 452 archivos hermanos
del mismo producto, que era el control que importaba.

## Cierre por marca, no derivado

Único adaptador del registro, además de Codex, con **marca explícita**:
`TurnBegin` abre, `TurnEnd` cierra. En el corpus: **1,789 `TurnBegin` y
1,637 `TurnEnd`** — la diferencia son turnos interrumpidos o en curso,
que quedan abiertos y se recogen cuando cierren, exactamente como manda
el `ok` residual de ADR-010 §1.

## Incompatibilidad declarada

`protocol_version` es la versión del **formato**. Observadas: **1.3
(81), 1.7 (108), 1.9 (124), 1.10 (68)**, todas con el mismo vocabulario
de turno, así que v1 del parser las soporta. Una versión fuera de esa
lista da `version_no_soportada` — segundo adaptador con predicado
positivo, tras cline.

## Dos trampas que lo habrían dejado inservible

1. **`timestamp` es un float epoch**, no ISO. Servido tal cual, ADR-008
   lo trata como no parseable = histórico, y **ningún turno de kimi
   entraría** fuera de `--backfill`. La ficha convierte a ISO 8601 UTC.
   Antes de corregirlo: 1,637 turnos sin tiempo utilizable. Después: **0**.
2. **`user_input` aparece en dos formas**: lista de partes (523) y
   **string suelto** (99), normalmente la instrucción inicial del
   agente. Aceptar sólo la primera dejaba **363 turnos con
   `texto_usuario` vacío**. Después de aceptar ambas: **0**.

Las dos se detectaron mirando el resultado sobre el corpus real, no
leyendo el código: el adaptador "funcionaba" en ambos casos.

## Resto de la ficha

- **`session_id`**: nombre de la **carpeta** de la sesión — todos los
  archivos se llaman `wire.jsonl`.
- **`turn_id`**: calificado `kimi-code:{session_id}:{ordinal}` (ADR-010
  §7). El wire no da id de turno; el ordinal es estable porque el log es
  de sólo-anexado — declarado como tal en la ficha.
- **`proyecto`: siempre ausente**, por declaración. El wire no expone
  `cwd`, y deducirlo de la ruta del archivo está **prohibido** (ADR-010
  §2). `~/.kimi-code/session_index.jsonl` sí tiene `workDir`, pero es
  otro archivo: usarlo rompería la frontera por archivo.
- **`think` fuera del texto del agente** (19,364 partes contra 3,629 de
  texto): razonamiento, no diálogo — misma decisión que en cline.

## Resultado con las cuatro fichas registradas

| CLI | Archivos | Diagnóstico | Turnos |
|---|---|---|---|
| codex-cli | 643 | 643 `ok` | 16,279 |
| claude-code | 205 | 205 `ok` | 1,808 |
| cline | 176 | 176 `ok` | 74 |
| **kimi-code** | **381** | **381 `ok`** | **1,637** |
| **Total** | **1,405** | — | **19,798** |

Cero detección cruzada, cero ambigüedad. **195 tests OK** (183 + 12).
