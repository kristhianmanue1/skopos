# Contrato base candidato de custodia de fuentes

Estado: **PROPUESTA documental**, 2026-10-08. Identificador candidato:
`skopos/source-custody/v0.1`. No implementado, aceptado ni activado.
Fuentes contrastadas: ADR-020, ADR-021, `docs/contratos/source-store-v3.md` y Solicitud B
`expertogobernanza/skopos-source/v0.1`. No sustituye esos contratos ni
declara compatibilidad con ellos. El perfil PDF candidato está en
`2026-10-08-perfil-pdf-solicitud-b-expertogobernanza.md`.

## Decisión de diseño propuesta

Skopos registraría una **instantánea de bytes de alcance explícito** y podría
recuperarla por identidad y revisión bajo una política de custodia fijada.
Esa política puede verificar una referencia estable cuya copia conserva el
consumidor o conservar una copia adicional gestionada por Skopos. La custodia
común no promete entender
el formato, buscar contenido, extraer texto ni producir citas. Un perfil de
formato aceptado por separado define esas capacidades y sus localizadores.
No se afirma soporte universal de TXT, código, Word, Excel, PDF, audio o video.
Los formatos hoy admitidos por `source` siguen sujetos a sus contratos y
custodia por referencia; este candidato no los migra ni los reetiqueta.

| Frontera | Promesa candidata | Lo que no acredita |
|---|---|---|
| Captura | Bytes recibidos, longitud, SHA-256, identidad y alcance declarados | Que un archivo fuera de la instantánea exista, que el autor sea auténtico o que la fuente siga vigente |
| Custodia | Bytes recuperables al consultar o error tipado; revisión inmutable y modo de custodia explícito | Que Skopos posea una copia adicional en modo referencia, disponibilidad futura, respaldo remoto o borrado selectivo sin ensayo |
| Derivación | Objeto separado, versionado y ligado al padre | Correspondencia semántica o fidelidad del extractor sin evaluación propia |
| Consulta por perfil | Localizador definido y validado para una representación concreta | Verdad de la cita, relación jurídica, relevancia o aceptación del consumidor |

Un documento puede ser un objeto; un repositorio, carpeta, exportación con
adjuntos o paquete audiovisual puede ser un conjunto. **v0.1 sólo propone
`single_object`**. Una solicitud `manifested_set` devuelve
`unsupported_scope`. Un perfil futuro para conjuntos necesitaría manifiesto
versionado de miembros, rutas lógicas, tamaños, hashes y exclusiones, además
de semántica propia de recuperación y revisión. No se infiere que un `.py`
suelto sea todo un repositorio, ni que un Excel incluya sus vínculos externos.

## Entrada, identidad y recibo candidatos

Entrada manual propuesta: `contract_id` y `contract_version` bilaterales
aceptados, `request_id` y `request_sha256` de los bytes exactos del archivo de
solicitud, `project_id`, `material_id`,
`source_revision`, `expected_previous_sha256` si procede, `source_delivery`,
`scope=single_object`, `custody_mode`, tipo declarado, procedencia opcional
atribuida, `classification`, `custody_policy_id` y versión,
`seal_profile_id`, presupuesto y límites del perfil. Una URI de procedencia
no desencadena descarga. El productor registra tipo detectado y método por
separado; ni extensión ni MIME declarado prueban formato seguro.

`source_delivery` describe **cómo llegan los bytes**, no quién los conserva.
Propone `mode=authorized_reference` con `file_ref` bajo raíz acordada, o
`mode=provided_file` con un archivo lateral entregado por el consumidor y
una referencia de transporte autorizada. No se incrusta el binario en JSON.
Si `provided_file` se combina con `verified_external_reference`, un
`persistent_ref` adicional identifica la copia gobernada por el consumidor;
Skopos debe comprobar que sus bytes coinciden con los del archivo lateral
antes de admitir. La copia lateral no se convierte en esa referencia por
tener el mismo nombre o hash declarado.
La entrega física del PDF es opcional si la referencia autorizada ya permite
leerlo. Para una nueva admisión sí debe haber bytes legibles por alguna de
esas vías: procedencia sola no alcanza. En ambos modos Skopos calcula
longitud y SHA-256 del archivo recibido y contrasta `expected_source_sha256`
cuando se aporte. `request_sha256` identifica el archivo JSON de solicitud;
no sustituye el hash del material.

