# H25.2 — mantenimiento coordinado y Llavero

AMENDS las propuestas de continuidad de `h252-recuperacion-nube-2026-10-06.md`
y el pendiente de transporte largo de `h252-llavero-respaldo-2026-10-06.md`.
Autoridad: Operador, «adelante con las tres recomendaciones». Alcance:
perfil local monousuario, no aceptación de relevancia ni cierre global de H25.

## Implementación y operación

`scripts/runtime_operations.py` coordina el respaldo mediante `flock` exclusivo
no bloqueante compartido con el lanzador privado `operate.py`. Verifica dbPath,
puerto 37030, primario, envolturas y hashes antes de parar el Mongo dedicado.
Copia db y sources con Mongo detenido, rechaza enlaces, intenta reiniciar incluso
si falla la copia y verifica estado lógico antes de publicar. Sólo después de
copia y hashes correctos avanza `maintenance-state.json`. Cada corrida conserva
`operation.json`; los fallos no se convierten en éxitos.

La exclusión es cooperativa: todos los escritores deben usar el lanzador privado.
No aísla clientes directos ni procesos del mismo UID. `finally` cubre excepciones,
no muerte abrupta del proceso, corte eléctrico o pérdida de disco. Si el servicio
no está disponible, la automatización alerta; no improvisa recuperación ni
reconfigura Mongo legado. El respaldo frío implica una interrupción breve.

Comandos desde la raíz del repositorio, con la venv existente:

```bash
.venv/bin/python scripts/runtime_operations.py backup --if-changed
.venv/bin/python scripts/runtime_operations.py backup
.venv/bin/python scripts/runtime_operations.py restore-latest
```

El primero omite copias sólo si coinciden estado lógico, manifiesto y hash del
archivo. El segundo fuerza respaldo: usar antes de cambios de configuración,
migraciones o rotaciones. No automatiza esos cambios. El lanzador ejecuta el
primero después de importaciones exitosas; si éstas ya se confirmaron pero falla
el respaldo, devuelve código 3 y pide consultar receipt antes de repetir.

Restauración en directorio nuevo `runtime-v3/restore-drills/<id>`, puerto 37033,
replica set autenticado, credenciales de Llavero. Se verifica hash del archivo,
rutas y tipos antes de extraer; valida colecciones, fuentes, proyecciones,
búsquedas, recibos y replay. Incluye escritura y rollback transaccional en copia.
Sólo se relocalizan fuentes y miembro en la copia. Detiene el proceso propio y
elimina su keyfile temporal después de comprobar su salida; no borra evidencia.

## Periodicidad activada

### Aclaración del Operador: independencia de proveedor

Decisión explícita posterior del Operador, 2026-10-06: Codex y los productos
OpenAI se aceptan como mecanismo inicial, no exclusivo ni como infraestructura
obligatoria de Skopos. El proyecto debe poder operar con otras herramientas y
sin infraestructura OpenAI. Esta decisión AMENDS la aceptación del programador
descrita abajo; no revoca su uso inicial ni autoriza instalar otro ahora.

Estado observado: los scripts locales de respaldo/restauración no invocan un
modelo ni APIs OpenAI. Sin embargo, el disparador periódico activo y su lógica
de seguimiento semanal/mensual están en una automatización de Codex. Por tanto,
la periodicidad actual sí tiene dependencia operativa de ese producto; no se
declara independencia completa ni se confunde código local con operación autónoma.

Requisito para cerrar esa dependencia: ejecución periódica y seguimiento mediante
un mecanismo sustituible, independiente de proveedor/modelo/chat, con configuración,
estado, registros y alertas recuperables fuera del chat. Debe comprobarse respaldo
y restauración sin Codex ni servicios OpenAI, conservando bloqueo, permisos,
trazabilidad y tratamiento de fallos. La elección, instalación y activación del
mecanismo sustituto quedan pendientes de su decisión y verificación propias.
Este requisito no obliga a eliminar los adaptadores de fuentes Codex existentes
ni acredita portabilidad entre sistemas operativos: el perfil actual usa macOS,
Keychain, Mongo local y OneDrive.

### Qué significa validación desatendida pendiente

Significa que todavía falta observar una corrida iniciada por el horario, sin
que el Operador o el agente lancen manualmente el comando: comprobar que arranca,
obtiene acceso autorizado, termina, verifica el servicio y registra el resultado
o comunica el fallo. Las ejecuciones manuales ya probadas no acreditan esa ruta.
Una corrida diaria correcta tampoco acredita por sí sola la semanal, la mensual,
el funcionamiento tras reinicio ni un SLA. La descarga web mensual puede requerir
intervención humana; no se presenta como flujo totalmente desatendido.

Automatización en este chat: `skopos-respaldo-y-recuperaci-n`, ACTIVE, comprobada
en su configuración local. Diario 23:00, zona local America/Mexico_City:

- Respaldo si cambió el contenido; el lanzador cubre también post-ingesta.
- Domingo: ensayo de restauración; siguiente corrida disponible si pasaron siete
  días sin ensayo correcto. No repetir contra Mongo operativo.
- Mensual: solicitar descarga web para cotejo y recuperación; la copia
  sincronizada no se presenta como descarga. La descarga de octubre ya consta.
- Avisos ante fallo, recuperación, ensayo semanal o intervención necesaria;
  silencio ante estado sin cambios no accionable.

