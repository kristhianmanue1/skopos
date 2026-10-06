# Contrato de fuentes diversas — T4 / ADR-020

Estado: D1 aceptada para implementación; aceptación operativa pendiente de D2.
No sustituye documento-analisis-mongo v2 ni documento-turno-mongo v2.

## Extensión JSON optativa — ADR-021

import_file añade source_format='diarized-text'; CLI import añade
--format diarized-text|whisperx-json. Default y salida TXT intactos.
whisperx-json genera source-envelope/v1 con lector whisperx_reader.parse;
source-record/v3 admite unión explícita v0/v1. No hay migración de documentos.
Un consumidor previo rechaza v1; no admitirlo hasta disponer del nuevo lector.
Sobre v1 mantiene metadatos/identidad/captura de v0, pero omite adjacent_overlaps
y cambia adapter a skopos/whisperx-reader/v1, formato skopos/whisperx-json/v1.
Los segmentos llevan start_seconds/end_seconds, speaker nullable, word_count,
text, derived_text_sha256 y locator json-value (pointer, start_byte/end_byte,
sha256). ID ordinal acotado a fuente/revisión. Tiempos/confianza/etiquetas
originales completos permanecen en objeto JSON sellado, no se reinventan.
Fetch/search v1 devuelve status json_bytes_verified y original_json además del
segmento derivado: UTF-8 de original_json reproduce el slice original, no una
serialización normalizada. El presupuesto de 64 KiB cubre toda la salida.
Replay y CAS conservan su contrato. Rechazos nuevos: unsupported_source_format,
invalid_json, invalid_json_utf8, invalid_json_unicode, invalid_json_number,
duplicate_json_key, json_depth_exceeded, invalid_whisperx_schema,
invalid_whisperx_segment, invalid_whisperx_word, invalid_word_time,
invalid_word_score, invalid_speaker, word_limit_exceeded,
word_segments_mismatch y json_locator_missing. Límites y perfil en ADR-021.

## Fronteras y datos

- `source_reader.parse`: bytes → segmentos y localizadores originales.
- `source_envelope.build_envelope`: bytes + metadatos → source-envelope/v0
  (misma semántica del prototipo T3, que permanece como referencia).
- `source_store.SourceStore`: base Mongo → admisión/transacción/recuperación.
- `source_cli.source_command`: JSON/stdout; errores stderr y exit 1.

Registro `skopos/source-record/v3`: `_id`, project_id, source_id,
source_revision, envelope, source_path y admitted_at. El sobre incluye texto
indexado derivado, no una copia íntegra del archivo original. Tiene sello propio
y sello del original distintos; admitted_at es hora observada por este proceso.
El esquema v0 del sobre no implica v0 del almacenamiento; versiones separadas.

Cabeza: `_id`, project_id, source_id, source_revision, source_sha256 y
revision_key. Revisión insert-only; cabeza mutable sólo dentro de transacción.
Claves únicas y CAS definidos en ADR-020. SourceStore no acepta sobres arbitrarios:
los construye desde una única lectura de un archivo regular explícito.
Se fija N por fstat del descriptor y se leen N bytes; lectura corta falla.
No es una instantánea atómica general del filesystem; cambios posteriores pueden
volver la referencia indisponible. No acredita audio ni completitud de captura.

## Operaciones Python

`import_file(path, *, project_id, source_id, captured_at, source_revision=1,
expected_previous_sha256=None, capture_completeness='unknown', completeness_basis=None)`:
valida/admite; devuelve identidad, source_sha256, envelope_sha256, admitted_at
y status imported/duplicate. Revisión 1 sin padre, posteriores consecutivas
con hash de la cabeza anterior. Mismo hash no sustituye identidad explícita.
Repetición conserva primer registro completo; ruta/metadatos no se reescriben.

`receipt(*, project_id, source_id, source_revision, source_sha256)`:
devuelve primer recibo con status duplicate o status not_found; hash distinto
en la misma clave es revision_conflict. No lee archivos. Sirve para reconciliar
resultado incierto, no como promesa de que el archivo todavía esté disponible.
Receipt y replay verifican identidad del registro y sello del sobre antes de
confirmar duplicate, sin leer el original. Registro incoherente produce
store_integrity_failed o envelope_integrity_failed, nunca recibo afirmativo.

