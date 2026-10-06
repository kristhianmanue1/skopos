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
