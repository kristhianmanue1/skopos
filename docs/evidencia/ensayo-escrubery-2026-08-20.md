# Evidencia · ensayo del canal escrubery (Fase 6, REQ-10)

Snapshot: **2026-08-20**, load average 6.6–9.4 al medir (regla X-2).
Primer ejercicio real de la integración (`analisis.py:_ficha_escrubery`)
contra el clon local `/Users/krisnova/www/aria/escrubery`, exigiendo
`escrubery_script` explícito, como dispone ADR-004 (opcional, nunca
bloqueante). Medición ejecutada por operador separado del implementador.

## Método

Llamadas directas a `scripts/consultar` (listar / ficha cli / ficha de
CLI inexistente) con `time.perf_counter`, más dos llamadas a la función
real `_ficha_escrubery` de Skopos en el venv del proyecto (timeout 30 s).

## Resultados

| # | Prueba | Resultado |
|---|---|---|
| 1 | `scripts/consultar` existe y es ejecutable | ✓ (`-rwxr-xr-x`) |
| 2 | `listar` incluye `codex-cli` | ✓ (entre 9 CLIs: antigravity-cli, claude-code, cline, codex-cli, grok-build, grok-cli-community, kimi-code, opencode, qwen-code) |
| 3 | `ficha cli codex-cli` (fría) | exit 0, **0.798 s**, stdout 10,922 bytes, JSON válido con `cli_producto`/`comandos`/`entidad` y bloque de `procedencia` por comando |
| 4 | 4 repeticiones calientes | 0.285/0.267/0.267/0.260 s — media **0.270 s** |
| 5 | `ficha cli no-existe-xyz` | exit 1, stdout JSON `{"error":{"codigo":"sin_datos",…}}` (77 bytes), **0.273 s** |
| 6 | `_ficha_escrubery('codex-cli', …)` real | dict con `entidad`/`cli_producto`/`comandos`, **0.53 s** |
| 7 | `_ficha_escrubery('no-existe-xyz', …)` real | **None sin excepción** (0.44 s) — camino "sin ficha" del CONTRATO consulta-escrubery-cli v1 y ADR-004 ✓ |

## Conclusiones

1. **Canal funcional de punta a punta**: ficha con procedencia, camino
   de fallo tolerado verificado (CLI sin ficha → None, sin excepción).
2. **Hallazgo de diseño confirmado con números (proyección aritmética,
   no medición por turno)**: el diseño actual consulta un subprocess por
   turno; a 0.270 s/call, un backfill de 14,822 turnos acumularía
   **~1.1 h de subprocess** para obtener la misma ficha 14,822 veces.
   La ficha no cambia por turno dentro de un CLI. **Recomendación
   (no implementada aquí, como dispone el plan)**: memoización por
   `(cli)` en la sesión del vigilante, o mover la consulta a la
   frontera de sesión. Requiere un cambio mínimo en `analisis.py`
   cuando el uso real lo pida.
3. Escrubery aporta la verdad versionada del CLI (fichas con
   procedencia); los parsers los escribe Skopos — límite respetado.