`provenance` es un bloque opcional de antecedentes aportados por el
consumidor: `asserted_by`, origen inmediato declarado, referencia a ficha o
registro lateral y SHA-256 de sus bytes, URL atribuida, fechas y límites de
la afirmación. Su ausencia queda `unknown`, no se rellena por inferencia.
Skopos puede verificar que leyó el registro exacto y que el hash declarado
coincide; eso no comprueba que sus afirmaciones sean verdaderas ni que la URL
sea oficial o vigente. Cada dato conserva estado `consumer_declared` o una
comprobación específica fechada; nunca se eleva todo el bloque a `verified`
por coincidir los hashes del PDF y la ficha.
Para este manual, la ficha de expertoGobernanza le atribuye al consumidor una
descarga HTTPS de la URL del IMSS y un cotejo puntual por SHA-256, tamaño y
`cmp` el 2026-10-08. En este trabajo Skopos sólo releyó la ficha y calculó
localmente los hashes de la copia del consumidor y de la ficha. No descargó
de nuevo la URL ni reprodujo ese cotejo remoto. Ni el resultado atribuido ni
la comprobación local prueban vigencia jurídica, autenticidad institucional o
permanencia de los bytes en la URL.

Identidad lógica: `(project_id, material_id, source_revision)` dentro de un
contrato/ámbito autorizado. El hash identifica bytes, no el material, dueño,
política ni versión jurídica. Revisiones no se reescriben; cambiar bytes
requiere revisión y predecesor correctos. Una nueva herramienta de extracción
crea derivado nuevo, no revisión ficticia del original. Duplicado de la misma
identidad y hash devuelve el primer recibo sin alterar política ni metadatos;
conflicto de hash, predecesor o política se rechaza explícitamente. No se
deduplican objetos entre ámbitos en el primer incremento.

Respuesta candidata, con campos y semántica aún por fijar con el consumidor.
El hash de solicitud se calcula fuera del archivo de solicitud y se transporta
en un sobre separado: el propio archivo no contiene su digest. La respuesta
repite los cuatro campos de correlación exactos y las versiones del productor
y adaptador. `request_digest` no es alias admitido de `request_sha256`.

```text
schema: skopos/source-custody/v0.1
contract_id, contract_version, request_id, request_sha256
status: ok | invalid_input | execution_failed | budget_exceeded | unsupported_version
error: null | {code, stage}
material: {project_id, material_id, source_revision,
           previous_source_sha256, scope: single_object}
original: {object_ref, sha256, byte_length, media_type_declared,
           media_type_observed, detection_method, captured_at,
           provenance, provenance_checks, seal_policy, seal_check}
coverage: {declared_scope, status, exclusions, basis}
custody: {mode, policy_id, policy_version, owner, classification,
          admitted_at, retention_basis, recoverability_checked_at}
receipt: {receipt_id, admission_status, producer_version, adapter_version}
```

`object_ref` es opaca y no concede lectura por sí sola. La lectura comprueba
alcance autorizado en el perfil local, revisión, longitud y hash de los bytes
recuperados. El recibo
identifica la admisión; no es comprobación actual de disponibilidad. La
consulta `fetch_original` exige revisión y hash explícitos y retorna bytes
idénticos dentro del límite/transporte acordado o error, sin fallback a
derivado, resumen, última revisión u otra fuente. Para objetos grandes se
requiere transporte acotado e integridad de objeto completo al finalizar;
no se declara suficiente un fragmento aislado.
En el intercambio local de archivo JSON propuesto, `fetch_original` debe
escribir una salida de bytes en `output_ref` autorizado mediante archivo
temporal, verificar longitud/hash del origen y salida, y publicar el archivo
de salida antes de devolver `ok` con `bytes_ref`. Esa salida es entrega
temporal al consumidor, no segunda custodia permanente de Skopos. Un puntero
a la ruta de origen o a metadatos no basta: puede cambiar después del check.
El consumidor vuelve a leer y verificar el archivo entregado antes de
admitirlo. Raíces autorizadas, permisos, caducidad, limpieza, fallos de
salida y límites del transporte requieren acuerdo y pruebas bilaterales.

`seal_policy` se fija en el perfil bilateral, no en cada respuesta. `required`
necesita esquema, objeto cubierto y material de verificación autorizados;
`not_required` informa `seal_check=not_applicable`. Un SHA-256 coincidente
prueba correspondencia de bytes, no firma, autoría, oficialidad ni vigencia.

## Cobertura y derivados

`capture_coverage` enumera sólo los bytes u objetos efectivamente recibidos:
alcance declarado, miembros observados, exclusiones y estado
`complete_for_declared_scope`/`partial`/`unknown` con base. No afirma que el
origen externo fuera completo. `extraction_coverage` pertenece al perfil:
páginas, hojas, regiones, intervalos o archivos que el extractor examinó,
con fallos y exclusiones propios. No se permite promover captura completa a
extracción completa, ni extracción completa a validez semántica.

