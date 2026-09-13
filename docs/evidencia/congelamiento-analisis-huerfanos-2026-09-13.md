# Congelamiento de los 44 análisis huérfanos — 2026-09-13

> Operación sobre datos, reversible. Decidida por el dueño el
> 2026-09-13 ("congelados, no eliminados") sobre la medición de abajo.
> Cierra el primero de los tres pendientes que dejó abiertos el cierre
> del 2026-09-12.

## Qué era un huérfano

Un documento de `skopos.analisis` cuyo `turn_id` ya no existe en
`skopos.turnos`. Nacieron de la reconstrucción del índice de P-007
(2026-09-12): el corpus se re-segmentó, así que los `turn_id` de la
segmentación vieja dejaron de tener turno detrás. **No es pérdida de
contenido** — el texto del análisis está intacto y la conversación sigue
indexada bajo otros `turn_id`.

## Medición previa (2026-09-13, colección real)

| Grupo | Cuántos | Situación |
|---|---|---|
| Archivo de origen aún indexado bajo otros `turn_id` | 41 | re-derivable con `analyze` |
| Residuo de tests (`turn-test-001/002`, rutas en `/tmp`) | 2 | no es conversación |
| Rollout de codex borrado del disco | 1 | **único irreproducible** |

- **Ninguno servía evidencia verificable**: 41 daban `integridad_fallida`
  y 3 `origen_perdido` al pedir `fragmento_completo`.
- 36 de los 44 siguen presentes en `skopos.turnos_respaldo_20260912`, así
  que su identidad vieja es rastreable.
- No había defecto de supersede: `query` servía la versión vigente. Los
  9 que aparecían fallando en una consulta eran huérfanos, no v1
  superseded (las 18 v1 superseded tienen v2 sana, como decía el cierre
  del 2026-09-12).

## Por qué congelar y no borrar, ni dejarlos donde estaban

**Borrar** es la única operación que este proyecto nunca ha elegido, y
aquí no hacía falta: 41 de 44 son re-derivables y el que no lo es es
precisamente el que no se puede reponer si se borra.

**Dejarlos** era peor que moverlos: no estaban inertes. En una consulta
sin filtro ocupaban **9 de 20 asientos** —45 % de la primera página—
mientras 109 resultados válidos quedaban fuera por `--max`. Pesaban poco
(8 KB, su fragmento es `null`) pero desplazaban lo que sí tiene
evidencia. El costo no era egreso, eran asientos.

## Qué se hizo

Movidos a `skopos.analisis_huerfanos_20260913` con el patrón reversible
de P-007: **copiar, verificar, y sólo entonces retirar**.

1. Copia de los 44 documentos completos (con su `_id`).
2. Verificación documento a documento: los 44 presentes y **byte a byte
   iguales** al original (comparación del documento completo, no de una
   muestra de campos). El script aborta antes de borrar si uno difiere.
3. Retirada de `skopos.analisis`: 44 eliminados.

Deshacer es el movimiento inverso: los documentos conservan su `_id`, así
que volver a insertarlos los restituye idénticos.

## Estado resultante

```
skopos.analisis                      174 -> 130 documentos (112 turn_id)
skopos.analisis_huerfanos_20260913     0 ->  44 documentos
huerfanos restantes en skopos.analisis: 0
```

Estado del fragmento de las 112 versiones vigentes: **7 `integro`, 80
`truncado`, 25 `origen_de_filas`, 0 `integridad_fallida`**. Es la primera
vez que `skopos.analisis` no tiene ningún fallo de integridad.

## Lo que queda pendiente, dicho explícitamente

- Los 41 re-derivables: una corrida de `analyze` sobre los archivos que
  siguen indexados produce el análisis con el `turn_id` nuevo. Cuando
  exista, su congelado es redundante y su borrado deja de tener costo.
- El 1 irreproducible (rollout borrado): se queda congelado. Es la única
  interpretación del corpus que nadie puede volver a generar.
- Los 2 de test: basura, pero se movieron con los demás en vez de
  borrarse aparte — una regla uniforme costaba menos que una excepción.