`search(*, project_id, term, limit=20)`: term no vacío y hasta 1024 bytes;
limit entero 0–20 (bool inválido). Sólo cabezas del proyecto, antes del filtro.
Devuelve results, excluded {result_limit, fragment_too_large},
unavailable_sources {código: número de fuentes}, declaration y
selection per_source_head_observed. Los contadores de indisponibilidad no son
conteos de coincidencias: no se conoce el contenido verificable de esas fuentes.
La cantidad de fuentes escaneadas y el coste de lectura no están acotados por
limit; no es un índice de ranking ni una garantía de latencia.

`fetch(*, project_id, source_id, source_revision, source_sha256, segment_id)`:
revisión histórica explícita o vigente; comprueba sello del sobre, tamaño/hash
del archivo y slice UTF-8 del segmento. Devuelve identidad, hashes, segmento,
status transcript_bytes_verified, audio_alignment/speaker_identity not_verified
y declaration. Nunca devuelve texto ante error. Hasta 64 KiB por resultado
JSON compacto UTF-8, incluidos metadatos y declaración, no sólo texto;
si excede, fragment_too_large. Un fragmento no equivale a la fuente completa.

No hay redacción en esta frontera de evidencia: crudo verificado, marcado como
dato. Redacción futura deberá producir derivado con hash y contrato propios.

## CLI manual

`skopos source --database DB [--uri URI] import PATH --project-id P --source-id S
--revision N --captured-at ISO [--expected-previous-sha256 HASH]
[--completeness unknown|partial|complete] [--completeness-basis TEXTO]`

Subcomandos search (term, --project-id, --limit), fetch (--project-id, --source-id,
--revision, --source-sha256, --segment-id), receipt (igual sin --segment-id).
Conexión por defecto localhost:27017; requiere replica set para importar.
La ayuda no conecta ni activa servicios. La invocación no concede permisos;
se usan los del proceso y servidor. No hay ACL multiusuario en este contrato.

## Errores y compatibilidad

Errores del sobre/lector se conservan. Nuevos: transactions_required,
source_record_too_large, source_record_not_encodable, revision_conflict,
predecessor_conflict, source_unavailable, invalid_source_file, source_short_read,
envelope_integrity_failed, source_integrity_failed, locator_mismatch,
fragment_too_large, revision_not_found, segment_not_found, store_integrity_failed,
invalid_term, invalid_limit, invalid_source_sha256, invalid_segment_id.
Un fallo de driver se comunica sin URI/credenciales, y puede dejar el resultado
de admisión incierto; resolver con receipt. No interpretar exit 1 como rollback
demostrado cuando se perdió comunicación después de commit.

No se ejecuta LLM, no se llama Ágora/AN-KLA, no se migra legado. Consultar no
crea colecciones/índices. Deshabilitar la entrada nueva conserva consumidores
v2; v3 permanece almacenado y no se borra para simular rollback.

## H25.2 — entrada runtime integrada (2026-10-06)

Implementación autorizada por el Operador para preparar operación; activación
productiva y aceptación de relevancia no se deducen de esa autorización.
`runtime_reader`, `runtime_envelope`, `runtime_verification`, `runtime_views`
y `runtime_store.RuntimeSourceStore` incorporan el perfil probado en laboratorio.
El código experimental anterior permanece como antecedente; los tests runtime
ahora ejecutan los módulos integrados. No hay dependencias nuevas.

Se conserva el identificador histórico `skopos/experimental-runtime-envelope/v0`
del adaptador para no cambiar sobres/hashes ya admitidos. Su nombre no acredita
ni niega aceptación operativa; contrato detallado y límites en
`docs/propuestas/h25-dsh-session-v0-contract.md`. Se mantiene source-envelope/v2,
política runtime-text-policy/v0 y rechazo de versiones desconocidas. BSON Int64
se convierte a entero JSON al leer; bool y otros tipos no se coercionan.

Entrada explícita: `source ... import PATH --format dsh-session-v0-jsonl`,
con los mismos IDs, revisión, captura y predecesor obligatorios del contrato.
No autodetecta ZIP, no extrae archivos ni recorre directorios. Import requiere
replica set. El archivo original debe permanecer en su ruta de custodia.

Lecturas runtime explícitas:
- `source ... search TERM --project-id P --kind runtime-events [--limit 20]`
- `source ... receipt --project-id P --source-id S --revision N
  --source-sha256 HASH --kind runtime-events`
- `source ... fetch-runtime --project-id P --source-id S --revision N
  --source-sha256 HASH --view text_projection --text-id ID`
