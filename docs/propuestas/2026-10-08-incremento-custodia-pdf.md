# Incremento técnico PDF por referencia — 2026-10-08

Estado: implementación local de laboratorio. El contrato bilateral
`skopos/source-custody/v0.1` y el perfil `skopos/pdf-profile/v0.2` siguen
**candidatos**. No hay política real de host instalada, prueba bilateral con
expertoGobernanza, admisión del PDF IMSS, incorporación al corpus ni aceptación
jurídica. Este incremento implementa sólo custodia mecánica del original.
La respuesta y el registro usan `skopos/pdf-custody-lab/v0.1`, para no fingir
conformidad con el contrato y perfil completos todavía no implementados.

## Alcance operativo

`skopos custody` acepta una solicitud JSON bajo una raíz de solicitudes
preconfigurada. Un sobre separado declara `request_file_ref`, SHA-256 de los
bytes exactos de esa solicitud y sus tres campos de correlación. Skopos
comprueba la coincidencia antes de ejecutar. La política, proporcionada por el
host y fuera de Git, fija proyecto, propietario, clasificación, raíces,
retención, límite de bytes y sello `not_required`. La solicitud no crea raíces
ni concede permisos.

`admit_original` exige una copia persistente accesible bajo `source_root` y
guarda identidad, revisión, hash, longitud, referencia, política y procedencia
atribuida en colecciones separadas `pdf_custody_*_v1`. `provided_file` sólo es
transporte: se lee bajo `input_root`, se compara byte a byte con
`persistent_ref` y se conserva esta última como referencia. Se exige MongoDB
con transacciones; revisión y cabeza se publican juntas. `receipt` permite
consultar una admisión ya confirmada mediante identidad, SHA del original y
SHA de la solicitud de admisión sin volver a leer el archivo.

`fetch_original` selecciona identidad y hash admitidos, vuelve a leer el
original dentro de la raíz y comprueba longitud y SHA-256. Publica bytes en
`delivery_root` con creación exclusiva, sin sobrescribir archivos existentes.
Una modificación de la política de host, incluso si conserva su ID y versión,
invalida la recuperación hasta que exista una vía explícita de migración.
El consumidor debe releer el resultado y comprobar hash y longitud. Si el
original desapareció, cambió o la política caducó, falla sin entrega. El
recibo histórico no acredita disponibilidad actual.

La solicitud debe pedir `recovery_requirement=while_reference_available`,
coincidente con la política de host. Una exigencia de recuperación
independiente de esa copia se rechaza. La detección del tipo observado
comprueba únicamente el prefijo `%PDF-`. No
prueba estructura, ausencia de cifrado, número de páginas, renderizabilidad,
ausencia de contenido activo ni seguridad del visor. Por ello la respuesta de
capacidades declara `format_validation=pdf_header_only`. `max_pages` se
rechaza con `unsupported_limit`: no hay parser que pueda comprobarlo. El
ejemplo bilateral previo con `max_pages=200` requiere una solicitud de
custodia binaria separada o validación PDF adicional antes de ejecutarse.
Este incremento no ejecuta extracción ni OCR. No se ofrece
`managed_copy`, sello criptográfico adicional, URL de ingesta ni borrado de la
copia del consumidor.

## Política de host requerida

Ejemplo para **fixture**, con rutas que deben sustituirse por directorios
preconfigurados y gobernados por el responsable de plataforma. No es política
operativa de expertoGobernanza ni autorización para usar su PDF:

```json
{
  "schema": "skopos/pdf-custody-policy/v0.1",
  "project_id": "fixture",
  "policy_id": "fixture/external-reference",
  "policy_version": "v0.1",
  "owner": "fixture",
  "classification": "consumer_declared_public",
  "requests_root": "/absolute/fixture/requests",
  "input_root": "/absolute/fixture/input",
  "source_root": "/absolute/fixture/persistent",
  "delivery_root": "/absolute/fixture/output",
  "retention_until": "2027-01-01T00:00:00Z",
  "retention_basis": "fixture-policy",
  "max_bytes": 2000000,
  "seal_policy": "not_required",
  "seal_profile_id": "fixture/not-required",
  "recovery_requirement": "while_reference_available"
}
```

Precondiciones que el host debe resolver antes del primer intercambio real:

1. Política bilateral aceptada, vigente y vinculada al proyecto; responsable
   de la copia persistente y retiro definidos. `retention_until` es una
   declaración de política, no un bloqueo técnico que impida borrar el PDF.
2. Directorios absolutos existentes con permisos efectivos para el proceso.
   Raíces de solicitudes, lateral, original persistente y salida se separan.
   Los permisos de OS, respaldo y control de acceso pertenecen al host.
3. MongoDB de Skopos con replica set y transacciones, base dedicada y acceso
   gobernado. `project_id` es selector, no ACL multiusuario.
4. Límite de salida y plazo de consumo acordados bilateralmente. La
   implementación actual no caduca archivos de salida ni los limpia sola;
   el host debe hacerlo mediante política propia antes de uso real.
5. Aceptación de que la referencia externa deja de ser recuperable si el
   custodio pierde su única copia. No hay garantía de respaldo por parte de
   Skopos.

La CLI se invoca como:

```text
skopos custody --policy /absolute/host/policy.json --database DB \
  --envelope-ref envelope.json
```

`envelope.json` se lee bajo `requests_root`. `describe_capabilities` funciona
sin Mongo; admisión, consulta de recibo y recuperación requieren Mongo.
`receipt` usa `admission_request_sha256`, el digest exacto que devolvió el
recibo de admisión. La solicitud `receipt` tiene su propio `request_sha256`
externo para correlación. En el contrato documental previo estos dos hashes
no estaban separados de forma suficientemente explícita; esta distinción es
una corrección candidata a acordar con el consumidor.

## Errores y controles

Rutas relativas con `..`, enlaces finales o componentes intermedios enlazados,
archivos no regulares y raíces ausentes se rechazan. Cada lectura usa un
descriptor abierto bajo la raíz. La política caducada falla cerrado. La
salida existente no se sobrescribe. Las respuestas de error exponen código y
etapa, sin ruta absoluta ni contenido del PDF. La identidad se guarda en una
colección distinta de las fuentes TXT/ASR/runtime; no cambia esos contratos.

Esto no autentica al emisor: el acceso depende de la distribución segura del
archivo de política y de los permisos efectivos del host. Tampoco resiste a
un proceso concurrente con capacidad de modificar las raíces o Mongo entre
verificaciones. La evidencia de pruebas locales sólo cubre el entorno de
fixtures y la versión inspeccionada; hay que probar permisos y recuperación
en el host de ambos agentes antes de anunciar operación autónoma.
La CLI acepta `--policy`, `--uri` y `--database` del proceso invocador: por
sí sola no impide que un agente con acceso de shell elija otro archivo de
política o base. Para uso entre agentes, el host debe exponer una herramienta
limitada que fije esos valores fuera del control de las solicitudes, o aislar
permisos de OS y Mongo de modo equivalente. Esa envoltura aún no existe.

## Puerta para aceptar el PDF real

Pendiente de decisión y preparación del responsable de plataforma: instalar
una política real y comprobar que su raíz persistente, retención, salida y
acceso corresponden al contrato aceptado. Después, expertoGobernanza puede
ofrecer la copia y ficha atribuidas mediante un sobre correlacionado. Skopos
debe verificar hash y bytes, y el consumidor debe ensayar recuperación del
original. Sólo entonces puede describirse como **admisión técnica**. Vigencia
jurídica, cita, corpus y promoción de fase conservan autoridades separadas.
