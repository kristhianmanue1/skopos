# H25.2 — contrato candidato de captura DSH session v0

Estado: PROPUESTO para implementar y probar; no aceptación productiva.
Fecha: 2026-10-05, America/Mexico_City. INFORMS: ADR-020, ADR-021,
SPEC-007 y propuesta h25-runtime-events-v0. No cambia contratos vigentes.

## Objetivo y exclusiones

Conservar eventos de una ejecución como evidencia, sin certificar sus
veredictos. COMMITTED/PASS/isError/model son declaraciones del productor;
Skopos no las transforma en éxito verificado, autorización o identidad efectiva.
Sin ejecutar tools, LLM, watcher, red, escritura AN-KLA ni reparación DSH.
No depende de resolver el aislamiento de Microsoft AGT ni de activar AMeC.

## Perfil seleccionado para el prototipo

Formato explícito dsh-session-v0-jsonl, no detección automática de JSON genérico.
Entrada inicial: bytes JSONL UTF-8 de session.jsonl, no ZIP en SourceStore.
El ZIP original se conserva como contenedor con hash propio. La extracción
posterior será operación explícita acotada a una única entrada session.jsonl,
sin extracción de paths; exige límites antes y durante descompresión.
No se habilita todavía importación del ZIP ni del JSONL en el CLI productivo.

Fuente primaria de semántica: checkout local DeepSeek Harness HEAD
38e3827543d32b59e75a22ed2eb6937872a53439,
packages/session/session-format-v0-to-v1/src/codec.ts, funciones
decodePackedRun, expandAssistantChunkRun y decodeSeqRanges. Se registrará hash
del archivo inspeccionado: HEAD por sí solo no acredita bytes sin cambios.
Es evidencia del lector del productor, no prueba de versión del exportador.

Reconocimiento ejecutado sin ingesta: ZIP SHA-256
38b386616677c31b2f1d9c58da203968dfca6625ab161ed2b07c55fe706c42b3;
entrada SHA-256
6fe02ace6d9e31233e18b920796a539c362637733f7efb2881595c90994dfcb2.
Codec inspeccionado SHA-256
bdfd0239e33abeccece7a3751c7d2cdb4ea4607b4c63c3787c1dc4c3aedb3a7f.
126 slices reconstruidos exactamente;1375 secuencias sin huecos/colisiones;
15 filas de referencias expanden1330 referencias, todas resueltas dentro
del export;8 llamadas/8 resultados con multiconjunto callId coincidente.
Esto no demuestra completitud del runtime ni éxito semántico de las llamadas.
Sonda y resultado locales, ignorados por Git:
runs/ankla-mediator-validation/evidence-20261005/recognize-dsh.py y
dsh-recognition.json. Sin payload privado en este documento.

## Identidad y localizadores

- Un header type=session/version=0; id nativo conservado como declaración.
- source_id/project_id/revisión/predecesor explícitos, reglas ADR-020.
- Una fila física: id ordinal row-N, localizador byte [start,end) que incluye
  terminador original LF/CRLF cuando existe; hash de ese slice. Nunca normalizar.
- Header no contado como evento; sí conservado y localizable.
- Evento simple: seq entero no negativo y time entero seguro JSON.
- Lote: seq0 y time0, payload no vacío (texts o args), dt de longitud N-1.
  Miembro i tiene seq0+i y tiempo time0+sum(dt[:i]); conservar signos de dt,
  no exigir reloj monótono ni deducir causalidad.
- Evento lógico derivado referencia fila y member_index; NO inventar offsets
  propios de un evento expandido que nunca existió como línea original.
- sourceEventSeqs: enteros o [inicio,fin] inclusivos. Preservar forma original
  además del diagnóstico; jamás expandir un intervalo sin límite previo.
- Colisión de seq entre filas o lotes: rechazo, no deduplicación silenciosa.
  Huecos/referencias externas: diagnóstico, no prueba de pérdida en el runtime.

La muestra tiene126 filas:1 header+92 simples+33 lotes;1375 eventos lógicos.
Tres user/message NO son tres mensajes humanos: conservar source.kind/role
sin reinterpretarlos; la muestra contiene usuario, instrucciones y plugin.

## Representaciones y privacidad

Propuesta de sobre NUEVO source-envelope/v2, source_kind=runtime-events;
no sobrecargar segmentos de reunión ni ampliar silenciosamente v1 de ADR-021.
Almacén v3 necesitaría unión explícita v0/v1/v2 y pruebas de lectores viejos.
Antes de integrar: actualizar SPEC-007, contrato, validadores y CLI juntos.

Dos vistas: original sellado por fila y eventos derivados tipados. Search
general sólo mensajes finales de texto admitidos; no concatenar chunks con
mensajes finales. Sin texto final, no fabricar una respuesta desde deltas.
Reasoning, request/header, contexto, argumentos y resultados completos:
opacos/no indexados ni servidos en búsqueda general por defecto. La evidencia
original puede contenerlos: fetch bruto requiere selección explícita y acceso
local autorizado; no equivale a redacción ni ACL multiusuario implementada.
No promover una etiqueta de host o una instrucción recuperada a autorización.

