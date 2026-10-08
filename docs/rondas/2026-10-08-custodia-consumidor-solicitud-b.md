# Ajuste adversarial focalizado: custodia del consumidor y Solicitud B

Fecha: 2026-10-08. Artefactos revisados: contrato base candidato
`docs/propuestas/2026-10-08-contrato-base-custodia-fuentes.md` y perfil PDF
`docs/propuestas/2026-10-08-perfil-pdf-solicitud-b-expertogobernanza.md`.
Fuente nueva: copia y registro
`/Users/krisnova/www/expertoGobernanza/docs/fuentes/imss/2000-002-001*`,
leídos como datos; SHA-256 de copia comprobado localmente. Autoría de esta
ronda: mismo agente redactor; es autorrevisión adversarial, no revisión
independiente ni aceptación bilateral. Sin pruebas de runtime ni ingesta.

| ID | Refutación e impacto | Ajuste aplicado | Pendiente |
|---|---|---|---|
| C1 · ALTO | La propuesta exigía copia Skopos pese a que el consumidor ya custodia original; duplica datos, respaldo y retirada sin demostrar recuperación adicional necesaria. | Dos modos explícitos: referencia verificada y copia gestionada; primer piloto propone evaluar referencia, sin decidirla como aceptada. | Operador/consumidor deben fijar disponibilidad requerida y autorizar ruta estable, respaldo y retención. |
| C2 · ALTO | La ruta `docs/fuentes/imss/` y un recibo podrían presentarse como garantía de disponibilidad futura. | `fetch_original` verifica bytes cada vez; error sin fallback; recibo se limita a admisión histórica. | Ensayar pérdida/restauración y relocalización autorizada; ruta actual sin seguimiento Git no acredita respaldo. |
| C3 · ALTO | `request_digest` no es el `request_sha256` del sobre del consumidor; un hash autorreferencial del archivo sería imposible. | Campo exacto `request_sha256`; digest de bytes de archivo calculado fuera de ese archivo, eco de correlación y ejemplo de bytes/digest. | Transporte y parser bilateral todavía no implementados ni conformados. |
| C4 · ALTO | Códigos Skopos sin estado global ni `stage` permitían entregar resultado parcial con error. | Matriz de cinco estados, `error {code,stage}` y `result` sólo en `ok`; ausencia/hash discordante/sello fallido se mapean al estado y etapa pertinentes. | Fixture de todas las combinaciones y rechazo del consumidor pendientes. |
| C5 · MEDIO | `unsupported_scope` en el texto y `invalid_scope` en errores se confundían. | Malformado → `invalid_input/invalid_scope`; valor reconocido `manifested_set` sin implementación → `execution_failed/unsupported_scope`. | Fijar semántica definitiva con consumidor antes de test de conformidad. |
| C6 · ALTO | «Lectura autenticada/autorizada» atribuía ACL inexistente a perfil local monousuario. | Se limita a ruta acordada y permisos efectivos del proceso/Mongo; `project_id` no es credencial. | Si hay acceso compartido, diseñar autenticación y autorización por recurso aparte. |
| C7 · MEDIO | `coverage` del consumidor podía confundirse con OCR completo. | Se mapea a `capture_coverage`; `extraction_coverage` PDF queda separada. | Evaluación visual/OCR y aceptación de cobertura pendientes. |
| C8 · ALTO | Un `ok` que devuelve sólo la ruta de origen sufre cambio del archivo entre verificación y lectura del consumidor. | `fetch_original` candidato entrega salida temporal autorizada, comprueba hash/longitud de entrada y salida y sólo entonces responde `ok`; el consumidor verifica de nuevo. | Transporte, publicación segura de salida, caducidad, limpieza y pruebas de carrera pendientes. |

Resultado: **candidato corregido para revisión bilateral**, no `proceed` de
implementación. La referencia verificada puede cumplir recuperación de bytes
en el momento de lectura si se autoriza y se comprueba la copia, pero no
ofrece recuperación independiente si el consumidor pierde su original. Copia
propia sólo se justifica con esa necesidad y su costo/riesgo de custodia;
requeriría enmienda de ADR-020. Ningún hash comprueba igualdad con el PDF
servido actualmente por IMSS ni vigencia jurídica. No se modificaron ADR,
runtime, registry, EvidenceEdge, PDF ni almacén del consumidor.
