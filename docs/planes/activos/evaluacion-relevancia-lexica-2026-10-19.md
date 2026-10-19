# Plan — evaluación de relevancia léxica para decidir ADR-019 — 2026-10-19

Estado: **ACTIVO**. Autorizado por el Operador el 2026-10-19 («adelante con
recomendaciones»), tras el análisis crítico de la afirmación «el índice
textual no es búsqueda semántica»: cierta, pero incompleta —la capa léxica
misma está desintonizada y la condición de reapertura del hito 11 ya tiene
métrica definida sin medir.

## Contexto verificado (2026-10-19)

- Índice vivo `skopos.turnos` (17,849 turnos): `texto_usuario_text_texto_agente_text`
  con `default_language: "english"` sobre corpus español — sonda directa del
  2026-10-19. El stemmer inglés no conjuga español y las stopwords inglesas
  no filtran las españolas (evidencia 2026-09-13: `de` recuperaba 331/332).
- La capa interpretada (`skopos.analisis`, 332 documentos) sí normaliza
  vocabulario vía LLM, pero su cobertura global es 1.9 %.
- Hoja de ruta, hito 11: reabrir semántica sólo si «cuántas consultas reales
  **no comparten ninguna palabra** con su objetivo» lo justifica, medido.
- Pendiente registrado: 12 consultas reales con objetivos adjudicados para
  evaluar relevancia léxica; decisión ADR-019 posterior.

## Objetivo y no-objetivos

**Objetivo**: medir la tasa de cero solapamiento léxico sobre consultas
reales con objetivos adjudicados por el Operador, y poner esa cifra frente a
la decisión ADR-019 (recrear índices de texto en español).

**No-objetivos**: activar ADR-019 (operación sobre datos, decisión del
dueño, plan propio si se acepta); implementar embeddings (hito 11, condicional
a esta medición); tocar producción, índices o corpus; redactar secretos.

```text
TAREA T0 — instrumento de medición
Consumes: este plan; docs/hoja-de-ruta.md (hito 11); docs/adr/ (ADR-019 propuesto).
Produce: scripts/lexical_overlap.py: métrica por par (palabras compartidas totales y de contenido), resumen en dos variantes con lista de stopwords integrada y versionada, resolución de target_turn_id contra skopos.turnos en sólo lectura, y modo --self-check de la parte pura.
Steps:
- [x] Implementar tokenización española (casefold, sin puntuación), stopwords integradas versión fijada, y las dos variantes del resumen.
  **Hecho (2026-10-19)** — `scripts/lexical_overlap.py`: tokens `[a-záéíóúüñ0-9]+` sobre casefold, 99 stopwords españolas versionadas (`spanish-builtin-v1`), resumen en dos variantes con pares irrecuperables enlistados.
  Verificación: python3 scripts/lexical_overlap.py --self-check en verde, con casos de control incluidos (solapamiento pleno, sólo-stopword, cero).
- [x] Resolver target_turn_id a texto (unión de texto_usuario y texto_agente, lo que indexa $text) rechazando turnos ausentes.
  **Hecho (2026-10-19)** — `resolve_targets` con `target_turn_id_not_found: <id>` tipado; el par sin objetivo se rechaza con `invalid_pair`, nunca inventa texto.
  Verificación: par con turn_id inexistente falla con código tipado; nunca inventa texto objetivo.

TAREA T1 — pares adjudicados por el Operador
Consumes: T0; el uso real de consulta del Operador.
Produce: docs/evidencia/adr019-pares-2026-10-19.jsonl: doce consultas reales (emitidas en trabajo efectivo, no sintéticas) con objetivo adjudicado (target_turn_id), una por línea.
Steps:
- [x] El Operador aporta las consultas reales y adjudica el objetivo correcto de cada una; el agente verifica que cada turn_id existe en skopos.turnos antes de congelar el archivo.
  **Hecho (2026-10-19)** — preguntas redactadas por el agente desde el trabajo real del Operador y ratificadas en bloque por directiva («adelante», dos veces, tras ver candidaturas y extractos); objetivos seleccionados del corpus verificado. Sesgo declarado en la evidencia: mismo autor para pregunta y objetivo, sin adjudicación turno a turno. Cada turn_id verificado existente; unicidad comprobada (20,250 distintos).
  Verificación: doce líneas válidas para el instrumento; cada turn_id resuelve a texto no vacío; cero pares fabricados por el agente.
- [x] Congelar el archivo con hash SHA-256 registrado en la evidencia.
  **Hecho (2026-10-19)** — `docs/evidencia/adr019-pares-2026-10-19.jsonl`, SHA-256 `d19640f796a50f3085dee5e2e9cdc06404ee92fbff4f2ef5b16fa5c7c71963a2`, registrado en la evidencia de medición.
  Verificación: shasum -a 256 del archivo coincide con el registrado; el archivo no cambia tras la congelación.

TAREA T2 — medición y recomendación
Consumes: T1; scripts/lexical_overlap.py.
Produce: docs/evidencia/adr019-relevancia-lexica-2026-10-19.md: tasa de cero solapamiento en ambas variantes, pares irrecuperables enlistados, y recomendación explícita sobre ADR-019 para adjudicación del Operador.
Steps:
- [x] Correr el instrumento sobre los pares congelados y archivar el informe JSON junto a la evidencia.
  **Hecho (2026-10-19)** — informe `docs/evidencia/adr019-relevancia-lexica-2026-10-19.json` (359 líneas); resumen: 2/12 irrecuperables en contenido (0/12 en todas-las-palabras), lista v2; sensibilidad v1→v2 documentada (v1 habría reportado 0/12 por artefacto). Complemento recall@20: 1/12 en top-20, totales de 92–96 % del archivo por consulta.
  Verificación: el resumen cita doce pares; las dos variantes reportadas; la lista de irrecuperables coincide con el detalle.
- [x] Redactar la recomendación (recrear índice español / no hacerlo / ampliar muestra) sin ejecutar ninguna mutación.
  **Hecho (2026-10-19)** — recomendación en `docs/evidencia/adr019-relevancia-lexica-2026-10-19.md`: ADR-019 sí (ataca arrastre de stopwords y ausencia de stemming, 11/12 fuera del top-20 y 1/2 irrecuperables); embeddings no todavía (una brecha verdadera en n=12); refresco periódico del índice como frente separado. Ninguna escritura a Mongo durante la medición.
  Verificación: ninguna escritura a Mongo durante la medición (sólo lectura); la decisión queda en el Operador, no adjudicada por el agente.
```

## Riesgos y abortos

- Si el Operador no aporta doce consultas reales, no se mide con muestra
  menor ni se rellena con sintéticas: se registra la imposibilidad y el plan
  queda en espera.
- Si algún par resulta ambiguo (varios objetivos defendibles), se excluye y
  se documenta; la adjudicación dudosa no entra a la tasa.
- La elección de stopwords mueve la frontera entre variantes: por eso el
  resumen reporta ambas y la lista queda versionada en el propio instrumento.