Cada derivado conserva `derivation_id`, tipo, hash, longitud, hash del padre,
herramienta/versión, digest de parámetros, alcance y limitaciones. El original
nunca se sustituye. Una cita sólo existe si un perfil define representación
hasheada, localizador y comprobación reproducible. Se informan separadamente
`original_bytes_verified`, `derivative_bytes_verified` y
`content_correspondence_reviewed`; los dos primeros no implican el tercero.
Si no hay perfil, el material puede ser custodiable pero extracción, búsqueda
y citas devuelven `unsupported_format`, no una conversión silenciosa a texto.

Perfiles futuros posibles, todos pendientes de decisión y evidencia:

| Familia | Localizador o riesgo que exige perfil propio |
|---|---|
| Texto plano | Codificación, BOM, CRLF y offsets sobre bytes concretos |
| Código | Archivo frente a árbol Git/commit; rutas, revisión y secretos incluidos por error |
| Word | Partes, tablas, comentarios, cambios controlados y contenido externo |
| Excel | Hoja/celda, fórmula frente a valor, nombres, vínculos externos y macros |
| PDF | Página física, región, texto incrustado/OCR y diagramas |
| Audio | Pista, intervalo temporal, transcripción y alineación no presumida |
| Video | Pista/cuadro o intervalo, base temporal, subtítulos y volumen |

## Almacenamiento, fallos y recuperación

La copia `docs/fuentes/imss/2000-002-001.pdf` ya existe bajo custodia declarada
de expertoGobernanza y tiene el mismo SHA-256 que el archivo entregado por el
Operador. El registro `2000-002-001-PROCEDENCIA.md` atribuye el origen inmediato
a esa copia local y documenta el cotejo puntual del consumidor con la URL del
IMSS, sin admisión al registry ni vigencia jurídica comprobada.
El archivo y registro están sin seguimiento Git en el checkout consumidor;
su presencia actual no demuestra una ruta estable, respaldo, control de acceso
o retención acordada. Ninguna opción sustituye esa custodia del consumidor.

Una entrega `provided_file` que sólo exista durante el intercambio no
sostiene `verified_external_reference` después de la admisión. Para ese modo
el consumidor debe conservar una referencia gobernada y accesible, con
retención y relocalización acordadas. Si sólo entrega una copia efímera,
Skopos puede verificarla en una operación puntual, pero no declarar
recuperación futura bajo Solicitud B. `managed_copy` resolvería la dependencia
de esa ruta sólo tras decisión de custodia, almacenamiento y recuperación.

| Modo candidato | Recuperación y brecha | Costo, retirada y autoridad |
|---|---|---|
| `verified_external_reference` | Skopos registra identidad/revisión/hash/ruta autorizada; en cada `fetch_original` abre la copia del consumidor y recomputa longitud y SHA-256. Si falta o cambia, falla sin texto ni fallback. No permite recuperar tras pérdida de la única copia salvo restauración del consumidor. | Evita duplicar el PDF; expertoGobernanza conserva propietario, ubicación, respaldo y retirada del original. Skopos mantiene metadatos/derivados bajo política separada. Encaja con la custodia por referencia de ADR-020, pero PDF y nuevo sobre requieren decisión/contrato propios. |
| `managed_copy` | Skopos conserva objeto adicional y puede recuperarlo si la copia del consumidor se pierde, sujeto a respaldo y claves propios. Hash igual no demuestra independencia si ambas copias comparten equipo/soporte. | Más almacenamiento, acceso, respaldo y superficies de retiro; coordinar plazos y borrado de ambas copias. Cambia la elección de referencia externa de ADR-020 y requiere enmienda expresa antes de implementarse. |

Para el primer piloto se **propone evaluar la referencia verificada**, no
declararla aceptada. El consumidor debe autorizar esa ruta y su acceso local,
fijar su conservación y ensayar pérdida/restauración; si necesita recuperación
independiente de su copia, se justifica `managed_copy` con decisión separada.
Un recibo de importación por referencia acredita el hash observado entonces,
no disponibilidad posterior: `fetch_original` vuelve a leer y verificar.
Un cambio de ruta no se arregla con el mismo hash por inferencia; exige
relocalización autorizada y auditable, o nueva revisión según el contrato
elegido. El `SourceStore` actual no relocaliza referencias automáticamente.

En `managed_copy`, la ubicación física no se fija por el hash ni por
`Downloads`. Skopos debe elegir almacén privado y estable, identificadores
opacos, permisos, límites y respaldo probados. Mongo puede registrar identidad,
revisión y relaciones, pero sus transacciones no incluyen archivos externos.
Protocolo candidato: copiar a área temporal bajo límites; comprobar
hash/longitud y persistencia; publicar objeto inmutable; confirmar registro y
cabeza bajo CAS; reconciliar objetos huérfanos y resultados inciertos. Cada
corte requiere ensayo. No borrar huérfanos hasta demostrar que no corresponden
a una admisión confirmada o aún en curso. El orden exacto sigue pendiente.

