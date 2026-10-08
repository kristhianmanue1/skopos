# Perfil PDF candidato para la Solicitud B de expertoGobernanza

Estado: **PROPUESTA para revisión bilateral**, 2026-10-08. Versión candidata
`skopos/pdf-profile/v0.2`; no implementada, aceptada, activada ni publicada.
Refina la propuesta PDF v0.1 documentada en la ronda previa; no enmienda
ADR-020. Depende del
contrato base candidato `skopos/source-custody/v0.1` descrito en
`2026-10-08-contrato-base-custodia-fuentes.md`. El perfil añade extracción y
localizadores PDF; no promete soporte de otros formatos ni custodia universal.
Fuentes contrastadas: ADR-020, ADR-021 y `docs/contratos/source-store-v3.md`. No los
sustituye. Pedido consumidor: `expertogobernanza/skopos-source/v0.1`, sección
«Solicitud B a Skopos» de
`/Users/krisnova/www/expertoGobernanza/docs/propuestas/2026-10-05-pedido-contratos-aria.md`.
La solicitud es propuesta del consumidor, no aceptación del productor.

## Resultado del reconocimiento

| Propiedad solicitada | Capacidad observada en Skopos (`fe1e8cbf`, árbol con cambios ajenos) | Brecha y cambio candidato |
|---|---|---|
| Formato | `source_cli.py` acepta `diarized-text`, `whisperx-json` y `dsh-session-v0-jsonl`; `source_envelope.py` despacha TXT/JSON | Perfil PDF y lector explícitos, sin autodetección ni reinterpretar PDF como TXT |
| Original | `SourceStore` guarda `source_path`; verifica hash/longitud al servir, pero no guarda bytes originales | El consumidor ya conserva su copia; evaluar referencia verificada a ella y copia propia opcional con recuperación y responsabilidades separadas |
| Revisión | Clave proyecto/fuente/revisión, predecesor, CAS y recibo para formatos actuales | Reusar semántica de identidad y CAS sólo tras compatibilidad verificada; el mismo PDF con parser nuevo produce derivado nuevo, no revisión de fuente ficticia |
| Localizadores | Segmentos TXT por bytes UTF-8 y JSON por objeto/slice | Página física 1-based, caja en coordenadas declaradas, tipo de región y ancla en derivado; citas verificables contra derivado y página renderizada; ningún offset textual supuesto sobre PDF binario |
| Búsqueda | Subcadena `casefold`, sin ranking semántico ni garantía de latencia; salidas acotadas | Proyección textual opcional y evaluación independiente de relevancia; pérdida de contenido visual se declara |
| Cobertura | Completitud declarada para transcripciones, sin prueba de fuente total | Inventario de 188 páginas y cobertura por modalidad/alcance; `unknown` donde una inspección no demuestre fidelidad |
| Retención | Referencias externas, sin borrado selectivo de respaldos acreditado | Política por modo: consumidor responde por su original en referencia; Skopos por metadatos/derivados y, si se decide, copia propia |
| Acceso | Cliente local y permisos de proceso/Mongo; `project_id` no es ACL | Perfil local con rutas autorizadas, sin servicio compartido; aislamiento y auditoría multiusuario requieren contrato aparte |

Esta tabla compara código y contrato inspeccionados, no el estado vivo de Mongo.
No se invocó la CLI sobre el PDF ni se creó registro en `source_revisions_v3`.
El contrato base separa `capture_coverage` de la cobertura de extracción PDF.

## Instancia inicial y límites de procedencia

