# ADR-019 — corrección acotada de la regresión de tilde

Base: main 8da948f. Rama: codex/adr019-accent-expansion.
Autoridad: Operador pidió analizar pendientes/reparación y resolver regresión
de tilde. Código y pruebas autorizados; no reconstrucción productiva ni merge
de esta rama por inferencia. Producción conserva sus índices y datos.

## Alcance implementado

query/search aceptan --expand-accents; Python usa expand_accents=True.
Default false, sin alteración del comportamiento existente. Helper puro
text_query.expand_accents, sin archivos/red/modelo. No instala dependencias.
Expande reparación escrita como reparacion, validacion, etc. únicamente cuando
son tokens simples ASCII terminados en cion; conserva mayúsculas del sufijo.
No es diccionario ni garantía para todas las palabras/idiomas. Opt-in puede
modificar ranking y agregar coincidencias; el Operador elige usarlo.

| Entrada | Consulta efectiva con opción |
|---|---|
| reparacion | reparacion reparación |
| índice -reparacion | índice -reparacion -reparación |
| "reparacion exacta" | Sin cambios: frase exacta preservada |
| reparacion.py /x/reparacion x_reparacion | Sin cambios: tokens técnicos |

Las consultas con escapes o comillas desbalanceadas se conservan completas;
no se intenta reinterpretar sintaxis ambigua. Una negación expandida excluye
ambas variantes, no introduce una coincidencia positiva accidental. No se
escribe texto normalizado en documentos ni se alteran sellos/offsets.

Mongo documenta stopwords/stemming y semántica de frases/negaciones. La
insensibilidad a diacríticos por defecto no elimina la diferencia observada
de raíces españolas. Referencia primaria consultada:
https://www.mongodb.com/docs/manual/reference/operator/query/text/

## Verificación y autorrevisión

Fixtures nuevos en índice español real: reparacion sin opción sólo recupera
el documento sin tilde; con opción recupera también el acentuado. Negación
excluye ambas formas, frase acentuada recupera su objetivo, frase sin tilde
conserva el resultado nativo. Control inglés worker permanece; sólo negaciones
no inventan resultados. Consumidor query no resucita análisis superseded y
search mantiene límite/conteo. Tests de CLI comprueban opt-in/default sin DB.

Autorrevisión (misma instancia): no afirmar corrección de todas las tildes,
no alterar frases con OR, no perder negaciones, no tocar identificadores ni
activar ADR-019 completo. La opción puede aumentar coincidencias; hace falta
corpus de relevancia independiente antes de adjudicar mejora de ranking.
Primera sonda sin harness omitió integración por conexión no disponible; no
se contó como validación. Ensayo dirigido posterior en Mongo temporal: OK.

Suite final sobre el código terminado: 365 tests, 69.042 s, OK, sin skips,
mediante scripts/run_isolated_tests.py y réplica temporal exclusiva en 37027.
Log local no publicado: /private/tmp/skopos-accents.5EHdcy/final-tests.log.
Gates de tamaños (199 archivos) y planes (1 plan), y git diff --check: OK.

Medición adicional, sólo lectura en copias españolas del respaldo (puerto
37035): reparacion pasa de 0 a 7 coincidencias en analisis y de 18 a 635 en
turnos. La consulta acentuada sola daba 7 y 627: la unión conserva además
coincidencias que se perderían sustituyendo el término. No son juicios de
relevancia ni conteos de versiones vigentes del consumidor. No cambió ningún
índice/documento de esas copias. En frases sin tilde persiste el comportamiento
nativo: corregirlas exige otro contrato, no insertar OR dentro de las comillas.
Autorrevisión añadió protección de comillas adyacentes y restringió el patrón
a ASCII real (IGNORECASE solo admite caracteres Unicode adicionales).

## Reparación y pendientes

La evidencia previa en referencias-adr019-copia-2026-10-05.md sigue siendo la
última comprobación de corpus; no se presenta como auditoría nueva. 202
candidatos sin relocalización de bytes idénticos; 1175 fuentes ausentes.
Se pidió ubicación de backups de originales. No se puede reconstruir el hash
original desde texto indexado ni usar el respaldo lógico Mongo como sustituto.

Prioridad: aportar originales y cotejar hashes; alternativamente decidir
conservación de evidencia no disponible y reingesta con procedencia nueva.
No borrar/quarantinar ni reanalizar corpus por iniciativa del agente.
Después: validar relevancia léxica, decidir reconstrucción ADR-019, elegir
export real del segundo origen. Embeddings siguen diferidos. AN-KLA rev11
permanece histórica respecto de estos incrementos; no se escribió memoria.

## Continuación autorizada — 2026-10-05, observaciones UTC del 6

El Operador autorizó los cuatro pasos: merge, búsqueda de originales,
evaluación ADR-019 y segundo origen; también actualización de AN-KLA.
La autorización no aporta los originales ni identifica un runtime/export.
Revalidación previa al merge: 365 tests OK sin skips, 86.180 s, con
scripts/run_isolated_tests.py y Mongo temporal exclusivo. Log tests.log en
/private/tmp/skopos-four.0lVFuY. Cambios posteriores sólo documentales.

