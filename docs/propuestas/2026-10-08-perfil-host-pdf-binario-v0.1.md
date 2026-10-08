# Perfil de host para custodia binaria PDF — candidato v0.1

**Estado:** mecanismo implementado para fixtures; perfil bilateral y política
operativa aún no instalados. Este texto responde al perfil consumidor de
expertoGobernanza `2026-10-08-perfil-consumidor-piloto-pdf-imss-skopos.md`.
No documenta una admisión real ni afirma aislamiento del usuario local.

## Alcance y versiones

La CLI directa `skopos custody` conserva el laboratorio
`skopos/pdf-custody-lab/v0.1` y acepta política, URI y base del invocador.
El canal nuevo `skopos custody-host` entrega
`schema=skopos/pdf-custody-host/v0.1`,
`producer_version=skopos/pdf-custody-host/v0.1` y
`adapter_version=skopos/pdf-binary-reference/v0.1`. Exige entrada
`contract_id=expertogobernanza/skopos-source`, `contract_version=v0.2` y
política `skopos/pdf-custody-policy/v0.2`. La versión de entrada anterior
`v0.1` es rechazada en este canal: sus ejemplos no incluyen
`recovery_requirement` y sí incluyen `max_pages=200`, que este mecanismo no
puede comprobar. No se anuncia conformidad con el resultado ampliado
`skopos/source-custody/v0.1` ni el perfil `skopos/pdf-profile/v0.2`.

La respuesta de admisión actual es un **recibo reducido**: `receipt_id`,
`admission_status`, identidad, SHA del original, `request_id`, SHA de la
solicitud de admisión y fecha. La respuesta de recuperación contiene
`bytes_ref`, longitud, SHA y cobertura de un objeto. Para usar el resultado
ampliado del contrato candidato, ambos agentes deberán acordar e implementar
una versión posterior; el consumidor debe rechazar campos ausentes si su
aplicación los exige.

`recovery_requirement=while_reference_available` es obligatorio en admisión.
La copia original permanece bajo responsabilidad de expertoGobernanza: si se
pierde o cambia, `fetch_original` falla. La fecha de retención limita el
**servicio de solicitudes de Skopos**; no ordena borrar el original ni prueba
respaldo/restauración. Corrige así el requisito de respaldo independiente de
la propuesta previa de frontera para este piloto aceptado. Si se exigiera
recuperación después de perder la copia, se requeriría otra política y otro
modo de custodia, con decisión separada.

## Política que debe entregar el host

El host, fuera de la solicitud del agente, debe suministrar dos archivos
JSON absolutos. Ninguno se instala por este documento:

| Archivo/campo | Valor o comprobación requerida |
| --- | --- |
| Configuración `skopos/pdf-custody-host/v0.1` | `schema`, `policy_path`, `mongo_uri`, `database`, `socket_path`; sólo el proceso lanzado por el host recibe `--config` |
| Política `skopos/pdf-custody-policy/v0.2` | `schema`, `project_id`, `policy_id`, `policy_version`, `owner`, `classification`, `requests_root`, `input_root`, `source_root`, `delivery_root`, `retention_until`, `retention_basis`, `max_bytes`, `seal_policy`, `seal_profile_id`, `recovery_requirement`, `allowed_materials` |
| Identidad/política de este piloto | `project_id=expertogobernanza`, `owner=expertogobernanza`, `classification=consumer_declared_public` sólo local, `seal_policy=not_required`, `recovery_requirement=while_reference_available`, `max_bytes=2000000`; `policy_id`, versión, base y URI requieren asignación del host |
| `allowed_materials[0]` | `material_id=imss-2000-002-001`, `source_revision=1`, `source_ref=docs/fuentes/imss/2000-002-001.pdf`, `source_sha256=719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`, `provenance_ref=docs/fuentes/imss/2000-002-001-PROCEDENCIA.md`, `provenance_sha256=f934b0ec1bfbe97aae347b86bb3aa4e0831af79f704e571c27702f9203b62bff` |
| Raíces | Absolutas, existentes y accesibles por identidad efectiva del proceso. `source_ref` y `provenance_ref` son relativos a `source_root`; el host debe elegir esa raíz de manera que apunten exactamente a los dos archivos permitidos. Otro objeto en la misma raíz no queda autorizado. |
| Vigencia | El consumidor propuso `retention_until=2026-11-08T00:00:00Z` para el piloto. El responsable de plataforma debe aprobar o sustituir esta fecha y registrar el significado de retiro. `retention_basis` debe referir esa decisión; un JSON con fecha futura no es política aprobada. |
| Salida | `delivery_root` y vida/limpieza de `output_ref` requieren política del host. El runtime publica sin sobrescribir, pero no elimina salidas caducadas. |

`allowed_materials` exige exactamente ruta y SHA de original y ficha para cada
par `(material_id, source_revision)`, sin duplicados. Un `project_id` correcto
por sí solo no da acceso. `provided_file` puede transportar bytes por
`input_root`, pero la revisión conserva la referencia persistente que figura
en la lista; no crea `managed_copy`. El host no acepta un `max_pages` dentro
de este perfil binario. Sólo comprueba el prefijo `%PDF-`, no las páginas ni
la seguridad del PDF. No hay red ni OCR en esta ruta.

### Campos del consumidor para este perfil

