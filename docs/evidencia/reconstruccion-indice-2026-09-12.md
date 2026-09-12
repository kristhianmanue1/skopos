# Evidencia: reconstrucción del índice de turnos (P-007)

Fecha: 2026-09-12. Autorizada por el dueño el mismo día, en modo
desarrollo y con respaldo. Cierra el hallazgo de
`docs/propuestas/P-007-offsets-irrecuperables-en-el-indice.md`.

## Procedimiento ejecutado

1. **Ensayo no destructivo**: `skopos.turnos_v2` construido en paralelo
   con el parser de hoy, sin tocar nada vigente. 158.8 s para las cuatro
   fuentes de archivo; opencode añadido aparte por ser fuente de filas
   (`procesar_base_filas`, ADR-013).
2. Medición y comparación antes de decidir (abajo).
3. `watch` detenido.
4. **Renombrado, no borrado**: `turnos` → `turnos_respaldo_20260912`,
   `turnos_v2` → `turnos`. El corpus anterior sigue íntegro en la base.
5. `analyze` sobre la ventana de anclas para cubrir la segmentación
   nueva: 5 análisis nuevos, 105 ya estaban.
6. `watch` rearrancado en `--solo-indice`.

## Resultado

| Medida | Antes | Después |
|---|---|---|
| Turnos en el índice | 26,007 | **16,974** |
| Offsets fuera del EOF | 78 % de la muestra | **0 / 12,156** |
| Sellos `sha256` verificados | — | **300 / 300** |
| Archivos de origen inexistentes | 0 | 0 |

Reparto por CLI tras la reconstrucción: codex-cli 8,338, opencode 4,818,
claude-code 2,111, kimi-code 1,637, cline 70.

**Ningún turno se perdió.** La comparación de `turn_id` dio *0 sólo en
v2*: el índice reconstruido es un subconjunto estricto del anterior. Los
**9,033 de diferencia** son artefactos de la segmentación vieja —
codex-cli 8,798 y claude-code 235—, turnos que el parser de hoy no
produce y cuyos offsets no resolvían contra ningún archivo.

La verificación de sellos es la prueba que importa: 300 de 300 fragmentos
releídos por rango coinciden con su `fragmento_sha256`. **La recuperación
del fragmento de origen de ADR-009 (P3) vuelve a funcionar**, y con ella
el entregable del hito 16 que P-007 declaraba incumplido.

## Lo que NO quedó resuelto, y es lo que hay que decidir

Sobre los 156 análisis, el estado del fragmento quedó así:

| Estado | Total | Con turno vivo |
|---|---|---|
| `truncado` (se sirve, acotado por P5) | 62 | 62 |
| `integro` | 7 | 7 |
| `origen_de_filas` (opencode, sin fragmento por diseño ADR-012) | 25 | 25 |
| `integridad_fallida` | 59 | **18** |
| `origen_perdido` | 3 | 0 |

Dos poblaciones distintas, con remedio distinto:

**(a) 18 análisis vivos con offsets rancios.** Su `turn_id` sobrevivió a
la reconstrucción, pero el documento de análisis guarda **su propia
copia** de `offset_inicio`/`offset_fin` (`_documento`), tomada cuando el
índice aún estaba mal. El turno de al lado está sano; el análisis apunta
al sitio viejo.

Remedio: `skopos reanalyze <turn_id>` — es exactamente el caso para el
que existe ADR-007, y deja la versión vieja como auditoría en vez de
pisarla.

**(b) 44 análisis huérfanos**, todos de codex-cli: su turno ya no existe
bajo ninguna segmentación. Conservan texto válido pero no tienen
evidencia cruda recuperable ni turno al que volver.

Remedio: decisión del dueño. Borrarlos deja la colección coherente;
conservarlos mantiene interpretación cuyo origen no se puede auditar —
que es justo lo que ADR-009 quiso evitar. **No se tocaron.**

Los 22 huérfanos de opencode que el ensayo preveía **se recuperaron
solos** al reconstruir también la fuente de filas.

## Reversión

`turnos_respaldo_20260912` (26,007 documentos) sigue en la base. Deshacer
es invertir los dos renombrados. No se borra hasta que el dueño lo
ordene: mientras exista, esta operación es reversible.

## Lo que esta evidencia NO establece

- No confirma la causa de §4 de P-007 (el acumulador entre archivos).
  Se reparó sin diagnosticar, como recomendaba la propuesta: el remedio
  era el mismo en cualquier caso.
- No añade la invariante de §6.4 (`offset_fin` ≤ tamaño del archivo al
  indexar). **Sigue pendiente**, y es lo único que impide que el defecto
  vuelva en silencio.
- No decide qué pasa con los 44 huérfanos ni ejecuta los 18 `reanalyze`.
