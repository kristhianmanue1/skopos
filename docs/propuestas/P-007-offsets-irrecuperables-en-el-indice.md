# P-007: offsets irrecuperables en el índice (el fragmento no se puede releer)

Estado: **propuesta — no decidida. Hallazgo registrado, sin corregir.**
No implementa nada: documenta lo medido (§1), acota el alcance (§2),
descarta lo que NO es (§3) y pide decisiones (§6).
Fecha: 2026-09-12.
Origen: verificación de la primera corrida de `skopos analyze`
(ADR-017). `skopos query` empezó a servir resultados y **todos** salían
con `fragmento_estado: "integridad_fallida"` y `fragmento_completo:
null`. El hallazgo es incidental: no lo produjo el cambio de hoy.

## 1. Lo medido

Archivo testigo, un rollout de codex sin modificar desde antes de que se
lo indexara (mtime 2026-08-01; `indexado_en` 2026-08-29):

| Medida | Valor |
|---|---|
| Tamaño real del archivo | 1,692,713 bytes |
| Turnos suyos en `skopos.turnos` | 310 |
| Turnos que da `parsear()` hoy | 30 |
| `offset_fin` máximo en el índice | 14,536,234 (8.6× el archivo) |
| Turnos del índice dentro del EOF | 34/310 |

Mismo `turn_id`, comparado entre el índice y el reparseo de hoy:

```
fresco  (1,446,836 → 1,492,339)
índice (14,293,731 → 14,338,752)     desfase ≈ 12.85 MB
```

El desfase **no es constante**: crece turno a turno (12,846,895 /
12,850,269 / 12,852,197 en tres turnos consecutivos). Eso es la firma de
un **acumulador de offsets que siguió corriendo entre archivos en vez de
reiniciarse en cada uno**.

Muestra de 20 archivos de codex tomada al azar (semilla fija):

| Medida | Valor |
|---|---|
| Turnos en el índice | 918 |
| Turnos que da `parsear()` hoy | 192 |
| Con `offset_fin` más allá del EOF | 720 (78 %) |
| Archivos de origen inexistentes | 0 |

Y el corte que importa para decidir — validez según quién indexó:

| Corrida | Offsets fuera del EOF |
|---|---|
| Masiva del 2026-08-29 (P-004, hito "índice lleno") | 29/400 |
| Parser de hoy (2026-09-12, `index` y `watch`) | **0/400** |

## 2. Qué rompe, exactamente

La recuperación del fragmento completo de **ADR-009 (P3)** —entregable
del hito 16— sobre la parte del índice construida en la corrida masiva.
`query` y `buscar` releen el archivo por rango y verifican el sello
antes de servir; con offsets que caen fuera del EOF la lectura devuelve
vacío, el sha256 no coincide y el fragmento se niega.

**La verificación de integridad hace bien su trabajo**: detecta y niega
en vez de servir bytes equivocados. Lo que falla es lo sellado, no el
guardián. Ese es el único motivo por el que esto no fue un incidente
silencioso de corrupción.

## 3. Qué NO es (descartado con medición)

- **No es pérdida ni corrupción de contenido.** Los textos almacenados
  son conversación real; el análisis que produce el modelo sobre ellos
  es válido. Lo roto es el puntero al origen, no el dato.
- **No son duplicados.** De las 608 anclas del corpus, 595 tienen texto
  distinto: sólo 2 % son copias exactas. El índice **no está inflado con
  basura**; está **segmentado distinto** de como segmenta el parser de
  hoy — más turnos y más chicos cubriendo el mismo texto.
- **No es que falten los archivos de origen.** 0 inexistentes en las dos
  muestras. Lo que hace falta para reparar sigue en disco.
- **No lo introdujo `skopos analyze`.** Los 8 análisis de agosto,
  producidos por `watch`, traen `integridad_fallida` igual.

## 4. Hipótesis de causa (no confirmada)

El desfase creciente apunta a que la corrida masiva del 2026-08-29 pasó
a `parsear()` una marca de agua **acumulada entre archivos** en vez de
una por archivo — el `desde` de la lectura incremental (ADR-011) o el
equivalente en el camino de indexado de P-004, en el mismo cruce donde
se estrenó el adaptador de la fase A (2026-08-28).

Se registra como hipótesis, no como diagnóstico: confirmarla exige
reconstruir la invocación de aquella corrida, y eso es trabajo de la
ronda, no de este documento.

## 5. Por qué se registra en vez de corregirse aquí

Tocar esto significa decidir qué se hace con los 25,909 documentos ya
indexados, y eso es decisión del dueño, no del agente que lo encontró.
Además cae en territorio de tres decisiones cerradas (ADR-009 §P4a,
ADR-010 §5, ADR-011): el método del proyecto pide ronda con medición
completa, no un parche al final de una sesión.

Mientras tanto **no hay urgencia operativa**: el guardián niega, la capa
de análisis sigue siendo válida y la ingesta nueva ya nace sana.

## 6. Preguntas para las rondas (decisión del dueño)

1. ¿Se confirma la hipótesis de §4 antes de reparar, o se repara sin
   diagnosticar por ser el remedio el mismo en cualquier caso?
2. **Reparación: ¿reindexar desde cero o marcar lo irrecuperable?** Los
   archivos siguen en disco y `indexar` es idempotente, así que un
   reindexado completo regeneraría offsets sanos. El costo es una
   corrida masiva y la pérdida de los turnos cuyos archivos ya no
   existan. La alternativa —marcar los rotos y dejarlos— conserva el
   texto pero renuncia al fragmento para siempre en esa parte.
3. Si se reindexa: ¿se descartan los documentos viejos o conviven? La
   segmentación distinta significa que los `turn_id` **no coinciden**, y
   la dedup de ADR-005 no los reconocería como el mismo turno: un
   reindexado sin borrado dejaría las dos segmentaciones encima.
4. ¿Se añade al gate una comprobación de que `offset_fin` ≤ tamaño del
   archivo al indexar, para que esto no pueda repetirse en silencio?
5. ¿Los análisis ya producidos sobre turnos con offsets rotos se
   conservan (el texto es válido) o se rehacen contra la segmentación
   nueva?

## 7. Relación con decisiones cerradas

- **ADR-009**: el sello P4a y la verificación P3 funcionan como se
  prometió. Este hallazgo no los cuestiona: los confirma.
- **ADR-005**: la dedup por `turn_id` es lo que hace que un reindexado
  con segmentación distinta **no** sea idempotente (§6.3).
- **ADR-017**: la ventana de 7 días adoptada para la primera corrida de
  `analyze` (decisión del dueño, 2026-09-12) resulta ser también la que
  evita este defecto — los turnos recientes tienen offsets sanos (§1),
  así que el piloto evalúa la capa interpretada **con** su evidencia
  cruda en vez de sin ella.
- **Hito 16**: queda con un entregable parcialmente incumplido en el
  corpus histórico. No se reabre aquí; se anota.
