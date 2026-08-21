# Evidencia · tamaño de fragmentos del corpus para C-6 (ADR-009)

Snapshot: **2026-08-20**, medido sobre el corpus real de
`~/.codex/sessions/` con el código de `main@8d57842` (regla X-2).

## Método

Suma de bytes entre offsets (`offset_fin − offset_inicio`) de todos los
turnos extraídos con `extraer_turnos` sobre el corpus completo (mismo
glob recursivo que `descubrir_rollouts`). El turno cubre todos los bytes
del archivo entre su inicio y su cierre — incluidas líneas que no son
mensaje (turn_context, event_msg intermedios): es la unidad que
`skopos query` sirve hoy como `fragmento_completo`.

## Números

| Métrica | Valor |
|---|---|
| Turnos medidos | 14,824 |
| Fragmentos totales | **2.28 GB** (2,281,373,335 bytes) |
| Por turno: media | 150 KiB |
| Por turno: mediana | 62 KiB |
| Por turno: p95 | 456 KiB |
| Por turno: máximo | **41.3 MiB** (3 turnos exceden el límite BSON de 16 MiB) |

## Verificación de la ronda 6 (revisión independiente)

- La suma de `st_size` del corpus ese día fue 2.288 GB: los fragmentos
  cubren el **99.8%** del corpus — coherente **por construcción**: los
  offsets de los turnos teselan `[0, fin del último cierre)` sin huecos.
  Consecuencia para ADR-009/P4a: el hash del fragmento basta para
  detectar rotación/edición/truncación del archivo; sellar el archivo
  entero daría falsos positivos ante appends de sesiones vivas.
- Turnos recontados por el revisor el mismo día: 14,831 (corpus vivo,
  +7 — esta sesión incluida). Snapshot consistente.
- Distribución: 46.5% de los turnos excede 64 KiB (insumo para el
  default del tope de la palanca P5).
