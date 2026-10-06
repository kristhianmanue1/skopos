# ADR-020 — frontera de fuentes diversas

Estado: ACEPTADO para implementar T4, por «adelante» del Operador en respuesta
a la decisión D1 con custodia mediante referencias externas (2026-10-05).
Acepta contrato y almacenamiento separado; no autoriza corpus real, migración,
activación, cambio de topología productiva ni merge de este incremento.
Fecha: 2026-10-05. Plan: `docs/planes/activos/h25-fuentes-v1.md`.
INFORMS: ADR-016/018 (idioma y evolución), ADR-007 (versiones de análisis),
ADR-009 (evidencia). No sustituye esos ADR ni modifica contratos v2 vigentes.
D1 aceptada; REQUIRES_DECISION: D2a (corpus) y D2b (aceptación/activación/merge).

El anexo de implementación al final concreta D1 y manda sobre los párrafos
históricos de propuesta conservados debajo. T3 no se reetiqueta como producto.

## Problema comprobado y requisitos del primer incremento

El lector diarizado conserva bytes y declara completitud desconocida. El piloto
de reuniones exige complete booleano y serializa una fuente JSON diferente.
Forzar el primero al segundo convierte incertidumbre en falsedad o reetiqueta
bytes derivados como originales. Tampoco deben inventarse roles usuario/agente.

| REQ | Propiedad | Falsación y evidencia requerida |
|---|---|---|
| H25-R1 | Identidad explícita y acotada por proyecto | Dos fuentes con ordinal s1 colisionan; probar separación |
| H25-R2 | Revisión de fuente separada del análisis | Reanalizar modifica source_revision; probar que no ocurre |
| H25-R3 | Localizadores sobre bytes originales | Slice UTF-8/CRLF difiere del texto; comprobar cada segmento |
| H25-R4 | Incertidumbre conservada | unknown se transforma en false/complete; probar las tres declaraciones |
| H25-R5 | Captura independiente de LLM | Construir sobre requiere red/modelo; prueba sin dependencias de modelo |
| H25-R6 | Repetición determinista e identidad estable | Renombrar archivo o repetir cambia identidad declarada; comprobar |
| H25-R7 | Frontera fail-closed acotada | Dato inválido o excesivo se trunca silenciosamente; probar rechazo |
| H25-R8 | Publicación gobernada | Crear sobre importa, exporta o ejecuta contenido; comprobar efectos |

R1–R8 delimitan la frontera inicial, no la persistencia ni el hito completo.
El único formato experimental de esta revisión es la transcripción diarizada
ya observada por el lector. No se afirma validación de otras herramientas ASR.

## Propuesta recomendada

Importación manual de un archivo identificado por el Operador; sin discovery,
watcher, HTTP de ingesta ni proveedor LLM en H25.1. El adaptador recibe una
instantánea de bytes y metadatos explícitos. El almacenamiento productivo es
otra frontera. El prototipo no abre archivos ni persiste: recibe bytes.

Contrato experimental: `skopos/source-envelope/v0`, diccionario cerrado producido
por el constructor; no es un validador de sobres recibidos de terceros.

| Campo | Semántica candidata |
|---|---|
| schema | skopos/source-envelope/v0 |
| project_id, source_id | IDs ASCII declarados, 1–128 caracteres, inicio alfanumérico, resto alfanumérico o . _ -; sin rutas |
| source_kind | meeting-transcript; constante del adaptador, no detección universal |
| source_revision | Entero positivo (bool rechazado), máximo 2^63−1; asignado por caller |
| previous_source_sha256 | null en revisión 1; 64 hex minúsculas en revisiones posteriores |
| source_sha256, source_bytes | SHA-256 y longitud del buffer crudo observado |
| adapter | ID skopos/diarized-reader/v0 y formato skopos/diarized-transcript/v0 |
| captured_at | Fecha UTC normalizada desde entrada ISO con zona explícita entre −14:00 y +14:00, sin −00:00; declaración del caller |
| captured_at_basis | caller_declared; no es fecha de reunión ni hora medida por el parser |
| occurred_at | null; no se infiere del archivo ni de captured_at |
| capture_completeness | value: unknown, partial o complete; basis: null si unknown, explicación explícita de 1–512 caracteres en los otros casos |
| audio_alignment, speaker_identity | not_verified; una etiqueta no acredita una persona |
| segments | Campos del lector: id ordinal, línea, inicio/fin ms, speaker, text, offsets UTF-8; sin roles artificiales |
| adjacent_overlaps | Sólo intersecciones entre pares adyacentes; no totalidad de solapamientos |
| envelope_sha256 | SHA-256 del JSON UTF-8, ensure_ascii=False, sort_keys=True, separadores compactos, sin este campo |

