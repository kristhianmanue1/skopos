# Evidencia · remedición del ciclo del vigilante para C-10 (decisión 8)

Snapshot: **2026-08-20**, medido sobre el corpus real de
`~/.codex/sessions/` con el código de `main@222a522` (regla X-2: estado
fechado, no propiedad del repo). Compara contra el snapshot 2026-08-19
registrado en P-001 §4.9.

## Advertencia de comparabilidad (ronda 4, H1/H2)

Los timings de esta máquina varian por órdenes de magnitud con la carga:
el mismo día se midió el parseo completo en 9.5 s y en 50.8 s con load
average de 2 a 47 (la máquina corría trabajo pesado durante gran parte
del día). **Los tiempos no son comparables entre instantes sin el load
registrado al lado**; esta serie alimentará el gate de la Fase 3(b) y
debe leerse con esa regla. Los conteos (archivos, bytes, turnos) sí son
exactos y reproducibles bit a bit.

## Método

1. **Corpus**: conteo de archivos `*.jsonl` vía glob recursivo — el
   mismo patrón que `vigilante.descubrir_rollouts` (`rglob("*.jsonl")`;
   equivalencia empírica verificada: cero `.jsonl` no-rollout en el
   árbol, 612/612) — y suma de `os.path.getsize`.
2. **Costo de parseo por ciclo**: pasadas completas de `extraer_turnos`
   sobre todos los archivos ordenados (lo que `vigilante.ciclo` ejecuta
   por barrido antes de Mongo/Ollama). Se reportan varias pasadas con el
   load del momento.
3. **Costo de dedup por ciclo**: llamadas reales de `existe_turn_id`
   contra el Mongo local (colección con 0 documentos, índice compuesto
   `(turn_id, version)`), extrapoladas a los turnos del corpus.
4. **Ritmo de análisis**: `analizar_turno` real contra Ollama local
   (`qwen3:8b`), turnos reales de sesiones 2026-08-19/20. Dos tandas;
   primera llamada de cada tanda con timeout extendido (recarga del
   modelo documentada ~90 s, README). Contabilidad: 7 llamadas en
   total; 2 fallaron al timeout por defecto de 120 s (se reportan como
   fallos, no dentro del rango de éxitos); 5 exitosas que definen el
   rango 90–126 s.
5. **Tamaño de turno del corpus**: media y mediana de chars
   (`texto_usuario`+`texto_agente`) sobre los 14,822 turnos — para
   controlar el confounder de tamaño contra la línea base.

## Números (snapshot 2026-08-20)

| Métrica | Hoy 2026-08-20 (load al medir) | Snapshot 2026-08-19 (P-001 §4.9) |
|---|---|---|
| Rollouts | **612** | 609 |
| Volumen | **2.28 GB** (2,281,708,113 bytes) | 2.1 GB |
| Turnos cerrados | **14,822** (todos con `timestamp_cierre`, 0 ausentes — medido) | ~8k–19k (estimado) |
| Chars/turno del corpus | media **6,795**, mediana **2,780** | ~1,534 (42,958/28, sesión de la prueba) |
| Parseo por ciclo | **9.5–50.8 s** (load 2 → 47) | ~8 s (load sin registrar) |
| `existe_turn_id` | 0.16 ms/call en reposo; **4.85 ms** bajo load 28–54 (revisión independiente) → 2.4–72 s por ciclo | "orden de 10⁴ consultas" |
| Ritmo de análisis | **90–126 s/turno** (5 éxitos; 2/7 cayeron al timeout por defecto de 120 s) | 19.6 s/turno |
| Backfill completo | **~81 h** (× 19.6 s) a **~474 h** (× 115 s); ver advertencia | 40–100 h |

## Lecturas

1. **El ciclo excede su intervalo en cualquier carga medida**: entre
   9.5+2.4 ≈ 12 s (reposo) y 50.8+72 ≈ 123 s (load alto), contra
   intervalo por defecto de 5 s. El disparador de la Fase 3(b) sigue
   cumplido, ahora con remedición fechada y carga registrada.
2. **El contraste de ritmo 19.6 s → 90–126 s/turno es una cota superior
   sin control de confounders** (ronda 4, H1): la línea base eran
   turnos de ~1,534 chars; hoy se muestrearon 3,000–12,000 chars
   (media del corpus: 6,795), bajo carga alta, con recargas de modelo.
   No se afirma "empeoró 6×"; se afirma: **en el estado del entorno de
   hoy, el ritmo observado fue 90–126 s/turno**, y la causa exacta
   (carga vs tamaño vs Ollama) no se investiga aquí.
3. **La marginalidad del timeout de 120 s es función de la latencia por
   turno** (carga/recarga de Ollama), no del tamaño del corpus (H12):
   2 de 7 llamadas reales de hoy cayeron en él. Riesgo operativo
   registrado; su tratamiento no es parte de esta decisión.
4. **Conclusión para la decisión 8**: el backfill masivo es inviable
   como comportamiento por defecto en cualquier punto de la horquilla
   (81–474 h); los pilotos (Fase 3c/5) deben ser de sesión única.
