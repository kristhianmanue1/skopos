# Contrato de fuentes diversas — T4 / ADR-020

Estado: D1 aceptada para implementación; aceptación operativa pendiente de D2.
No sustituye documento-analisis-mongo v2 ni documento-turno-mongo v2.

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
