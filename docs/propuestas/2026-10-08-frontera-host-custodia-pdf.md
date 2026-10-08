# Frontera de host para custodia PDF — propuesta bilateral

**Estado:** propuesta de integración; no implementada ni instalada. Fecha:
2026-10-08. Responde a la evaluación documental del consumidor en
`/Users/krisnova/www/expertoGobernanza/docs/propuestas/2026-10-08-respuesta-custodia-pdf-skopos.md`,
leída sin modificar. Esa respuesta estaba sin seguimiento Git al inspeccionarla;
no constituye política bilateral ni autorización de acceso.

## Dictamen de precondiciones para el manual 2000-002-001

| Precondición | Evidencia actual | Resultado |
| --- | --- | --- |
| Identidad de PDF y ficha | Hashes locales coincidentes: PDF `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`; ficha `f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff`. Ensayo temporal recuperó los 1,311,822 bytes del PDF. | Verificada sólo para la copia leída y el ensayo |
| Acceso efectivo | Este proceso pudo leer la copia y su ficha en el checkout consumidor. | Observado localmente; no acredita acceso del futuro servicio |
| Raíz preautorizada y material permitido | No se localizó una configuración instalada. La CLI de laboratorio permite elegir `--policy`, `--uri` y `--database`. | No satisfecha |
| Copia persistente y restaurable | Archivos del consumidor sin seguimiento Git; no se localizó prueba de restauración de estos bytes. La ausencia de seguimiento no prueba ausencia de otro respaldo. | No acreditada |
| Retención, retiro y clasificación bilateral | La ficha difiere ubicación/retención; la Solicitud B exige acordarlas. La clasificación `consumer_declared_public` sólo se usó en fixture. | No satisfecha |
| Recuperación requerida | `while_reference_available` es candidato del consumidor, condicionado a política vigente; no implica recuperación tras pérdida. | Pendiente de política |

Resultado: **`not_ready_for_operational_admission`** es el juicio del
consumidor y coincide con este examen de precondiciones. En una operación real
sin política instalada Skopos debe fallar cerrado con `policy_unavailable`;
si la configuración carece de retención vigente,
`retention_policy_missing`. No se genera recibo de admisión. Un respaldo
externo o política posterior puede falsar este diagnóstico si se identifica y
se prueba específicamente para estos dos objetos.

## Divergencia entre propuesta y laboratorio

| Campo o promesa | Propuesta documental | Runtime de laboratorio `e610f47` | Corrección antes de aceptación bilateral |
| --- | --- | --- | --- |
| Esquema de respuesta | `skopos/source-custody/v0.1` y perfil `skopos/pdf-profile/v0.2` | `skopos/pdf-custody-lab/v0.1`; `producer_version=skopos/pdf-custody/v0.1` es etiqueta estática | Fijar versión exacta de productor/adaptador y completar o versionar la respuesta; no anunciar conformidad por nombre de contrato de entrada |
| `recovery_requirement` | El consumidor declara necesidad de recuperación; ejemplos PDF previos no incluyen campo | Exige `while_reference_available`, idéntico a política de host | Añadir campo a la solicitud bilateral aceptada o rechazar con razón tipada; no rellenarlo por inferencia |
| `max_pages=200` | Presente en los ejemplos PDF | `unsupported_limit`; sólo comprueba prefijo `%PDF-` | Separar custodia binaria de extracción o aprobar un validador de páginas/versionado. No quitar el límite si el consumidor lo considera precondición |
| `receipt` tras respuesta perdida | Recibo correlacionado por solicitud | La consulta requiere `admission_request_sha256` además de su propio digest externo | Fijar ambos nombres y prueba de reconciliación sin segunda admisión |
| Datos de admisión | Resultado candidato incluye material, original, cobertura, custodia y recibo | Resultado de laboratorio devuelve un recibo reducido | Acordar campos/verificaciones faltantes; el consumidor debe rechazar respuesta incompleta |
| Retención | Perfil aprobado y recuperación según dueño | JSON `retention_until` validado al leer; no bloquea borrado ni respalda la copia | Probar política de propietario, protección de raíz, restauración y retiro; no derivar durabilidad del campo JSON |

