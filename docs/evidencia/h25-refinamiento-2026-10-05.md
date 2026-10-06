# H25.1 — afinamiento, verificación y alcance del merge

Base: fe9839943a4141a26382646381cb4295a298e253. Fecha local 2026-10-05.
Operador autorizó implementar plan refinado, merge tras verificar, producción
sin cambios y continuación separada de runtime/referencias/ADR-019.
Productor y revisor: misma instancia Codex; autorrevisión, no revisión independiente.

## Correcciones y criterios

- Receipt/replay verifican identidad del registro, esquema y sello del sobre
  antes de confirmar duplicate. Fetch utiliza la misma validación. Corrupción
  de identidad/sello o campos ausentes se rechaza con error estable; no se
  interpreta como importación confirmada. El recibo sigue funcionando sin
  original: verifica registro, no custodia externa. No autentica un escritor
  capaz de reescribir datos y sellos coherentemente.
- Gate de publicación: requiere primario de replica set temporal; falla ante
  cero tests, skips, fallos y expected failures. Pruebas con controles positivos
  y negativos verifican la decisión; no convierte un puerto local en sandbox.
- Secuencias: ocho semillas, 30 acciones cada una (240), modelo de lista de
  revisiones independiente de _publish. Importar/repetir/conflicto/fetch y
  búsqueda vigente se comparan después de cada acción. No prueba todos los
  órdenes concurrentes posibles.
- Combinaciones: producto cartesiano 2 saltos de línea × 3 textos Unicode ×
  3 estados de completitud = 18 combinaciones, todas con replay y fetch.
  Cubre todos los pares y triples de esos factores, no factores omitidos.
- Fronteras: 19/20/21 resultados; presupuesto del fragmento justo menor/igual/
  mayor que la representación real. Tests previos cubren 16 MiB/10000 segmentos.
- Reintento del driver: inyección etiquetada TransientTransactionError después
  de _publish dentro de transacción real; callback repetido, una revisión final.

## Caída real en laboratorio

Ejecutor versionado: experiments/source-resilience-v1/pilot.py. Sólo mongod
hijo propio, puerto 37033, replica set un nodo y base skopos_test_crash.
Primero se confirma importación válida. SIGKILL con transacción sin commit;
reinicio deja revisión pendiente ausente y cabeza sin avance. Reintento publica
revisión 2. Otro SIGKILL después de commit confirmado; tras reinicio se recupera
receipt sin archivo original y fetch positivo al restaurar el fixture.
Siete comprobaciones OK; cierre final exit 0. No es pérdida real de ACK de red,
failover multinodo ni pérdida eléctrica: las páginas del SO sobreviven SIGKILL.
El fixture eliminado se reconstruye inmediatamente; no se borra fuente real.

Primer intento falló antes de importar porque el cliente de bootstrap había
observado topología sin sesiones. Corregido el harness: renovar cliente después
de habilitar replica set. Segundo intento completó los siete controles.
Expediente local: /private/tmp/skopos-refinement.lnsEvi/crash-retry.json y logs;
no contiene la transcripción real. No se reinició producción.

## Métodos externos adoptados, no certificación

Se aplican técnicas de límites/estados y cobertura combinatoria, implementadas
con unittest. No se instaló Hypothesis, ACTS ni Jepsen ni se declara conformidad
ISO. El modelo y el oráculo siguen siendo propios; deben revisarse también.

- [ISTQB, técnicas de prueba](https://astqb.org/assets/documents/ISTQB_CTFL_Syllabus_v4.0.1.pdf).
- [NIST, cobertura combinatoria](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software/faqs).
- [Hypothesis, modelo por estados](https://hypothesis.readthedocs.io/en/latest/stateful.html): referencia metodológica, no dependencia.
- [Jepsen, modelos de consistencia](https://jepsen.io/consistency/models): guía para no sobredeclarar resultados de historiales.
- [PyMongo, reintento transaccional](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/).

## Continuación separada

Segundo origen diseñado en docs/propuestas/h25-runtime-events-v0.md, no
implementado. Exige reconocer un export real antes de prometer soporte.
Escaneo de búsqueda todavía sin presupuesto total: antes de activación fijar
contrato de cancelación/límite y resultado incompleto. No se añade silenciosamente
un límite que pueda convertir búsqueda exhaustiva en parcial sin declararlo.
Standalone productivo no soporta las transacciones de v3; merge no activa v3.
AN-KLA rev11 conserva el estado previo; leer esta evidencia para el incremento.

Referencias/ADR-019 evaluados por separado en
docs/evidencia/referencias-adr019-copia-2026-10-05.md. Ninguna de las 202
referencias candidatas admite relocalización idéntica; no se falsificó reparación.
El índice español mejora el fixture salvo consulta sin tilde: decisión pendiente.

## Gate final y autorrevisión fresca

Suite final: 361 tests, 75.916 s, OK sin skips ni expected failures. Log local:
/private/tmp/skopos-refinement.lnsEvi/final-tests.log. Replica set temporal
37027, harness estricto, Ollama local para las pruebas existentes; sin corpus
real en suite. Corrida anterior: 360 tests, 114.103 s; después se agregó el
test de reintento y se repitió toda la suite. Artefacto de caída final probado
tras comprobar dbPath del servidor: crash-final.json, siete controles y exit 0.
Gates: 196 archivos/un plan; diff-check sin errores. No cambios de dependencias.

Autorrevisión final: comprobar recibo sin original, errores de identidad/sello,
replay sin relocalización, ausencia de falsos verdes y que los ensayos no se
presenten como producción. Corregido el harness de bootstrap y añadido control
de dbPath para no adoptar otro servicio por puerto. Disposición PROCEED_MERGE
dentro del alcance autorizado, sin blocker de H25.1 abierto. La publicación se
confirma por SHA remoto tras el merge; este documento se prepara antes de él.
Persisten límites operativos explícitos: sin ACL multiusuario, sin presupuesto
global de búsqueda, custodia externa y topología productiva sin transacciones.
