# F1 — Máquina de estados de un turno

Un turno detectado por SPEC-001 tiene ciclo de vida propio: puede fallar
en el análisis o en la persistencia, y ese fallo debe quedar explícito.

```text
ESTADOS: detectado, analizado, guardado, fallido, omitido

TRANSICIONES:
  detectado --ya_guardado--> omitido
  detectado --analisis_ok--> analizado
  detectado --analisis_falla--> fallido
  analizado --persistencia_ok--> guardado
  analizado --persistencia_falla--> fallido

INVARIANTES:
  - un turno nunca llega a "guardado" sin pasar por "analizado";
  - "fallido" es terminal para ese intento — un reintento (si existe en
    la implementación) genera un intento nuevo, no revive el mismo turno
    en su estado previo;
  - un timeout de análisis (SPEC-002) o de persistencia (SPEC-003)
    produce "fallido" explícito; "guardado" nunca se infiere por ausencia
    de error;
  - "omitido" existe para el vigilante en vivo (docs/adr/ADR-005): un
    turno con turn_id ya guardado en Mongo no se vuelve a analizar ni a
    persistir en un ciclo posterior.
```