Fetch deberá separar original_jsonl y derived_event; verificar fuente completa,
slice y representación derivada antes de servir. Dato/no instrucción explícito.
Todo resultado <=64KiB; exclusiones contadas, no truncado silencioso.
No conservar contenido privado en Git, informes ni fixtures.

## Límites candidatos y errores

16MiB de archivo,10000 filas,100000 eventos lógicos,100000 referencias por
archivo, profundidad64, enteros seguros JSON para seq/time y acumulaciones.
UTF-8 estricto, sin BOM, claves duplicadas, NaN/Infinity ni sustitutos aislados.
Línea JSON completa sin newline final aceptada; JSON truncado rechazado.
Líneas vacías rechazadas en este perfil. Tipos desconocidos con estructura
simple válida se conservan opacos; no expandir lotes desconocidos.
Validación completa antes de admisión: no guardar la mitad de una fuente.
Errores propuestos: invalid_runtime_header, invalid_runtime_row,
invalid_runtime_batch, duplicate_runtime_seq, runtime_limit_exceeded.

## Matriz de aceptación pendiente

1. UTF-8, escapes, CRLF/sin LF final: reconstrucción exacta de cada fila.
2. Batch de un miembro; dt negativo; overflow y dt de longitud incorrecta.
3. Referencias simples/rangos, intervalos enormes, huecos y colisiones.
4. Un texto repetido con seq distinto conserva dos eventos, no dos sources.
5. Texto hostil permanece inerte; COMMITTED+error no se convierte en éxito.
6. Mensajes finales+chunks no duplican búsqueda; reasoning no se sirve default.
7. Replay, revisión, CAS, recibo perdido y fetch de fuente alterada/ausente.
8. Regresión TXT/v0 y WhisperX/v1; consumidor antiguo rechaza v2 claramente.
9. Piloto local autorizado, con lectores/retención explícitos antes de ingesta.

## Secuencia y cierre

Reconocimiento verificable → constructor puro con fixtures sintéticos →
revisión del contrato candidato → integración en copia → regresión completa →
piloto y adjudicación. No cambiar índices ADR-019 ni introducir embeddings.
Los logs del adaptador AN-KLA son evidencia complementaria de estados, no el
mismo formato que session v0: requieren un perfil propio antes de admitirlos.
Autorrevisión del diseño de la misma instancia; no revisión independiente.

## Incremento experimental del lector — 2026-10-05

Implementación acotada en `experiments/runtime-source-v1/reader.py`, función
`parse(bytes)`, pruebas sintéticas en `tests/test_runtime_source.py`. No abre
archivos ni requiere servicios. Devuelve `skopos/experimental-dsh-reader/v0`,
NO source-envelope/v2: identidad por proyecto, revisiones, admisión, fetch y
selección de texto para búsqueda siguen pendientes de la siguiente frontera.
La salida interna contiene valores originales potencialmente privados; no es
una API de consulta limitada a 64KiB ni debe mostrarse como resultado general.

Semántica acotada: expande los tres lotes conocidos con claves cerradas según
el codec citado; los eventos simples sólo validan type/seq/time y referencias.
No valida el esquema completo de cada payload DSH ni certifica conformidad
universal. Referencias futuras o externas son diagnóstico, no causalidad;
los rangos deben ser crecientes, pero listas simples conservan repeticiones.
Su presupuesto es global, no el límite por seq del codec: diferencia deliberada
de este perfil de preservación, no equivalencia con el validador del productor.
Header sin eventos se conserva como captura de completitud desconocida.
`sequence_gap_count` cuenta ausencias desde cero hasta el mayor seq observado,
sin materializar ese intervalo; no significa eventos perdidos demostrados.

Autorrevisión adversarial: reforzadas las pruebas contra resultados esperados
explícitos del formato de expansión (no sólo conteos), límites inclusivos,
underflow de tiempo, fila vacía después de header válido y profundidad exacta.
No se ejecuta contenido ni se promueven COMMITTED/isError a un veredicto propio.
No se modificó DSH, SourceStore, CLI, Mongo productivo, corpus ni AN-KLA.

Sonda del lector sobre el export real ya identificado: hash de entrada idéntico
al reconocimiento anterior,126 filas/1375 eventos/1330 referencias, cero huecos
y referencias no resueltas. Los126 hashes de slice y valores JSON coinciden con
el original. Lectura acotada del ZIP en memoria, sin extracción a disco, ingesta,
ejecución de tools ni publicación de contenido privado. No equivale a piloto
de persistencia o prueba de completitud del export.

Verificación final:19 pruebas específicas OK; suite completa396 pruebas OK,
sin omisiones,69.399 s en Mongo temporal exclusivo37027 y fixture Ollama local.
Log local: `/private/tmp/skopos-runtime.hmdFUy/final.log`. Gates266 archivos
y un plan válidos; diff revisado. Código sin cambios posteriores a esa suite.
Autorrevisión, no revisión independiente. Procede publicar el experimento,
no activar producción ni dar por aceptado el sobre runtime pendiente.

