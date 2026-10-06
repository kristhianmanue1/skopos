# H25.2 — recuperación de descarga OneDrive

Resultado: **PASS para recuperación de datos con claves locales disponibles**.
Observación: 2026-10-06, 06:16 America/Mexico_City (12:16 UTC).
No equivale a recuperación ante pérdida simultánea del equipo y sus claves.

El Operador confirmó la descarga manual después de observarse el respaldo en
OneDrive web. Archivo recibido:
`/Users/krisnova/Downloads/OneDrive_1_6-10-2026.zip`.
Su procedencia de descarga es declaración del Operador; presencia remota previa,
archivo local y contenido fueron comprobados por el agente.

## Integridad y método

ZIP SHA-256:
`8934c069006627857ce7737ad80b2e17d1cd013fcbef345012f0131276318613`.
Contiene exclusivamente manifest.json y runtime-v3-data.tar.gz. Hash del tar:
`833d22dfaec636d26bd58fa1ba1d93d50975acbe9ee9e05f0dd61450922202c0`,
igual al valor conocido antes de descargar y al manifiesto recibido. Se limitaron
tamaños y rutas, rechazando enlaces y miembros fuera del árbol previsto.

Se restauraron los bytes descargados en directorio nuevo:
`/private/tmp/skopos-cloud-recovery.i6T7z3/restored`.
Mongo dedicado temporal 127.0.0.1:37033, con autenticación y replica set.
Credenciales obtenidas desde el backend Llavero fijado del lanzador operativo;
no se leyeron credentials.json ni el keyfile original para esta restauración.
Sólo la copia restaurada recibió reconfiguración del miembro y relocalización
de source_path. Ni Mongo legado ni la instancia operativa 37030 se modificaron
o detuvieron durante el ensayo.

## Verificaciones

- validate completo correcto en source_revisions_v3 y source_heads_v3.
- Dos revisiones y dos cabezas, sin documentos adicionales tras replay.
- Hashes de ambas fuentes correctos: sintética y export DSH autorizado.
- Dos proyecciones por fuente recuperadas exactamente, cuatro en total.
- Búsquedas literales y vistas text_projection, original_jsonl y derived_event.
- Receipt y replay idénticos, con estado duplicate, sin nueva ingesta lógica.
- Instancia temporal detenida al terminar. Copia temporal en claro de keyfile
  eliminada sólo después de finalizar el proceso; originales conservados.

Informe: `/private/tmp/skopos-cloud-recovery.i6T7z3/report.json`.
Arnés reproducible junto a él: `verify_download.py` (usa directorio nuevo para
otro ensayo; no reutilizar ni sobrescribir la evidencia existente).
Tiempo medido por el arnés: 2.351 s, excluye descarga e interacción humana;
no es RTO comprometido ni medición general de recuperación.

## Efecto y pendientes

Este resultado AMENDS el pendiente de descarga/restauración de
`h252-llavero-respaldo-2026-10-06.md`. No cambia su política de periodicidad ni
activa un programador. Las claves independientes continúan diferidas por decisión
del Operador. No se probó pérdida de energía, fallo de disco ni indisponibilidad
de Keychain. No es una auditoría independiente ni validación de relevancia.

Siguiente paso técnico propuesto: convertir el procedimiento de respaldo en una
operación repetible con exclusión de ingestas, recuperación ante fallo y evidencia
de cada corrida, antes de activar la periodicidad documentada. Resolver por
separado el truncamiento de claves largas en el transporte general de Llavero.
Mantener ADR-019 y embeddings diferidos; no borrar ni reanalizar corpus.

AN-KLA actualizada mediante plan y commit gobernados, summary/model_derived;
verify correcto, revisión 18:
`sha256:61f3673aac9f97d656a6087c12cd3f300c84544c5c411d1573b5bebd0dcb95e4`.
Registro `f-skopos-h252-cloud-restore-2026-10-06`. No se guardaron secretos.

Regresión de publicación: 462 tests OK sin omisiones en 83.053 s sobre Mongo
temporal exclusivo 37032, detenido al finalizar. Log en
`/private/tmp/skopos-cloud-recovery.i6T7z3/regression/suite.log`.
Gates correctos: 284 archivos y un plan. Diff documental leído; sin cambios de
código del producto. El ensayo operacional no certifica seguridad general.
