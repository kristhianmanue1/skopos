# PDF IMSS: ensayo temporal y puerta de admisión — 2026-10-08

**Estado:** ensayo técnico local positivo; admisión operativa rechazada por
precondiciones de política y custodia no demostradas. No se escribió en
expertoGobernanza, corpus, AN-KLA ni Mongo operativo. El ensayo no adopta el
contrato bilateral `skopos/source-custody/v0.1` ni el perfil PDF completo.

**Productor inspeccionado:** Skopos `main@e610f474965e04c7c5a3979b70eb9c792366a5f9`, árbol limpio al inicio.
**Consumidor leído:** expertoGobernanza
`feat/R2-H1-02@97f3c33239070e2e0487ae55043dd805a918f088`, con PDF y ficha
sin seguimiento Git al momento de la inspección. La existencia local no prueba
retención, respaldo ni aceptación del contrato.

## Observaciones de entrada

| Objeto | Observación local | Límite |
| --- | --- | --- |
| `docs/fuentes/imss/2000-002-001.pdf` del consumidor | 1,311,822 bytes; SHA-256 `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323` | Se leyó una copia local; no se volvió a descargar la URL de origen |
| Ficha `2000-002-001-PROCEDENCIA.md` | SHA-256 `f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff` | Sus afirmaciones de descarga y cotejo remoto pertenecen a expertoGobernanza |
| `pdfinfo` 26.05.0 | 188 páginas, PDF 1.7, `Encrypted: no`, metadatos legibles | Comprobación de parser; no prueba estructura íntegra, seguridad del visor ni vigencia jurídica |
| Permisos observados | Directorios `755`, PDF y ficha `644`, propietario local `krisnova` | Acceso actual de este proceso, no raíz preautorizada ni inmutabilidad |

La ficha del consumidor dice expresamente que ubicación y retención deben
decidirse antes de admitir al corpus. La autorización R1 localizada trata
canales de análisis y envío a proveedores; no fija retención ni respaldo de
esta copia para el intercambio con Skopos. El respaldo H25.2 inspeccionado
cubre la colección `source_revisions_v3` de su runtime, no acredita cobertura
de esta copia en expertoGobernanza ni de `pdf_custody_revisions_v1`.

## Ensayo ejecutado

Se creó un directorio temporal con raíces separadas `requests`, `input`,
`persistent` y `output`. Se copiaron allí **el PDF y la ficha exactos** del
consumidor. Una política de fixture de 24 horas fijó
`verified_external_reference`, `consumer_declared_public`,
`while_reference_available`, límite de 2,000,000 bytes y sello
`not_required`. La solicitud usó `authorized_reference`, hash esperado y
procedencia `consumer_declared`; no incluyó `max_pages`, que la implementación
actual rechaza porque no puede comprobar páginas. Se inició un replica set
Mongo exclusivo en loopback `127.0.0.1:37028`, base
`skopos_test_pdf_imss_trial`; al terminar se borró la base y se destruyeron
Mongo y archivos temporales.

| Propiedad ensayada | Resultado observado |
| --- | --- |
| `admit_original` con bytes y ficha cotejados | `admission_status=admitted` en `skopos/pdf-custody-lab/v0.1` |
| Consulta de recibo por identidad, SHA del PDF y SHA de solicitud | Mismo `receipt_id` |
| `fetch_original` por revisión y SHA admitidos | 1,311,822 bytes; SHA recuperado idéntico `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`; comparación byte a byte positiva |
| Almacén del ensayo | Sólo `pdf_custody_heads_v1` y `pdf_custody_revisions_v1` en la base temporal |

Esto es un **control positivo de mecánica local** con los bytes de interés. No
demuestra operación entre procesos/agentes, garantía de copia persistente,
restauración, autoría, vigencia o aptitud de extracción. La suite publicada en
`e610f47` cubre errores de referencia alterada, política caducada, rutas fuera
de raíz, hash discordante, replay y salida existente con fixtures sintéticos;
no sustituye una prueba del host definitivo.
Después del ensayo, la suite completa de Skopos pasó con **487 pruebas, sin
omisiones**, sobre Mongo temporal exclusivo `127.0.0.1:37027`; los gates de
tamaño y planes pasaron con 334 archivos y dos planes. No se ejecutó ninguna
prueba contra Mongo operativo.

## Resultado determinista para operación real hoy

`verified_external_reference` exige raíz preautorizada, acceso efectivo,
copia persistente y retención vigente. El acceso local al archivo se observó;
las otras condiciones no están acreditadas. Por el contrato propuesto la
respuesta correcta **hoy** es `policy_unavailable` o
`retention_policy_missing`, sin registrar la revisión real. La CLI de
laboratorio acepta `--policy`, `--uri` y `--database` del invocador; por ello
no constituye una frontera de autorización para agentes consumidores.

| Preparación única | Responsable | Evidencia de salida exigida |
| --- | --- | --- |
| Fijar propietario, raíz duradera, plazo, respaldo/restauración y retiro de la copia | Custodio de expertoGobernanza y responsable de plataforma | Política/versionado aprobado; prueba de lectura y restauración; limitaciones de borrado explícitas |
| Exponer sólo un canal de solicitud que fije política, Mongo y raíces fuera del control del agente | Responsable de plataforma Skopos | Identidad de proceso/ACL y prueba negativa: el agente no puede cambiar esos valores ni leer fuera de raíz |
| Acordar solicitud y respuesta bilaterales | Ambos responsables | Versión exacta, clasificación descriptiva, sello, `recovery_requirement`, vida de `output_ref`, errores y recibo; eliminar `max_pages` del perfil de custodia binaria o aprobar un validador que lo cumpla |
| Ensayar el intercambio instalado | Ambos agentes bajo políticas anteriores | `describe_capabilities` → admisión → recibo → recuperación → cotejo de bytes y ficha, más mutaciones negativas y resultado incierto |

Si se exige recuperación tras perder la única copia del consumidor, este modo
no cumple: habría que aprobar custodia propia y su política de respaldo y
retiro. La admisión técnica resultante tampoco habilita corpus, cita ni
adjudicación jurídica. El siguiente trabajo autorizado en Skopos puede
preparar un adaptador de host y fixtures de conformidad; **instalarlo con una
política real** requiere los valores y permisos de plataforma anteriores.
