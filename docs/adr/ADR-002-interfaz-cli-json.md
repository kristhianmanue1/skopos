# ADR-002: interfaz de recuperación — CLI que imprime JSON

Estado: aceptado

Contexto: REQ-4 (`docs/f0-analisis-y-requerimientos.md`) exige que dos
tipos de consumidor — el propio agente conversacional y otro sistema o
agente distinto — puedan recuperar información por tema. Ninguno está
confirmado como Python-nativo en el mismo proceso, y no hay un requisito
que exija un servidor corriendo permanentemente.

Decisión: la recuperación se expone como un comando CLI
(`skopos query <tema>`) que imprime JSON a stdout (contrato completo en
`docs/contratos/f1-contratos.md`).

Alternativas descartadas:
  - API HTTP local (ej. FastAPI): agrega un framework web y un proceso
    persistente desde el primer día, sin un requisito confirmado que lo
    justifique todavía.
  - Función Python importable: más simple aún, pero sólo sirve si el
    consumidor comparte el entorno Python de Skopos; no cubre "otro
    sistema o agente distinto" en el caso general.

Consecuencias: cualquier consumidor invoca Skopos como subproceso y
parsea JSON de stdout — funciona igual para un agente, un script o una
persona. Si más adelante se confirma consumo remoto o de baja latencia
repetida, se sustituye este ADR por uno que agregue una API, reusando el
mismo núcleo de consulta (SPEC-004) sin reescribirlo.