- Vista `original_jsonl` exige `--row-id`; `derived_event` exige `--event-id`.
  Un único selector, coherente con vista, se comprueba antes de conectar.

Default de import sigue siendo TXT; search/receipt siguen seleccionando el
consumidor legado salvo --kind runtime-events. El consumidor legado puede
reportar v2 como no soportado; usar el consumidor explícito correcto, no degradar
sobres ni reescribirlos. fetch de transcripción conserva su contrato anterior.
La búsqueda runtime es subcadena casefold, no ranking ni respuestas semánticas;
la evaluación documental $text/ADR-019 constituye un frente separado.

### Preparación operativa y reversión

Antes de activar: fijar perfil local monousuario o compartido, lectores,
retención, ubicación estable de originales, URI/base dedicada v3 y respaldo en
otro soporte. project_id no es ACL. El texto de evidencia no está redactado;
no exponer esta interfaz como servicio multiusuario sin contrato de acceso.
No convertir el Mongo legado por conveniencia. Un replica set de un nodo
permite transacciones, pero no aporta alta disponibilidad.

Ensayar primero contra base nueva: import, receipt, replay, search y las tres
vistas; verificar hash de original antes/después. Ante resultado incierto,
consultar receipt con la misma identidad. No aumentar revisión a ciegas.
Respaldar original y base de forma consistente; ensayo de recuperación debe
incluir ruta original o relocalización autorizada, no sólo apertura de Mongo.
La copia de custodia actual no reubica referencias almacenadas automáticamente.

Reversión no destructiva: dejar de invocar runtime, conservar base v3 y fuentes,
volver al consumidor anterior para TXT/v2 legado; éste no leerá sobres runtime.
No borrar colecciones, migrar a v2 ni alterar índices ADR-019 como rollback.
El despliegue y su validación final quedan pendientes del perfil operativo.

### Perfil operativo confirmado — 2026-10-06

Decisión del Operador: por ahora local monousuario, bajo su cuenta y con agentes
autorizados; conservar la posibilidad de uso multiusuario futuro sin implementarla.
Puede haber varios procesos: monousuario no significa exclusión mutua ni una
sola sesión. Se mantienen las transacciones/CAS y sus pruebas de concurrencia.
No exponer Mongo ni la CLI como servicio de red compartido. Loopback reduce
exposición de red, pero no autentica ni aísla procesos locales; project_id sigue
siendo selector, no credencial. Directorios privados no sustituyen autenticación
Mongo si otros procesos pueden conectarse. No hay ACL por agente/persona.

Un futuro perfil compartido exige decisión y contrato nuevos: autenticación,
autorización por recursos, aislamiento entre usuarios/agentes, auditoría y pruebas
negativas con controles positivos. No se habilita cambiando bindIp ni compartiendo
credenciales de la cuenta actual. No se añaden dependencias especulativas ahora.

La confirmación no acredita despliegue ni respaldo independiente. Sigue pendiente
identificar soporte/destino de respaldo autorizado y comprobar su restauración,
además del arranque y verificación del servicio dedicado. La copia en el mismo
equipo conserva su utilidad de custodia, no protección ante pérdida del equipo.

Verificación de integración:462 pruebas OK sin omisiones en65.912s,
Mongo temporal exclusivo37027; log `/private/tmp/skopos-h252.WBLheT/final-suite.log`.
CLI sobre export privado autorizado, en base de laboratorio nueva: import,
replay,receipt,2 proyecciones,2 búsquedas literales y fila original correctos;
hash del JSONL en custodia estable sin cambios. Datos privados fuera de Git.
Autorrevisión adversarial: no se confunde integración con despliegue; selector
de vista incorrecto falla antes de conectar; ruta de retorno conserva registros;
tests de parser/sobre/vistas ahora usan módulos integrados, no sólo prototipos.
El prototipo conserva copias históricas; mantener su divergencia fuera de producto.

Actualización operativa posterior: la instancia dedicada local fue activada y
verificada; el Mongo legado permanece separado. El estado pendiente de despliegue
y destino de respaldo de los párrafos anteriores es histórico. Véanse comandos,
evidencia, reversión y límites vigentes en
`docs/evidencia/h252-operacion-local-2026-10-06.md`. Recuperación ante pérdida del
equipo aún no demostrada: faltan custodia independiente de claves y ensayo desde
nube. No se adjudica relevancia ni se habilita multiusuario.
