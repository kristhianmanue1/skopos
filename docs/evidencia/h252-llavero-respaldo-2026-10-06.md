# H25.2 — Llavero y continuidad del respaldo

## Alcance y decisión

El Operador pidió integrar custodia mediante `/Users/krisnova/www/aria/llavero`,
comprobar descarga desde OneDrive y definir periodicidad. Después precisó:
«utiliza el llavero después yo veré su resguardo». La custodia independiente
queda a cargo del Operador; no se declara completada ni demostrada.

Este registro AMENDS el estado de custodia local de
`h252-operacion-local-2026-10-06.md`; no cambia ADR-019, relevancia, corpus legado,
identidad de fuentes ni criterios de aceptación global de H25.

## Llavero observado y límites

Base Git: `d9b829eb7fe9dff7add7f6af6d441b7087df52f6`, rama main con cambios
preexistentes: README.md, llavero.py y archivos sin seguimiento, incluidos
llavero_core.py, docs/ y tests/. No se modificaron ni publicaron esos cambios.

Backend revisado `llavero_core.py`, SHA-256:
`b7d9c2d24b84fd24f85a2329c88c3b689af56a7715a3abb19c98bb53a7d95003`.
Se conservó copia fijada en `Skopos-private/runtime-v3/llavero_core.py`; el
lanzador comprueba ese digest antes de usarla. Es fijación de versión, no
aislamiento frente a procesos con autoridad para alterar lanzador y backend.

Se usa únicamente almacenamiento/lectura de Llavero con macOS Keychain, servicio
`llavero`. No se finge un proveedor LLM para Mongo ni se usa un perfil HTTP.
Este adaptador operativo local no declara conformidad con el contrato neutral
`credential-delivery/v1`, que permanece propuesto, ni implementa broker/ACL por
agente. El consumidor autorizado recibe los secretos en memoria. No se pasan
por argv o variables de entorno de subprocessos del lanzador.

Referencias específicas de la instancia:

- `skopos.local.runtime-v3.mongo-app`: cuenta readWrite de la base dedicada.
- `skopos.local.runtime-v3.mongo-admin`: administración separada.
- `skopos.local.runtime-v3.replica-key-v1-part-0` a `part-5`: clave interna,
  seis partes ordenadas verificadas contra el original. Si falta una, se rechaza.

`operate.py` ahora usa Keychain para source/status/stop. No recurre al archivo de
credenciales si Llavero falla. `start` sigue usando el keyfile 0600 requerido por
la configuración existente de mongod. Copia del lanzador anterior:
`operate.pre-llavero.py`. Informe privado: `llavero-custody.json`.

Los originales `credentials.json` y `keyfile` permanecen privados; no se borraron
ni se subieron a OneDrive. Por tanto, no se afirma haber eliminado todas las
copias locales en claro. Tampoco se demostró sincronización de Keychain a otro
dispositivo ni independencia respecto del equipo.

## Fallo encontrado y corrección acotada

La guarda inicial de la clave larga no confirmó éxito; la comparación mostró un
prefijo truncado. El lanzador no se activó hasta resolverlo. Una tentativa de
partes de 192 bytes también falló. Sonda posterior con cinco canarios reales:
48, 64, 96 y 128 bytes pasan; 192 no pasa. Se eliminaron exclusivamente esos
cinco canarios al terminar. No se deduce el límite exacto entre 128 y 192.

Se admitieron partes de hasta 128 bytes con nombres nuevos y se comprobó su
concatenación exacta antes de activar. Las entradas incompletas `replica-key` y
`replica-key-part-0` se conservaron, excluidas del consumidor. No constituyen
respaldos válidos. Esta adaptación es local: el transporte general de Llavero
sigue necesitando corrección y un test de longitudes que cubra lo que promete.
No sustituir backend/formatos automáticamente ni sobrescribir esas referencias.

## Pruebas ejecutadas

- Suite Llavero: 41 tests OK en 1.734 s, incluida la prueba real opcional de
  Keychain con canario; el canario propio fue eliminado por su cleanup.
- La corrida inicial restringida falló por socket/TTY; la repetición autorizada
  fuera de esas restricciones pasó. No se atribuyó ese fallo inicial al producto.
