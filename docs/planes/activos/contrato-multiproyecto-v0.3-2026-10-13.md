# Plan — contrato multiproyecto para consumidores (v0.3) — 2026-10-13

Estado: **ACTIVO, sin ejecutar**. Autorizado por el Operador el 2026-10-13
(«adelante con propuestas para issues y multiproyecto»). Responde a la crítica
de consumidores (Ágora/AN-KLA): los contratos de acceso vigentes no tienen eje
de proyecto. Nace de una instancia viva (pilotos CTIM/RS1 2026-10-09/10,
corridas Ágora p18/p21, piloto de consulta con tres proyectos en una
instancia), conforme a la regla ADR-010: el contrato generaliza, no precede.

## Contexto verificado (2026-10-13)

- `docs/contratos/ctim-source-access-v0.2-local.md` y el puente MCP v0.2 no
  mencionan proyectos: el acceso se acota por identidad de fuente/material
  (`source_not_allowed`), sin frontera de proyecto.
- El almacén sí es multiproyecto: eje `project_id` desde el hito 13; el piloto
  de consulta ejercitó pilot-cedro/pilot-olmo/pilot-pino con búsquedas acotadas
  y 104/108 éxitos por rúbrica respetando alcance.
- La decisión monousuario del 2026-10-06 (multiusuario diferido) no cubre este
  eje: multiproyecto para consumidores autorizados bajo la misma cuenta es
  alcance contractual, no aislamiento entre usuarios.

## Objetivo y no-objetivos

**Objetivo**: contrato de acceso v0.3 con lista exacta `allowed_projects` por
consumidor y error tipado `project_not_allowed`; fail-closed: proyecto no
listado nunca sirve contenido, ni siquiera metadatos de existencia.

**No-objetivos**: autenticación entre usuarios o multiusuario (decisión del
Operador 2026-10-06, vigente); instancias por proyecto; renombrado de campos
almacenados; promesas de aislamiento más allá del alcance contractual.

```text
TAREA T0 — preflight y decisiones de alcance
Consumes: este plan; AGENTS.md; docs/contratos/ctim-source-access-v0.2-local.md; docs/contratos/source-custody-v0.3-local.md.
Produce: manifiesto de alcance autorizado; confirmación de no-contradicción con la decisión monousuario.
Steps:
- [ ] Revalidar premisas contra código: ubicación real del loader de política de acceso y del path de errores tipados.
  Verificación: archivo y línea exactos citados en el manifiesto; sin suposiciones.
- [ ] Confirmar con el Operador el alcance: sólo eje proyecto bajo la cuenta vigente, sin multiusuario.
  Verificación: respuesta explícita registrada en el manifiesto; si no llega, no iniciar T1.

TAREA T1 — contrato documental v0.3
Consumes: T0; docs/contratos/ctim-source-access-v0.2-local.md; docs/propuestas/ctim-mcp-consumer-bridge-v0.2.md.
Produce: se crea docs/contratos/ctim-source-access-v0.3-local.md con allowed_projects, semántica del error tipado y límites.
Steps:
- [ ] Redactar el contrato: campo allowed_projects (lista exacta), rechazo project_not_allowed, interacción con allowed_sources/materials y compatibilidad v0.2.
  Verificación: ronda de lectura propia; cada afirmación anclada a la instancia viva de los pilotos; cero promesas de aislamiento multiusuario.

TAREA T2 — implementación acotada con pruebas
Consumes: T1; src/skopos/source_cli.py; src/skopos/runtime_store.py; src/skopos/runtime_views.py.
Produce: loader extendido con allowed_projects y error tipado; suite en verde con casos nuevos.
Steps:
- [ ] Extender la política y el rechazo tipado en el punto que T0 localizó; sin tocar campos almacenados.
  Verificación: pruebas unitarias nuevas: proyecto listado sirve; no listado rechaza project_not_allowed; política sin allowed_projects se rechaza por fail-closed.
- [ ] Correr la suite completa y los gates.
  Verificación: python3 -m unittest discover -s tests en verde; check_sizes y check_plans en verde.

TAREA T3 — ensayo de dos proyectos
Consumes: T2; instancia de laboratorio del piloto (corpus pilot-cedro/pilot-olmo).
Produce: evidencia con recibo: proyecto permitido sirve, proyecto ajeno rechazado.
Steps:
- [ ] Ejecutar el ensayo espejo del patrón RS1 (identidad ajena → source_not_allowed): consumidor con allowed_projects=[pilot-cedro] consulta cedro (sirve) y olmo (project_not_allowed).
  Verificación: recibos de ambas llamadas archivados; ninguna fuga de contenido del proyecto ajeno.

TAREA T4 — ronda adversarial y publicación
Consumes: T3; docs/rondas/.
Produce: ronda adversarial documentada; correcciones aplicadas; commit y push reportados.
Steps:
- [ ] Ronda adversarial con revisor sin contexto de autoría; corregir lo que refute.
  Verificación: tabla de hallazgos con veredicto; propuesta/contrato corregidos antes de publicar.
- [ ] Publicar con suite y gates en verde; reportar el push.
  Verificación: git ls-remote coincide con main local; árbol limpio.
```

## Riesgos y abortos

- Si T0 no localiza un único punto de aplicación (política dispersa), abortar y
  proponer consolidación previa en vez de parches múltiples.
- Si el ensayo T3 filtra contenido del proyecto ajeno, BLOCKER: el contrato no
  se publica y se registra el fallo.