Nueva sonda sintética bilingüe sobre Mongo temporal exclusivo 37027:
seis documentos y ocho consultas con objetivos fijados antes de ejecutar.
No usa conversaciones privadas ni juicios humanos del corpus real.
Documentos: a=`índice reparación exacta`, b=`índice reparacion pendiente`,
c=`índice sin cambios`, d=`analizar documentos`, e=`worker running code`,
f=`la llave de proveedor`. Buscar text, ordenar textScore descendente con
desempate _id ascendente, top 3; comparar conjuntos contra objetivos.

| Consulta | Objetivo | english | none | spanish | spanish + expansión |
|---|---|---|---|---|---|
| reparacion | a,b | a,b | a,b | b | a,b |
| reparación | a,b | a,b | a,b | a | a |
| analizado | d | vacío | vacío | d | d |
| worker | e | e | e | e | e |
| run | e | e | vacío | vacío | vacío |
| "reparación exacta" | a | a | a | a | a |
| índice -reparacion | c | c | c | c,a | c |
| de | vacío | f | f | vacío | vacío |

Conjunto exacto: 6/8, 5/8, 4/8 y 6/8 respectivamente. No es una clasificación
general de motores: la selección es pequeña, sintética y del propio autor.
Autorrevisión corrigió el control de stopword: la primera versión contenía
del y no de, por lo que su ausencia no demostraba filtrado. Se repitió con de
presente: english/none recuperan f y español no, control positivo pertinente.
Artefactos locales: /private/tmp/skopos-four.0lVFuY/evaluate.py y relevance.jsonl.

Conclusión: no activar el índice español todavía. La expansión sólo corrige
sin tilde → con tilde; no la dirección inversa. El stemming inglés run/running
se pierde con español. Ninguna variante supera todas las expectativas.
La corrección optativa sí conserva su contrato acotado y default sin cambios.

Evaluación real pendiente: el Operador debe identificar consultas de trabajo
y objetivos relevantes antes de ver rankings (español, inglés/técnico,
negaciones, frases y sin resultados esperados). Comparar las cuatro variantes
en copia, sólo versiones vigentes, registrar objetivos recuperados/top 20 y
primer objetivo en ranking. Propuesta de gate: cero pérdidas de objetivos
críticos respecto del índice actual; discrepancias no críticas adjudicadas
explícitamente, sin promover el promedio sintético a aceptación productiva.

Búsqueda acotada de nombres en Downloads no identificó un respaldo inequívoco
de conversaciones; no se abrieron archivos comprimidos ajenos ni se concluye
ausencia global. El respaldo Mongo conocido no custodia fuentes externas.
La reparación sigue bloqueada por ruta de originales o decisión de retención;
no hubo reingesta, borrado, cuarentena ni sustitución de hashes históricos.

## Recomendaciones de continuación — cierre JSON

El Operador declaró después que no hay respaldo disponible. Conservar los
registros/hashes históricos sin falsear recuperación. La reunión JSON ASR es
fuente nueva, no restauración de esas conversaciones. No borrar ni poner en
cuarentena el corpus. No se ejecutó reanálisis.

Para ADR-019 recomiendo 12 consultas reales fijadas antes de ver resultados:
cuatro españolas (incluidas flexión y tilde), cuatro técnicas/inglesas y cuatro
de frase, negación, ausencia esperada y paráfrasis. El Operador identifica
objetivos por referencia; el agente puede preparar candidatos, pero sus
juicios no sustituyen la aceptación humana. Comparar english/none/spanish y
spanish+expansión sobre copia y versiones vigentes: recall de objetivos en
top20, posición del primero, falsos positivos revisados y fallos de integridad.
Separar ajuste de evaluación reservando al menos cuatro consultas sin usar
para afinar. Gate propuesto: cero pérdida de objetivos críticos, sin regresión
de negación/frase/integridad; restantes diferencias adjudicadas explícitamente.
No reconstruir índices hasta cumplir ese gate; embeddings permanecen diferidos.

Operación productiva: recomiendo un replica set local dedicado para v3 antes
que convertir el Mongo standalone del corpus legado durante este incremento.
Es propuesta, no servicio creado: evaluar coste operativo, backup/restauración,
permisos y autenticación antes de decidir. Un nodo habilita transacciones, no
alta disponibilidad. Mantener v2 sin migraciones y entradas manuales optativas.
Custodia recomendada: copia inmutable gobernada del original con hash y recibo,
respaldo probado en otro soporte y lectores explícitos. Requiere contrato propio;
actualmente las referencias externas pueden quedar indisponibles. Definir con
el Operador plazo de retención por tipo de fuente y borrado verificable; no
elegir retención indefinida ni borrar pilotos por conveniencia técnica.
