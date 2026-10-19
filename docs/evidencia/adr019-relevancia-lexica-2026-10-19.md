# Evaluación de relevancia léxica para decidir ADR-019 — 2026-10-19

T1+T2 del
[plan de evaluación](../planes/activos/evaluacion-relevancia-lexica-2026-10-19.md).
Mide la métrica de reapertura del hito 11 (consultas que no comparten
ninguna palabra con su objetivo) y, complementariamente, si el objetivo
cae en el top-20 de `$text` con redacción natural. **Sólo lectura: ninguna
escritura a Mongo durante la medición.**

## Procedencia y sesgo declarado

Las doce preguntas salen del trabajo real del Operador (respaldo H25.2,
revisión OCR de RS1, cancelación de prime, colisión P-004, ADR-011,
muse-code, ADR-016/018, upgrade AN-KLA, hallazgo del índice, sellos,
launchd) y fueron **redactadas por el agente** a partir de ese trabajo;
el Operador las ratificó en bloque por directiva («adelante», 2026-10-19,
dos veces tras ver la tabla con candidaturas y extractos), y las
candidaturas de objetivo fueron seleccionadas por el agente del corpus
verificado — no hubo adjudicación turno a turno del Operador. Éste es un
sesgo declarado: mismo autor para pregunta y objetivo. La muestra es
n=12, intencionalmente mitad control (mismo vocabulario esperado) y
mitad paráfrasis (otras palabras).

## Corpus y congelación

- El índice estaba rancio (último turno 2026-09-14); se reindexó el mismo
  día: 17,849 → **20,250 turnos** (dedup de Mongo al mando, sin LLM). Sin
  ese refresco, siete objetivos no existían y la evaluación se invalidaba
  en silencio.
- Pares congelados en `adr019-pares-2026-10-19.jsonl` (12 líneas,
  `query` + `target_turn_id`), SHA-256
  `d19640f796a50f3085dee5e2e9cdc06404ee92fbff4f2ef5b16fa5c7c71963a2`.
  Cada `turn_id` verificado existente; unicidad comprobada (20,250
  distintos = total).
- Informe del instrumento: `adr019-relevancia-lexica-2026-10-19.json`.

## Sensibilidad de la lista de stopwords

Con `spanish-builtin-v1` el resultado habría sido **0/12 irrecuperables**
— artefacto: las preguntas «compartían» sólo `cómo`, `fue`, `qué` con sus
objetivos (interrogativos y conjugaciones ausentes de v1). Corregido a
`spanish-builtin-v2` (108 términos, commit `2cedaad`) antes de medir. La
elección de lista mueve el veredicto; queda versionada y reportada.

## Resultado

**Cero solapamiento (irrecuperable para un índice léxico):**

| Variante | Cifra | Cuáles |
|---|---|---|
| todas las palabras | 0/12 | — (el arrastre de stopwords españolas indexadas «recupera» todo) |
| palabras de contenido (v2) | **2/12 (16.7%)** | «¿Cómo recuperamos todo si se pierde la computadora?» y «¿Cómo se comprueba que una conversación citada no fue alterada?» |

Los seis controles comparten contenido genuino: el instrumento no marca
todo por marcar.

**Recall@20 (`$text`, redacción natural, orden `textScore`):**

| Pregunta | Total recuperado | Rango del objetivo |
|---|---|---|
| OCR páginas 22 a 25 | 19,253 | **14** — único en top-20 |
| las otras once | 17,750–19,517 | **>20** |

Cada pregunta natural recupera el **92–96 % del archivo**: las stopwords
españolas no filtradas (índice `default_language: english`) inundan el
ranking y entierran al objetivo incluso cuando comparte palabras fuertes
(p. ej. `respaldo`+`mongo` no bastan para entrar al top-20 entre 19,209
resultados).

## Partición de enfermedades

1. **Arrastre de stopwords** (ranking inservible, 11/12 fuera del
   top-20): lo repara recrear el índice en español (ADR-019).
2. **Sin stemming español** (morfología: `recuperamos` ↔ `recuperación`,
   `pierde` ↔ `pérdida`): la pregunta siete es irrecuperable sólo por
   esto; el Snowball español del índice ADR-019 la puentearía.
3. **Brecha verdadera de vocabulario** (1/12: la pregunta de sellos —
   «comprueba/citada/alterada» ↔ «sello/integridad/verificación»): ningún
   stemmer la salva; territorio de capa semántica (hito 11) o de la capa
   interpretada ya existente (`skopos query`).

## Recomendación (adjudicación pendiente del Operador)

- **ADR-019: sí** — recrear los índices de texto en español ataca las
  enfermedades 1 y 2, que explican 11/12 fuera del top-20 y 1/2 de los
  irrecuperables; sin dependencias nuevas, reversible (recreación de
  índice, no de datos). Operación sobre datos: requiere decisión y plan
  propios del dueño.
- **Embeddings (hito 11): no todavía** — una sola brecha verdadera en
  n=12, y esa pregunta es hoy atendible por la capa interpretada donde hay
  análisis. Reabrir sólo si una muestra mayor o adjudicada turno a turno
  muestra más brechas.
- **Refresco del índice**: decidir periodicidad (el archivo quedó un mes
  rancio sin señal alguna); candidato natural: cabalgar el launchd diario
  existente. Decisión del Operador, frente separado.

## Límites

n=12; preguntas y objetivos del mismo autor con ratificación en bloque;
una sola corrida; el recall@20 mide el ranking vigente tal cual (con
`default_language: english`), no el índice español propuesto; la métrica
de contenido depende de la lista v2 (sensibilidad documentada arriba).
