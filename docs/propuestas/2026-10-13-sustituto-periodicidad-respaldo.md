# Sustituto de la periodicidad de respaldo fuera del chat Codex

Estado: **PROPUESTA v2 para decisión del Operador**, 2026-10-13. La v1 fue
sometida a
[ronda adversarial](../rondas/2026-10-13-ronda-sustituto-periodicidad.md)
el mismo día: un hallazgo bloqueante (un solo agente launchd no puede ejecutar
comandos distintos por calendario) y ocho correcciones/afinados, todos
incorporados aquí. Responde al requisito registrado en
[mantenimiento H25.2](../evidencia/h252-mantenimiento-2026-10-06.md):
«ejecución periódica y seguimiento mediante un mecanismo sustituible,
independiente de proveedor/modelo/chat, con configuración, estado, registros y
alertas recuperables fuera del chat». No instala ni activa nada por sí misma.

## Contexto

- Los scripts locales (`runtime_operations.py`, `runtime_restore.py`) **no**
  dependen de Codex ni de OpenAI (verificado en imports y subprocess); la
  dependencia operativa está sólo en el **disparador** y su seguimiento (diaria
  23:00, domingo ensayo, mensual solicitud de descarga), hoy en la automatización
  de chat `skopos-respaldo-y-recuperaci-n`.
- Sin validación desatendida observada desde su creación (ver
  [drill 2026-10-13](../evidencia/h252-restore-drill-2026-10-13.md): ningún
  respaldo nuevo desde el 6 de octubre, sin poder distinguir «sin cambios» de
  «no corrió»).

## Opción recomendada: dos LaunchAgents de usuario con wrapper propio

- **Qué**: dos agentes launchd por usuario (`~/Library/LaunchAgents/`), cada
  uno con un solo `StartCalendarInterval` — `backup` diario 23:00 y
  `restore-drill` domingo 23:45 — que invocan a un **wrapper** (shell/python,
  en la raíz privada junto a `operate.py`, no en el repo) con el intérprete
  absoluto de la venv. launchd ejecuta las mismas `ProgramArguments` para todo
  disparo de un job: dos comandos distintos exigen dos agentes; además, un
  segundo disparo del mismo job mientras corre el primero se descarta en
  silencio, y dos agentes convierten ese silencio en un fallo registrado.
- **Obligaciones del wrapper** (lo que la v1 omitía):
  1. **Rutas absolutas**: `launchctl getenv PATH` está vacío; venv python,
     `/usr/bin/security`, `/usr/bin/osascript`, `mongod` de Homebrew.
  2. **Registrar TODA corrida** —incluido `unchanged`— en un anillo de
     registros en la raíz privada: es la única fuente de atribución, porque el
     camino `unchanged` de `--if-changed` no escribe nada en disco.
  3. **Reintentar con backoff** ante `runtime_busy_retry_later` (p. ej. tres
     intentos en 45 min): sin esto, una ingesta a las 23:00 cuesta el respaldo
     del día, porque ni el script ni launchd reintentan.
  4. **Autocuración**: si al arrancar el Mongo operativo (37030) está caído,
     intentar `start_and_verify` **antes** de declarar fallo — hoy un SIGTERM a
     media copia (apagado, reinicio) deja el servicio detenido y la corrida
     siguiente aborta en `preflight` sin levantarlo.
  5. **Avisar por `osascript`** en fallo, declarando su límite: con pantalla
     bloqueada o No molestar la notificación puede esperar horas; el registro
     local es la evidencia, la notificación es cortesía.
- **Por qué cumple el requisito**: configuración y registros en disco local
  recuperables, sin proveedor, modelo ni chat; macOS nativo (launchd incluido;
  `mongod` de Homebrew es dependencia de sistema ya existente, no nueva);
  sobrevive al cierre del chat; se retira con `launchctl bootout` + borrar el
  plist (los registros del anillo persisten y son la historia).
- **Qué no resuelve**: ejecución con la sesión del usuario cerrada (requeriría
  LaunchDaemon sin sesión GUI, donde el llavero del usuario no está disponible
  — el problema es el contexto de llavero, no root); equipo **apagado** a la
  hora programada (corrida perdida sin recuperación); en **suspensión**,
  launchd coalesce los eventos perdidos en **una** corrida al despertar — a
  hora arbitraria, posiblemente con ingesta activa (el reintento del wrapper
  absorbe la contención) y con el llavero aún bloqueado si la sesión no se
  desbloquea (el fallo queda registrado con aviso, no silencioso); el
  recordatorio mensual de descarga web sigue siendo notificación que requiere
  intervención humana.

## Alternativas descartadas

- **cron**: mismo disparo único sin reintentos que launchd; a su favor, ni
  coalescing tras suspensión ni entorno mínimo de PATH; en contra, manejo de
  entorno y estado más pobre y desuso por parte de Apple. El descarte real es
  por coalescing y entorno, no «porque no reintenta» — launchd tampoco.
- **Automatizaciones de chat de otros proveedores**: reproduce exactamente la
  dependencia que el requisito manda eliminar.
- **Servicio residente propio (daemon Python)**: resolvería reintentos,
  serialización respaldo/ensayo y colas reales — a cambio de un componente con
  ciclo de vida propio que vigilar. Para dos entradas de calendario no se
  justifica hoy; si el calendario crece, reabrir esta opción.

## Plan de verificación si se autoriza

1. Instalar los dos LaunchAgents y el wrapper (raíz privada), con `launchctl
   bootstrap gui/$(id -u)`.
2. Corrida manual inmediata del wrapper; comprobar registro, recibo y estado.
3. **Pausar la automatización de chat Codex durante la validación** (si no,
   ambos disparadores contienden a las 23:00 y la «primera ejecución
   desatendida» observada puede ser la de Codex, no la de launchd — el recibo
   quedaría sin atribución). Validación desatendida: una corrida iniciada por
   el horario, sin lanzamiento manual, con arranque, acceso al llavero,
   término, verificación del servicio y registro propios.
4. Un domingo con ensayo de restauración desatendido y reporte `pass`;
   precondiciones del ensayo verificadas por el wrapper: `maintenance-state.json`
   presente, archivo OneDrive legible (hidratado si usa Files-On-Demand), puerto
   37033 libre, llavero accesible.
5. **Retirar la automatización de chat Codex** sólo después de 3–4, no antes.

## Riesgos residuales declarados

`restore_latest` escribe su reporte y borra el keyfile en un `finally` sin
manejo de señales: un `wait` que exceda 30 s puede dejar la corrida sin
`report.json` (probabilidad baja, documentada; arreglarlo toca código de
producto con tests propios y no bloquea esta propuesta). El descarte del
ensayo dominical por contención con un respaldo largo produce fallo registrado
y aviso — aceptable a estas horas de carga. Sin autorización explícita del
Operador no se instala launchd, no se escribe el wrapper ni se toca la
automatización existente.
