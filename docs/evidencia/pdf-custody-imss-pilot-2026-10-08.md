# Custodia PDF IMSS: admisión técnica bilateral del piloto — 2026-10-08

**Estado:** admisión técnica real de un objeto bajo
`verified_external_reference`, en piloto local monousuario. La ejecución no
adjudica procedencia remota, vigencia jurídica, corpus ni recuperación si la
copia de expertoGobernanza desaparece. Los agentes consumidor y productor
hicieron comprobaciones separadas; esta revisión de Skopos es autorrevisión
del productor, no auditoría independiente.

**Productor:** Skopos `main@a9c1bbd` más la corrección de cierre de socket de
este incremento, antes del commit. **Consumidor:** expertoGobernanza
`feat/R2-H1-02@97f3c332` al preparar la prueba, con cambios propios en curso.
**Observado al cierre:** 2026-10-08 UTC; los procesos de servicio son locales
y pueden detenerse sin retirar la base persistente.

## Política y entorno aplicado

| Campo | Valor comprobado |
| --- | --- |
| Entrada/salida | `expertogobernanza/skopos-source` `v0.2`; respuesta `skopos/pdf-custody-host/v0.1`, perfil `skopos/pdf-binary-reference/v0.1` |
| Política | `expertogobernanza/imss-2000-002-001-reference@v0.2-2026-10-08`, esquema `skopos/pdf-custody-policy/v0.2`, `while_reference_available`, sello `not_required`, clasificación atribuida `consumer_declared_public` |
| Identidad y alcance | `expertogobernanza` / `imss-2000-002-001` / revisión `1`; PDF `docs/fuentes/imss/2000-002-001.pdf` de 1,311,822 bytes y SHA-256 `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323` |
| Ficha | `docs/fuentes/imss/2000-002-001-PROCEDENCIA.md`, SHA-256 `f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff`; contenido atribuido al consumidor |
| Vigencia | Servicio hasta `2026-11-08T00:00:00Z`, acordado por custodio consumidor para este piloto; no ordena borrar PDF/ficha |
| Límite y transporte | 2,000,000 bytes; `authorized_reference`, sin OCR, red ni `max_pages` |
| Política instalada | `/Users/krisnova/www/aria/skopos/runs/pdf-custody-imss-pilot-v1/policy.json`, modo `0600`, fuera de Git; SHA-256 de bytes `eba99bfb8132824c4d533c2a58410d61bc5a2d35f7716698937a130e8ac4f18b`; digest canónico guardado en la revisión `a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160` |
| Configuración | `host.json` en el mismo directorio, `0600`, SHA-256 de bytes `d92fbce2511d3124c739c0de5bcc58c78458f03c4eccf4d57c814d860f8f937f`; socket `agent.sock` en ese directorio, modo `0600` |
| Raíces | Solicitudes `/Users/krisnova/www/expertoGobernanza/runs/pdf-custody-imss-pilot-v1/requests`; original `/Users/krisnova/www/expertoGobernanza`; salidas `/Users/krisnova/www/aria/skopos/runs/pdf-custody-imss-pilot-v1/delivery` |
| Almacén | Mongo replica set `skoposPdfImssPilot` dedicado en `127.0.0.1:37034`, base `skopos_pdf_imss_pilot_v1`, dbpath bajo `runs/pdf-custody-imss-pilot-v1/db`; no se usó Mongo operativo. Datos locales persistentes, sin respaldo independiente acreditado. |

El custodio de expertoGobernanza aceptó esos valores en el intercambio entre
agentes. La política ata identidad, ruta y ambos hashes mediante
`allowed_materials`. El host leyó el PDF y la ficha exactos con hash correcto
antes de admitir; la base dedicada estaba vacía. El usuario de OS fue el
mismo en ambos agentes; el socket restringe la invocación contractual, pero
**no demuestra aislamiento** ante un proceso con shell o credenciales del
mismo usuario.

## Recibo y recuperación observados

1. El consumidor ejecutó `describe_capabilities` y comprobó política,
   vigencia, límite, modo, sello y validación `pdf_header_only`. Tras una
   revisión adversarial, el host añadió el digest canónico `policy_sha256` a
   la oferta; la tercera corrida lo fijó en el cliente consumidor y comprobó
   `a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160`.
2. `admit_original` respondió `admitted` para
   `request_id=imss-2000-002-001-r1-admit-v1` y
   `admission_request_sha256=4fbed2bd3d2633aafc2646e8369e0227610d37672cee2f048b7a9b1b3dde870a`.
   El recibo es
   `expertogobernanza:imss-2000-002-001:1:4fbed2bd3d2633aa`.
