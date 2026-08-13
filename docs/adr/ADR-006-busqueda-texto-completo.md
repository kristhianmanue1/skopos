# ADR-006: recuperación por tema usa búsqueda de texto completo, no igualdad exacta

Estado: aceptado

Contexto: REQ-4 exige que una consulta por tema recupere "toda la
información relevante... que coincide". La implementación original de
`buscar_por_tema` usaba igualdad exacta de string (`{"tema": tema}`).
Una ronda adversarial (2026-08-13) verificó contra Ollama real que el
modelo genera temas distintos para turnos claramente relacionados (tres
turnos sobre índices de MongoDB produjeron "Índices en MongoDB",
"Optimización de consulta en MongoDB" e "Índices compuestos") — con
igualdad exacta, una consulta por cualquiera de esos temas encuentra sólo
1 de los 3 registros relevantes, incumpliendo el criterio de aceptación
de REQ-4 en el caso normal, no en el borde.

Decisión: `buscar_por_tema` usa `$text` de MongoDB sobre un índice de
texto en `tema`+`resumen`, ordenado por relevancia (`textScore`).
`coleccion_local` crea ese índice (idempotente) junto con el índice único
de `turn_id` (ADR de facto, mismo cambio: ver HIGH de condición de
carrera en la misma ronda).

Alternativas descartadas:
  - Mantener igualdad exacta: falla el criterio de aceptación de REQ-4
    demostrado con datos reales, no es hipotético.
  - Búsqueda semántica con embeddings (`nomic-embed-text` ya está
    disponible en el entorno, ver EV-6 de F0): resolvería mejor los casos
    de sinónimos/reformulación total, pero es una dependencia nueva
    (vector store o índice de similitud), una decisión de mayor alcance
    que "mínimo necesario" no justifica todavía sin evidencia de que
    `$text` sea insuficiente en uso real.
  - Normalizar el `tema` con un paso adicional de canonicalización antes
    de guardar (ej. otra llamada al modelo para mapear a una taxonomía
    fija): agrega latencia y una llamada más a Ollama por turno, sin
    resolver el problema de fondo (sigue siendo coincidencia por
    categoría fija, no por contenido).

Consecuencias: `$text` es coincidencia por palabra (con stemming y
stopwords según el idioma configurado en Mongo), no semántica —
reformulaciones sin palabras en común siguen sin recuperarse. Si eso
resulta insuficiente en uso real, se sustituye este ADR por uno que
adopte embeddings, reutilizando `nomic-embed-text`.