Errores mínimos: `not_found`, `revision_unavailable`, `bytes_unavailable`,
`hash_mismatch`, `seal_missing`, `seal_invalid`, `unsupported_format`,
`invalid_scope`, `unsupported_scope`, `manifest_mismatch`, `policy_unavailable`,
`permission_denied`, `limit_exceeded`, `budget_exceeded`,
`revision_conflict`, `predecessor_conflict`, `result_uncertain` y
`store_integrity_failed`. Un presupuesto agotado no es una búsqueda vacía ni
una admisión parcial. Reintentos con resultado incierto consultan recibo y
estado del objeto; no inventan una revisión nueva.

Antes de admitir, decidir propietario, lectores, clasificación, plazo,
exportación, retiro y respaldos **por modo**. Exportar exige bytes y manifiesto
con hashes, revisiones, contrato y límites de cobertura. En modo referencia,
la exportación de bytes depende de lectura autorizada de la copia del
consumidor; Skopos no promete exportarla si desapareció. Restaurar exige
probar resolución de la referencia y recuperación de bytes, o, en modo copia,
objetos, manifiestos y registros juntos. La retirada bloquea nuevas lecturas
y registra qué copias/respaldos quedan y hasta cuándo.
Si borrado selectivo de respaldos no está acreditado, se declara no soportado
y no se admite material que lo exija. Un respaldo sincronizado o una copia de
Mongo sola no prueban recuperación de los originales.

## Matriz de intercambio con Solicitud B

Esta es una conciliación **propuesta**, no aceptación del consumidor. El
perfil común del pedido exige sobre JSON UTF-8 local; un `request_sha256`
corresponde a los bytes exactos del archivo de solicitud y viaja fuera de
ese archivo. Skopos y el consumidor lo recomputan. La respuesta eco de
correlación no autentica al emisor por sí sola.

| Solicitud B del consumidor | Campo/comportamiento Skopos candidato | Brecha o regla de traducción |
|---|---|---|
| `contract_id`, `contract_version` | Campos planos idénticos en sobre y respuesta | Identificadores propuestos distintos requieren elección bilateral exacta; `schema` interno no sustituye versión del contrato |
| `request_id` | Consumidor asigna; productor devuelve igual | Reintento explícito usa nuevo ID y referencia al intento anterior; nunca inventar ID desde material |
| `request_sha256` | Campo exacto en sobre y respuesta | Reemplaza `request_digest`; SHA-256 de bytes de archivo de solicitud, calculado fuera de él; entrada discordante: `invalid_input/hash_mismatch` |
| Estado global | `ok`, `invalid_input`, `execution_failed`, `budget_exceeded`, `unsupported_version` | Sólo `ok` permite `result`; no mapear ausencia de bytes a `ok` vacío |
| Error | `error: {code, stage}` o `null` | `stage` mínimo: `validation`, `admission`, `retrieval`, `delivery`, `derivation`, `seal`; ningún secreto ni resultado consumible en fallo |
| Identidad/revisión/hash | `material_id`, `source_revision`, `original.sha256`, `byte_length` | El consumidor contrasta con su copia y revisión; hash igual no prueba oficialidad ni recuperación futura |
| Entrega del material | `source_delivery.mode` y archivo lateral o referencia autorizada | El PDF físico es opcional si la referencia permite leer bytes; ficha de procedencia sin bytes no produce admisión `ok` |
| Tipo/codificación | Tipo declarado y observado con método; codificación sólo si perfil textual la acredita | `application/pdf` declarado no basta para aceptar parser; sin perfil de extracción, `unsupported_format` |
| Procedencia/captura/versiones | `provenance` opcional y atribuida, comprobaciones puntuales, `captured_at`, versión de productor/adaptador | Hash de ficha vincula sus bytes, no valida sus afirmaciones; ausencia de antecedentes se marca `unknown` |
| `coverage` | `coverage` equivale sólo a `capture_coverage` del alcance declarado; perfil agrega `extraction_coverage` separada | No llamar completa a la lectura de portada/diagrama por conservar todos los bytes |
| `seal_policy` y `seal_check` | Perfil bilateral fija `required`/`not_required`; respuesta informa método y estado | `required` sin sello: `execution_failed/seal_missing`; inválido: `execution_failed/seal_invalid`; `not_required`: `not_applicable`, nunca `verified` |
| Bytes recuperables | `fetch_original` por material/revisión/hash, salida autorizada verificada y `bytes_ref` en `ok` | En modo referencia lee copia del consumidor y entrega bytes exactos en salida temporal; `bytes_unavailable`/`hash_mismatch` detienen resultado, sin fallback |
| Retención/retiro | `custody.mode`, propietario y política/versionado | Modo referencia no promete borrar ni respaldar la copia del consumidor; modo copia exige política conjunta de ambos |