3. El consumidor consultó `receipt`, recuperó el mismo identificador y
   recibió rechazo `revision_conflict` con digest de admisión falso.
4. `fetch_original` produjo una salida de 1,311,822 bytes. El consumidor
   cotejó longitud, SHA-256 e igualdad byte a byte; Skopos repitió el cotejo,
   verificó registro/cabeza y digest de política. La revisión tiene
   `record_sha256=0cc590c6e4f278c4350665526d8ee63732494afb977d4a97472e328b6b6f3ffb`.
5. Se detuvieron host y Mongo. La base en disco persistió. Tras iniciar
   ambos con el mismo dbpath/política, el consumidor repitió la solicitud:
   `admission_status=duplicate`, mismo digest de admisión y mismo recibo;
   `fetch_original` entregó de nuevo bytes idénticos. Skopos comprobó una
   sola revisión y una sola cabeza y el mismo digest de política en Mongo.
6. Se repitió el intercambio con el cliente actualizado que exige el digest
   anunciado. Respondió `duplicate`, mismo recibo y bytes idénticos. Su
   control negativo de otro material y digest falso de recibo volvió a
   rechazar. Skopos cotejó la tercera salida y confirmó que no apareció una
   segunda revisión.

El primer output `imss-pdf-61bbac923fa772861dc1b6d4.pdf` y el segundo
`imss-pdf-c72218d58bc6fa7015082cfd.pdf`, más el tercero
`imss-pdf-8424161c0931bf32e9a2e6df.pdf`, se retiraron individualmente
**después** de cada cotejo. Skopos confirmó su ausencia y la permanencia
del PDF, ficha y revisión. La salida temporal no constituye custodia propia.

## Controles negativos y límite de las pruebas

El consumidor obtuvo `material_not_allowed` al intentar admitir
`other-in-same-project` con proyecto/hash/revisión correctos. Skopos envió al
socket un campo `policy_path` inventado (`invalid_request`), referencia con
`..` (`path_outside_root`) y sobre inexistente (`bytes_unavailable`). La base
seguía con una revisión y una cabeza. Los fixtures previos cubrieron además
política cambiada/caducada, archivo y ficha mutados, enlace, salida no
escribible y solicitud de socket incompleta; ver
[`pdf-custody-host-fixtures-2026-10-08.md`](pdf-custody-host-fixtures-2026-10-08.md).

La primera parada por señal dejó un socket residual: Mongo estaba detenido y
la conexión al socket devolvía `ConnectionRefused`. Sólo entonces Skopos
retiró ese socket, corrigió el servidor para limpiar el mismo inode al recibir
`SIGTERM` y comprobó esa corrección en un proceso temporal. El reinicio del
piloto usó el código corregido. No se instaló un supervisor ni identidad/ACL
separadas; el servicio puede requerir arranque local y las salidas futuras
deben retirarse tras el cotejo. La política en `runs/` y Mongo no tienen
recuperación remota acreditada. Un resultado positivo en este usuario no
prueba enforcement entre usuarios ni seguridad del contenido PDF.

La parada final con el servidor corregido eliminó el socket propio. Skopos
comprobó Mongo detenido, directorio de salidas vacío, política/configuración
y base en disco persistentes, y PDF/ficha originales presentes. Volver a
servir el recibo requiere iniciar de nuevo el Mongo dedicado y el host;
no se afirma disponibilidad continua ni respaldo remoto.

**Verificación del código final:** 10 pruebas focales de custodia host y 497
pruebas de la suite completa, sin omisiones, en otro Mongo replica set
temporal exclusivo `127.0.0.1:37029`. Las pruebas no usaron la base piloto ni
el Mongo operativo. Los gates de tamaño y planes pasaron sobre el diff final
antes del commit.

**Contrato congelado para este piloto:** entrada `v0.2`, host
`skopos/pdf-custody-host/v0.1`, política
`expertogobernanza/imss-2000-002-001-reference@v0.2-2026-10-08` y recibo
anterior. Cambiar cualquiera exige nuevo perfil/revisión y prueba bilateral;
no se reutiliza el recibo para otro material. La admisión técnica no promueve
el PDF a `corpus/registry.yaml` ni adjudica sus afirmaciones.
Los archivos de sobre/solicitud bajo `requests_root` pertenecen al consumidor,
quien definió su retiro; Skopos no los borra desde otro proyecto.