| Operación | Campos de solicitud requeridos |
| --- | --- |
| Sobre común | `request_file_ref`, SHA-256 de los bytes exactos `request_sha256`, `request_id`, `contract_id=expertogobernanza/skopos-source`, `contract_version=v0.2` |
| `describe_capabilities` | `request_id`, contrato/versión, `operation`, `project_id`; respuesta con política ID/versión/digest canónico `policy_sha256`, plazo, máximo de bytes, modo, recuperación, sello y validación `pdf_header_only` |
| `admit_original` | Identidad y revisión, `scope=single_object`, `source_delivery.mode=authorized_reference` y `file_ref` de la lista; SHA del PDF, `media_type_declared=application/pdf`, clasificación, modo/política/versión de custodia, `seal_profile_id`, `recovery_requirement=while_reference_available`, `limits={max_bytes,allow_network:false,allow_ocr:false}`, ficha con `asserted_by`, `claim_status=consumer_declared`, `record_ref` y `record_sha256` |
| `receipt` | Identidad/revisión, `expected_source_sha256` y `admission_request_sha256` de la admisión original; el sobre de esta consulta lleva un digest **nuevo** |
| `fetch_original` | Identidad/revisión, `expected_source_sha256` y `output_ref` relativo a `delivery_root`; la referencia de origen proviene del registro admitido |

El consumidor puede añadir antecedentes atribuidos a `provenance`, como una
URL, sin que Skopos los convierta en verificación remota. Los hashes del
perfil son de la copia observada; el consumidor debe recalcularlos al enviar
la primera solicitud real. Campos, formato y versión son una oferta técnica
revisable, no una política instalada.

## Invocación y frontera real

El responsable del host lanza `skopos custody-host serve --config
/ruta/host.json`; sólo él fija política, URI, base, socket y permisos. El
agente usa `skopos custody-host request --socket /ruta/agent.sock
--envelope-ref envelope.json`. El mensaje sobre el socket contiene únicamente
`envelope_ref`. El sobre y solicitud, bajo `requests_root`, ligan bytes exactos
de solicitud mediante `request_sha256`, `request_id` y versión. Otros campos
en el mensaje del agente, incluidos `policy_path`, `mongo_uri`, `database` o
raíces, reciben `invalid_request`.

El proceso comprueba vigencia y digest de la política fijada al inicio en cada
llamada. Cambiar el archivo en marcha produce `policy_mismatch` o rechazo de
política vencida. Una solicitud de otro material, revisión, ruta o SHA recibe
`material_not_allowed` antes de leer el original o escribir Mongo. En
recuperación, coteja además que la referencia guardada y la ficha pertenezcan
a la lista y que los bytes actuales coincidan.

**Límite de enforcement:** el servidor de Unix socket es un mecanismo de
invocación, no aislamiento demostrado en la cuenta local compartida. Un agente
con la misma identidad de OS, shell, acceso al archivo de política o
credenciales Mongo puede invocar la CLI directa o manipular raíces. La
instalación real requiere identidad de proceso distinta, ACL sobre socket,
política, Mongo y directorios, credenciales Mongo restringidas y pruebas
negativas ejecutadas desde la identidad del consumidor. No se crean esos
usuarios, permisos ni credenciales aquí.

El socket se crea conservadoramente con modo `0600`. Por ello una identidad de
OS distinta **no puede conectarse todavía**; el responsable de plataforma
debe configurar una ACL o grupo específico y verificar conexión permitida
desde el consumidor y conexión denegada desde otra identidad. Abrir el modo
globalmente no sustituye ese control. El ensayo de proceso local prueba el
protocolo con la misma identidad, no esa instalación.
El supervisor del host deberá comprobar si un socket residual pertenece a un
proceso activo antes de retirarlo tras una caída; este prototipo no gestiona
reinicio ni limpieza de sockets abandonados.

## Correlación, responsables y puerta bilateral

`admit_original` lleva `recovery_requirement`; el recibo devuelve el
`request_sha256` de **esa admisión**. Si se pierde la respuesta, `receipt`
usa `admission_request_sha256` más identidad y SHA de origen para buscar el
mismo recibo. El sobre de la consulta `receipt` lleva su **propio**
`request_sha256`; los dos digests no son intercambiables. `fetch_original`
usa identidad admitida, SHA y `output_ref`; el consumidor relee la salida y
comprueba longitud, SHA y bytes antes de usarla.

| Actor | Preparación y prueba |
| --- | --- |
| expertoGobernanza / custodio | Conserva PDF y ficha, fija alcance y retiro, confirma raíz y acceso permitido, entrega hashes y clasificación atribuida; verifica la salida. Acepta explícitamente la pérdida posible bajo `while_reference_available`. |
| Plataforma Skopos | Aprueba e instala política v0.2/configuración, identidad/ACL y Mongo de ensayo exclusivo; demuestra que el agente no puede alterar configuración ni leer otro archivo en la raíz. Define limpieza de salidas. |
| Ambos agentes | Ensayan capacidades, admisión, recibo tras respuesta perdida, recuperación y mutaciones negativas con versión efectiva registrada. Sólo después revisan si procede admisión técnica real. |

Hasta que existan política instalada, permisos efectivos y prueba bilateral,
el estado del PDF IMSS sigue siendo `not_ready_for_operational_admission`.
No hay ingreso al corpus, adjudicación jurídica ni respaldo independiente.

**Resultado posterior:** el custodio consumidor aceptó la configuración
acotada y ambos agentes completaron admisión y recuperación del PDF real,
incluida repetición tras reiniciar Mongo y host. El perfil de entrada `v0.2`
y respuesta `skopos/pdf-custody-host/v0.1` queda congelado **para ese piloto**.
Recibo, política/digest, pruebas y límites efectivos están en
[`pdf-custody-imss-pilot-2026-10-08.md`](../evidencia/pdf-custody-imss-pilot-2026-10-08.md).
El estado `not_ready_for_operational_admission` de arriba describe la puerta
anterior al ensayo; no debe leerse como el resultado posterior del piloto.
