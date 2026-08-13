# ADR-004: escrubery es fuente de referencia opcional, no dependencia dura

Estado: aceptado

Contexto: REQ-10 (`docs/f0-analisis-y-requerimientos.md`) agrega la
posibilidad de enriquecer el análisis de un turno con metadata de
referencia sobre el CLI observado, consultando escrubery
(`github.com/kristhianmanue1/escrubery`, clon local en
`/Users/krisnova/www/aria/escrubery`). Escrubery está en Fase 0 de su
propio desarrollo (ver su README: "Fase 0 en curso"); su disponibilidad y
estabilidad no están garantizadas de la misma forma que el pipeline
crítico de Skopos (REQ-1..4).

Decisión: la consulta a escrubery es un paso opcional y no bloqueante
dentro de SPEC-002 (análisis). Su ausencia, fallo o falta de ficha para el
CLI observado no cambia el estado del turno más allá de omitir el campo
de metadata de referencia — el turno sigue su ciclo normal (detectado →
analizado → guardado) sin ese enriquecimiento.

Alternativas descartadas:
  - Dependencia dura (bloquear el análisis si escrubery no responde):
    acopla la disponibilidad de Skopos a la de otro proyecto en fase 0,
    sin que ningún REQ imprescindible lo exija.
  - Cachear localmente de antemano todas las fichas de escrubery:
    prematuro — no hay evidencia de qué CLIs concretos se necesitarán más
    allá de Codex (único CLI en alcance, REQ-1).

Consecuencias: el campo de metadata de referencia en el documento de
Mongo (`docs/contratos/f1-contratos.md`) es opcional; un análisis sin él
sigue siendo válido y completo respecto a REQ-1..4. Si escrubery madura y
se vuelve una dependencia crítica confirmada, este ADR se sustituye por
uno que la trate como dependencia dura, con su propio manejo de fallos.