## Diseño del sobre y consulta — propuesta 2026-10-05

Alcance de este incremento: definición documental, no implementación ni
aceptación de contrato productivo. Base Skopos: 34a91ff. El Operador autorizó
continuar con esta definición; la integración en copia es el paso posterior.
Las reglas siguientes precisan la propuesta anterior, no modifican ADR-020/021.

### Sobre candidato cerrado

Nombre reservado: `skopos/source-envelope/v2`, source_kind=`runtime-events`.
El constructor recibirá bytes JSONL y metadatos explícitos; no un resultado
mutable del lector experimental ni un sobre suministrado por el consumidor.
No se almacenará la salida completa del lector: duplicaría payload privado
en rows/events y aumentaría innecesariamente el documento BSON.

Campos obligatorios propuestos:

| Campo | Regla |
|---|---|
| schema, source_kind | Constantes v2/runtime-events |
| project_id, source_id, source_revision, previous_source_sha256 | Gramática, rango y predecesor de ADR-020; no derivarlos de cwd/id del export |
| source_sha256, source_bytes | Bytes originales, no JSON normalizado |
| captured_at, captured_at_basis | Fecha UTC explícita; caller_declared |
| occurred_at | null; no convertir automáticamente el reloj del runtime en fecha acreditada |
| capture_completeness | value/basis de ADR-020; declaración, nunca inferida de seq contiguos |
| adapter | id versionado del constructor y format=dsh-session-v0-jsonl |
| projection_policy | skopos/runtime-text-policy/v0; cambio exige nueva revisión explícita |
| rows | id row-N, start_byte, end_byte y sha256; sin value ni payload duplicado |
| events | id event-SEQ, seq, time, type, row_id, member_index nullable; sin data |
| texts | Proyecciones de bloques admitidos según la tabla inferior |
| diagnostics | Conteos de huecos, referencias, exclusiones y motivos; sin payload |
| producer_claims | not_verified; no campo de éxito adjudicado |
| envelope_sha256 | Digest JSON canónico de todos los campos salvo éste, como v0/v1 |

No usar segments, audio_alignment ni speaker_identity para eventos. Claves
desconocidas en el sobre son error. source_id conserva identidad entre revisiones;
event-SEQ y row-N sólo son identidades dentro de esa revisión. La metadata nativa
del header permanece recuperable por su fila sellada, no se copia como autoridad.
Los enteros derivados seq/time conservan el rango seguro JSON. Ningún número
opaco debe entrar a BSON sólo porque el lector JSON pudo representarlo.

Cada elemento texts contiene exclusivamente id=`event-SEQ-block-I`, event_id,
row_id, block_index, pointer, role, source_kind, text y derived_text_sha256.
pointer identifica el bloque en el JSON de la fila, no bytes del texto decodificado.
No inventar offsets de texto para escapes Unicode. Hash del texto: UTF-8 exacto,
sin trim, normalización Unicode, concatenación ni redacción implícita.
block_index es el índice original, no el ordinal después de exclusiones.
pointer es /data/content/I en user/message y /data/message/content/I en
assistant/message. source_kind del texto es user o model, a diferencia del
source_kind=runtime-events del sobre. role y origen se conservan como declaraciones.
Máximo 100000 bloques examinados por archivo (incluidos los excluidos), antes
de derivar; exceso rechaza todo con runtime_limit_exceeded. Este límite se añade
a los del lector, no los sustituye. No truncar listas para obtener un sobre válido.

### Política de proyección por lista permitida

Fuente de forma: `payload-validation.ts`, funciones messageValue,
messageSourceValue y contentBlockValue del mismo checkout DSH citado arriba.
Son evidencia del productor, no implementación reutilizada ni certificado DSH.
SHA-256 del archivo inspeccionado:
32a46e4ca5d17972360c423c63002054df022750ade0e11ece2232b21eb0da62.

| Entrada | Proyección consultable propuesta |
|---|---|
| user/message | Sólo data.role=user y data.source.kind=user, bloques text en data.content |
| assistant/message | Sólo data.message.role=assistant y source.kind=model, sin interrupted presente; bloques text en data.message.content |
| reasoning o reasoning-delta | Ninguna; ni texto ni preview en búsqueda |
| assistant/chunk y los tres lotes | Ninguna; no reconstruir respuesta desde deltas |
| tool/call, tool/result, tool-call/tool-result anidados | Ninguna; no descender a su contenido |
| plugin, agent-instructions, goal, skill, relay, snapshot, request y tipos desconocidos | Ninguna aunque traigan role=user o texto |