La clave de segmento es (project_id, source_id, source_revision, segment.id).
Reordenar texto puede cambiar ordinales: no prometen identidad entre revisiones.
source_id NO es el hash: una corrección mantiene la fuente y cambia revisión/hash.
La misma fuente copiada conserva identidad sólo si el caller entrega los mismos
IDs. El adaptador no acredita autoridad del caller ni descubre duplicados globales.

La revisión y el predecesor se validan sintácticamente en v0. Una forma correcta
NO acredita existencia ni vigencia. T4 debe comparar predecesor bajo transacción
o CAS; dos escritores de la misma cabeza no pueden publicar ambos como siguiente.
Cambiar de parser puede cambiar el sobre sin cambiar source_sha256; su versión
se conserva y la política de rederivación se decidirá antes de almacenar.

Límites v0: 16 MiB del lector, 10.000 segmentos. Captura completa o parcial es
siempre declaración con procedencia; se puede registrar pero nunca promocionar
a verificación de audio o totalidad. La redacción de texto crea un derivado con
hash propio; no debe mantener una falsa equivalencia con offsets originales.

Errores estables nuevos: invalid_source_bytes, invalid_project_id,
invalid_source_id, invalid_source_revision, invalid_predecessor,
invalid_capture_time, invalid_completeness, invalid_completeness_basis,
segment_limit_exceeded. Se conservan los errores del lector para tamaño,
UTF-8, líneas e intervalos. No se devuelve sobre parcial ante error.

## Evolución productiva propuesta para D1

Recomendación: conservar v2 sin cambios y diseñar colección separada de fuentes
v3 en el Mongo local ya adoptado. Esta es una propuesta, NO una decisión de
backend ni implementación en este acto. No duplicar el rol de Ágora dentro de
Skopos. Una interfaz de almacenamiento debe permitir evaluar alternativas.

Antes de aceptar D1 se completará un anexo F1 con: claves únicas, CAS, estados
de admisión, recibo de importación, orden de persistencia y recuperación ante
corte, selección vigente, autorización de lectura, límites de salida y matriz
de compatibilidad de consumidores reales. No hay migración masiva automática.
La propuesta está lista para discusión, no para iniciar T4 sin aceptación.

### Anexo candidato D1: comportamiento productivo a decidir

- Clave de revisión: (project_id, source_id, source_revision), única. Cabeza
  por (project_id, source_id). Análisis conserva su identidad/revisión propia.
- Admisión manual: entregar referencia explícita y expected_previous_sha256.
  Repetición de clave+hash devuelve duplicate sin nueva revisión; misma clave
  con hash distinto devuelve revision_conflict. Nunca basta con hash global.
- Publicación atómica: comparación de cabeza, inserción y avance visibles
  juntos. Si Mongo disponible no soporta la transacción elegida, no degradar
  silenciosamente: revisar el diseño con evidencia del entorno. No modificar
  topología productiva por conveniencia de implementación.
- Recibo: identidad, revisión, hash, estado imported/duplicate y fecha de
  admisión; fallo explícito no avanza cabeza. Reintento tras resultado incierto
  consulta clave/hash antes de repetir. El test de corte verifica esa regla.
- Buscar devuelve sólo cabezas del proyecto solicitado, sin cruce implícito;
  fetch acepta revisión explícita y vuelve a comprobar bytes. Selección y fetch
  fijan revisión/hash: un cambio posterior no convierte lo servido en actual.
- Salida propuesta: 20 resultados, 64 KiB por fragmento y exclusiones contadas;
  error de integridad o acceso no devuelve texto. Redacción genera un derivado
  con su propio sello y relación al original; nunca offsets falsos.
- Custodia inicial propuesta: referencia externa, sin copiar originales al
  almacén. Fuente ausente produce source_unavailable. Sólo aceptar esta opción
  si el Operador admite que no garantiza preservación ante pérdida del archivo;
  otra exigencia requiere política de copia/retención antes de D2a.
- Compatibilidad: rutas actuales v2 no leen v3 por accidente; adaptador explícito
  para consumidores nuevos. Ensayar consumidor CLI v2 y uno programático sobre
  fixtures; Ágora permanece opcional hasta verificar su contrato real.
- Retorno: deshabilitar la nueva entrada conserva lecturas v2; no borrar v3 ni
  reescribir legado. Una migración futura tendrá backup, ensayo y decisión propios.

Esta propuesta expone una elección material: preservar referencias externas
no equivale a custodiar las fuentes. No existe decisión de aceptación de ese
riesgo ni implementación productiva en T3.

Alternativas: extender v2 (rompe roles/localizadores obligatorios); promover
SQLite del piloto (no hay evidencia productiva que lo justifique); forzar todo
a texto genérico (pierde semántica nativa). Mantener prototipos separados es
válido durante T3 pero no satisface integración ni durabilidad de H25.1.

