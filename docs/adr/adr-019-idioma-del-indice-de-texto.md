# ADR-019: los índices de texto se declaran en español

Estado: **propuesto** — enmienda de ADR-006, pendiente de decisión del
dueño. No sellado: recrear un índice de texto sobre 17,417 turnos es una
operación sobre datos y no se ejecuta por iniciativa del agente.

Contexto: ADR-006 decidió `$text` sobre `tema`+`resumen` y dejó escrito
que la coincidencia es "por palabra, con stemming y stopwords **según el
idioma configurado en Mongo**". Nunca se configuró. `almacenamiento.py`
crea los dos índices de texto sin el parámetro, así que ambos quedaron en
el default de Mongo, `english`, sobre un corpus en español.

La medición del 2026-09-13
(`docs/evidencia/idioma-del-indice-de-texto-2026-09-13.md`) cuantifica el
efecto sobre 332 análisis:

- `de` recupera **331 de 332** documentos; `del` 248; `la` 260. Las
  stopwords españolas son términos buscables porque las que Mongo filtra
  son las inglesas.
- El ruido llega al ranking, no sólo al conteo: `textScore` pondera
  frecuencia y una stopword aparece muchas veces por documento. La
  consulta "donde vive la llave del proveedor" pone en el top-3 dietas de
  eduEMD y gobernanza de EKTEL; con índice español pone en el #1 "Fallo
  de autenticación de la llave ZAI_API_KEY".
- La morfología española no colapsa: `analizado` daba 0 resultados
  mientras `analizar` daba 5, siendo la misma idea.
- `$text` **no pierde nada de lo que está escrito**: 8 de 8 palabras
  probadas con recall exacto. El defecto era el idioma del análisis
  léxico, no la capacidad de recuperar.

Decisión propuesta:

(a) Los dos índices de texto se crean con `default_language="spanish"`:
    `skopos.analisis` (`tema`+`resumen`) y `skopos.turnos`
    (`texto_usuario`+`texto_agente`). Es el parámetro que ADR-006 dejó
    implícito, no una decisión nueva sobre el motor.

(b) Los índices existentes se recrean. `create_index` es idempotente
    **sólo si la especificación coincide**: cambiar `default_language`
    exige `drop_index` + `create_index`, que sobre `skopos.turnos`
    (17,417 documentos) deja la búsqueda sin índice de texto durante la
    reconstrucción. Se hace con `search` y `watch` detenidos, y se
    verifica con un conteo de control antes y después.

(c) Mitigación del defecto medido: el stemmer español falla con términos
    en `-ción` escritos sin tilde (`reparacion` → 0 resultados,
    `reparación` → 4). El CLI expande el término al armar la consulta
    (`-cion` → también `-ción`), con test propio. `$text` une términos
    con OR, así que agregar la variante no puede reducir el recall.

(d) `documento-analisis-mongo` y `documento-turno-mongo` **no cambian**:
    esto es configuración del índice, no del esquema. No hay migración de
    datos ni versión nueva de contrato.

Alternativas descartadas:

- **Adoptar embeddings ahora (hito 11)**: resolvería el ruido por
  accidente —un vecino semántico ignora stopwords— al precio de una
  dependencia nueva, un almacén de vectores y re-indexar 17,417 turnos.
  Sería pagar un modelo para arreglar un parámetro. Y el hito 11 se
  llevaría el crédito de una corrección de una línea, dejando sin
  responder si de verdad hace falta.
- **`default_language: "none"`** (sin stemming ni stopwords): quita el
  ruido de las stopwords españolas sólo si el usuario no las escribe, y
  pierde el colapso de morfología que es la mitad de la ganancia.
- **Filtrar stopwords en el CLI antes de consultar**: arregla la consulta
  pero no el índice; los términos vacíos seguirían indexados, y el
  ranking seguiría ponderando su frecuencia en los documentos.
- **`language_override` por documento**: el corpus es español entero; un
  campo por documento es maquinaria para una variabilidad que no existe.
  Queda disponible si algún día entra corpus en otro idioma.

Consecuencias:

- La condición que ADR-006 puso al hito 11 —"que `$text` resulte
  insuficiente en uso real"— **sigue sin evaluarse**, y por primera vez
  se podrá: el ruido medido hasta hoy venía del idioma, no del motor.
- Lo único que un índice léxico no recupera, y quedó medido: una
  paráfrasis **sin una sola palabra en común** con el documento (la
  consulta "demora del canal hacia el repositorio ajeno" contra
  "Ensayo de medición de latencia Skopos ↔ escrubery" queda en la
  posición #274 de 331 con el índice inglés, y no aparece con el
  español). Ése es el alcance exacto de lo que comprarían los
  embeddings, y la métrica con la que el hito 11 debería reabrirse:
  cuántas consultas reales no comparten ninguna palabra con su objetivo.
- ADR-006 no se sustituye: su decisión (`$text` en vez de igualdad
  exacta) se confirma. Esta enmienda fija el parámetro que dejó abierto.
