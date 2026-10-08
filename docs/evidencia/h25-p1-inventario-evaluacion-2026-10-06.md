# H25 P1 — inventario de evaluación documental anterior

Observación: 2026-10-06. Alcance: lectura de artefactos ya existentes de O2,
sin ejecutar búsqueda, Mongo ni consultas sobre conversaciones privadas. Este
expediente INFORMS D0/P2; no adjudica relevancia ni activa ADR-019.

## Identidad y estado de los artefactos

| Archivo preexistente | SHA-256 actual | Contenido y vínculo |
|---|---|---|
| `/private/tmp/skopos-local-eval.bkdb5V/manifest.json` | `325eb076a9565c36641816178f5464d32e339a971dc47a11cf92065a1318a80a` | Commit `49910d8c7a52f37cd04945b62d035e47175f71de`; 99 Markdown, 637 fragmentos fijos de 20 líneas, 12 consultas: ocho desarrollo y cuatro reserva. Coincide con `manifest_sha256` de conclusion. |
| `/private/tmp/skopos-local-eval.bkdb5V/results.json` | `836fde00e57cee182ab898ccd17534251218e4b65fa1afa3f662ad8f494e6c34` | 12 filas por variante english, none, spanish y spanish_expansion; rankings top20, objetivos conocidos, omisiones y truncamiento. |
| `/private/tmp/skopos-local-eval.bkdb5V/conclusion.json` | `84e62f119204fa605e9d36a19bbb52560c09a2fa8c1d13a1c9707c58a8372b3e` | Declara 4/12, 4/12, 5/12 y 5/12 conjuntos completos; recálculo de las banderas `full_evidence` de results coincide. Registra incidente de medición y nueva base con manifiesto intacto. |
| `/private/tmp/skopos-h252.WBLheT/context_probe.py` | `5758c851801612f83b8dc76783e3821afe946d8c0d34e536e4612d92406f195e` | Sonda de vecinos ±20 líneas sólo sobre desarrollo, manteniendo `_acotar` y presupuesto por bloque; escribe el resultado en la ruta histórica. No se volvió a ejecutar. |
| `/private/tmp/skopos-h252.WBLheT/context-results.json` | `4cbe07cda5acefa74ff37bc746837b511cafb35786a7b6e8e6da3b15ea37f4` | Ocho filas por variante. Completa 5/8, 4/8, 6/8, 6/8; coincide con el expediente ADR019. No contiene segunda prueba de reserva. |
| `/private/tmp/skopos-validation.8SDigv/local-query-candidates.json` | `864534331ef3ae88f89b3ad7d261df6337bd481d689ac3951db3b8ca6a543a79` | Doce *candidatas* para conversaciones reales, `evaluation_executed=false`, sin qrels humanos. Es otro protocolo, no los resultados documentales anteriores. |

La ruta temporal existe en esta observación, pero no es custodia duradera.
`49910d8` es ancestro del HEAD actual `fe1e8cb`. De los 99 hashes de archivos
del manifiesto, 93 coinciden con el checkout actual y seis cambiaron:
ADR-020, source-store-v3, adr019-expansion, guía rápida, hoja de ruta y F1
specs. Las consultas local-01, local-02 y local-12 apuntan a uno de esos
archivos modificados. Por tanto, los rankings siguen siendo resultados del
corpus congelado en el manifiesto; sus anclas de línea no se trasladan sin
revalidación al checkout actual. `src/skopos/busqueda.py` y
`src/skopos/almacenamiento.py` no tienen diff entre ese commit y HEAD, pero
eso no equivale a reproducir índices, servidor ni corpus.

## Diagnóstico de las ocho consultas de desarrollo

Los identificadores y blancos proceden del manifiesto; la clasificación
siguiente infiere mecanismos posibles a partir de rankings y sonda, no prueba
causalidad del índice. “Ausente” significa ausente del top20 observado.

| Consulta | Observación | Clasificación y siguiente falsación |
|---|---|---|
| local-01, tildes y límite | Un objetivo aparece en english/spanish y el otro falta; vecinos no completan ninguna variante. | Candidato ausente del top20 o demasiado distante para ±20 líneas; comprobar ranking profundo y fragmento objetivo antes de atribuirlo a stemming. Archivo blanco cambió después. |
| local-02, pruebas sin modificar corpus | English/spanish recuperan una de dos anclas; vecinos completan esas variantes, none sigue incompleto. | Fragmentación para variantes con ancla; para none, ausencia/ranking de ancla o presupuesto. Archivo blanco cambió después. |
| local-03, analizar/analizado | Las cuatro variantes recuperan una ancla; vecinos completan las cuatro. | Fragmentación del documento fijo de 20 líneas; la sonda no demuestra mejora del stemmer. |
| local-04, JSON frente a TXT | Objetivo completo en las cuatro variantes; vecinos no cambian resultado. | Control positivo de recuperación de un objetivo, sin evidencia de fallo. |
| local-05, BSON Int64 | Objetivo completo en las cuatro variantes; vecinos no cambian resultado. | Control positivo del expediente DSH. |
| local-06, replay/receipt | Ninguna variante trae las dos anclas y vecinos no completan. | Candidatos ausentes del top20; verificar si el índice puede encontrarlos por términos explícitos antes de proponer contexto adicional. Es fallo crítico de esta evaluación documental. |
| local-07, evento/fila | Objetivo completo en las cuatro variantes; vecinos no cambian resultado. | Control positivo de recuperación. |
| local-08, restauración | English/none no traen anclas; spanish/expansion traen una de dos y vecinos completan ambas. | Mezcla de ausencia/ranking en english/none y fragmentación en spanish/expansion. Fallo crítico de base, no del contexto de desarrollo probado. |

Las ocho consultas de desarrollo registran truncamiento de al menos una salida
salvo local-08 en spanish/expansion. La conclusión histórica declara control positivo:
los doce conjuntos requeridos sobreviven redacción y presupuesto cuando se
seleccionan directamente. Eso limita la explicación por truncamiento, pero
no sustituye un diagnóstico de cada ranking ni demuestra calidad de consulta.

## Reserva y fronteras de aceptación

local-09..12 fueron **reserva en la evaluación original**, pero sus resultados
se publicaron en `results.json` y `conclusion.json`; la reserva está consumida
para ese candidato. `context-results.json` sólo contiene desarrollo, así que
no prueba vecinos en reserva. Las cuatro consultas candidatas de conversación
en el archivo de validación tienen nombres parecidos, pero no son qrels humanos
ni se evaluaron allí. No usar las métricas 5/12 como aceptación H25.2 ni como
decisión de reconstrucción de índices. Si una corrección se ajusta con cualquier
resultado reservado ya visto, se necesita reserva nueva antes de adjudicarla.

Separación contractual: `source`/runtime verifica original y busca subcadenas
en cabezas/vistas explícitas; `search`/`query` legado usa `$text` y ranking.
P1 diagnostica sólo el segundo recorrido documental. La utilidad literal DSH
necesita protocolo propio P2/D1 con fuente, revisión, vista y respuesta esperada.

Pendiente de P1: reproducción en Mongo aislado no ejecutada ni requerida para
este inventario; clasificación causal de candidatos ausentes continúa como
hipótesis hasta inspección de ranking/índice en laboratorio autorizado. No se
creó ni sustituyó ningún artefacto histórico.
