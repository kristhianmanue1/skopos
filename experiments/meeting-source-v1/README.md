# Piloto de reunión y corrección de fuente

Experimento aislado del producto: `pilot.py` implementa un almacén efímero de
fuentes JSON. No conecta con Mongo, no usa los parsers CLI, no activa un servicio
ni importa contenido privado. No es todavía un conector desplegado de Skopos.

Ejecutar desde la raíz:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_meeting_pilot.py -v
```

Los cinco casos crean archivos temporales de una reunión ficticia de Nerea:
«La entrega será el lunes», corregido a «la entrega será el martes». Comprueban
importación, duplicados, búsqueda vigente, navegación explícita a ambas revisiones,
huella del archivo completo y localizador tiempo/hablante/segmento. También prueban
captura parcial, origen desaparecido, archivo modificado, conflicto de revisión
y predecesor incorrecto. Resultado observado: 5/5 pruebas pasan.

`complete` es una declaración de captura, nunca una demostración. `search` consulta
la copia indexada y marca integridad no comprobada; `fetch` relee y verifica los
bytes. Verificar esos bytes no acredita que el diálogo recibido esté completo.
El término antiguo deja de aparecer en búsquedas actuales; permanece recuperable
por revisión explícita para auditoría.

Este experimento versiona **la fuente**, mientras ADR-007 versiona **el análisis**.
No reutiliza sus números ni fuerza reuniones al esquema usuario/agente. El hash
identifica los bytes recibidos: un cambio sólo de formato también cambia revisión.
Búsqueda por subcadena y almacenamiento en memoria bastan para el piloto, pero no
acreditan búsqueda semántica, persistencia, concurrencia ni escala. No hay control
de acceso de producción ni inferencia automática sobre transcripciones.

Autorrevisión adversarial: se rechaza sustituir contenido bajo la misma revisión
y enlazar revisiones con un predecesor falso. La desaparición del archivo no elimina
la copia indexada ni se presenta como eliminación autorizada del contenido.
Antes de un conector real faltan persistencia, política de retención/acceso,
contrato de captura del origen elegido y prueba con una exportación autorizada.
No hay conexión a Ágora o AN-KLA ni escritura cruzada.

Verificación conjunta: suite de Skopos con 298 tests, OK y uno omitido. Se
interceptó la selección de bases Mongo para rechazar nombres distintos de
`admin` o `skopos_test*`; ninguna prueba activó ese rechazo. Gate de tamaños OK;
gate de planes inactivo porque no hay planes declarados. El piloto no evalúa
la precisión de un modelo ni constituye una integración extremo a extremo.

## Persistencia optativa del piloto

`persistent.PersistentMeetingStore(path)` conserva registros en una base SQLite
exclusiva del experimento. Sólo biblioteca estándar, sin instalar dependencias.
La ruta debe ser nueva o una base de este contrato (application_id y versión 1).
No pasar bases de otros sistemas; se rechazan antes de crear tablas.

`ingest` serializa la lectura de revisión y la inserción con BEGIN IMMEDIATE,
commit/rollback y clave compuesta. Reabrir conserva revisiones, deduplicación y
localizadores. `search` y `fetch` refrescan la vista; un segundo manejador observa
los commits del primero. Debe cerrarse con `close()`.

Cinco pruebas adicionales cubren reapertura, dos manejadores, conflicto de
revisión, rollback por predecesor falso, base ajena y desaparición del archivo.
Diez casos del piloto pasan en total. La prueba con dos manejadores es secuencial;
no demuestra resistencia a carreras multiproceso ni cortes de energía.

SQLite es una elección de este experimento, no una decisión sobre la arquitectura
final de Skopos. Se carga el índice completo en memoria: no se acredita escala.
La transcripción original sigue fuera de SQLite: no es un backup del archivo ni
un almacén de blobs. Se conserva el texto indexado, pero fetch sólo declara
verificación al releer la fuente y comprobar su huella. La base debe protegerse
según su contenido; este piloto no implementa cifrado, acceso multiusuario,
retención, migraciones ni eliminación gobernada.

## Exportación al consumidor

`export.export_packet(store, terms)` verifica cada fragmento seleccionado contra
su archivo y produce `skopos/meeting-evidence-packet/v0`, un contrato experimental.
Incluye identidad/revisión/huella de fuente, texto derivado con su propia huella,
rangos UTF-8 y localizadores nativos. Sólo una revisión por paquete. No implica
captura o selección completas; se conservan como declaraciones separadas.
Un origen ausente o alterado bloquea la exportación. Ágora puede consumir este
paquete mediante su entrada local sin importar ni modificar el almacén de Skopos.