La selección valida la estructura exacta de message: id no vacío, role,
content lista y source objeto. Para user: source exige kind y permite únicamente
rpcId/clientTimeZone strings no vacíos. Para model: kind/provider/model strings
no vacíos y replayState opcional opaco, nunca proyectado. Bloque text exige sólo
type y text string; texto vacío/blanco se excluye con motivo empty_text.
No convertir números, listas ni objetos a string. Bloques no text se excluyen
individualmente y se cuentan; jamás recorrerlos buscando una clave text.
Mensaje elegible con forma inválida se conserva como evidencia opaca pero no
produce texts: motivo invalid_message_projection. No rechazar todo el archivo
por esta exclusión semántica si el lector estructural ya lo admitió.
Un bloque que declara type=text pero tiene forma inválida invalida la proyección
del mensaje completo; no publicar parcialmente ese mensaje. Los contadores
separan eventos excluidos (event_type, source_kind, interrupted,
invalid_message_projection) de bloques excluidos (non_text, empty_text).
Precedencia por evento: tipo → interrupción → forma del mensaje → origen;
una exclusión de evento no cuenta además sus bloques como exclusiones de bloque.

assistant/message significa mensaje materializado, NO necesariamente última
respuesta del turno, éxito o finalización de tarea. interrupted se excluye
conservadoramente incluso si trae false o valor inválido; no se imputa completitud.
Dos bloques o eventos iguales mantienen sus identidades; no deduplicar por texto.
Cada bloque admitido es un resultado separado; así no se inventan separadores ni
coincidencias entre bloques. Las etiquetas de origen son declaraciones, no prueba
de persona humana ni identidad efectiva del modelo. Un secreto copiado dentro
de un bloque text podría seguir saliendo: esta selección NO equivale a redacción.

### Frontera de recuperación y compatibilidad

Proponer operaciones explícitas search_runtime y fetch_runtime antes de alterar
la salida de search/fetch actuales. Las consultas antiguas de transcripciones no
deben intentar servir v2 como segmento. Antes de admitirlo se define su exclusión
contada por tipo y se prueba que v0/v1 siguen funcionando en colecciones mixtas.
Hoy el lector viejo rechaza v2 como store_integrity_failed; no es compatible.
No basta con añadir v2 al conjunto de schemas aceptados del validador.

search_runtime fija cabezas por proyecto antes del filtro, respeta orden por
source_id/seq/block_index y subcadena casefold, sin ranking ni embeddings.
Sólo devuelve proyecciones admitidas e identidad/revisión/sellos/localizadores;
nunca original_jsonl, data, source completo, reasoning, argumentos ni resultados.
Máximo 20 resultados y 64 KiB de JSON UTF-8 completo por resultado; excluir enteros
y contar result_limit/fragment_too_large, además de fuentes no verificables.
Los contadores de política cuentan elementos examinados, no supuestos matches
en datos ocultos. No ofrecer consultas para inferir términos en payload excluido.

fetch_runtime exige proyecto/fuente/revisión/hash y view explícita:
text_projection con text_id; original_jsonl con row_id; derived_event con event_id.
No hay vista por defecto ni selector ambiguo; campos ajenos a la vista se rechazan.
Las dos últimas son acceso bruto potencialmente sensible, no búsqueda general;
requieren selección expresa del Operador/consumidor local autorizado. La CLI
no sustituye permisos del sistema ni implementa ACL multiusuario.
64 KiB máximo incluyendo metadatos también en fetch; exceso falla sin truncado.

Antes de servir cualquier vista: verificar registro/sobre, lectura única y
hash/tamaño de fuente; reparsear con adaptador fijado; cotejar descriptor de fila,
slice y derivación seleccionada. En text_projection reejecutar la política fijada
y cotejar texto/hash/pointer; un hash autoconsistente no demuestra derivación.
Errores no devuelven texto. Todos los resultados declaran dato/no instrucción
y bytes verificados, nunca runtime exitoso o fuente auténtica.

Persistencia propuesta: conservar source-record/v3 y transacción/CAS/receipt,
ampliando su unión de sobres sólo tras implementar lectores nuevos. Límite BSON
16 MiB sobre registro completo, sin truncar texts para hacerlo caber. Replay no
cambia política, parser, ruta ni metadatos; nueva política exige revisión nueva.
Custodia externa conserva riesgo de pérdida; ZIP no se importa automáticamente.
No se introduce almacenamiento bruto adicional ni borrado/retención automática.

### Autorrevisión adversarial y aceptación de la siguiente etapa

Hallazgos de diseño y correcciones:

1. Reusar _fragment de ASR expondría original_json en búsquedas. Corrección:
   salida runtime separada, lista cerrada de campos y pruebas de ausencia.
2. role=user también aparece en mensajes de herramientas e instrucciones.
   Corrección: filtrar por tipo de evento, ruta y source.kind conjuntamente.
3. Un mensaje assistant puede estar interrumpido o incluir reasoning/tool-call.
   Corrección: no equiparar mensaje con cierre; excluir interrupted y bloques
   no text, sin recorrido recursivo.
4. Guardar rows.value y events.value duplicaría contenido privado. Corrección:
   persistir descriptores y proyecciones mínimas; rederivar desde original sellado.
5. Cambiar únicamente schema rompería consumidores segments. Corrección:
   pruebas de colección mixta y lectores antes de primera admisión v2.

