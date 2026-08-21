# Ronda 14 — verificación de fixes de la ronda 13 + residuos y corrección (2026-08-20)

**Objetos:** los cinco fixes de la ronda 13 (F-1..F-5). **Método:**
subagente independiente con contexto fresco, instruido a refutar los
fixes y verificar stop rules.

## Hallazgos y corrección

| Id | Nivel | Hallazgo | Destino |
|---|---|---|---|
| R-1 | MEDIO | Escape hatch residual en la forma congelada de `detalle`: "exige nueva versión del contrato **o extensión declarada**" — "extensión declarada" no existe como mecanismo y contradecía el encabezado de §3 | Eliminadas las tres palabras; sólo "exige nueva versión del contrato" (verificado: 0 matches de "extensión declarada" en el repo) |
| R-2 | BAJO | Tensión en §8: "ningún parser existente cambia" vs "la existente se enmienda" | Acotado: "ningún parser cambia" aplica a `cli_producto` nuevo; la enmienda de ficha del mismo producto lleva bump de `version_parser` |
| R-3 | BAJO | Colisión terminológica: §1(ii) "marcas de estructura que reconocen la versión" vs ficha con rol extracción/cierre | §1(ii) ahora dice "con su rol declarado por la ficha (extracción/cierre o reconocimiento de versión)"; ambos lados anotados |

## Ronda 15 — certificación (subagente independiente, misma fecha)

Verificó los tres fixes: **✓✓✓ sin regresión** (congelación §3
intacta, dos niveles intactos, ficha alineada, SPEC-006 coherente).
Comandos de cierre corridos por el revisor: `git diff --check` exit 0;
`git diff --exit-code -- docs/contratos/f1-contratos.md` exit 0;
`git diff --name-only` sólo `.md` autorizados; suite **102
descubiertos, OK, 0 saltados**; `git log -1` = `457d827`; ADR-010
propuesto con firma en blanco. Único hallazgo (MEDIO): la cita
"ronda 14 R-3" en ADR-010 §1(ii) no tenía acta — **resuelto por este
mismo documento**. Veredicto condicionado exclusivamente a este
registro.

## Estado

Paquete estable para presentación a Pinax y firma 🔒 del dueño. Sin
commit ni push.