La correspondencia de errores propuesta es: esquema, hash de solicitud o
localizador de entrada inválidos → `invalid_input`/`validation`; versión de
contrato incompatible → `unsupported_version`/`validation`; límite agotado →
`budget_exceeded` en la etapa afectada; revisión/bytes ausentes, hash de bytes
recuperados discordante, sello fallido o formato de extracción no soportado →
`execution_failed` en `retrieval`, `delivery`, `seal` o `derivation` según
corresponda. Fallo de salida es `execution_failed/output_unavailable` en
`delivery`, nunca un éxito que sólo ofrece la ruta de origen.
`invalid_scope` significa valor malformado (`invalid_input/validation`);
`unsupported_scope` significa valor reconocido como `manifested_set` pero no
implementado (`execution_failed/admission`). No se usan como sinónimos.
Si el hash declarado de un archivo entregado o de la ficha lateral no coincide
al validar la entrada, se rechaza `invalid_input/hash_mismatch` en
`validation`; si cambian los bytes de una referencia ya admitida durante la
recuperación, se devuelve `execution_failed/hash_mismatch` en `retrieval`.
La falta de antecedentes opcionales no es error de captura: se conserva como
`unknown`. Una contradicción declarada no se oculta ni se resuelve inventando
oficialidad; se devuelve al consumidor para corrección o decisión.

| Afirmación | Control positivo reproducible | Mutación negativa y rechazo esperado |
|---|---|---|
| Admisión con ficha opcional | Fixture PDF y ficha legibles, hashes coincidentes; recibo atribuye declaraciones | Quitar `provenance` del JSON y recalcular digest: admisión mecánica posible, procedencia `unknown` si la política no exige ficha |
| Hash del PDF | Archivo y `expected_source_sha256` coincidentes | Cambiar un byte del fixture: `invalid_input/hash_mismatch` en `validation`, sin cabeza nueva |
| Hash de la ficha | Ficha legible y digest coincidente | Cambiar ficha o declararla pero retirarla: `invalid_input/hash_mismatch` o `invalid_input/provenance_incomplete` en `validation`; no descartarla en silencio |
| Bytes al admitir | Ruta autorizada y PDF legible | Quitar PDF dentro de la raíz: `execution_failed/bytes_unavailable` en `admission` o `permission_denied` si ése es el fallo identificado; sin `ok` |
| Frontera de ruta | Archivo ordinario bajo raíz acordada | Ruta fuera de raíz o enlace que escape: `invalid_input` en `validation` sin abrir el objetivo |
| Recuperación por referencia | `fetch_original` lee revisión/hash admitidos y entrega salida verificada | Alterar copia: `execution_failed/hash_mismatch`; retirarla: `execution_failed/bytes_unavailable`, ambos en `retrieval`, sin fallback |
| Respuesta perdida y reintento | Capturar recibo confirmado; consultar por identidad/solicitud y obtener el mismo estado | Cortar canal después de confirmar: no crear otra revisión; `result_uncertain` hasta reconciliar el recibo |
| Revisión inmutable | Rev 2 con predecesor rev 1 correcto conserva ambas | Mismo número/hash distinto o predecesor falso: `revision_conflict` o `predecessor_conflict`, sin mover cabeza |
| Entrega al consumidor | Salida bajo raíz autorizada, escrita y verificada antes de `ok` | Hacer `output_ref` no escribible: `execution_failed/output_unavailable` en `delivery`, sin `result` |
| Procedencia frente a verificación | Hash de PDF y ficha correctos, afirmaciones atribuidas | Incluir URL o relato falso con hashes locales válidos: ningún ascenso automático a oficialidad o vigencia |

Cada mutación necesita su control positivo con la misma política y un fixture
legible para demostrar que la sonda funciona. **Ninguno de estos ensayos de
runtime se ha ejecutado para el contrato PDF candidato**; los gates de
documentación sólo verifican estructura y ejemplos, no estos comportamientos.

### Transporte local candidato y límites por acordar

El archivo de solicitud se codifica en UTF-8; `request_sha256` cubre **todos
sus bytes exactos**, incluidos espacios o salto final si los tuviera. Los
ejemplos fijan una sola línea sin salto final. Un sobre separado, no incluido
en ese digest, contiene `request_file_ref`, `request_sha256`, `contract_id`,
`contract_version` y `request_id`; el productor abre el archivo bajo una raíz
de solicitudes acordada, recalcula el digest y compara los otros tres campos
del sobre con el JSON antes de devolverlos en la respuesta.
La relación sobre→archivo no autentica al emisor; el acceso lo concede la
configuración bilateral de raíces y los permisos del proceso, no `project_id`.

