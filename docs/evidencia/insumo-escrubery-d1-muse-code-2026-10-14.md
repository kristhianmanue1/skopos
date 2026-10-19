# Nota de insumo externo: escrubery — muse-code cruza D1 (veredicto decretado) + 8º proveedor typesafe

**Estado:** informativo, no vinculante. No modifica ADRs, contratos ni specs de skopos.
**Fecha:** 2026-10-14. **Origen:** veredicto D1 decretado por el Mediador de escrubery
(mismo día); complementa las notas `insumo-escrubery-2026-08-22.md`,
`insumo-escrubery-verificacion-2026-08-22.md` e
`insumo-escrubery-errata-adaptadores-2026-08-28.md` de este directorio. Disparador
declarado en escrubery el 2026-10-13: «muse-code cruza D1/verificación activa».

## Qué se notifica

**1. muse-code cruzó D1.** El 10º CLI del catálogo de escrubery (Meta, binario
cerrado `muse`) pasó de estado **parcial** a **curado** en
`docs/investigacion/tos-clis.md`, y su Fase 3 (introspección activa) quedó
**desbloqueada con condiciones** por decreto del Mediador. Base: lectura completa
del ToS legal («Meta Model API Terms of Service», last updated 2026-10-09) y del
AUP en `dev.meta.ai/legal` — renderizado server-side, texto íntegro, capturas
crudas con hash (`terms-of-service c3674f86…`, `acceptable-use-policy a13eb020…`,
`geographic-use-policy 3248b319…`), citas verificadas contra el HTML.

Condiciones del veredicto (resumen):

- Automatización permitida: ToS §6.2 «The Services are offered programmatically»
  + docs de producto (`muse exec` headless/CI de primera clase).
- Benchmarking solo evaluación/calidad propia (§10.1(ix) lo permite
  explícitamente); publicación de benchmarks con la condición §10.1(xi)
  declarada en fichas (solo está restringido si es para promover un producto
  competidor).
- Extracción limitada a Outputs propios (§10.1(ii)); reverse-engineering/probing
  prohibido (§10.1(x)).
- Sin contenido sensible/confidencial mientras la cuenta esté en modo
  Contributor (§6.2 + §3.3: Contributor por defecto en suscripción del harness,
  cambio prospectivo).

**2. 8º proveedor `typesafe` incorporado al catálogo de modelos** (mismo día,
commit `556d3f4`). System One/Jev: modelos de decisión estructurada
(`mode: evaluation` en LiteLLM) que no generan texto. Cambios de contrato en
escrubery: enum §2.2 += `typesafe`; **errata 10** — campo nuevo `modo`
(`chat|responses|evaluation|null`) en `consultar_modelo`. Política de datos
confirmada por docs oficiales: no entrena con contenido de clientes
(Privacy Policy literal) + ZDR enterprise.

## Impacto para skopos

- Parsers ADR-010 que lean el estado ToS de CLIs (`tos-clis.md`): muse-code
  sirve ahora como **curado**, no parcial. La ficha del CLI sigue declarando
  que ningún comando está verificado aún por introspección (F3 sobre muse-code
  aún no se ejecuta: espera la migración de introspección a servidor).
- Parsers que validen el enum de proveedores del contrato v0 §2.2 contra lista
  cerrada: la lista creó un octavo valor (`typesafe`). El campo `modo` es
  aditivo — consumidores que ignoren campos desconocidos no se ven afectados.
- Nada de esto requiere acción inmediata de skopos; es aviso de estado para que
  ningún parser se sorprenda.

## Anclajes en escrubery

- Veredicto D1: commit
  [04c4194](https://github.com/kristhianmanue1/escrubery/commit/04c4194)
  (`docs/investigacion/tos-clis.md` § muse-code, citas + hashes).
- Incorporación typesafe: commits
  [556d3f4](https://github.com/kristhianmanue1/escrubery/commit/556d3f4) y
  [cf122c3](https://github.com/kristhianmanue1/escrubery/commit/cf122c3)
  (contrato errata 10, mig 016, política de datos, curaduría de aliases).
- Cabeza de escrubery a la fecha de esta nota:
  [fd8a54a](https://github.com/kristhianmanue1/escrubery/commit/fd8a54a).