La creación del horario no prueba su primera ejecución desatendida. Requiere
equipo y aplicación disponibles, Keychain accesible y permisos de ejecución sobre
custodia y OneDrive. Si el sandbox impide una operación, debe avisar sin evadirlo.
RPO de 24 horas es objetivo condicionado, no garantía; RTO no comprometido.
No se implementó purga: conservar 7 diarios/4 semanales/3 mensuales sigue siendo
política pendiente de aplicación explícita, no autorización para borrar.
No se instaló launchd/cron ni se modificaron permisos generales.

## Evidencia observada

Respaldo final: `runtime-v3-backup-20261006T151151Z-c6d5f71e` en la custodia y
carpeta OneDrive autorizadas. Archivo SHA-256:
`87cf1b5913ac6c91035d8c68c35ceaf5a6905583903562bd268f07220b1a169e`.
Dos revisiones conservadas; reinicio y huella lógica verificados. El manifiesto
declara ausencia de credenciales **en claro**, no ausencia de verificadores SCRAM
en los archivos Mongo. No hay cifrado adicional del tar ni verificación de
descarga remota de este nuevo respaldo. Claves independientes diferidas por el
Operador. Los respaldos anteriores permanecen intactos.

Primer ensayo del nuevo arnés falló sin causa capturada: informe conservado en
`restore-drills/e87609bb646e47f6bfb976f34c873a1e/report.json`. No se atribuye causa
ni se declara resuelto por recencia. Se añadieron tipo/código de error redactados.
Dos repeticiones consecutivas pasaron sobre el primer archivo nuevo: hashes,
dos revisiones, cuatro proyecciones, replay y transacción/rollback. Informes:
`cafb94abed7e4957ac4a70593cf3fef8` y `3cd8cee597724128b5f8e8c913f0c8fd`, bajo
el mismo directorio. Un fallo posterior debe notificarse y diagnosticarse.

El respaldo final también fue restaurado correctamente a las 15:12:49 UTC:
dos revisiones, cuatro proyecciones, replay y rollback transaccional correctos;
proceso temporal detenido y keyfile temporal eliminado. El lanzador rechazó
contención real de su lock; un replay de la fuente sintética devolvió duplicate
y ejecutó comprobación post-ingesta unchanged, manteniendo dos revisiones.
Arnés: `/private/tmp/skopos-maintenance.EEy0En/verify_launcher.py`.

13 pruebas unitarias nuevas cubren éxito, exclusión de credenciales, contención,
preflight erróneo, parada incierta, fallos de copia/reinicio/publicación, cambios
concurrentes, corrupción del archivo/manifiesto y extracción maliciosa. Son
fallos simulados, no ensayos de corte eléctrico. Autorrevisión adversarial del
productor, no auditoría independiente.

## Llavero: corrección separada

En `/Users/krisnova/www/aria/llavero`, `store_secret` mantiene pseudo-TTY hasta
128 bytes y usa una orden hexadecimal por pipe a `security -i -q` para 129–1024
bytes ASCII imprimibles, sin shell, secreto en argv o entorno. Lectura exacta
obligatoria antes de éxito. Unicode y controles largos se rechazan antes de
escribir: la CLI puede representar esos bytes como hexadecimal ambiguo.

46 tests pasan, incluidos canarios reales de 128/129/192/512/1024 bytes,
duplicado sin reemplazo, reemplazo explícito, timeout, tamaño excesivo y rechazo
de entradas ambiguas. Se eliminaron sólo canarios propios. No se modificaron
credenciales del servicio ni ACL. Skopos conserva el backend fijado anterior y
las seis partes ya verificadas: no se impone una migración de claves innecesaria.

Cambios Llavero: llavero_core.py, README.md y tests/test_long_secrets.py. No commit
ni push allí: base d9b829e con trabajo preexistente sin publicar. Se preservó y
no se atribuye al agente. Copias previas y parches del encargo en
`/private/tmp/skopos-maintenance.EEy0En`. El arreglo general no equivale a adoptar
el contrato neutral ni certificar aislamiento por agente.

## Reversión y límites

Ante fallo de mantenimiento, comprobar `operate.py status`; no repetir ingesta
sin consultar recibo. Para revertir integración del lanzador, pausar primero la
automatización y restaurar la copia `operate.before.py` del directorio de
evidencia, verificando que no haya ediciones posteriores. Eso desactiva bloqueo
y post-ingesta; no destruye base ni respaldos. Revertir Llavero debe preservar
los cambios ajenos usando el diff acotado, nunca resetear el repositorio entero.

## Verificación de entrega

Suite Skopos final: **475 tests OK, sin omisiones**, en 86.302 s, Mongo temporal
exclusivo 37032 detenido al terminar. Log:
`/private/tmp/skopos-maintenance.EEy0En/regression-final/suite.log`.
Llavero: **46 tests OK** en 3.336 s, con opt-in Keychain. Backend corregido SHA256
`a9611d1e3850e7a5d2dd8aabdc235eca2d2a932ea82987972372a09ac0067eeb`.

AN-KLA escrita con plan/commit gobernados, representación summary y autoridad
model_derived, no attestation. Verify correcto, revisión 19, registro
`f-skopos-h252-maintenance-2026-10-06`, digest
`sha256:33ef48172aae84e4007b5ccc47fcbde7099d4f582b50c4fadca36cd7bf91cfd4`.
No se guardaron secretos ni se promovió contexto canónico en AGENTS.md.

No se cambiaron ADR-019, embeddings, relevancia, corpus legado ni dependencias.
No se acredita operación multiusuario, recuperación sin claves locales o SLA.