## Canal propuesto del host

1. Un proceso del host, con identidad de OS propia y credenciales Mongo
   restringidas, carga **fuera de la solicitud del agente** un perfil de
   despliegue aprobado: contrato/versión, política/versión/digest, base y URI
   Mongo, raíces de solicitudes, transporte, original y salida, clasificación,
   sello, plazo, propietario, acceso y retirada. Un agente consumidor sólo
   entrega referencia relativa al sobre y su digest. No puede señalar otro
   archivo de política, URI, base ni raíz.
2. La raíz del original debe contener sólo objetos habilitados para este
   intercambio, o el host debe fijar una allowlist por
   `(project_id, material_id, source_revision)` con ruta y hash esperados. La
   política actual de laboratorio sólo limita el directorio: un agente que
   pueda usar la CLI directamente podría pedir **otro archivo dentro de esa
   raíz**. El hash declarado en la solicitud no sustituye una allowlist.
3. El proceso verifica sobre/solicitud, permisos efectivos, política vigente,
   archivo regular, bytes/hash y ficha antes de llamar al almacén. La
   persistencia usa revisión y predecesor; la lectura verifica el original
   admitido y publica salida temporal bajo raíz gobernada. El host define
   vencimiento y limpieza de `output_ref`, que el laboratorio no implementa.
4. El agente consumidor relee salida, verifica longitud/SHA-256 y conserva
   recibo, versión efectiva y estados atribuidos. El runtime no determina
   autenticidad, vigencia jurídica ni admisión al corpus.

Una función Python que fije estos parámetros dentro del **mismo usuario con
shell y credenciales Mongo compartidas** no demuestra aislamiento: el agente
podría invocar la CLI directa. La frontera requiere separación efectiva de
identidad, permisos y canal de invocación. No se propone por ahora una ruta
`/etc`, un usuario de servicio ni nueva base productiva sin conocer la
plataforma y su autoridad; escoger nombres aquí no instalaría el control.

## Fixture bilateral y falsadores

Secuencia positiva con política de prueba fijada por el host:

```text
describe_capabilities → oferta con policy_id/version, modos, sello y límites
admit_original      → request_id + request_sha256; original/ficha verificados
receipt             → mismo recibo usando admission_request_sha256
fetch_original      → revisión y SHA admitidos; bytes_ref temporal
consumer_verify     → longitud/hash/bytes coinciden con su copia autorizada
```

Cada mutación negativa debe acompañarse de ese control positivo en el mismo
entorno autorizado:

| Mutación | Resultado esperado |
| --- | --- |
| Agente intenta cambiar policy/URI/database/root o leer otro material dentro de la raíz | Canal lo rechaza antes de abrir el objeto; no hay escritura Mongo |
| Falta política, está caducada, o no cubre material/retención | Rechazo tipado sin recibo de admisión |
| El original o ficha desaparece/cambia, o un enlace sale de la raíz | Error tipado sin entregar bytes ni usar otro origen |
| `provided_file` difiere de `persistent_ref` | No se convierte el lateral en custodia duradera |
| Se pierde la respuesta después del commit | `receipt` reconcilia la primera operación; no crea revisión nueva |
| Salida no escribible o existente | No retorna `ok` con archivo parcial ni sobrescribe |
| Restaurar copia y ficha desde el respaldo declarado | Hashes y permisos iguales; si falla, política no satisfecha |

**Criterio de avance:** política de custodio aprobada y comprobada, canal de
host con controles negativos efectivos, contrato de respuesta completo o
versión más estrecha aceptada por ambos agentes, y corrida bilateral con
recibos archivados. Hasta entonces el resultado correcto es rechazo operativo,
aunque la mecánica de laboratorio siga pasando. Este documento no instala la
frontera ni convierte el ensayo en admisión real.