Riesgos residuales: texto admitido puede contener secretos/órdenes, etiquetas
pueden ser falsas, archivo externo puede perderse; no ACL ni garantía de escala.
Autorrevisión de la misma instancia; no revisión independiente ni adjudicación.

Siguiente incremento recomendado: constructor y proyector puros experimentales,
sin SourceStore. Casos exigidos: roles/orígenes cruzados con controles positivos;
reasoning/tool-result anidado con señuelo text; interrupted ausente/true/false;
chunks+mensaje sin doble indexación; Unicode/escapes; iguales en seq distintos;
origen desconocido/inválido excluido y contado; hashes de proyección y fuente;
límites, determinismo y rechazo de metadatos. Después, propuesta de extensión
contractual para integración en copia con replay/CAS/fetch y regresión v0/v1.
No constituye autorización automática de activación o ingesta productiva.

Verificación documental: diff leído y gates verdes (266 archivos/un plan).
Sonda sin Mongo: sobre v0 válido aceptado; sólo cambiando schema a v2 y
recalculando su digest, rechazo store_integrity_failed, como predice el código.
Regresión previa a publicar esta propuesta:396 pruebas OK sin omisiones,
93.174 s, Mongo temporal exclusivo37027 y fixture Ollama local. Log:
`/private/tmp/skopos-runtime.hmdFUy/design-tests.log`. No hubo cambios de código;
esta suite NO valida comportamiento del sobre/proyector aún no implementados.

## Constructor y proyector experimentales — 2026-10-05

Continuación autorizada por el Operador: implementación pura en
`experiments/runtime-source-v1/envelope.py`, `build_envelope(bytes, **metadata)`.
El módulo se importa con su directorio en sys.path para resolver reader;
las pruebas usan importlib y restauran el registro temporal de módulos.
Reutiliza validación de identificadores/fecha de source_envelope sin modificar
el módulo productivo. No requiere dependencias nuevas, filesystem, red o Mongo.

Produce el sobre candidato v2 con descriptores de filas/eventos y textos
seleccionados; no copia rows.value, events.data, header, replayState ni contenido
excluido. No es un validador de sobres externos: sólo construye desde bytes;
validación de entradas persistidas y rederivación en fetch siguen pendientes.
El sello no prueba autoridad y la marca model no verifica identidad del modelo.
La salida puede contener secretos dentro del texto admitido: no hay redacción.

Precisión del presupuesto: cuenta las entradas de listas content de los dos
tipos de mensaje, incluidos mensajes después excluidos, antes de proyectar.
No desciende a bloques anidados ni inspecciona payloads de otros tipos para
buscar text. Sus bytes siguen acotados por el lector. blocks_examined identifica
este presupuesto, no un conteo de contenido privado indexado.
La forma externa del mensaje se valida antes del origen; la validación de
bloques text sólo se aplica tras admitir el origen. Mensaje inválido no produce
textos ni exclusiones de bloque parciales. Campos extra en bloque text invalidan
el mensaje; bloques opacos con type no vacío sólo cuentan como non_text.

Autorrevisión adversarial de la misma instancia: corregido presupuesto para
incluir mensajes excluidos; probado invalidado completo si el último bloque
text es inválido; probados señuelos text dentro de reasoning/tool-result,
interrupted false/null, roles cruzados, proyecciones repetidas con seq distintos,
predecesor/fecha/identificadores inválidos y sustituto Unicode en completeness_basis.
Pruebas específicas:15 del constructor más19 del lector,34 OK con fixtures
sintéticos. Un test confirma que el SourceStore actual rechaza el v2 construido;
no se amplió su unión de sobres ni se conectó este experimento a la CLI.

Pendiente fuera de este incremento: diseño aceptado de integración, validador
del sobre persistido, search_runtime/fetch_runtime, límites BSON/salida,
colecciones mixtas y piloto de persistencia en copia. H25 permanece abierto.

Sonda adicional del constructor sobre el export identificado (mismo SHA de
entrada):126 filas/1375 eventos y2 textos proyectados, ambos cotejados por
pointer y hash contra el original. Exclusiones:1365 eventos por tipo,2 por
origen y11 bloques no textuales;15 bloques en el presupuesto, cero mensajes
inválidos o interrumpidos. Los contadores no califican relevancia ni éxito.
Construcción en memoria con identidad de reconocimiento, sin ingesta y sin
mostrar/copiar texto privado a evidencia versionada. No equivale a piloto Mongo.

Regresión final:411 pruebas OK sin omisiones en69.627 s contra Mongo temporal
exclusivo37027 y fixture Ollama local; gates268 archivos/un plan verdes.
Log: `/private/tmp/skopos-runtime.hmdFUy/envelope-tests.log`. Diff revisado,
sin cambios de código posteriores a la suite. Procede publicar el experimento,
no admitir v2 en SourceStore ni activar producción. AN-KLA no se escribió.

## Extensión contractual para laboratorio — 2026-10-05