Raíces distintas gobiernan solicitudes, archivos laterales, copia persistente
del consumidor y salidas. Sus rutas reales, propietarios y permisos siguen
pendientes. Se rechazan `..`, rutas absolutas inesperadas, enlaces simbólicos
que escapen y cambios de archivo entre validación y lectura. La implementación
debe abrir un archivo regular dentro de la raíz autorizada, comprobar la
identidad efectiva del objeto leído y cerrar la carrera con verificación de
bytes sobre el descriptor usado. En `provided_file`, lateral y `persistent_ref`
se leen y comparan **antes** de confirmar admisión; el registro fija la
referencia persistente. `fetch_original` fija proyecto, material, revisión,
hash y esa referencia admitida; no acepta una nueva ruta de origen.

`output_ref` se resuelve bajo la raíz de salida, se publica después de escribir
y verificar bytes completos, y queda disponible sólo durante un plazo a
acordar. El consumidor debe releer y verificar longitud/hash antes de ese
vencimiento. El productor no anuncia `ok` si la salida no pudo publicarse;
un timeout obliga a reconciliar el recibo antes de repetir efectos. La vida
exacta del lateral, de `output_ref`, de la referencia persistente y el método
de publicación segura requieren acuerdo y prueba bilateral.

### Ejemplos mínimos de intercambio, no ejecutados

**Solicitud completa de admisión candidata.** El archivo es exactamente la
línea JSON UTF-8 siguiente, sin salto final. Su `request_sha256`, calculado
sobre esos bytes exactos y enviado en el sobre externo, es
`f6705bd3906d581bfb1475e1ab65cc04fed6be6ecf7674e4ab869deecb41b1fc`.
El hash del PDF es otro campo y se vuelve a calcular al leer el archivo.
`file_ref` se resolvería bajo una raíz del consumidor acordada, no bajo el
cwd de Skopos. Los nombres de política, clasificación y límites son valores
ilustrativos pendientes de aceptación bilateral; el ejemplo no autoriza la
admisión ni acredita que exista runtime PDF.

```json
{"contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-admit-001","operation":"admit_original","project_id":"expertogobernanza","material_id":"imss-2000-002-001","source_revision":1,"scope":"single_object","source_delivery":{"mode":"authorized_reference","file_ref":"docs/fuentes/imss/2000-002-001.pdf"},"expected_source_sha256":"719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323","media_type_declared":"application/pdf","provenance":{"asserted_by":"expertogobernanza","record_ref":"docs/fuentes/imss/2000-002-001-PROCEDENCIA.md","record_sha256":"f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff","origin_url":"https://www.imss.gob.mx/sites/all/statics/pdf/manualesynormas/2000-002-001.pdf","claim":"Descarga HTTPS y cotejo puntual de SHA-256, tamaño y cmp con la copia local el 2026-10-08","claim_status":"consumer_declared"},"classification":"consumer_declared_public","custody_mode":"verified_external_reference","custody_policy_id":"candidate/consumer-reference","custody_policy_version":"v0.1","seal_profile_id":"candidate/not_required","limits":{"max_bytes":2000000,"max_pages":200,"allow_network":false,"allow_ocr":false}}
```

El `record_sha256` corresponde a la ficha local observada aquí y debe
recalcularse al usar el ejemplo. Si se omite `provenance` entero, cambia el
archivo de solicitud y se calcula un `request_sha256` nuevo; el estado de
procedencia será `unknown`.

**Variante completa `provided_file`.** El siguiente archivo también es una
sola línea JSON UTF-8 sin salto final. Su digest externo es
`0b8a24c1f9ec25e7acb44e5b4a68c5f43e5a77e2c4a1f0c21b33990e7194f571`.
El PDF lateral se entrega fuera del JSON bajo la raíz de entrada acordada;
`persistent_ref` se resuelve bajo la raíz de custodia del consumidor. Antes
de emitir recibo de admisión, Skopos leería ambos archivos completos y
comprobaría longitud y hash idénticos al hash esperado. Si falta la copia
duradera, no emite `ok` en `verified_external_reference`. El lateral se puede
retirar después de que el resultado y cualquier reintento incierto queden
conciliados; plazo y responsable de limpieza requieren acuerdo bilateral.

