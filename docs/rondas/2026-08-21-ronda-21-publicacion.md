# Ronda 21 — adversarial de publicación del lote origin/main..fb37414 (2026-08-21)

**Objeto:** el lote completo de 23 commits del ciclo Fases 0–7
(origin/main..fb37414), como gate previo a solicitar autorización de
push.
**Método:** subagente independiente con contexto fresco, que no
intervino en el ciclo; verificaciones con git diff/show por commit,
lectura de diffs de src/tests/contratos, corrida de suite y fetch del
remoto.
**Veredicto: PUBLICABLE — procede solicitar autorización de push.**

## Hallazgos (5, ninguno BLOCKER/ALTO)

| Id | Nivel | Hallazgo | Clasificación/propuesta |
|---|---|---|---|
| H-1 | MEDIO | README:56 describe `docs/propuestas/` como "análisis abiertos, sin decidir (P-001…)" — desactualizado: P-001 superada, P-002 aprobada (2026-08-20). Sobrevivió a los greps de unanimidad porque éstos apuntaban a Fase 7 | Cosmético-registral. Propuesta acotada (NO aplicada): commit de una línea en un futuro acto ("docs: propuestas/ ya decididas"), antes o después del push |
| H-2 | BAJO | `git diff --check origin/main..HEAD` da 2 incidencias (trailing whitespace ADR-008:26; blank-line EOF ensayo-escrubery:52). Las actas 19/20 registraron exit 0 sobre diffs más angostos (vs 457d827) — veraz pero no equivalente al gate del lote completo | Cosmético. Relevante sólo si algún día se automatiza el gate; exigiría commit adicional (el lote no se reescribe) |
| H-3 | BAJO | 27c1332 usa prefijo `feat:` sin cambios de código (entregable C-5 = evidencia) | Estilo histórico; sin acción |
| H-4 | BAJO | El árbol de fb37414 (`e954a5d6…`) no consta en acta — auto-registro imposible (estructura: el acta 20 vive dentro del commit que registra a fc37a90) | Estructural. Propuesta acotada: esta ronda 21 queda asentada en un acto futuro con autorización; el veredicto del lote no depende de ello |
| H-5 | BAJO | Numeración salta la "15" (la ronda 15 vive como sección del acta 14; la 16 es asiento tardío documentado) | Ya explicado en el propio repo; sin acción |

## Los 9 puntos de la misión (veredicto del revisor)

1. Publicable como unidad ✓ (arco coherente apertura→fases→cierre;
   mensajes vs contenido verificados commit a commit; cronología
   monótona; sin huérfanos).
2. Decisiones 🔒 respaldadas ✓ (ADR-007/008/009/010: aceptados con
   firma/fecha; secuencias propuesto→feat🔒→cierre trazables; exigencias
   de las firmas verificadas: enmienda ADR-005 dentro del commit de
   aceptación de ADR-008; sello P4a ANTES de la primera ingesta del
   piloto — restricción de orden honrada; riesgo timeout registrado).
3. Runtime ↔ fases aceptadas ✓ (sólo 5 commits tocan src/tests: los 4
   feat aceptados + 1 fix de test; `git diff fc37a90..HEAD -- src/
   tests/` = vacío: cero implementación multi-CLI encubierta; en
   captura.py NO existe detección/predicados/ResultadoParseo — SPEC-006
   aceptada sin implementar, como se declaró).
4. Pruebas ejercitan el runtime ✓ (102 descubiertos, OK, 0 saltados;
   cobertura verificada por cambio: proyecto/supersede/reanalizar/
   t0-backfill/sello/estados/--max; saltos condicionados sólo a
   MongoDB:27017 y Ollama:11434).
5. Árbol libre de accidentales ✓ (.an-kla/ gitignored y jamás
   commiteado; sk-AAA… = fixtures falsos con assertNotIn deliberados;
   rutas personales sólo en evidencias + 1 dato medido citado;
   pyproject sin cambios; imports nuevos = stdlib + pymongo.errors ya
   declarado).
6. Remoto ✓ (fetch + rev-list: 23 ahead / 0 behind exactos).
7. Historia limpia ✓ (0 merges; padres fc37a90→457d827,
   fb37414→fc37a90; árbol de fc37a90 coincide con acta 20).
8. Gates canónicos ✓ con H-2 anotado (2 incidencias de whitespace en
   el diff completo del lote); f1-contratos.md revisado hunk a hunk:
   todo atribuible a C-9/ADR-007/ADR-009 con sus etiquetas, incluido
   el nuevo contrato cli-skopos-reanalizar.
9. AN-KLA ✓ (único uso = memoria local gitignored + P-001 superada;
   cero presencia en src/pyproject; jamás autoridad ni dependencia).

## Verificaciones del auditor principal (comandos literales)

```
git rev-parse HEAD            → fb37414b61bd3620450caa958319f3c76a0183eb
git status --short            → (vacío)
git rev-list --count origin/main..HEAD → 23
git rev-list --count HEAD..origin/main → 0
git log --oneline origin/main..HEAD    → 23 commits (apertura → registro)
git diff --stat origin/main..HEAD      → 52 archivos, +5515/−134
  por tipo: 39 .md · 12 .py · 1 .gitignore
git diff --name-status -- src/ tests/ pyproject.toml → 12 M en src+tests; pyproject: 0 líneas
git log --merges → 0
grep de secretos → sólo fixtures falsos de tests de redacción
unittest discover → Ran 102 tests — OK (102 descubiertos, 0 saltados;
  servicios requeridos: MongoDB localhost:27017, Ollama localhost:11434)
```

## Riesgos residuales

1. H-1: lector fresco podría creer la integración AN-KLA pendiente
   (commit de una línea lo cierra, a discreción del dueño).
2. H-2: 2 incidencias de whitespace si el gate se automatiza algún día.
3. Suite dependiente de servicios locales para 8 pruebas (en CI sin
   ellos correría con saltos, no fallos).
4. Deuda documental F-1/F-2/F-3 (ronda 17) — registrada, no bloqueante.

## Nota de transparencia (añadida en el acto de saneamiento, por orden del dueño)

El encargo de la ronda 21 era **read-only**; el objeto auditado fue el
**árbol limpio en `fb37414`**. Este acta fue **creada después** de
auditar ese objeto — por ello, la confirmación final del reporte
("sin cambios") fue **incorrecta respecto del worktree entregado**: la
creación del acta dejó un archivo no rastreado. La creación no cambió
el contenido del objeto auditado (el lote `origin/main..fb37414`
permanece exactamente el que se certificó), pero la afirmación de
"sin cambios" debió referirse sólo al objeto. La incorporación de este
archivo al historial queda autorizada exclusivamente mediante el acto
de saneamiento del dueño que la ordena (2026-08-21). La incidencia se
registra, no se oculta.

## Conclusión

**Procede SOLICITAR autorización de push.** Ninguna corrección se
aplicó en este acto (encargo read-only; hallazgos clasificados con
propuesta acotada, sin ejecutar).
