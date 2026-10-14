# Acta de decisiones del Operador — 13 de octubre de 2026

Medio: sesión con el agente Skopos. El Operador aprobó la hoja de
recomendaciones del 2026-10-13 («adelante con recomendaciones»). Decisiones
registradas con su alcance exacto:

1. **`rlmDepth` (plan adaptador prime-agent, T0)**: sólo sesiones padre
   (`rlmDepth: 0`). Los sub-agentes no se indexan; el rechazo vive en la
   ficha como incompatibilidad tipada y puede relajarse después sin
   migración. Desbloquea T1–T4 del plan.
2. **Alcance del contrato multiproyecto (plan multiproyecto, T0)**:
   confirmado **sólo eje proyecto bajo la cuenta vigente** — contrato nuevo
   `source-consumer-access-v0.1` en la superficie del almacén de fuentes; sin
   multiusuario (decisión monousuario 2026-10-06 intacta) y sin tocar la
   pasarela CTIM ni su contrato v0.2. Desbloquea T1–T4 del plan.
3. **Periodicidad de respaldo (propuesta launchd v2)**: aprobada — instalar
   los dos LaunchAgents y el wrapper, con el plan de verificación de 5 pasos.
   La pausa de la automatización de chat Codex durante la validación (paso 3)
   es acción del Operador en su chat; este acta la deja señalada como
   pendiente de su lado. Instalación y evidencia:
   [launchd install](h252-launchd-install-2026-10-13.md).
4. **Piloto de consulta desde agente**: adjudicación **aceptada** — se
   aceptan los resultados de la evaluación del 2026-10-13 (104/108 éxitos,
   0 fallos críticos, 0 violaciones de autoridad; ningún umbral
   preregistrado de utilidad cumplido; promoción bloqueada por la regla de
   ejecución completa). B se conserva como candidato experimental sin
   promoción; C descartada; el piloto se cierra sin serie nueva mientras no
   exista una pregunta real que la justifique.
5. **RS1 (vence 2026-10-19T16:00Z)**: default **sin renovación** — dejar que
   la retención expire con `block_then_explicit_retirement`, salvo consulta
   concreta que necesite el material antes del viernes; en ese caso se admite
   con el expediente de fidelidad ya publicado. El original externo conserva
   sus bytes (verificado el 2026-10-13), así que re-admitir después es barato.
6. **Descarga web del respaldo `…c6d5f71e`**: compromiso del Operador de
   realizarla esta semana y cotejar SHA `87cf1b59…` — único eslabón que
   ningún agente puede firmar.

Los dos planes quedan con T0 resuelto (1 y 2) y en estado ejecutable.