```json
{"contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-admit-002","operation":"admit_original","project_id":"expertogobernanza","material_id":"imss-2000-002-001","source_revision":1,"scope":"single_object","source_delivery":{"mode":"provided_file","file_ref":"in/eg-b-pdf-admit-002.pdf","persistent_ref":"docs/fuentes/imss/2000-002-001.pdf"},"expected_source_sha256":"719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323","media_type_declared":"application/pdf","provenance":{"asserted_by":"expertogobernanza","record_ref":"docs/fuentes/imss/2000-002-001-PROCEDENCIA.md","record_sha256":"f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff","origin_url":"https://www.imss.gob.mx/sites/all/statics/pdf/manualesynormas/2000-002-001.pdf","claim":"Descarga HTTPS y cotejo puntual de SHA-256, tamaño y cmp con la copia local el 2026-10-08","claim_status":"consumer_declared"},"classification":"consumer_declared_public","custody_mode":"verified_external_reference","custody_policy_id":"candidate/consumer-reference","custody_policy_version":"v0.1","seal_profile_id":"candidate/not_required","limits":{"max_bytes":2000000,"max_pages":200,"allow_network":false,"allow_ocr":false}}
```

Sobre externo ilustrativo de esa variante; sus bytes **no** forman parte del
digest del archivo de solicitud:

```json
{"request_file_ref":"requests/eg-b-pdf-admit-002.json","request_sha256":"0b8a24c1f9ec25e7acb44e5b4a68c5f43e5a77e2c4a1f0c21b33990e7194f571","contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-admit-002"}
```

Ambos ejemplos son **alternativas para una primera admisión**, no solicitudes
sucesivas para crear la misma revisión. Si se intentan ambas, identidad y
política iguales obligan a reconciliar el recibo existente, no a crear una
segunda admisión.

**Recibo de admisión hipotético** para la solicitud `admit-001`, suponiendo
que la política y clasificación ilustrativas fueron aceptadas antes, que
los bytes siguen accesibles y que todas las comprobaciones pasan. Fechas,
referencia opaca e identificador de recibo son valores de ejemplo, no una
ejecución de Skopos. `provenance_checks` distingue lo que comprobaría el
productor localmente de lo que seguiría siendo declaración del consumidor:

```json
{"schema":"skopos/source-custody/v0.1","contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-admit-001","request_sha256":"f6705bd3906d581bfb1475e1ab65cc04fed6be6ecf7674e4ab869deecb41b1fc","status":"ok","error":null,"producer_version":"candidate","adapter_version":"skopos/pdf-profile/v0.2","result":{"material":{"project_id":"expertogobernanza","material_id":"imss-2000-002-001","source_revision":1,"previous_source_sha256":null,"scope":"single_object"},"original":{"object_ref":"example:imss-2000-002-001-r1","sha256":"719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323","byte_length":1311822,"media_type_declared":"application/pdf","media_type_observed":"application/pdf","detection_method":"example:pdf-signature","captured_at":"2026-10-08T17:00:00Z","provenance":{"asserted_by":"expertogobernanza","record_sha256":"f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff","claim_status":"consumer_declared","record_ref":"docs/fuentes/imss/2000-002-001-PROCEDENCIA.md","origin_url":"https://www.imss.gob.mx/sites/all/statics/pdf/manualesynormas/2000-002-001.pdf","remote_byte_match":"consumer_declared"},"provenance_checks":[{"field":"original.sha256","status":"matched_locally","actor":"skopos"},{"field":"provenance.record_sha256","status":"matched_locally","actor":"skopos"},{"field":"provenance.origin_url","status":"consumer_declared","actor":"expertogobernanza"},{"field":"provenance.remote_byte_match","status":"consumer_declared","actor":"expertogobernanza"}],"seal_policy":"not_required","seal_check":"not_applicable"},"coverage":{"declared_scope":"single_object","status":"complete_for_declared_scope","exclusions":[],"basis":"full_byte_read"},"custody":{"mode":"verified_external_reference","policy_id":"candidate/consumer-reference","policy_version":"v0.1","owner":"expertogobernanza","classification":"consumer_declared_public","admitted_at":"2026-10-08T17:00:00Z","retention_basis":"example:consumer-policy","recoverability_checked_at":"2026-10-08T17:00:00Z"},"receipt":{"receipt_id":"example:eg-b-pdf-admit-001","admission_status":"admitted","producer_version":"candidate","adapter_version":"skopos/pdf-profile/v0.2"}}}
```

Fallo hipotético correlacionado: si el PDF difiere del hash esperado al
validar, no existe `result` consumible ni nueva cabeza. Un fallo de ficha
declarada usa también `invalid_input` en `validation`, con código tipado por
acordar; este ejemplo muestra el caso PDF:

```json
{"schema":"skopos/source-custody/v0.1","contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-admit-001","request_sha256":"f6705bd3906d581bfb1475e1ab65cc04fed6be6ecf7674e4ab869deecb41b1fc","status":"invalid_input","error":{"code":"hash_mismatch","stage":"validation"},"producer_version":"candidate","adapter_version":"skopos/pdf-profile/v0.2"}
```