- Adaptador privado: seis tests OK; secreto ausente falla antes de Mongo,
  partes ausentes rechazan, orden de recomposición, cuenta app diferenciada,
  restricciones de URI/base y canario entregado sólo dentro del proceso.
- Autenticación app real, status con dos revisiones y receipt privado correctos.
- Autenticación admin real y recomposición de keyfile exacta, sin salida secreta.

Artefactos de ejecución: `/private/tmp/skopos-key-custody.FoFlev`.
Autorrevisión del mismo productor; no revisión independiente. No cambios del
paquete Skopos ni dependencias nuevas. No aislamiento de procesos del mismo UID.

## OneDrive

Se observó en OneDrive web autenticado la carpeta exacta
`runtime-v3-backup-20261006T112547Z`, con `manifest.json` y
`runtime-v3-data.tar.gz`, ambos marcados Privado. Esto acredita presencia remota
observada, no integridad descargada ni una auditoría completa de permisos.

La descarga se solicitó mediante el control web, pero falló el recibo del
navegador (`Invalid InterceptionId`). No apareció archivo nuevo en Descargas
en la comprobación inmediata. El acceso automatizado a la página interna de
descargas fue bloqueado por política; no se intentó eludir ese límite.
El Operador aceptó realizar la descarga manual desde la web. Hasta recibir ese
archivo, la recuperación desde nube permanece pendiente, no repetida con una
copia local presentada como descarga.

Tras la descarga: cotejar SHA-256 con
`833d22dfaec636d26bd58fa1ba1d93d50975acbe9ee9e05f0dd61450922202c0`,
extraer a directorio nuevo fuera de OneDrive, restaurar Mongo aislado, verificar
colecciones, hashes, recibos, vistas y replay, sin tocar la instancia operativa.
El ensayo utilizará Llavero local: no demuestra recuperación si también se
pierde el equipo, pendiente del resguardo independiente del Operador.

Método de descarga: [documentación oficial de Microsoft](https://support.microsoft.com/es-es/onedrive/download-files-and-folders-from-onedrive-or-sharepoint).

## Periodicidad definida para el perfil actual

Política operativa recomendada, sin instalar un programador ni activar un
apagado recurrente del servicio:

| Momento | Acción y condición |
|---|---|
| Después de cada lote de ingesta aceptado | Respaldo nuevo con base y originales consistentes; no considerar protegido el lote hasta comprobarlo |
| Diariamente, 23:00 America/Mexico_City | Comprobar antigüedad; respaldar si hubo cambios, o registrar ausencia de cambios. Si el equipo no estuvo disponible, hacerlo al volver a operar |
| Antes de actualización, migración o rotación | Punto de recuperación adicional y comprobación de credenciales aplicables |
| Semanalmente | Restauración aislada completa del respaldo más reciente, sin alterar producción |
| Mensualmente | Descargar desde OneDrive y repetir restauración; no basta leer la carpeta sincronizada |

Objetivo propuesto: pérdida máxima de 24 horas, condicionado a ejecución exitosa
y copia remota comprobada; no es garantía actual. La captura por lotes reduce
esa ventana cuando su respaldo se completa. RTO aún no fijado: medir restauración
completa con claves disponibles antes de prometer un tiempo de recuperación.

Retención propuesta: al menos siete copias diarias, cuatro semanales y tres
mensuales, más el último punto previo a un cambio. No se ejecuta poda ni se
borra evidencia automáticamente. Fuentes canónicas no son copias desechables.
Antes de automatizar copias frías, coordinar ausencia de ingestas, parada limpia
y reinicio incluso si falla el respaldo. El script temporal del ensayo anterior
no es un servicio recurrente ni debe instalarse como tal.

## Cierre de verificación

Regresión Skopos repetida: 462 tests OK sin omisiones sobre Mongo temporal
exclusivo 37032, detenido al finalizar. Log:
`/private/tmp/skopos-key-custody.FoFlev/regression/suite.log`.
Gates correctos: 283 archivos, un plan. Cambios persistentes del repositorio
limitados a documentación; el adaptador y referencias operativas son privados.

AN-KLA rev17, summary/model_derived, plan y commit gobernados, verify correcto:
`sha256:2af5f0f4e0458ec5ea4a1a0237999f47de0022c9dadc2b51b9b34172bcf412e3`.
Registro `f-skopos-h252-llavero-custody-2026-10-06`. No se guardaron secretos.
