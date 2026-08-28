# Evidencia · Fase A de P-003 — parser codex como adaptador registrado

**Fecha:** 2026-08-28. **Alcance:** fase A de
`docs/propuestas/P-003-colector-conversation-event.md` (aceptada 🔒
2026-08-28): extracción del parser Codex incrustado a **adaptador tras
`parser-contrato/v1`** (ADR-010), con constantes de ficha declaradas,
registro del §8 y la frontera de SPEC-006 implementada
(`src/skopos/parseo.py`). Máquina y corpus: los del dueño, snapshot de
esta fecha.

## Qué entrega la fase A

- `src/skopos/captura.py` — adaptador **parser-codex/v1**: la ficha del
  ADR-010 §8 deja de vivir sólo en prosa y queda como constantes
  (`ID_FICHA`, `CLI_PRODUCTO`, `VERSION_PARSER`, `VERSION_FORMATO`,
  `LINEAS_ESCANEO_IDENTIDAD`, `PATRON_ORIGINATOR`, `EVENTOS_DECLARADOS`,
  predicado de cierre, roles). Extrae sobre la **instantánea de bytes**,
  no sobre el archivo.
- `src/skopos/parseo.py` — frontera de **SPEC-006**: protocolo de
  instantánea del §5, selección en dos niveles del §1, vocabulario
  cerrado de diagnósticos y `ResultadoParseo` del §3, `Detalle` como
  unión cerrada validada en construcción, y el **registro de
  adaptadores** del §8 (hoy: una ficha).
- `tests/test_parseo.py` — 29 tests nuevos: protocolo, precedencia,
  cada diagnóstico, reglas de `detalle`, registro y regla de separación
  de líneas (sólo `\n`, para no mover offsets ni sellos ya guardados).

**Corrección de no conformidad declarada en ADR-010 §5:** el ADR anotaba
que `captura.py` leía el archivo **dos veces** (iteración y sello por
rango) y que eso era *no conforme*. Ya no: una apertura, N por `fstat`
del mismo descriptor, lectura exacta de N bytes, y offsets, parseo y
sello sobre ese mismo buffer.

## Gate 1 · Suite completa

`python3 -m unittest discover -s tests` → **131 tests OK** (102 previos
+ 29 nuevos). El único test previo modificado es
`test_archivo_ilegible_al_sellar_deja_sello_none`: verificaba que el
sello degradara a `None` al **releer** el archivo, comportamiento que el
§5 eliminó. Se sustituyó por
`test_sello_se_computa_sobre_la_instantanea_no_releyendo_el_archivo`,
que fija el contrato nuevo (el archivo crece tras materializar y el
sello sigue siendo el de la instantánea).

## Gate 2 · Predicado de identidad contra el corpus real

Método: `casa_identidad()` del adaptador sobre un prefijo de 1 MiB de
cada archivo — equivalente al archivo completo para un predicado
acotado a 10 líneas, y verificado archivo por archivo (0 casos con
prefijo insuficiente).

| Población | Resultado |
|---|---|
| `~/.codex/sessions/**/*.jsonl` (**643** archivos) | **643/643 casan** — 0 no-match, 0 ilegibles |
| `~/.claude/projects/**/*.jsonl` (**394** archivos) | **0/394 casan** — 0 falsos positivos |
| `~/.codex/history.jsonl` (JSONL del mismo producto, no rollout) | no casa |

El corpus está **vivo**: la medición del 2026-08-20 fue 616 positivos y
253 archivos de Claude Code; hoy son 643 y 394. Los números se citan
como snapshot de esta corrida, no como constantes (misma nota de drift
que `predicado-identidad-codex-2026-08-20.md`). La proporción se
mantiene: 100 % de positivos, 0 % de falsos positivos.

**Enum de `originator` observado hoy** — `Codex Desktop` 526,
`codex_exec` 69, `codex-tui` 46, **`codex-chrome-extension-sidepanel`
2**. El cuarto valor **no estaba** en el enum documentado por la ficha
del ADR-010 §8 (que lista tres). Casa correctamente por la frontera de
palabra (`codex-` + separador), así que **no cambia ningún resultado**;
queda registrado aquí porque el enum de la ficha es descriptivo y su
actualización exige pasada propia sobre un ADR aceptado 🔒.

## Gate 3 · Equivalencia turno a turno con el extractor previo

El refactor no debe cambiar ni un turno. Se comparó el extractor de
`0dd1417` (previo a la fase A) con el nuevo, campo por campo — incluidos
offsets y `fragmento_sha256`:

- Muestra: **45 archivos** — 40 aleatorios (semilla 42, misma
  metodología que C-9) + los **5 mayores** del corpus.
- **2,496 turnos** comparados.
- **45/45 archivos idénticos, 0 diferencias.**

## Gate 4 · Barrido de `parsear()` sobre el corpus completo

643 archivos, 42.6 s, lectura completa (2.3 GB):

| Métrica | Valor |
|---|---|
| `ok` | **643/643** |
| `identidad_reconocida_sin_cierres` | 11 archivos (sesiones sin cierre — el `ok` residual del §1, observable aparte) |
| turnos extraídos | 16,201 |
| `eventos_no_reconocidos` | 6,015 (evolución aditiva del formato: se cuentan, no diagnostican) |
| `descartes_linea` | 0 |
| negativos claude-code | 394/394 `formato_desconocido` |
| negativo `history.jsonl` | `formato_desconocido` |

Deriva del corpus vivo: una primera corrida del mismo barrido, minutos
antes, dio 16,196 turnos con el resto de métricas idénticas. Se cita la
última; la diferencia es el corpus creciendo entre corridas, no una
discrepancia del parser.

Ningún archivo del corpus real cae en `version_no_soportada` ni
`deteccion_ambigua`, como la ficha predice (§8: sin predicados positivos
de incompatibilidad en v1, `version_no_soportada` es inalcanzable salvo
por retiro). Esos caminos quedan cubiertos por tests con fichas
sintéticas, no por el corpus.

## Límites y pendientes declarados

- **El pipeline todavía no pasa por la frontera.** `orquestador.py` y
  `cli.py` siguen llamando a `extraer_turnos()` (SPEC-001) directamente,
  que parsea sin detectar. La fase A entrega el contrato implementado y
  probado; **enrutar la ingesta por `parsear()`** cambia qué archivos se
  ingieren (los que no casan dejarían de entrar) y merece su propia
  pasada con evidencia — no se coló en un refactor.
- **Dos notas de estado quedan desactualizadas** en documentos aceptados
  🔒, y actualizarlas exige pasada autorizada: el registro del ADR-010 §8
  dice "implementación de detección pendiente del plan de fase", y
  SPEC-006 dice "sin implementación todavía". Ambas describen el estado
  previo a este commit.
- Los scripts de verificación son de un solo uso y viven fuera del repo
  (directorio volátil de la sesión); lo reproducible es el método
  descrito arriba sobre las mismas poblaciones.