Estado: PROPUESTA DOCUMENTAL, no ADR aceptado ni implementación del almacén.
Base de código inspeccionada: 76842e3. INFORMS: SPEC-007 y source-store-v3.
La continuación autoriza redactar esta extensión; no convierte la propuesta
en aceptación productiva. La autoridad operativa sigue siendo del Operador.

### Admisión y persistencia propuestas

Extender import_file con source_format='dsh-session-v0-jsonl', manteniendo
default diarized-text y whisperx-json. Una lectura regular explícita con límites
actuales; no autodetección, ZIP, watcher, LLM, memoria ni descubrimiento de rutas.
El constructor runtime recibe los bytes de esa lectura y metadatos explícitos.
El importador nunca acepta un sobre v2 construido por un tercero como atajo.

source-record/v3 mantiene campos e identidad; envelope admite v0/v1/v2
mediante dispatch explícito. Conserva transacción snapshot/majority, CAS,
revisiones consecutivas, índices, límite BSON de 16 MiB y errores existentes.
No dividir ni truncar una fuente para que quepa; no prometer que 16 MiB de entrada
caben junto con descriptores/textos. Fallo de validación precede a _prepare.

Regla nueva propuesta: source_kind no puede cambiar dentro de una identidad
project_id/source_id. Runtime y reunión usan source_id distintos; v0↔v1
siguen siendo meeting-transcript. Comparar dentro de la misma transacción,
con error source_kind_conflict. No migrar ni renombrar identidades existentes.
El replay de misma clave/hash conserva primer sobre/ruta/política/recibo;
si cambia el formato explícito de esa llamada a otra familia, rechazar, no
confirmar silenciosamente la representación equivocada. No cambiar de versión
para resolver respuesta incierta: consultar receipt de la misma identidad.

### Validación en dos niveles

Nivel S, sin abrir el original: identidad de registro, schema reconocido,
claves cerradas y tipos exactos (bool no entero), metadatos válidos, límites,
adapter/projection_policy soportados, sello canónico y consistencia interna.
Para v2 comprobar filas ordenadas, contiguas desde 0 hasta source_bytes,
IDs ordinales únicos, hashes sintácticos; eventos únicos por seq, row_id existente,
member_index entero no negativo sólo para miembro de lote, id=event-SEQ;
texts con event_id/row_id coincidentes, block_index no negativo, id y pointer
con forma exacta, role/source_kind permitido, texto no blanco y sello de texto.
Diagnósticos usan claves conocidas y contadores enteros no negativos acotados;
sequence_gap_count conserva rango seguro JSON, no el límite de cantidad de eventos.
Rechazar campos ocultos añadidos, segmentos mezclados y versiones desconocidas.
El nivel S comprueba coherencia declarada; no demuestra fidelidad al archivo.
La familia debe corresponder al schema: v0/v1=meeting-transcript,
v2=runtime-events. Sobre conocido mal formado produce store_integrity_failed;
sello discordante produce envelope_integrity_failed; schema o política no
soportados conservan sus errores específicos. No clasificar corrupción como
simple exclusión de familia ni servir una vista parcial para tolerarla.
La cabeza sólo se coteja al seleccionar vigentes o publicar una revisión nueva;
fetch histórico y receipt no exigen coincidir con la cabeza actual. Para verificar
familia al publicar, cargar y validar el registro apuntado por la cabeza dentro
de la transacción. No añadir source_kind a la cabeza como fuente de verdad paralela.
Un member_index presente exige type=assistant/chunk y, por fila, índices 0..N-1
y seq consecutivos; la procedencia real de lote se acredita únicamente en D.

Nivel D, para cualquier lectura que entregue contenido: después de S, leer una
sola instantánea del original, cotejar longitud/hash, reconstruir el sobre con
adapter y política fijados y los mismos metadatos declarados. Comparar la forma
canónica completa reconstruida con la persistida, incluidos textos, localizadores
y diagnósticos. No basta comparar hashes recalculados sobre datos manipulados.
No actualizar sobre/política durante lectura; versión no disponible falla explícito.
Esto verifica derivación, no autoría: alguien con control de base y archivo puede
reescribir ambos. No se implementa autenticación por hash ni firma de procedencia.

Receipt sólo aplica S: no requiere original y no afirma disponibilidad, derivación
actual ni éxito del runtime. Replay también valida el registro previo antes de
retornar duplicate. La identidad cruzada/sello inválido impiden recibo afirmativo.
La admisión nueva aplica S y D sobre el buffer ya leído antes de persistir.
import_file, incluido su replay, mantiene lectura previa del archivo como hoy;
únicamente receipt permite reconciliar sin él. No prometer replay offline.

### APIs y salidas candidatas cerradas

`search_runtime(*, project_id, term, limit=20)`:
term no blanco y máximo 1024 bytes UTF-8; limit entero 0..20. No acepta view ni
selector de payload bruto. Captura cabeza por fuente antes del filtro, valida S,
selecciona runtime, valida D completo antes de acumular resultados de esa fuente.
Sin fuente parcialmente servida cuando el último elemento falla validación.
Orden por source_id, seq numérico y block_index; coincidencia subcadena casefold.
No lee revisiones antiguas para llenar cupos. limit=0 cuenta sin servir textos.

