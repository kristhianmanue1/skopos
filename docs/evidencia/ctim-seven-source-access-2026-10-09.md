# Acceso local a siete fuentes CTIM — 2026-10-09

## Resultado observado

El inventario de expertoGobernanza contiene siete originales: cinco PDF y dos HTML. El perfil privado `seven-source-access/policy.json` fijó el hash del inventario, las siete identidades, cinco manifiestos PDF completos y dos derivados HTML. `list_sources` respondió `ok` con 7/7; verificó 19,909,414 bytes de entrada en 140 ms de tiempo de pared en esta ejecución local. Las cinco coberturas PDF suman 840/840 páginas físicas derivadas; cada PDF reporta una página `no_text` nativa. Los HTML contienen 10,756 y 507 segmentos respectivamente, como texto visible para el parser. Estas cifras no son un porcentaje de fidelidad.

Para los PDF antes parciales se generaron derivaciones nativas adicionales, sin alterar los manifiestos históricos: administración 403 páginas (`ba5ce2b8…`, 3146 ms), procedimiento 91 (`0bf9b839…`, 2096 ms), POBALINES 78 (`1744c626…`, 2085 ms). Los recibos y contenidos completos permanecen en `runs/`, fuera de Git. El DPM usa el manifiesto completo `372fdaef…`, que corresponde a la política actual; un manifiesto anterior `26c4382b…` falló correctamente `manifest_integrity_failed` por cambio de hash de política. El perfil no lo usa.

La búsqueda literal `CTIM` respondió `ok`, con fuente, SHA original, página física y `item_id`; `fetch_fragment` de la primera coincidencia respondió `ok`. La subcadena también aparece dentro de “Víctimas”; es ruido literal, no un acierto semántico. El método limita los resultados y comunica el total y los conteos por fuente.

El socket real respondió `list_sources` con 7/7, modo `0600`, 19,909,414 bytes verificados y 345 ms; se retiró el socket al detener el host. `fetch_fragment` respondió `ok` para un fragmento identificado de cada una de las siete fuentes. En copias temporales del perfil, un hash falso del manifiesto produjo `coverage_mismatch` y un hash falso del inventario produjo `inventory_mismatch`; no se alteraron originales ni políticas vigentes. La prueba `tests.test_ctim_source_access` pasó (3 casos). La suite completa pasó (473 casos, 6 omitidos); los gates de tamaño y planes pasaron. La suite imprimió advertencias de `MongoClient` sin cerrar en pruebas anteriores, sin fallo de casos.

## Controles y límites

El acceso comprueba políticas y recibos ya existentes, bytes originales y hashes de derivados; no prueba igualdad con los servidores remotos ni actualidad normativa. La cobertura nativa omite texto que exista sólo como imagen; las páginas `no_text` requieren evaluación visual si son relevantes. HTML no evalúa CSS/JS. No hubo llamadas a modelo ni decisión de corpus. La integración efectiva del agente consumidor, la selección de preguntas y la comparación con Muse/Spark corresponden al siguiente ensayo; no se infieren de esta prueba de infraestructura.

El perfil del host depende de archivos locales ignorados y de Mongo 37034. No se publica un socket activo ni se garantiza operación autónoma permanente. El costo indicado mide lectura/verificación local, no costo de modelo ni utilidad de recuperación.
