# Ronda 20 — adversarial sobre el registro del commit de cierre (2026-08-21)

**Objeto:** acto documental autorizado por el dueño: registro del SHA
real de cierre de Fase 7 en plan y hoja-de-ruta, sin commit ni push.
**Método:** subagente independiente con contexto fresco.
**Veredicto: PROCEED.**

## Verificado

1. SHAs ✓ — corto `fc37a90` y completo
   `fc37a9068aab03e49445c354c759181d627f43d5` = `git rev-parse HEAD`;
   tree citado `55386a4327015d85c887c5cfdf190ca6dec09c3f` =
   `HEAD^{tree}`; padre `457d827` = `HEAD^`. Escritos en plan (tabla +
   sección Fase 7) y hoja (Hito 12).
2. Atribución ✓ — el SHA se atribuye al commit de cierre de Fase 7
   (subject real: "docs: aceptar ADR-010 y cerrar Fase 7"), nunca al
   acto registral; "único commit del acto" es exacto.
3. Alcance ✓ — diff del acto: sólo `docs/hoja-de-ruta.md` y
   `docs/planes/plan-ciclo-precondiciones.md` (más este acta tras el
   veredicto); README/ADR/SPEC/f1-contratos/código intactos.
4. Implementación sigue no autorizada ✓ (plan y hoja lo conservan
   explícito).
5. Fase 7 permanece cerrada documentalmente ✓.
6. Sin push ✓ — `main...origin/main [ahead 22]`: fc37a90 y los 21
   commits locales precedentes NO están en origin.

## Observación preexistente (no introducida por este acto, fuera de
alcance, ya asentada)

`hoja-de-ruta.md` dice "rondas 10–18" y el plan "rondas 10–17" — la
dualidad paquete-vs-acto fue el H-1 de la ronda 19 (lectura veraz en
ambos lados).

## Comandos (corridos por el revisor)

```
git rev-parse HEAD            → fc37a9068aab03e49445c354c759181d627f43d5
git rev-parse HEAD^           → 457d8276f0b6803a8062ca1d308c8c176d7cff8e
git rev-parse 'HEAD^{tree}'   → 55386a4327015d85c887c5cfdf190ca6dec09c3f
git status -sb                → ## main...origin/main [ahead 22] + 2 M
git diff --name-status        → M hoja-de-ruta · M plan
git diff --exit-code -- docs/contratos/f1-contratos.md → exit 0
git diff --check              → exit 0
unittest discover             → Ran 102 tests — OK (102 descubiertos, 0 saltados)
```