Resultado raíz: results, excluded {result_limit, fragment_too_large},
unavailable_sources {código: cantidad}, excluded_source_kinds {meeting-transcript:
cantidad}, declaration y selection=per_source_head_observed. Los conteos por
tipo se calculan después de validar S, no confiando sólo en source_kind.
No devolver textos, snippets ni coincidencias de eventos excluidos por política.
No añadir contadores de política por término: podrían sugerir contenido oculto.
No prometer coste de escaneo ni latencia acotados por limit.

Cada resultado de búsqueda: project_id, source_id, source_revision,
source_sha256, envelope_sha256, view=text_projection, projection (un elemento
texts completo), locator (descriptor de fila sin payload),
status=runtime_projection_verified, producer_claims=not_verified y declaration.
JSON UTF-8 compacto completo ≤64 KiB, incluidos todos esos campos; exceso excluye
la coincidencia entera. No copiar metadata nativa adicional por conveniencia.

`fetch_runtime(*, project_id, source_id, source_revision, source_sha256,
view, text_id=None, row_id=None, event_id=None)`:
identidad/revisión/hash siempre explícitos. view exige exactamente un selector:

| view | Selector | Payload y status |
|---|---|---|
| text_projection | text_id | projection, locator; runtime_projection_verified |
| original_jsonl | row_id | original_jsonl UTF-8 exacto con terminador, locator; runtime_bytes_verified |
| derived_event | event_id | event reconstruido, locator de fila y member_index nullable; runtime_event_verified |

Todas las vistas añaden los cinco campos de identidad/sellos de search,
view, producer_claims=not_verified y declaration. No payload de otra vista.
original_jsonl puede seleccionar header; derived_event no transforma header
en evento. Selección de evidencia bruta es explícita, no permiso ampliado ni ACL.
Todas aplican S+D y límite de 64 KiB; exceso falla fragment_too_large sin truncado.
Campos seleccionados inexistentes: runtime_item_not_found; no búsqueda aproximada.

Errores nuevos candidatos: source_kind_conflict, unsupported_envelope_version,
unsupported_runtime_policy, invalid_runtime_view, invalid_runtime_selector,
runtime_item_not_found y runtime_derivation_mismatch. Conservar errores vigentes
para sellos, fuente ausente/alterada, identidad, BSON y driver. Errores de entrada
antes de conectar; mensajes sin texto del corpus, rutas privadas ni credenciales.
En search, fuente no verificable se cuenta entera como unavailable_sources;
identidad de cabeza/registro incoherente aborta la consulta como hoy. En fetch,
cualquier error implica cero contenido. No tratar error del driver como rollback
demostrado; receipt sigue siendo recuperación de resultado incierto.

### Colecciones mixtas y CLI: condición previa, no compatibilidad retroactiva

En el lector actualizado, search de transcripciones conserva su payload v0/v1;
añade excluded_source_kinds {runtime-events: cantidad}. Valida S antes de excluir
por tipo; no abre originales de otras familias. fetch de transcripción dirigido
a v2 devuelve source_kind_conflict; fetch_runtime dirigido a v0/v1 también.
No saltar una cabeza runtime para devolver una revisión histórica meeting.
Clientes que exijan claves raíz exactas deben actualizarse por ese campo aditivo.
Las versiones viejas seguirán siendo incompatibles con v2: sólo se asegura
convivencia con lectores actualizados, no acceso transparente desde código viejo.

CLI candidata: formato explícito nuevo y subcomandos source search-runtime /
fetch-runtime con flags equivalentes a las APIs; fetch-runtime exige --view y
el selector correspondiente, sin default bruto. --help no conecta servicios.
Sin comandos de activación, cambios de índices de corpus ni reconstrucción ADR-019.
Antes de integrar, actualizar ADR aceptado, SPEC-007 y source-store-v3 junto con
implementación/tests. Este documento no añade por sí solo comandos ejecutables.

### Matriz de laboratorio y condiciones de avance

Usar replica set temporal exclusivo, puerto distinto de 27017 y base skopos_test*;
fixtures sintéticos TXT/v0, ASR/v1 y runtime/v2. No clonar ni reanalizar corpus
productivo. El export privado sólo se incorpora después de fijar su identidad,
lectores y retención del piloto; no es requisito de la regresión sintética.

| Caso de falsación | Resultado exigido |
|---|---|
| Texto/pointer/contador alterado y sellos de texto/sobre recalculados | S puede pasar coherencia; D rechaza derivación; cero contenido |
| Campo extra, bool como seq, IDs duplicados, row inexistente | S rechaza; control positivo del mismo sobre válido |
| Original ausente/alterado y restaurado | fetch falla; search cuenta fuente; restauración permite control positivo |
| Replay, recibo perdido y revisión concurrente | Un único avance CAS; duplicate conserva primer recibo; no inventar revisión |
| Cambio runtime↔meeting bajo mismo source_id | source_kind_conflict sin avance ni escritura parcial |
| Búsqueda mixta y fetch cruzado | Cada familia sirve sólo su tipo; exclusiones contadas; sin fallback histórico |
| Última proyección corrupta tras primeras válidas | Ningún resultado de esa fuente servido |
| Exceso BSON/salida, limit=0/20, UTF-8 multibyte | Límites exactos; exclusión completa; sin truncado ni byte counts por caracteres |
| Reasoning/herramientas/instrucciones con señuelo text | No aparecen en search; bruto sólo con vista y selector explícitos |
| Política desconocida, lector antiguo | Rechazo claro, sin rederivación con versión nueva por defecto |