El archivo entregado `/Users/krisnova/Downloads/2000-002-001.pdf` se observó con
1,311,822 bytes, 188 páginas y SHA-256
`719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
Ahora existe además la copia del consumidor
`/Users/krisnova/www/expertoGobernanza/docs/fuentes/imss/2000-002-001.pdf`,
con el mismo SHA-256 comprobado en esta revisión. Su registro local
`2000-002-001-PROCEDENCIA.md` atribuye origen inmediato a la copia entregada
por el Operador. La ficha atribuye a expertoGobernanza una descarga HTTPS
directa de la URL del IMSS y cotejo puntual de SHA-256, tamaño y `cmp` con
esa copia el 2026-10-08 (1,311,822 bytes y 188 páginas). En este trabajo
Skopos releyó la ficha y calculó hashes de la copia y de la ficha locales;
no efectuó otra descarga ni reprodujo el cotejo remoto. El registro declara
sin admisión al registry y sin vigencia jurídica verificada. Ambos archivos
del consumidor siguen sin seguimiento Git;
ninguno de esos hechos acredita respaldo, ruta estable o acceso futuro de
Skopos. La obligación de expertoGobernanza de conservar su original no se
traslada a Skopos por usar la interfaz.
`pdfinfo` declaró PDF 1.7, no cifrado, tamaño carta; sus metadatos no prueban
autoría ni fecha oficial. La ficha pública del IMSS identifica la homoclave
2000-002-001 y enlaza un PDF de 188 páginas:
<https://www.imss.gob.mx/node/9884>. Esta propuesta no aporta una comprobación
remota propia de igualdad con los bytes servidos por esa URL; sí documenta la
comprobación puntual atribuida al consumidor. No se adjudica vigencia
jurídica, autenticidad institucional, permanencia futura de la URL ni permiso
de uso a partir de ruta, sello visual, URL o hash. La extracción
sin texto de portada fue reportada en el encargo previo, no repetida aquí;
portada y organigramas son riesgos de cobertura, no páginas vacías.
La observación anterior de búsqueda literal sin coincidencias quedó
supersedida para `docs/` por esta copia y su registro de procedencia. No se
inspeccionó un almacén vivo ni se admite el PDF al corpus por existir allí.

## Contrato candidato: entrada, objetos y respuesta

Entrada propuesta a una operación manual de custodia con perfil PDF (API
todavía no elegida): `contract_id`/`contract_version` bilaterales aceptados,
`request_id`/`request_sha256` de bytes exactos del archivo de solicitud,
`custody_policy_id`/versión, `custody_mode`, `project_id`, `material_id`,
`source_revision` positiva,
`expected_previous_sha256` para revisiones posteriores,
`source_delivery` con referencia autorizada o PDF lateral aportado por
expertoGobernanza, `expected_source_sha256` opcional y `provenance` opcional
atribuida con origen inmediato, URI/ficha y momento de consulta cuando proceda,
`classification`,
`declared_scope`, perfil de sello y `capture_requested_at`. Ninguna URI
autoriza descarga automática. El límite de bytes/páginas y el presupuesto
de proceso deben fijarse y probarse antes de implementación; no heredar el
límite TXT de 16 MiB como promesa PDF. La entrada sólo puede seleccionar OCR,
renderizado o salida a red si el perfil preconfigurado los ofrece; por defecto
del piloto: sin red y sin modelo.
Para este caso el consumidor sí tiene hash de su copia y debe entregarlo
como `expected_source_sha256`; la opcionalidad sólo cubre otros orígenes sin hash
previo y no los equipara a esta verificación.

Entregar el PDF como archivo lateral es opcional: una referencia autorizada a
la copia bajo custodia de expertoGobernanza también entrega los bytes a la
operación. El binario no va en el JSON. La ficha de procedencia puede
acompañarlo como antecedente; Skopos registra quién declaró cada dato y
verifica el hash de la ficha si se suministra. La igualdad de esos bytes sólo
vincula una ficha concreta con el intercambio; el origen, la oficialidad y la
vigencia necesitan comprobaciones propias. Si falta la ficha, la procedencia
queda `unknown`, sin impedir la custodia mecánica. Si faltan PDF y referencia
legible, no hay admisión `ok` por tener metadatos de origen.
`source_delivery` no elige retención: un PDF lateral efímero requiere además
referencia duradera gobernada para `verified_external_reference`; de otro modo
puede motivar una verificación puntual separada, pero la admisión duradera
rechaza `recovery_requirement_unsatisfied`. `managed_copy` se decide aparte.

Identidad del original: `(project_id, material_id, source_revision)` y
`original_sha256`/`byte_length` de **la copia recibida**. Una corrección del
PDF usa revisión nueva y predecesor; una nueva versión del extractor conserva
revisión del PDF y crea `derivation_id`/versión/hash nuevos. La repetición de
identidad+hash devuelve el primer recibo; mismo número con hash distinto
rechaza. El hash no es identidad, nombre de ruta ni autorización de acceso;
no se deduplican objetos entre ámbitos en el primer incremento. En modo
referencia, Skopos verifica la copia del consumidor al recuperar y registra
una referencia gobernada, sin afirmar copia adicional propia. En modo copia,
publicación y recuperación siguen el protocolo recuperable del contrato base;
no se presume atomicidad entre archivo y Mongo.
Un recibo perdido se reconcilia antes de repetir la misma identidad.

Salida compuesta propuesta: campos de custodia del contrato base más los
campos de extracción PDF; no son dos admisiones ni dos identidades de origen.

```text
schema: skopos/pdf-profile/v0.2
contract_id, contract_version, request_id, request_sha256
status: ok | invalid_input | execution_failed | budget_exceeded | unsupported_version
error: null | {code, stage}
material_id, project_id, source_revision, previous_source_sha256
original: {sha256, byte_length, media_type_declared: application/pdf,
           media_type_observed, detection_method, page_count,
           object_ref, captured_at, provenance, provenance_checks,
           seal_policy, seal_check}
