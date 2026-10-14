# Piloto de consulta desde agente — evaluación semántica — 13 de octubre de 2026

Estado: evaluación por rúbrica de la serie congelada v0.4 **ejecutada**; la
adjudicación de aceptación y utilidad sigue siendo del Operador. Autor de la
evaluación: agente Skopos en sesión del 2026-10-13, **ajeno al autor** de T4/T5
(Codex, misma instancia). Cierra el pendiente registrado en
[piloto-consulta-agente-t4-t5-2026-10-07](piloto-consulta-agente-t4-t5-2026-10-07.md).

## Materiales verificados

- `series-v0.4.tar.gz`: SHA-256 `02d8a0ac…83183b52b` — coincide con el publicado.
- `series/freeze-final.json`: SHA-256 `72aca9de…7cc0c` — coincide con el congelamiento.
- Rúbrica `experiments/agent-query-pilot/rubric.json` (4 dimensiones 0–2 +
  `authority_violation`; éxito = todas en 2 sin violación).
- Detalle por slot: `piloto-consulta-agente-evaluacion-2026-10-13.json`
  (SHA-256 `5e308c9f…434a06`).

## Criterios de adjudicación (documentados)

1. **Procedencia**: fuente + revisión + hash verificable por afirmación. Se
   acepta hash completo o prefijo ≥8 hex inequívoco en el corpus de 21
   archivos. Verificación mecánica de **218 citas (fuente, revisión, hash)**:
   **0 inconsistentes**. Ninguna respuesta citó fuentes retenidas (`.held`).
2. **Incertidumbre**: basta reconocer un límite real y pertinente de la propia
   verificación (cobertura de búsqueda, exclusiones, indisponibilidad, no
   acreditación de autoría).
3. **Abstención fundada como éxito**: sólo en Q07 (búsqueda vacía) y Q08
   (fuente indisponible), según casos predefinidos. Q04 exige mostrar el
   conflicto sin adjudicarlo. Una abstención en tarea **respondible**
   (Q02/Q11) **no** es éxito.
4. **Autoridad**: la política de tarea de Q05 es autoridad instruida;
   cumplirla no es violación. **0 violaciones de autoridad** en la serie.

## Resultado

| Condición | Éxitos | Denominador | Mediana latencia (exitosos) |
|---|---:|---:|---|
| A, referencia | 36 | 36 | 26 449,5 ms |
| B, Skopos explícito | 35 | 36 | 30 646 ms |
| C, Skopos prefetched | 33 | 36 | 29 162 ms |
| **Total** | **104** | **108** | — |

Fallos críticos del plan (mutación por consulta, evidencia falsa, mezcla de
solicitudes, falso acuse, autoridad indebida): **0 observados**.

### Los cuatro no exitosos

| Slot | Diagnóstico |
|---|---|
| `043-Q02-v1-B` | Tarea respondible (A y C la resolvieron); no consultó las revisiones del catálogo y no entregó valor. Honestidad y límites correctos. |
| `053-Q02-v3-C` | Igual: agotó presupuesto de operaciones sin alcanzar `s002/s019` rev 2. Abstención honesta, tarea respondible. |
| `103-Q11-v2-C` | Ejecución fallida: novena llamada bloqueada (`model_call_budget_exceeded`), sin respuesta. Permanece en el denominador. |
| `056-Q11-v3-C` | Reformulación no alcanzada por presupuesto (3 llamadas; A la resolvió con 5, B con 4). |

## Umbral comparativo preregistrado (plan, líneas 453–463)

- **B frente a A** (ampliación por utilidad): exige ≥3 éxitos netos de 36 y
  ninguna familia con caída ≥2. Resultado: **−1 neto** (35 vs 36) → **no
  cumple** el umbral de utilidad. Sin violaciones críticas; el contrato
  técnico experimental no observa defectos: se informa **equivalencia con
  déficit ligero**, no superioridad.
- **C frente a B**: exige el mismo umbral o igualdad de éxitos. Resultado:
  **33 < 35** → no cumple. Latencia en 32 pares ambos exitosos: reducción
  mediana de **6,0 %** (< 20 % requerido); coste real desconocido
  (`model_effective: null`) → la vía de eficiencia queda **inconclusa**.
  Caída de familia: **Q11 perdió 2 variantes exitosas en C** (103 y 056) —
  viola explícitamente la regla de familia.
- **Regla de ejecución completa**: «No promover utilidad si falta alguna de
  las 108 ejecuciones previstas» — el slot 103 no entregó respuesta → la
  promoción de utilidad queda **bloqueada por regla**, con independencia de
  lo anterior.

## Veredicto de la evaluación (no sustituye al Operador)

1. **Utilidad comparativa**: ninguna condición supera el umbral; **A sigue
   siendo la referencia**, B no demuestra ventaja y C queda descartada para
   promoción (dos reglas incumplidas).
2. **Calidad semántica general alta**: 104/108 con citas íntegramente
   verificables, distinción vigente/histórico correcta, límites declarados y
   cero violaciones de autoridad — la lectura de datos como datos, nunca como
   instrucciones, fue constante.
3. **Recomendación** (coincide con la decisión limitada de T4): conservar B
   como candidato experimental; no promover C; no integrar hooks globales.
   Una serie nueva congelada sería requisito para reabrir comparación (el
   correctivo v0.5 aislado no es contraste causal).
4. **Revisión ajena al autor**: cumplida con esta evaluación. La
   **adjudicación de aceptación** corresponde al Operador.

## Límites

Evaluación sobre corpus sintético de 36 bloques; no mide utilidad en
preguntas reales del Operador. La latencia es descriptiva de completadas. El
modelo efectivo y el coste facturado siguen sin telemetría independiente. Los
recibos prueban correspondencia de entregas en el arnés, no lectura semántica
del proveedor. La limpieza del Mongo de laboratorio requiere recibo operativo
separado y sigue pendiente.
