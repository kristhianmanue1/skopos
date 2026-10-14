# Sustituto de la periodicidad de respaldo fuera del chat Codex

Estado: **PROPUESTA para decisión del Operador**, 2026-10-13. Responde al
requisito registrado en
[mantenimiento H25.2](../evidencia/h252-mantenimiento-2026-10-06.md):
«ejecución periódica y seguimiento mediante un mecanismo sustituible,
independiente de proveedor/modelo/chat, con configuración, estado, registros y
alertas recuperables fuera del chat». No instala ni activa nada por sí misma.

## Contexto

- Los scripts locales (`runtime_operations.py`, `runtime_restore.py`) **no**
  dependen de Codex ni de OpenAI; la dependencia operativa está sólo en el
  **disparador** y su lógica de seguimiento (diaria 23:00, domingo ensayo,
  mensual solicitud de descarga), hoy en la automatización de chat
  `skopos-respaldo-y-recuperaci-n`.
- Sin validación desatendida observada desde su creación (ver
  [drill 2026-10-13](../evidencia/h252-restore-drill-2026-10-13.md): ningún
  respaldo nuevo desde el 6 de octubre, sin poder distinguir «sin cambios» de
  «no corrió»).

## Opción recomendada: launchd (LaunchAgent del usuario)

- **Qué**: un `LaunchAgent` por usuario (`~/Library/LaunchAgents/`) con dos
  `StartCalendarInterval` (diario 23:00; domingo 23:30 para el ensayo) que
  invoca `runtime_operations.py backup --if-changed` y, los domingos,
  `restore-latest`, con redirección de salida a un anillo de registros bajo la
  raíz privada y aviso por `osascript` (notificación) en fallo.
- **Por qué cumple el requisito**: configuración en un archivo versionable,
  estado y registros en disco local recuperables, sin proveedor, modelo ni
  chat; macOS nativo (cero dependencias nuevas); sobrevive al cierre del
  chat; se desactiva con `launchctl bootout` sin rastros.
- **Qué no resuelve**: ejecución con la sesión del usuario cerrada (eso sería
  un LaunchDaemon con root — no recomendado: las claves viven en el llavero
  del usuario); máquinas apagadas a las 23:00 (launchd no recupera corridas
  perdidas salvo `StartCalendarInterval` en sleep, que sí encola al
  despertar); el recordatorio mensual de descarga web sigue siendo una
  notificación que requiere intervención humana.

## Alternativas descartadas

- **cron**: sin estado, sin reintentos, deprecado por Apple en favor de
  launchd; mismo perfil de permisos de disco completo.
- **Automatizaciones de chat de otros proveedores**: reproduce exactamente la
  dependencia que el requisito manda eliminar.
- **Servicio residente propio (daemon Python)**: nuevo componente con ciclo
  de vida propio que vigilar; el proyecto no lo necesita para un horario de
  dos entradas.

## Plan de verificación si se autoriza

1. Instalar el LaunchAgent (archivo + `launchctl bootstrap gui/$(id -u)`).
2. Corrida manual inmediata del wrapper; comprobar registro, recibo y estado.
3. **Validación desatendida**: esperar una corrida iniciada por el horario
   (o adelantar el calendario en laboratorio) y observar arranque, acceso al
   llavero, término, verificación del servicio y registro — sin lanzamiento
   manual. Ese recibo es el que hoy falta.
4. Un domingo con ensayo de restauración desatendido y su reporte `pass`.
5. Retirar la automatización de chat Codex sólo después del paso 3–4, no
   antes.

Sin autorización explícita del Operador no se instala launchd ni se toca la
automatización existente.
