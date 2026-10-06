# Referencias rotas y ADR-019 — ensayo separado en copia

Observación iniciada: 2026-10-06T02:25:02Z. Respaldo lógico del 2026-10-05,
no medición nueva del estado productivo. Operador autorizó resolver referencias
y evaluar ADR-019 manteniendo producción sin cambios. Este documento informa
qué es reparable con evidencia, no declara reparación de originales perdidos.

## Entorno y método

Mongo temporal exclusivo 37035, base skopos_test_repair; restauración del
archivo runs/o1-backup.WPzdQE/skopos.archive.gz, sin --drop, renombrando namespace.
Antes del ensayo se verificaron conteos y hashes BSON completos de las cuatro
colecciones contra el manifiesto del respaldo verificado. Ninguna consulta del
ejecutor se dirige a 27017. Archivos fuente registrados se leen, no se modifican.
Expediente privado: /private/tmp/skopos-refinement.lnsEvi/, evaluate_copy.py,
copy-results.json, lexical-preregistered.json y logs. Ruta temporal, no archivo
permanente de evidencia privada. No se publica contenido ni IDs de conversaciones.

## Referencias: disposición y condición de reparación

17849 turnos: 11657 rangos accesibles, 1175 fuentes ausentes, 197 rangos fuera
de archivo y 4820 orígenes de filas presentes sin verificar su contenido interno.
Muestra determinista de 300 rangos accesibles: 289 hashes verificados, cinco
discordantes, seis excluidos por superar 2 MiB. No es muestra estadística.

Se reparsearon las rutas registradas de los 197 rangos fuera de archivo y las
cinco discordancias de la muestra, con tope de 64 MiB por archivo. Condición
previa a relocalizar en copia: identidad nativa única, textos normalizados
idénticos, mismo hash crudo registrado y verificación positiva del nuevo rango.

Resultado sobre los 202 candidatos:

- 61: identidad encontrada, pero bytes o texto distintos del registro.
- 141: sin identidad nativa única en el parseo actual.
- 0: cumplen la condición de relocalización conservando bytes.

No se cambiaron sellos para hacer pasar la comprobación, no se borraron turnos
y no se fabricaron originales desde texto indexado. Hash BSON final de turnos
igual al respaldo. Al no existir reparación admisible, **no se ejercitó una
reversión de mutaciones**; el chequeo final sólo demuestra ausencia de cambios.
Los 1175 orígenes ausentes no se reconstruyeron ni se buscaron en ubicaciones
ajenas al conjunto de rutas registrado.

Resolución segura pendiente:

1. Aportar backup de originales para cotejar los hashes esperados. Si aparecen
   bytes idénticos, proponer relocalización trazable y ensayarla primero en copia.
2. Para identidades con contenido diferente, reingesta/reanálisis nuevo con
   procedencia y versión propia; nunca llamar al nuevo hash reparación del viejo.
3. Si no existen originales, declarar evidencia no disponible y acordar una
   política de conservación/cuarentena. La pérdida no se soluciona con embeddings.
4. Reparar producción requeriría un alcance nuevo: este encargo la mantiene
   sin cambios. No se ejecutó reanalyze ni se llamó a un LLM sobre este corpus.

## ADR-019: comparación previamente fijada

Tres configuraciones: english, spanish y none. Ocho consultas fijadas antes
de comparar; fixture de cuatro documentos con seis expectativas explícitas
(morfología, tilde, frase, negación y stopword). Copias de analisis (332) y
turnos (17849), sin alterar índices de las colecciones restauradas originales.
Los conteos reales incluyen versiones históricas; no equivalen a salida vigente
del consumidor ni a precisión/recall semánticos. No hay juicios de relevancia
independientes del corpus real: no se adjudica ranking por contar resultados.

| Consulta sobre análisis | english | spanish | none |
|---|---:|---:|---:|
| de | 331 | 0 | 331 |
| analizado | 1 | 27 | 1 |
| reparación | 5 | 7 | 5 |
| reparacion | 5 | 0 | 5 |
| donde vive la llave del proveedor | 316 | 17 | 316 |

En turnos, `de`: 16407 → 0 con spanish; `reparación`: 285 → 627;
`reparacion`: 285 → 18. Son diferencias de coincidencia, no ganancia de calidad
demostrada en cada resultado. Fixture español: cinco de seis expectativas
exactas; falla la variante sin tilde. Inglés/none: cuatro de seis; fallan
morfología y filtrado de stopword. Frase y negación del fixture se conservan.

Conclusión: evidencia favorable al análisis léxico español, pero **no basta
para activar ADR-019 tal como está**. Su expansión propuesta -cion/-ción exige
contrato y tests de sintaxis (frases, negaciones, tokens técnicos), además de
evaluación bilingüe y juicios de relevancia sobre consultas reales separadas
del ajuste. No afirmar que todo el corpus es español por sus títulos: incluye
código, nombres propios y posiblemente otros idiomas, no etiquetados aquí.
Tampoco generalizar ocho palabras a «no pierde nada de lo escrito», ni reducir
todas las limitaciones léxicas a ausencia de palabras compartidas: top-k,
stemming, stopwords y segmentación también influyen.

## Siguiente decisión propuesta

Mantener embeddings diferidos. Primero preparar expansión sintácticamente
segura y corpus de evaluación con respuestas juzgadas por el Operador; comparar
spanish con y sin expansión y con english/none, incluyendo consultas españolas
y técnicas/inglesas. Fijar umbrales antes de medir. Sólo después decidir cambio
productivo, con escritores controlados, respaldo y reconstrucción reversible.
Evaluación O2 ejecutada; aceptación/migración no ejecutadas. Referencias rotas:
diagnóstico refinado completo, reparación pendiente de originales o política.
