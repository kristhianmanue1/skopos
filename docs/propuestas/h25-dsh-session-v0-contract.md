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
