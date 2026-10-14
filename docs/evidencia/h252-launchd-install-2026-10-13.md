# H25.2 — instalación launchd de la periodicidad de respaldo — 13 de octubre de 2026

Estado: instalada y verificada manualmente conforme a la [propuesta v2]
(../propuestas/2026-10-13-sustituto-periodicidad-respaldo.md), autorizada por
el [acta de decisiones](acta-decisiones-operador-2026-10-13.md) (decisión 3).
Pendiente: la **primera corrida desatendida** observada (hoy 23:00 si el
equipo sigue encendido) y el **ensayo dominical**. La pausa de la
automatización de chat Codex durante la validación es acción del Operador.

## Componentes instalados (fuera del repo, en raíz privada y LaunchAgents)

| Pieza | Ruta | SHA-256 |
|---|---|---|
| Wrapper (5 obligaciones v2) | `~/Skopos-private/runtime-v3/launchd_wrapper.py` | `4375a06d…75b957` |
| Agente respaldo (diario 23:00) | `~/Library/LaunchAgents/skopos.runtime.backup.plist` | `c6e9ca12…9d7f49` |
| Agente ensayo (domingo 23:45) | `~/Library/LaunchAgents/skopos.runtime.drill.plist` | `24856814…a889a` |

Ambos plists validados con `plutil -lint` y arrancados con `launchctl
bootstrap gui/$(id -u)`; `launchctl list` los muestra con exit 0. Intérprete
absoluto de la venv (PATH de launchd vacío, verificado en ronda). El wrapper
registra **toda** corrida —incluido `unchanged`— en
`launchd-logs/runs.jsonl` + `latest.json` (0700), reintenta ante
`runtime_busy_retry_later` (3 intentos en ~45 min), autocura el 37030 caído y
avisa por notificación sólo en fallo o cambio.

## Corrida manual de verificación (paso 2 del plan) — PASS

Ejecutado `launchd_wrapper.py backup` a las 2026-10-14T03:32Z:

- **Autocuración ejercitada**: el 37030 estaba detenido; el wrapper lo
  arrancó vía el lanzador privado (`self_heal_start`, PID 96249) y quedó
  operativo.
- `backup --if-changed` devolvió `unchanged` — huella lógica idéntica al
  respaldo del 2026-10-06 (sin ingesta desde entonces): correcto, y la corrida
  quedó registrada igualmente. **La ambigüedad "sin cambios vs no corrió"
  queda cerrada**: desde hoy toda corrida deja rastro en el anillo local.
- Exit 0; sin notificación (estado sin cambios no accionable, por diseño).

## Lo que queda por observar (pasos 3–4)

1. **Desatendida diaria**: corrida iniciada por el horario 23:00 sin
   intervención; su registro en `runs.jsonl` con `observed_at` fuera de
   horas de sesión será el recibo. Requiere equipo encendido, sesión activa y
   llavero accesible.
2. **Ensayo dominical** 23:45 (precondiciones del wrapper: estado de
   mantenimiento presente, OneDrive legible, 37033 libre, llavero accesible).
3. Retiro de la automatización de chat Codex **sólo después** de 1–2, con la
   pausa ya activa durante la validación (acción del Operador en su chat).
