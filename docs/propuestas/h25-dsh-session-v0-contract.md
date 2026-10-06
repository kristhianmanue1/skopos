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
