# ADR-001: motor de IA local para el análisis — Ollama

Estado: aceptado

Contexto: REQ-2/REQ-9 (`docs/f0-analisis-y-requerimientos.md`) exigen que
el análisis de cada turno lo haga un modelo de IA local en esta primera
iteración. El entorno de desarrollo ya tiene Ollama instalado
(EV-6 de F0: `which ollama` → `/opt/homebrew/bin/ollama`); no hay otro
motor local confirmado disponible.

Decisión: el análisis de turnos (SPEC-002) usa Ollama como motor de
inferencia local en esta primera iteración.

Alternativas descartadas:
  - llama.cpp directo: obliga a gestionar a mano el ciclo de vida del
    modelo (descarga, cuantización, servidor); Ollama ya lo envuelve.
  - Modelo de proveedor externo (Claude, OpenAI, etc.): descartado por
    REQ-9, restricción explícita del humano para esta iteración — no es
    una limitación técnica, es una decisión de alcance.

Consecuencias: Skopos depende de que Ollama esté corriendo localmente y
de un modelo descargado (la elección del modelo concreto se confirma en
implementación, contra el entorno real). Si Ollama no está disponible, el
análisis falla explícitamente (ver caso de timeout en SPEC-002), nunca se
infiere éxito. Migrar a otro motor local o a un proveedor externo exige un
ADR nuevo que sustituya a éste.