**Solicitud distinta de recuperación.** El archivo `fetch_original` siguiente
es una línea JSON UTF-8 sin salto final, con `request_sha256`
`da511d17e6c3d77b68ae07da3c13486bf6370a556fba053f314a7d89c8e46baf`
en su propio sobre externo. No admite ni renueva la custodia. La referencia
de origen se toma del registro admitido, no de la solicitud de lectura;
`output_ref` se resuelve bajo una raíz de salida autorizada. No concede
acceso ni crea la salida.

```json
{"contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-fetch-001","operation":"fetch_original","project_id":"expertogobernanza","material_id":"imss-2000-002-001","source_revision":1,"expected_source_sha256":"719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323","output_ref":"out/eg-b-pdf-fetch-001.pdf"}
```

Sobre externo de entrada: `request_sha256` igual al digest anterior, más una
referencia explícita al archivo exacto. Éxito **hipotético**, condicionado a
una admisión previa válida, lectura completa, igualdad de hash y política de
sello `not_required`:

```json
{"schema":"skopos/source-custody/v0.1","contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-fetch-001","request_sha256":"da511d17e6c3d77b68ae07da3c13486bf6370a556fba053f314a7d89c8e46baf","status":"ok","error":null,"producer_version":"candidate","adapter_version":"skopos/pdf-profile/v0.2","result":{"material_id":"imss-2000-002-001","source_revision":1,"source_sha256":"719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323","byte_length":1311822,"bytes_ref":"out/eg-b-pdf-fetch-001.pdf","coverage":{"status":"complete_for_declared_scope","scope":"single_object","exclusions":[]},"seal_check":"not_applicable","custody_mode":"verified_external_reference","custody_owner":"expertogobernanza"}}
```

Fallo hipotético si la copia del consumidor ya no se puede leer; `result`
queda ausente y el recibo anterior no se convierte en recuperación:

```json
{"schema":"skopos/source-custody/v0.1","contract_id":"expertogobernanza/skopos-source","contract_version":"v0.1","request_id":"eg-b-pdf-fetch-001","request_sha256":"da511d17e6c3d77b68ae07da3c13486bf6370a556fba053f314a7d89c8e46baf","status":"execution_failed","error":{"code":"bytes_unavailable","stage":"retrieval"},"producer_version":"candidate","adapter_version":"skopos/pdf-profile/v0.2"}
```

`bytes_ref` y `producer_version: candidate` son marcadores de diseño, no una
API ni una ejecución real. La respuesta `ok` no se emitiría sólo por encontrar
un índice, una ruta o un recibo: debe entregar salida de bytes y comprobar
longitud/hash. El consumidor debe leer y verificar la salida antes de
admitirla; una salida temporal no es custodia independiente permanente.

## Autoridad, interoperación y primer incremento

Los bytes se tratan como datos no confiables: no se ejecutan macros, código,
instrucciones incrustadas, vínculos externos ni contenido activo. Custodia
básica no invoca LLM ni red. Cada parser permitido requiere perfil, límites y
controles propios. El perfil local actual usa los permisos de la cuenta/proceso
y de Mongo, y la ruta que ese proceso puede abrir: `project_id` es selector,
no credencial ni ACL. «Lectura autorizada» en esta propuesta significa ruta
incluida en el alcance acordado y acceso efectivo del proceso local; no
autenticación individual de agente ni aislamiento multiusuario. Un perfil
compartido necesita autorización por recurso y auditoría verificadas aparte.

Skopos entrega bytes verificados, procedencia atribuida cuando exista y
localizadores conforme al perfil.
expertoGobernanza conserva la asociación de cada cita con `disposicion_id`,
criterios y resultado de su gate. El intercambio optativo no escribe registry,
EvidenceEdge, Ágora ni AN-KLA desde Skopos. El productor y el consumidor
deben acordar versión, transporte, errores, política de sello, datos y
responsables; sus identificadores de propuesta no son compatibles por nombre.

Primer incremento propuesto: contrato base sobre fixture textual sintético
y perfil PDF acotado sobre fixtures propios, primero con referencia verificada.
Para el PDF real se exige después decisión de clasificación, custodia,
retención, ruta autorizada y piloto. Criterios
previos a conformidad: controles positivo/negativo de bytes, revisión,
concurrencia, corte entre objeto y Mongo, respuesta perdida, falta de original,
formato sin perfil, ruta fuera de raíz, enlace simbólico, cambio de archivo
entre lectura y entrega, salida no escribible, exportación, restauración,
retiro y presupuesto. Buscar
contenido o demostrar utilidad es una evaluación separada. El perfil de
referencia no enmienda por sí solo la elección de custodia de ADR-020; la
copia propia sí requeriría un ADR que la enmiende. Ninguna opción está
aceptada ni implementada para PDF.
