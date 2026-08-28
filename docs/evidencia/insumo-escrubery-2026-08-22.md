# Nota de insumo externo: escrubery — censo HRA y mapa de superficies de conversación

**Estado:** informativo, no vinculante. No modifica ADRs, contratos ni specs de skopos.
**Fecha:** 2026-08-22. **Origen:** decreto §11.6 del Mediador de escrubery (notificación
cruzada al existir el reporte; ambos repos comparten dueño — nota de independencia).

## Qué se notifica

El repositorio [escrubery](https://github.com/kristhianmanue1/escrubery) publicó el
2026-08-22 dos documentos relevantes para el roadmap multi-CLI de skopos (ADR-010):

1. **Reporte del censo Harness–Runtime Assurance** —
   [permalink 6ce8efa](https://github.com/kristhianmanue1/escrubery/blob/6ce8efa/docs/investigacion/hra/reporte-censo-2026-08-22.md):
   5 CLIs principales (claude-code, codex-cli, opencode, cline, kimi-code) × 8 normas
   de seguridad, cada celda clasificada con evidencia citable o `pendiente` (fail-closed).
   Incluye el estado del gate N9 (si el agente puede reescribir su propia config de
   permisos) por CLI — dato directamente relevante para la superficie de reparación y
   confianza de skopos.

2. **Decisión de adaptadores de conversación** —
   [permalink 6ce8efa](https://github.com/kristhianmanue1/escrubery/blob/6ce8efa/docs/investigacion/probes/DECISION_ADAPTADORES.md):
   mapa de los almacenes locales de historial de los mismos 5 CLIs con evidencia por
   mecanismo (dónde vive cada formato, qué eventos son observables, cuáles no, riesgos
   por superficie). Producido por probes read-only sobre historiales reales
   (metodología y reportes por CLI incluidos).

## Relación con el ADR-010 de skopos

Esta nota NO altera la frontera del §9 del ADR-010: escrubery sigue siendo dependencia
blanda e insumo de **referencia con procedencia**, nunca autoridad de selección de
parser ni bloqueante. El punto 2 es el insumo directo: el trabajo de reconocimiento
de los 5 formatos que la familia de parsers necesitará ya está hecho y citable —
skopos escribe los parsers en Python; el mapa del terreno existe.

## Reproducibilidad

Los probes son públicos y reproducibles
(`docs/investigacion/probes/<cli>-2026-08-2*.md` en escrubery). El censo se verifica
con fail-closed (`npm run hra:sellar`). Fase 1 del censo: 20/40 celdas con evidencia,
20 pendientes (corpus v1 en camino: estados `sin_garantia` ≠ `sin_medir`, eje de modo
de fallo).
