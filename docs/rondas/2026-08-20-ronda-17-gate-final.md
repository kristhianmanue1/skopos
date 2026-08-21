# Ronda 17 — gate adversarial final sobre el artefacto post-F1 (2026-08-20)

**Objeto:** paquete ADR-010 + SPEC-006 (base `457d827`, sin commitear)
tras F1 (unión cerrada de `detalle`, reflejada en ADR y SPEC con casos
positivos/negativos) y F2 (acta 16 asentada desde la transcripción
auténtica, alcance pre-F1 declarado).
**Revisor:** subagente independiente con contexto fresco, instruido a
intentar refutar los 10 puntos exigidos por el dueño.
**Veredicto: PROCEED.**

## Hallazgos (3, todos BAJO, no bloqueantes — no corregidos para no
invalidar esta certificación con cambios post-revisión; registrados
como trabajo futuro documental)

| Id | Nivel | Hallazgo | Destino |
|---|---|---|---|
| F-1 | BAJO | «ronda de cierre» etiqueta a F1 como si fuera ronda; F1 es corrección del dueño, no ronda con acta propia | Futuro: reetiquetar o asentar acta de F1 en la próxima pasada documental |
| F-2 | BAJO | Lectura secuencial literal de Nivel B reglas 2/3 empata si dos versiones casan y una está retirada — el desempate vive en la cláusula de precedencia + precondición §8, no en el número de regla | Futuro: glosar el desempate en una frase |
| F-3 | BAJO | SPEC-006 cita «campos de SPEC-001 (incluidos … cli …)» pero SPEC-001 no enumera `cli` en el Turno (lo tienen el código y ADR §5) — nit preexistente en la base | Futuro: alinear el paréntesis o enumerar `cli` en SPEC-001 (toca spec vigente: exige cuidado de compatibilidad) |

## Los 10 puntos, veredicto del revisor

1. Paridad exacta ADR↔SPEC ✓ (unión de `detalle` equivalente en norma;
   8 campos idénticos; precedencia idéntica; protocolo §5; dos niveles)
2. Unión cerrada de `detalle` ✓ (ninguna cuarta forma; contraejemplos
   `{candidatos}` sin `codigo`, claves extra, `{codigo:"foo"}`, texto
   libre, `{}` — todos rechazados por la unión «nada más»)
3. Obligatoriedad/prohibición de `candidatos` ✓ (dos exigen, tres
   prohíben, mismos literales en ambos)
4. Cardinalidad/unicidad/orden ✓ («≥2», «sin duplicados»,
   «lexicográfico» en ambos; casos cubren required/forbidden/
   cardinalidad/duplicados/orden)
5. Precedencia diagnóstica ✓ (única, testeable, gobierna ambos niveles)
6. Selección producto→versión ✓ (agrupación por cli_producto; nunca por
   orden; perfil base v1 honesto)
7. Protocolo de lectura de una apertura ✓ (fstat del mismo descriptor;
   límites declarados; tamaño+mtime sigue prohibido como comparación)
8. Riesgos residuales declarados ✓ (los tres, sin empeorar)
9. Autenticidad y continuidad de las actas ✓ (0–16 completas; acta 16
   con nota de asiento F2 y alcance pre-F1; toda cita tiene acta;
   ninguna cita a ronda inexistente)
10. Stop rules y alcance documental ✓ (sólo `.md` autorizados;
    f1-contratos.md intacto; ADR propuesto, firma en blanco;
    `git log -1` = 457d827; suite 102 descubiertos, OK, 0 saltados;
    `git diff --check` limpio)

## Retirados por el revisor (constancia)

- «cuando aplique» como cuarta forma — su contexto es `lectura_corta`,
  no `candidatos`.
- `detalle = {}` sin caso negativo — excluido por la unión «nada más».
- Residuos (2)/(3) ausentes de SPEC — el ADR es el registro de
  decisión; la SPEC no los contradice.
- «extensión declarada» — 0 en ADR/SPEC; los matches son citas en
  actas que documentan la eliminación.
- `cli` no listado en SPEC-001 — preexistente en la base, conservado
  como F-3/BAJO.

## Comprobación de integridad post-acta

Este acta es el **único cambio posterior a la revisión**: la salida de
la ronda 17 verificó el árbol de trabajo y su captura de
`git status`/`name-only` coincide con el actual salvo por la adición de
este archivo (verificado en el reporte final del agente con los gates
corridos tras el asiento).