Antes de D2a, definir custodia del original: referencia externa puede desaparecer;
guardar copia inmutable mejora recuperación y aumenta datos sensibles retenidos.
No se elige ni activa backup, cifrado, borrado o acceso multiusuario aquí.
Un entorno local no equivale a control de acceso; un hash no autentica al autor.

## Verificación y alcance del prototipo

Cada prueba de rechazo se acompaña de una entrada válida de la misma frontera.
Cubrir metadatos inválidos, límites exactos, revision/parent, espacios de identidad,
Unicode/CRLF, texto con órdenes inertes, no mutación del buffer, hash de fuente
distinto del hash del sobre, y mismo origen con metadatos de captura diferentes.
Los tests sólo acreditan el contrato experimental, no audio, producción,
concurrencia del almacén, escala real, retención o interoperación con Ágora.

## Anexo F1 aceptado para T4 — 2026-10-05

Backend: Mongo local, colecciones `source_revisions_v3` y `source_heads_v3`,
sin tocar `turnos` ni `analisis`. `SourceStore` recibe una base explícita;
la CLI exige `--database`. No hay watcher ni entrada automática en v2.
El contrato ejecutable se detalla en `docs/contratos/source-store-v3.md`.

La clave única de revisión y su `_id` se forman con proyecto/fuente/revisión;
los IDs no permiten `:`. La cabeza tiene clave única proyecto/fuente.
Importar requiere replica set: `hello` debe declararlo antes de crear índices.
En una transacción snapshot/majority se consulta duplicado, compara la cabeza,
inserta revisión y reemplaza cabeza con CAS. El callback no abre archivos ni
llama servicios externos; puede repetirse por el driver. DuplicateKey concurrente
reintenta la misma clave hasta tres veces, no asigna otra revisión.
La capacidad real de transacción se confirma al ejecutar, no sólo con `hello`.
Standalone devuelve `transactions_required`; nunca hay fallback no atómico.
Cambiar la topología productiva queda fuera de esta aceptación.

Los originales se referencian por ruta absoluta; no se custodian copias.
Duplicado significa misma clave y hash de fuente: retorna el primer recibo,
sin cambiar captura, parser, completitud o ruta. Para corregir metadatos se
publica nueva revisión explícita con predecesor; no hay rederivación en sitio.
Renombrar una fuente ya admitida puede volverla indisponible aunque exista
una copia; replay no relocaliza. Esta limitación es visible, no se encubre.

Además del límite del lector, el documento BSON completo no puede superar
16 MiB; exceso o enteros no codificables rechazan antes de escribir. No se
promete que todo archivo de 16 MiB quepa en Mongo junto con el sobre.

Búsqueda inicial: subcadena casefold, orden por source_id/segmento, sin ranking,
sin $text ni dependencia de ADR-019. Cada cabeza se fija antes del filtro;
no es una instantánea global del proyecto bajo concurrencia. Los resultados
llevan revisión/hash, nunca una promesa de vigencia después de la selección.
Siempre se verifica el archivo antes de servir texto, también en búsqueda.
Máximo 20 segmentos y 64 KiB por resultado JSON compacto UTF-8, incluidos sus
metadatos (refinamiento adversarial: no sólo el texto): se excluye el segmento entero
excesivo, con contador. No hay truncado ni redacción que falsee localizadores.
Texto crudo verificado y marcado como dato (ADR-009); no garantiza ausencia de
secretos. Corpus y lectores requieren D2a. La búsqueda escanea fuentes vigentes;
escala, latencia y calidad de recuperación se evalúan en T5.

Acceso: cliente local con los permisos del proceso y de Mongo, no ACL por
proyecto ni aislamiento multiusuario. project_id es selector, no credencial.
Fuentes no regulares/enlaces finales se rechazan; denegación de lectura produce
source_unavailable. Nada en esta interfaz autoriza leer rutas ajenas.

Ante respuesta de admisión perdida: consultar receipt por clave+hash sin
necesitar el original; not_found no acredita fallo si todavía hay otra
transacción en curso. Esperar su resolución y repetir la MISMA identidad.
No incrementar revisión para resolver incertidumbre. El retorno operacional
consiste en usar el consumidor anterior sin invocar source; no borra v3.

Referencia del mecanismo, no evidencia de ejecución propia:
[transacciones PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/).

## Extensión H25.2 autorizada — 2026-10-06

El Operador autoriza continuar integración CLI, operación, reversión y memoria.
Se incorpora el perfil runtime probado, con formato y vistas explícitos, sin
migrar v2 ni activar índices ADR-019. AMENDS: alcance de formatos en SPEC-007 y
source-store-v3; conserva identidad, custodia por referencia y autoridad separada.
No convierte la evaluación documental deficiente en fallo de integridad runtime,
ni la captura correcta en aceptación de relevancia. Perfil de producción y
aceptación operacional final deben concretarse antes de habilitar el servicio.