Autorrevisión adversarial documental: se eliminaron equivalencias falsas
entre hash y derivación, v3 y compatibilidad, receipt y disponibilidad, y
selección de vista y autorización. Se fijaron validación por fuente antes de
servir, identidad estable por familia y presupuesto del JSON completo.
Riesgos residuales: secreto en text admitido, pérdida de original, coste de
reparseo, manipulación por actor con acceso local y ausencia de ACL multiusuario.
No revisión independiente ni validación clínica o certificación del runtime.

Próximo paso recomendado: aceptar esta extensión sólo para laboratorio e
implementar validador/lecturas y luego admisión, cerrando la matriz con controles
positivos y negativos antes de cualquier piloto privado. Producción, memoria,
embeddings y conservación del corpus histórico permanecen fuera del alcance.

Verificación de esta extensión documental: diff completo revisado y gates
268 archivos/un plan verdes. Suite del código existente:411 pruebas OK sin
omisiones,74.819 s en Mongo temporal exclusivo y fixture Ollama local; log
`/private/tmp/skopos-runtime.hmdFUy/contract-tests.log`. No hay cambios Python.
La matriz nueva define aceptación futura; no se declara ejecutada ni validada
por esta regresión. No se actualizó el contrato vigente ni se escribió AN-KLA.

## Aceptación acotada y validación/lecturas puras — 2026-10-05

El Operador aceptó continuar la extensión sólo para laboratorio mediante
«adealntes» tras la recomendación de validadores/lecturas antes de admisión.
Este incremento implementa el núcleo puro; no modifica aún SourceStore, CLI,
SPEC-007 ni source-store-v3. La aceptación no habilita producción ni datos nuevos.

Módulos experimentales:
- `verification.py`: validate(envelope), nivel S; verify(envelope, raw), nivel D.
- `views.py`: fetch_verified con identidad/revisión/hash y vista explícitos;
  search_verified sobre una única revisión y buffer entregados por el llamador.

No son todavía search_runtime/fetch_runtime del almacén. search_verified declara
selection=explicit_revision: no simula cabeza vigente, colección mixta, conteo de
fuentes indisponibles ni CAS. Los errores de esta única fuente fallan completos;
el futuro adaptador agregará conteos por fuente sin servir resultados parciales.
Ninguna función abre archivos ni conecta Mongo. raw ausente se trata como fallo
de integridad del buffer; source_unavailable corresponderá al futuro lector de disco.

S valida campos cerrados, metadatos, políticas conocidas, tipos estrictos,
límites, continuidad de filas, grupos de lotes, unicidad y enlaces internos,
sellos y forma de proyecciones. Usa límite de16MiB de JSON canónico del sobre;
no acredita que quepa el registro BSON, pendiente en admisión. D coteja fuente
y reconstruye el sobre completo; comparación canónica evita igualdad true==1.
fetch entrega exclusivamente la vista seleccionada y devuelve copias separadas;
search sólo texts, orden numérico de seq, exclusión contada por límite/tamaño.
El límite de64KiB cubre todo resultado serializado compacto, no sólo texto.

Autorrevisión adversarial: probada falsificación de texto con ambos sellos
recalculados y de contador coherente. S puede aceptar; D rechaza antes de servir
incluso el primer texto válido de la fuente. Positivos con fuente intacta,
header sin eventos, lote expandido y restauración del buffer. Negativos incluyen
bool como seq/contador/selector de revisión, campos extra, referencias internas
rotas, grupos de lote alterados, schema/política desconocidos y fuente alterada.
Señuelo PRIVATE no aparece en búsqueda; sólo en vista bruta explícita. Esto no
implementa ACL ni evita secretos dentro de bloques text admitidos.

15 pruebas nuevas de validación/vistas;49 en total del experimento runtime OK
con datos sintéticos, sin relectura del export privado en este incremento.
Revisión de la misma instancia, no independiente. No hay pruebas de persistencia
runtime aún: faltan conexión a lectura de archivo/Mongo, selección de cabezas,
compatibilidad mixta y admisión transaccional con su matriz completa.

Regresión final:426 pruebas OK sin omisiones en74.128 s sobre Mongo temporal
exclusivo37027 y fixture Ollama local. Gates271 archivos/un plan verdes; diff
leído, código sin cambios posteriores a la suite. Log local:
`/private/tmp/skopos-runtime.hmdFUy/verification-tests.log`. Procede publicación
del núcleo experimental, no integración/activación productiva ni cierre de H25.
