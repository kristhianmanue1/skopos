# AGENTS.md — instrucciones para agentes que trabajan en Skopos

**Empieza por `docs/guia-rapida.md`** (5 minutos) si es tu primera vez
aquí. Luego `docs/hoja-de-ruta.md` para saber qué ya está hecho y qué
falta. Este proyecto se construye siguiendo el método de
[Skevi](https://github.com/kristhianmanue1/Skevi) (fases F0→F3). Antes de
tocar código, lee `docs/f0-analisis-y-requerimientos.md`, `docs/adr/`,
`docs/specs/f1-specs.md` y `docs/contratos/f1-contratos.md` — las
decisiones de diseño ya están tomadas ahí; no las reinventes ni las
contradigas sin registrar un ADR nuevo que sustituya al anterior.

## Comandos

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e .   # build
python3 -m skopos                                                        # ayuda + comandos disponibles
python3 -m skopos query "<tema>"                                         # SPEC-004
python3 -m skopos watch [--backfill]                                               # SPEC-005
python3 -m skopos reanalyze <turn_id> [--solo-redaccion]                 # SPEC-003 v2
python3 -m skopos analyze --help                                         # ADR-017
python3 -m skopos index --help                                           # P-004
python3 -m skopos search --help                                          # ADR-009
python3 -m unittest discover -s tests                                    # test
```

La operación con datos requiere MongoDB local. El análisis requiere el
proveedor configurado: Ollama con `qwen3:8b` por defecto, o el autorizado
según ADR-014. `index` y `search` no necesitan un LLM. La ayuda no requiere
servicios activos. Ver `README.md` para arranque y próximos pasos.

## Convenciones

- Python 3.9+, `unittest` de la biblioteca estándar para tests (sin
  pytest ni otro runner, para no declarar una dependencia nueva sin
  necesidad).
- **Idiomas (ADR-018)**: identificadores estructurales nuevos en inglés,
  incluidos módulos, funciones, variables, comandos, flags y claves.
  Comunicación humana, producto, documentación y comentarios/docstrings:
  español por defecto, elegido en esta sesión; el humano puede escoger otro
  idioma para la conversación sin cambiar los artefactos persistentes.
  Contratos externos, campos almacenados y nombres legados se conservan;
  sus migraciones requieren decisión y verificación propias. La fuente
  completa es `docs/adr/adr-018-codigo-ingles-comunicacion-humana.md`.
- Un módulo por frontera de F1 (`captura.py` ↔ SPEC-001, etc.) — no
  mezcles responsabilidades de specs distintas en un archivo.
- Cero placeholders: no crees un módulo para una SPEC hasta implementarla
  de verdad. Un archivo vacío con `TODO` no es cascarón, es deuda.
- Cero dependencias especulativas: antes de agregar una a `pyproject.toml`
  confirma que está instalada en el entorno real (versión incluida) y que
  responde a un REQ concreto.
- Instalar una dependencia nueva requiere autorización explícita del
  humano — es una operación de autoridad separada (F3 §7 de la guía).

## Prohibido sin autorización explícita, una vez por operación

Merge a rama protegida, instalar dependencias nuevas, borrar o mover
archivos de `docs/` que registran decisiones ya cerradas (F0/F1).
Editar no implica commit.

**`git push` y `commit`: autorizados de forma permanente** por el dueño
el 2026-08-28 — no se pide confirmación cada vez. La contrapartida es
que la sección "Verificación antes de declarar terminado" deja de ser
un trámite: nada se empuja sin la suite en verde y el diff leído, y todo
push se reporta. El resto de esta lista sigue exigiendo autorización
**cada vez**.

## Memoria entre sesiones (AN-KLA)

El estado al cierre de cada sesión vive en `.an-kla/` (gitignorado), como
cadena de supersedes; el registro vigente y su revisión están en
`docs/hoja-de-ruta.md`. Para tomar contexto al arrancar:

```bash
.venv/bin/an-kla retrieve --query "<tema>" --budget 8000
```

**Pide 8000, no 2500.** El presupuesto lo elige quien consulta, no el
almacén, y un registro que no cabe **se excluye entero y en silencio** —
en `retrieve` es todo o nada por registro, no se sirve resumido. Pedir
poco no devuelve una versión corta: devuelve nada, y parece memoria
vacía. El cierre del 2026-09-13 cuesta 5,643 B; con 2500 no aparece, y
con 6000 entra él pero se cae por presupuesto el registro acompañante
del mismo día. La cifra sube cuando sube el registro: compruébala con
`used_bytes` y `excluded_summary.budget` de la respuesta, no de memoria.

No es que los registros hayan engordado por descuido: la representación
la gobierna la **autoridad**, no el autor. Una escritura con recibo
`attest` verificado (`tool_observed`) habilita `full`; una autoridad
derivada queda topada en `summary` por el propio motor. El detalle que
un registro se gana depende de la evidencia que trae.

Escribir requiere `plan-write` + `commit-write-plan`. Dos trampas que ya
costaron tiempo: el recibo de `attest` va como evidencia
`kind: attestation_receipt`, que **sólo existe en `write-authority-v2`**
(con v1 falla siempre con `cli_privileged_authority_unresolved`); y
`proposal_sha256` es el digest **canónico** del JSON
(`an_kla.write_policy.digest_json`), no el sha256 de los bytes del
archivo.

## Límites de tamaño

Heredados de Skevi (800 líneas por archivo de texto, 200 para este
archivo, 300 para `README.md`) y comprobados por el **gate de Skevi**
(ADR-015): `python3 scripts/check_sizes.py` — verdes o no se declara
terminado. Config del proyecto en `skevi-gate.json`; exención nueva se
escribe ahí, no en la costumbre.

## Verificación antes de declarar terminado

1. `python3 -m unittest discover -s tests` en verde.
2. `python3 scripts/check_sizes.py && python3 scripts/check_plans.py`
   en verde (gate de Skevi, ADR-015).
3. Diff leído completo, sin cambios fuera del alcance de la tarea.
4. Si el cambio toca specs/contratos (`docs/`), la implementación y los
   tests quedan consistentes con lo que esos documentos prometen.
5. Identificadores nuevos y comunicación revisados contra ADR-018;
   excepciones con contrato o razón. El gate no detecta idiomas.
