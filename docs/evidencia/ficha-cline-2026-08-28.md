# Evidencia · ficha del adaptador parser-cline/v1 (fase B, CLI 2 de 4)

**Fecha:** 2026-08-28. **Corpus:** `~/.cline/data/sessions/*/*.messages.json`,
**176 archivos**, 3,281 mensajes. Es el **primer adaptador cuyo origen no
es JSONL**: cada sesión es un único objeto JSON con un array `messages`.

## Identidad

**Adoptado:** en los primeros **4 KiB**, el archivo abre con `{`, su
primera línea **no** es un objeto JSON completo (así se descarta todo
formato JSONL sin parsear nada), y aparecen `"sessionId"` y `"messages"`.

| Población | Resultado |
|---|---|
| `*.messages.json` de cline | **176/176 casan** |
| codex | 0 falsos positivos de 643 |
| claude-code | 0 falsos positivos de 205 |
| kimi | 0 falsos positivos de 833 |
| qwen | 0 falsos positivos de 47 |
| **otros `.json` del propio cline** (sesión, compaction) | 0 falsos positivos de 174 |

**1,902 archivos ajenos, cero falsos positivos**, incluidos los del
mismo producto que no son transcripciones — el control que más importaba
aquí.

## Offsets sobre un origen sin líneas

ADR-010 §5 exige que todo turno sea **resoluble a bytes sellados de su
archivo original**. Aquí no hay líneas que contar, así que el rango de
cada mensaje se obtiene recorriendo el array con `raw_decode`, que
devuelve dónde termina cada elemento, y convirtiendo a bytes acumulando
la longitud codificada — un solo paso, sin volver atrás.

**Verificado contra los bytes reales**: para los turnos del corpus, el
`fragmento_sha256` coincide con el `sha256` del rango
`[offset_inicio, offset_fin)` leído del archivo. El contrato se honra
igual que en los formatos de línea.

## Primer predicado positivo de incompatibilidad del registro

A diferencia de codex y claude-code, este formato **declara la versión de
su propio esquema** (`version` de raíz, hoy `1` en 176/176). La ficha lo
usa como marcador explícito (ADR-010 §1, Nivel B regla 5): una `version`
distinta da **`version_no_soportada`**, alcanzable sin retirar el parser
— cosa que hasta ahora era imposible en el registro.

## Decisiones de ficha

- **Cierre derivado**, igual que claude-code: el turno va de un mensaje
  real del usuario al siguiente; el último de una sesión viva no cierra.
- **Los `tool_result` vuelven como mensajes de usuario** (1,538 contra
  239 de texto real): se excluyen, o cada salida de herramienta abriría
  un turno.
- **`thinking` no es conversación** (1,049 bloques): razonamiento del
  modelo, fuera del `texto_agente` — decisión de ficha, como Codex
  excluye `developer` (ADR-010 §6).
- **Sólo el agente principal**: `agent ∈ {lead, subagent, teammate}`;
  `subagent`/`teammate` son conversaciones derivadas y no producen
  turnos, igual que `isSidechain` en claude-code.
- **`turn_id` calificado** `cline:{id}` (ADR-010 §7).
- **Sin cursor útil**: un objeto JSON se reescribe entero al crecer, así
  que el digest de prefijo no casaría casi nunca. La ficha lo declara y
  ADR-011 lo tolera: el cursor es caché, no obligación.

## El detalle que lo habría dejado inservible en silencio

`ts` viene en **milisegundos epoch como entero**, no en ISO. Servido
tal cual, `timestamp_cierre` sería ilegible para el corte de ADR-008,
que trata lo no parseable como histórico: **ningún turno de cline
entraría jamás** fuera de `--backfill`. La ficha convierte a ISO 8601
UTC. Verificado: **74 de 74 turnos** tienen ahora un timestamp que
ADR-008 parsea con zona horaria.

## Resultado sobre el corpus real

| CLI | Archivos | Diagnóstico | Turnos |
|---|---|---|---|
| codex-cli | 643 | 643 `ok` | 16,279 |
| claude-code | 205 | 205 `ok` | 1,806 |
| **cline** | **176** | **176 `ok`** | **74** |

Cero detección cruzada y cero ambigüedad con tres fichas registradas.
Los 74 turnos salen de 239 mensajes de usuario con texto real (el resto
son `tool_result`), menos el turno abierto de cada sesión.

**183 tests OK** (173 previos + 10 nuevos en `tests/test_cline.py`).
