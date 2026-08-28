# Nota de insumo externo: escrubery — fe de erratas de la matriz de adaptadores

**Estado:** informativo, no vinculante. No modifica ADRs, contratos ni specs de skopos.
**Fecha:** 2026-08-28. **Origen:** fe de erratas autorizada por el Mediador de escrubery
(2026-08-22); complementa la nota `insumo-escrubery-2026-08-22.md` de este directorio.

## Qué se notifica

El documento **Decisión de adaptadores** que skopos recibió el 2026-08-22 (enlazado en
la nota anterior) contenía un total errado en su resumen: donde dice **21 ok / 5 parcial
/ 9 nd**, la cifra válida es **20 ok / 5 parcial / 10 nd** sobre las 35 celdas de la
matriz (5 CLIs × 7 tipos de evento de conversación).

**Mecanismo del error (verificado por ejecución en escrubery):** la decisión CE-T5
cerró en 16/4/8 sobre 28 celdas (4 CLIs); la columna claude-code añadida por CE-T6
aporta 4 ok / 1 parcial / 2 nd, pero el resumen se actualizó como si aportara 5 ok y
1 nd. El detalle por celda y por mecanismo NO cambia — solo el total del resumen.

**Corrección en el repo de escrubery:** nota al pie fechada en el propio documento,
sin reescribir el histórico ni la release v0.5.0 — commit
[9049f5b](https://github.com/kristhianmanue1/escrubery/commit/9049f5b), documento en
[permalink 9049f5b](https://github.com/kristhianmanue1/escrubery/blob/9049f5b/docs/investigacion/probes/DECISION_ADAPTADORES.md).
El error lo detectó la ronda adversarial independiente del plan H9 (2026-08-22) al
recalcular la aritmética de la matriz; el plan H9 fue aparcado sin implementar, pero
la errata se corrigió igual por afectar a un consumidor externo.

## Impacto para skopos

- Si algún documento o trabajo de skopos citó el total de la matriz, usar **20/5/10**.
- El contenido que sí importa al roadmap de parsers (ADR-010) queda intacto: superficies
  por CLI, mecanismos observables, huecos (`turno_fallido` transversal, `sesion_cerrada`
  solo en cline) y decisiones de adaptador no cambian.
- La frontera del §9 del ADR-010 permanece: escrubery es insumo de referencia con
  procedencia, nunca autoridad de selección de parser.
