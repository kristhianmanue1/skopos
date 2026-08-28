# Evidencia · el `turn_id` crudo de Codex NO es único: 35 % de los turnos se perderían

**Fecha:** 2026-08-28. **Severidad: ALTA — afecta a producción, no sólo
a P-004.** Encontrado al medir el piloto del índice de turnos: la ingesta
reportó 5,860 turnos "ya estaban" en un corpus donde nada estaba.

## El hallazgo

Sobre el corpus real de Codex (`~/.codex/sessions`, 645 archivos):

| Medida | Valor |
|---|---|
| Turnos extraídos | **16,301** |
| `turn_id` distintos | **10,441** |
| **Turnos que la dedup por `turn_id` descartaría** | **5,860 (35 %)** |
| Ids repetidos **dentro** de la misma sesión | **0** |
| Ids repetidos en **sesiones distintas** | **947** |

Y no son el mismo turno registrado dos veces: de los 947 ids repetidos,
**768 tienen texto distinto** en cada aparición. Ejemplo:
`019f658c-ee4a-7ed3-9267-58aa359f9886` aparece en el rollout del
2026-07-15 con 10,085 caracteres y en el del 2026-07-23 con 9,550.

## Qué contradice

**ADR-010 §7** permitió a parser-codex usar **id crudo** como
"excepción compatible y probabilística", justificada con evidencia de
unicidad (UUIDv7, verificación de la ronda 10) y con una condición
explícita: *"revisable a calificada si aparece un
contraejemplo/canario"*.

**Este es el contraejemplo.** El id es único dentro de una sesión, pero
**se repite entre sesiones** — probablemente por reanudación o
bifurcación de sesiones, donde el rollout nuevo re-registra turnos del
anterior con contenido editado.

## Por qué afecta a producción hoy

No es un problema del índice nuevo: es del pipeline vigente.

- **`existe_turn_id`** (dedup de ADR-005) daría por visto un turno que
  nunca se analizó, porque otro turno distinto usó ese id antes.
- El índice único **`(turn_id, version)`** de ADR-007 impide guardarlo:
  el segundo turno sólo cabría como "versión nueva" del primero, que es
  semánticamente falso — no es otro análisis del mismo turno, es **otro
  turno**.
- Resultado: **35 % de la conversación de Codex es ininsertable** y
  desaparece sin diagnóstico. Es exactamente el modo de fallo que el
  contrato de parsers existe para impedir.

Hoy el daño real es nulo porque `skopos.analisis` tiene 8 documentos.
En cuanto se ingiera de verdad, deja de serlo.

## La corrección que funciona, verificada

Calificar la identidad con la sesión, como ADR-010 §7 ya prevé para los
adaptadores nuevos:

```
turn_id := "codex-cli:" session_id ":" turn_id_bruto
```

Medido sobre el mismo corpus: **16,301 ids únicos, 0 colisiones.**
Separa exactamente los 5,860 turnos que hoy se pierden.

Coste de migración: **trivial hoy** — 8 documentos en `skopos.analisis`,
de los cuales uno solo referencia un archivo real. Dentro de un mes, con
el índice lleno, no lo sería.

## Qué exige

Cambiar la estrategia de identidad de parser-codex/v1 toca la **ficha
del ADR-010 §8** y la excepción del **§7**, ambos aceptados 🔒. El propio
ADR pre-autorizó la revisión *con evidencia* — esta es la evidencia—,
pero el acto sigue siendo del dueño.

**Recomendación:** aplicarlo antes de llenar el índice de P-004. Indexar
19,811 turnos con una identidad que se sabe rota, para migrarla después,
es pagar dos veces.
