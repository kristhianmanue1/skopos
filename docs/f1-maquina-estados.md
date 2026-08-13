# F1 — Máquina de estados de un turno

Un turno detectado por SPEC-001 tiene ciclo de vida propio: puede fallar
en el análisis o en la persistencia, y ese fallo debe quedar explícito.

```text
ESTADOS: detectado, analizado, guardado, fallido, omitido

TRANSICIONES:
  detectado --ya_guardado--> omitido
  detectado --dedup_falla--> fallido
  detectado --sin_contenido--> omitido
  detectado --analisis_ok--> analizado
  detectado --analisis_falla--> fallido
  analizado --persistencia_ok--> guardado
  analizado --persistencia_duplicada--> omitido
  analizado --persistencia_falla--> fallido

INVARIANTES:
  - un turno nunca llega a "guardado" sin pasar por "analizado";
  - "fallido" es terminal para ese intento — un reintento (si existe en
    la implementación) genera un intento nuevo, no revive el mismo turno
    en su estado previo;
  - un timeout de análisis (SPEC-002) o de persistencia (SPEC-003)
    produce "fallido" explícito; "guardado" nunca se infiere por ausencia
    de error;
  - "omitido" tiene tres causas, todas legítimas y distintas de "fallido"
    (ronda adversarial 2026-08-13 verificó que un fallo de Mongo durante
    el chequeo de deduplicación no debía tumbar el ciclo entero — corregido
    para que produzca "fallido" del turno, no un crash del proceso):
    turn_id ya guardado (ADR-005), turno sin contenido significativo
    (no vale una llamada a Ollama), o duplicado detectado por el índice
    único de Mongo al momento de insertar (dos ejecuciones concurrentes).
```
