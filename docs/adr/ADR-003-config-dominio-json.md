# ADR-003: configuración de dominio — archivo JSON

Estado: aceptado

Contexto: REQ-5 (`docs/f0-analisis-y-requerimientos.md`) pide que el
análisis sea configurable por dominio (ej. arquitectura de software y
programación) para mejorar precisión, sin bloquear el flujo de extremo a
extremo — es un requisito deseable, no imprescindible.

Decisión: la configuración de dominio vive en un archivo JSON (ruta
configurable, por defecto algo como `skopos.config.json`) con al menos un
campo `domain` y datos asociados (palabras clave, instrucción adicional
para el modelo de análisis).

Alternativas descartadas:
  - Variable de entorno: no escala si el dominio necesita más que un
    nombre (palabras clave, prompt adicional).
  - YAML: agrega PyYAML como dependencia nueva sin que ningún REQ lo
    exija; `json` ya es parte de la biblioteca estándar de Python.

Consecuencias: el esquema del archivo de configuración es parte del
contrato de SPEC-002 y debe versionarse si cambia de forma incompatible.
Sin archivo de configuración, el análisis corre sin dominio declarado
(comportamiento por defecto, REQ-5 sigue siendo deseable, no bloqueante).