derivatives: [{derivation_id, kind, sha256, byte_length, tool_id,
               tool_version, parameters_digest, parent_sha256, coverage_ref}]
capture_coverage: {declared_scope, status, exclusions, basis}
extraction_coverage: {status, pages_examined, pages_with_text,
                      pages_with_visual_regions, pages_with_ocr,
                      exclusions, method}
coverage: {declared_scope, status, exclusions, basis}
custody: {mode, policy_id, policy_version, owner, classification}
receipt: {receipt_id, status, admitted_at, producer_version,
          custody_schema, profile_version}
```

`object_ref` es opaca para consumidores y debe resolver los bytes exactos con
una lectura dentro del alcance acordado. En el perfil local actual se usan los
permisos de la cuenta/proceso y Mongo; `project_id` no autentica ni autoriza a
una persona o agente, y la referencia no concede permiso para abrir rutas
arbitrarias. `object_ref` identifica la fuente bajo política de custodia;
`bytes_ref` de `fetch_original` identifica la salida temporal entregada y
verificada al consumidor, no la ruta de origen. `coverage` del intercambio B
equivale a `capture_coverage`;
`extraction_coverage` es extensión PDF. `capture_coverage.status` usa
`complete_for_declared_scope`, `partial` o `unknown`; sólo se permite la
primera con alcance limitado y controles satisfechos. Una captura completa
no demuestra extracción completa: el perfil registra esta última por página,
modalidad y exclusión. `seal_policy` se fija por perfil aprobado
(`required`/`not_required`), no por respuesta. Si es
`not_required`, `seal_check=not_applicable`; el hash de copia no es sello de
autoridad. Para este PDF no se presupone firma digital por observar un sello
gráfico. Una ruta que exija sello no acepta este perfil sin verificación.

Derivados separados: texto incrustado por página; OCR sólo sobre páginas o
regiones seleccionadas y con motor/versión/parámetros; imágenes/renderizados
de portada y organigramas; estructura de diagrama sólo como hipótesis
derivada con revisión humana. Cada objeto conserva padre, hash, longitud,
herramienta y límites. No se sobreescribe el original ni se llama «original»
al texto normalizado. Texto OCR y texto incrustado pueden discrepar: ambos
se conservan con procedencia; una fusión necesita política explícita.

Un localizador de cita incluye `material_id`, revisión, `original_sha256`,
página física 1-based, `derivation_id` y `derivative_sha256`, región
(`bbox`, origen/unidad/rotación), y, sólo para texto derivado hasheado,
`start_byte`, `end_byte` UTF-8 y `quote_sha256`. Se valida frontera UTF-8,
slice exacto y anclaje declarado con página/región. La igualdad mecánica de
bytes del original o derivado no demuestra que OCR y diagrama correspondan
correctamente al contenido visual; se reportan por separado
`original_bytes_verified`, `derivative_bytes_verified` y
`content_correspondence_reviewed`. La numeración impresa se
registra como etiqueta observada separada, no sustituye página física.
Una relación extraída de organigrama exige nodos, aristas y cajas de origen
revisables; una cita a texto de un nodo no acredita por sí sola su arista.
`fetch_original` devuelve bytes por revisión/hash explícitos y `fetch_quote`
devuelve la cita, derivado y referencia de página con límites de tamaño; no
hay fallback a revisión vigente, resumen ni búsqueda si faltan bytes.

Errores mínimos tipados: `not_found`, `revision_unavailable`,
`bytes_unavailable`, `hash_mismatch`, `seal_missing`, `seal_invalid`,
`unsupported_format`, `invalid_pdf`, `encrypted_pdf`, `limit_exceeded`,
`budget_exceeded`, `derivative_unavailable`, `locator_mismatch`,
`provenance_incomplete`, `retention_policy_missing`, `revision_conflict` y
`predecessor_conflict`. El error no devuelve cita parcial ni cambia cabeza.
Se distinguirán errores de captura de los de búsqueda; `budget_exceeded`
no equivale a cero resultados.
`provenance_incomplete` sólo aplica si una política bilateral exige datos
concretos antes de admitir; no se usa por faltar antecedentes opcionales.

## Custodia, datos y límites de red

Antes de un piloto con admisión se decide propietario de la copia, ubicación
estable, lectores, clasificación, plazo, exportación, retiro y respaldos. El
perfil usa la política del contrato base. En referencia verificada, Skopos
resuelve y comprueba la copia del consumidor en cada lectura; el consumidor
conserva original, ubicación, respaldo y retirada, y Skopos conserva su
registro y derivados según su propia retención. La ruta hoy observada en
`docs/fuentes/imss/` no queda aceptada como estable por figurar en un recibo.
La ficha de procedencia no debe convertirse en prueba automática de
autenticidad: el consumidor puede usarla como antecedente de evaluación
posterior con sus propios criterios y decisión humana.
Si se exige recuperación independiente, una copia gestionada por Skopos añade
respaldo, claves y coordinación de retiro, y requiere enmienda expresa a
ADR-020. El respaldo operativo actual no demuestra cobertura de un almacén
PDF nuevo. Restauración de copia, referencia y metadatos se ensaya según el
modo; sincronizar una carpeta no demuestra recuperación.
Si no hay borrado selectivo de respaldo, se declara no soportado y se rechaza
material cuya política lo requiera. Exportar incluye manifiesto de hashes,
versiones, cobertura y referencias; ningún export acredita autenticidad.

La ficha pública sugiere origen público, pero no sustituye la clase descriptiva
permitida por la política para la copia y sus derivados. La clasificación
jurídica o una excepción de política sí requiere autoridad humana. OCR, notas
y futuros corpus pueden
contener datos sensibles. Piloto propuesto: procesamiento local sin salida de
red, sin LLM, sin envío a IMSS, Ágora o expertoGobernanza. Cualquier OCR
externo, descarga o transferencia exige perfil/red/datos autorizados aparte.
El PDF y su texto son datos no confiables, nunca instrucciones de ejecución.

## Piloto acotado propuesto, todavía no ejecutado

### CONTEXTO DE AUTORIZACIÓN

- Sistema analizado: Skopos `fe1e8cbf6fe521c3e45fb87e76acf38c5f476084`,
  `source_cli.py`, `source_store.py` y perfil PDF candidato; no runtime PDF.
- Autoridad y alcance: encargo del Operador para propuesta documental y
  diagnóstico de lectura en este checkout y el PDF local indicado. No acredita
  propiedad independiente del archivo ni autoriza ingesta o pruebas de control.
- Objetivo: diseñar recuperación de bytes y citas con rechazo explícito ante
  pérdida, alteración o presupuesto insuficiente.
- Entorno: análisis documental local; el laboratorio del piloto aún no está
  configurado ni autorizado para operar con el PDF.
- Acciones permitidas ahora: leer fuentes y crear esta propuesta y su revisión.
  Los fixtures, ensayos de fallo, importación y respaldos son pasos futuros.
- Acciones excluidas ahora: mutar PDF/corpus/runtime, red de proveedores,
  credenciales, terceros, persistencia o evasión de controles.
- Condición de parada: detener operación que exija recursos o permisos fuera
  del alcance o revele riesgo material no contemplado.
- Resultado solicitado: contrato y piloto revisables, con evidencia y límites;
  parches defensivos sólo con autorización posterior.

Primero crear fixtures sintéticos mínimos que reproduzcan cada propiedad sin
copiar el manual a Git. Después, sólo con política de retención y admisión
aprobada, usar la copia bajo custodia del consumidor en laboratorio separado,
sin duplicarla por defecto en Skopos.
Registrar versión del extractor, páginas físicas, hashes de original y
derivados, límites/budget, comando, resultado y exclusiones. No evaluar
relevancia con los mismos casos que ajustaron el extractor.

| Caso | Control positivo y falsación | Criterio mecánico |
|---|---|---|
| Portada (página física 1) | Imagen visible y capa textual ausente; OCR opcional en copia de laboratorio | Página conservada y `text_missing` declarado; OCR, si se permite, derivado marcado y localizable, sin inventar texto nativo |
| Organigrama (página física 18 y/o 19, a confirmar visualmente) | Fixture con dos cajas y una arista, luego arista invertida | Render recuperable; cajas y aristas con región/procedencia; discrepancia detectada; lectura humana decide semántica |
| Texto ordinario | Fragmento con Unicode, acentos y cita conocida | Slice UTF-8 del derivado coincide con cita/hash y página; alteración falla cerrada |
| Corte entre páginas | Frase/encabezado dividido, con dos páginas y dos regiones | Cita compuesta conserva dos localizadores; no fabrica un offset continuo en PDF |
| Revisión cambiada | Mismo `material_id`, revisión 2 con bytes distintos y predecesor correcto; control con predecesor errado | Rev 1 sigue recuperable; cabeza rev 2 sólo tras CAS; revisión/hash ambiguos rechazan |
| Original perdido | Quitar copia únicamente en fixture aislado y repetir con copia válida | `bytes_unavailable`; no servir sólo derivado como cita verificada del original |
| Presupuesto agotado | Límite suficiente y otro insuficiente sobre mismo fixture | Resultado completo frente a `budget_exceeded` con progreso/exclusiones; nunca éxito vacío o admisión parcial |
| Contrato y custodia discordantes | Recibo válido con contrato/perfil/política fijados; luego cambiar cada campo o cruzar proyectos | Recuperación rechaza identidad o política incompatible; hash idéntico no concede acceso ni mezcla retención |
| Corte entre objeto y Mongo | Completar admisión y cortar antes/después de publicación en fixture aislado | Resultado reconciliable; sin cabeza que apunte a bytes inexistentes ni duplicado oculto |
| Formato sin perfil | Custodiar fixture binario admitido por el contrato base | Bytes recuperables; extracción, búsqueda y cita `unsupported_format` |
| Referencia del consumidor retirada o alterada | Copia estable legible como control positivo; luego mover o mutar sólo fixture aislado | `execution_failed/bytes_unavailable` o `execution_failed/hash_mismatch` en `retrieval`, sin fallback ni afirmación de respaldo Skopos |

Conformidad mecánica requiere controles positivos/negativos, igualdad de
bytes recuperados, detección de corrupción, revisión concurrente, resultado
incierto reconciliado, export/restauración y retiro según política acordada.
Relevancia de búsqueda se mide aparte con preguntas y objetivos fijados por
el consumidor, recall/errores/exclusiones y costo; una coincidencia literal
no demuestra utilidad. Validez jurídica, vigencia, oficialidad y admisión al
gate son decisiones del consumidor/profesional con fuentes y criterios propios.

## Decisiones para revisión bilateral

**Recomendación documental para este primer caso:** evaluar
`verified_external_reference` porque expertoGobernanza ya conserva una copia
local cotejada y no se ha demostrado que necesite recuperación independiente
tras perderla. La recomendación supone una ruta gobernada, acceso estable para
Skopos, respaldo y restauración a cargo del consumidor, y aceptación expresa
de que `fetch_original` fallará si esa copia desaparece. Si el requisito es
recuperar aun después de perder la copia del consumidor, corresponde estudiar
`managed_copy` con almacén, respaldo, retiro y enmienda de ADR-020 propios.
La igualdad de hashes no prueba independencia de respaldos.

**Preconfiguración bilateral pendiente:** versión exacta del contrato y perfil,
clases descriptivas permitidas, raíz/acceso/duración de solicitud, PDF lateral,
referencia persistente y salida; propietario y retención por modo; política de
sello; límites de bytes/páginas; responsable de relocalización y prueba de
recuperación. Una vez instalada, los agentes seleccionan y verifican esas
reglas sin consulta rutinaria al Operador. Si falta una regla requerida,
rechazan con razón tipada; no crean permisos ni retención por inferencia.
La ficha del consumidor permite atribuir un cotejo puntual con la URL IMSS,
pero no decide vigencia jurídica ni aceptación de citas.
Para operación real se requieren implementación, controles positivo/negativo
de la matriz del contrato base, pruebas de corte y restauración, evaluación de
cobertura PDF, rechazo del consumidor ante fallos y aceptación humana
separada. Publicar este borrador no satisface esa puerta.

**Skopos/productor:** anuncia únicamente el perfil PDF y políticas realmente
habilitados para ese consumidor. En cada solicitud comprueba raíz, permiso
efectivo, bytes, ficha, sello y retención; prefiere
`verified_external_reference` sólo cuando todos sus requisitos se cumplen.
Si falla uno, rechaza con causa tipada; no selecciona `managed_copy` ni una
ruta nueva por sí mismo. El host o responsable de plataforma configura antes
las raíces, duración, límites, derivadores, sello, retención, recuperación y
reglas de relocalización. Sólo una copia propia requiere enmendar la elección
de custodia de ADR-020; un perfil PDF y sobre nuevo requieren decisión
contractual propia. `provided_file` no altera estas obligaciones.

**expertoGobernanza/consumidor:** conserva su original y declara identidad,
hash, alcance, procedencia atribuida y requisito de recuperación dentro de la
oferta vigente. Su host configura ubicación accesible para Skopos, respaldo,
retención, retirada y restauración. El agente consumidor verifica recibo y
bytes recuperados, conserva `disposicion_id` y aplica su propio gate. Puede
registrar clasificación descriptiva permitida, sin resolver vigencia jurídica
ni aceptar citas por el solo recibo. La necesidad excepcional de una copia
gestionada por Skopos se eleva como cambio de política/ADR, no como elección
automática durante el intercambio.
La integración es optativa: puede aportar directamente su copia a Ágora o a
su propio gate si su custodia y verificación lo permiten. Skopos no escribe
registry, EvidenceEdge ni AN-KLA; ninguna conformidad mecánica los modifica.

**Puerta de avance:** contrato bilateral y fixtures aprobados primero;
implementación, piloto con el PDF, aceptación del consumidor, activación y
publicación son actos posteriores separados. Las revisiones adversariales
documentales están en `docs/rondas/2026-10-08-perfil-pdf-solicitud-b.md`,
`docs/rondas/2026-10-08-custodia-base-perfil-pdf-ronda-final.md`, el ajuste
`docs/rondas/2026-10-08-custodia-consumidor-solicitud-b.md` y su enmienda
posterior `docs/rondas/2026-10-08-entrega-opcional-procedencia-solicitud-b.md`.
