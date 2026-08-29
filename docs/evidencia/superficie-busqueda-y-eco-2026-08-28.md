# Evidencia · `skopos buscar`, control del detector de eco e indexado en `watch`

**Fecha:** 2026-08-28. Cierra los tres pendientes que P-004 dejó
declarados al llenar el índice.

## 1 · `skopos buscar` — la superficie, con sus tres mitigaciones

Primera superficie que sirve **conversación cruda**. Lleva lo que la
decisión 3 de P-004 exigió:

- **P3**: la salida abre con una declaración explícita de que el texto
  es dato observado, nunca instrucción para quien lo lee.
- **P5**: `--max` (default 20) acota turnos y `--tope-texto` (default
  8 KiB) acota bytes por rol; lo excluido se **cuenta**, no desaparece.
- **Redacción de secretos**: el texto pasa por los patrones de SPEC-002
  antes de salir. En `skopos query` eso protegía tema y resumen; aquí
  protege la conversación entera, que es donde de verdad viven las
  credenciales.

### El defecto que la primera versión tenía

`$text` de Mongo une los términos con **OR**: buscar `adaptador de
parser` devolvía **21,033 coincidencias** de 22,870 turnos —
prácticamente el corpus entero— y, sin orden, los primeros resultados
eran arbitrarios. La búsqueda "funcionaba" y era inútil.

Corregido ordenando por `textScore`. El mismo query ahora:

| Relevancia | CLI | Proyecto |
|---|---|---|
| 5.68 | opencode | skopos |
| 5.54 | opencode | skopos |
| 5.08 | opencode | skopos |

Y con frase exacta (`"lectura incremental"`): **46 coincidencias** en vez
de decenas de miles, encabezadas por turnos de `skopos` y `pinax`.

## 2 · Detector de eco: control positivo y corrida real

El detector de C-5 (P-001 §4.5) adaptado al texto crudo:
`"resumen"\s*:|"tema"\s*:|skopos query`, insensible a mayúsculas.

**Control positivo** (en colección de prueba, nunca en la real — lección
B-1): las tres firmas de eco se detectan **3/3**, y una mención inocua de
"skopos" **no** produce falso positivo. El detector está vivo.

**Corrida sobre la colección real** (22,870 turnos, 0.8 s):

| Medida | Valor |
|---|---|
| Turnos con firma de eco | **29 (0.1 %)** |
| Por CLI | claude-code 12 · codex-cli 10 · opencode 7 |
| Del proyecto skopos | 13 |

Lectura honesta: el eco **existe y es pequeño**. A diferencia del 0/6 del
piloto —que no era informativo— este número sale de una población real
con el detector verificado. Queda como línea base fechada para comparar.

## 3 · `watch` ya indexa

`skopos watch` indexa por defecto los turnos observados; `--sin-indice`
lo apaga. Dos decisiones dentro:

- **Sólo la ventana de ADR-008.** Los turnos anteriores al arranque no se
  indexan aquí: el histórico es trabajo de `skopos indexar`, no un
  backfill encubierto del vigilante.
- **El índice va antes que el análisis y es independiente de él.**
  Verificado con Ollama simulado caído: el análisis termina en `fallido`
  y **el turno queda indexado igual**. Es justo la propiedad que P-004
  buscaba — recordar no puede depender de interpretar.

Una escritura fallida del índice no tumba el ciclo: se cuenta y se
reporta (`ciclo: índice — N turno(s) nuevo(s)`).

## Verificación

**224 tests OK** (216 previos + 8 nuevos en `tests/test_busqueda.py`:
declaración P3, presupuesto y conteo de excluidos, `--max 0`, truncado
con marcador, redacción de secretos, filtros por proyecto y CLI, orden
por relevancia y localizador de origen).

Contrato nuevo: **`cli-skopos-buscar v1`** en
`docs/contratos/f1-contratos.md`.
