# Ronda adversarial — sustituto de periodicidad de respaldo — 2026-10-13

Objeto: `docs/propuestas/2026-10-13-sustituto-periodicidad-respaldo.md` (v1).
Método: revisor adversarial independiente (subagente sin contexto de autoría)
más verificación propia con sondas de solo lectura. Veredicto:
**fix-and-retry** — aplicado el mismo día: la propuesta fue reescrita como v2
incorporando el bloqueante y las correcciones; esta ronda documenta el ataque.

| # | Severidad | Hallazgo | Veredicto | Disposición en v2 |
|---|---|---|---|---|
| 1 | BLOQUEANTE | Un solo LaunchAgent no puede ejecutar `backup` y `restore-latest` por calendario: launchd corre las mismas `ProgramArguments` para todo disparo del job y no expone cuál disparó; un segundo disparo del mismo job en curso se descarta en silencio | Refuta el diseño v1 | Dos agentes con un disparo cada uno; el silencio se convierte en fallo registrado |
| 2 | MEDIO | Contención con ingesta a las 23:00: `flock` no bloqueante → `runtime_busy_retry_later` → SystemExit; ni script ni launchd reintentan; el respaldo del día se pierde | Corrige | Wrapper con reintento y backoff (obligación 3) |
| 3 | MEDIO | Entorno no especificado: `launchctl getenv PATH` vacío (verificado); exige intérprete absoluto de venv, `mongod` de Homebrew, `security`; `operate.py` es privado y no versionable | Corrige | Obligación 1 del wrapper; «versionable» acotado a plist/registro |
| 4 | MEDIO | Respaldo frío desatendido: si `start_and_verify` falla tras el `stop`, el 37030 queda caído hasta intervención; SIGTERM a media copia no pasa por el `finally` y la corrida siguiente aborta en `preflight` sin levantar el servicio | Corrige | Autocuración del wrapper (obligación 4); riesgo residual declarado |
| 5 | MEDIO | Semántica de suspensión imprecisa: launchd **coalesce** en una corrida al despertar (no «encola»); la corrida coalesced ejecuta respaldo frío a hora arbitraria | Afina | Redacción corregida en «Qué no resuelve» |
| 6 | MEDIO | Transición con dos disparadores activos: la «primera ejecución desatendida» puede ser de Codex, no de launchd; el camino `unchanged` no deja rastro en disco | Corrige | Paso 3 pausa Codex; obligación 2 registra toda corrida |
| 7 | BAJO | Ensayo dominical: precondiciones no listadas (`maintenance-state.json`, OneDrive hidratado, puerto 37033, llavero tras suspensión) | Afina | Paso 4 del plan de verificación |
| 8 | BAJO | `finally` de `restore_latest` sin manejo de señales: `wait` >30 s puede perder el `report.json` y conservar el keyfile | Afina | Riesgo residual declarado; arreglar código de producto queda fuera |
| 9 | BAJO | Descartes con paja: cron se descarta «sin reintentos» cuando launchd tampoco reintenta; el daemon resolvería reintentos y no se dice | Afina | Alternativas reescritas con los argumentos reales |
| 10 | NIT | «Sin rastros» falso: `bootout` deja plist y registros; «LaunchDaemon = root» impreciso (puede correr como usuario; el problema es el llavero sin sesión GUI) | Afina | Ambas frases corregidas |
| 11 | BAJO | Notificación `osascript` como aviso: con pantalla bloqueada/No molestar puede esperar horas — cercano al silencio que se critica del chat | Afina | Obligación 5: registro es evidencia, notificación es cortesía |

## Afirmaciones que resistieron el ataque

- «Los scripts locales no dependen de Codex ni OpenAI»: imports verificados
  (stdlib + pymongo + skopos + lanzador privado; cero APIs de modelo).
- «Apagado no recupera la corrida» y «ningún respaldo nuevo desde el
  2026-10-06»: verificados en disco (`backups/` con sólo los dos del 6 de oct;
  `maintenance-state.json` apunta a `c6d5f71e`).
- `mongod` existe en la ruta absoluta que el ensayo usa (`/opt/homebrew/bin`).

## Sondas ejecutadas

`sw_vers` (macOS 26.6.2), `which launchctl osascript security`, `launchctl
getenv PATH` (vacío), grep de imports/subprocess en los dos scripts, lectura
de `runtime_operations.py`/`runtime_restore.py` y de las evidencias de
mantenimiento y drill. Nada mutado.
