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
python3 -m skopos reanalizar <turn_id> [--solo-redaccion]                # SPEC-003 v2
python3 -m unittest discover -s tests                                    # test
```

Requiere en el entorno: MongoDB local corriendo (`brew services start
mongodb/brew/mongodb-community`) y Ollama con `qwen3:8b` descargado
(`ollama pull qwen3:8b`). Ver `README.md` "Próximos pasos" para lo que
falta y por qué.

## Convenciones

- Español, Python 3.9+, `unittest` de la biblioteca estándar para tests
  (sin pytest ni otro runner, para no declarar una dependencia nueva sin
  necesidad).
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

`git push`, merge a rama protegida, instalar dependencias nuevas, borrar
o mover archivos de `docs/` que registran decisiones ya cerradas (F0/F1).
Editar no implica commit; commit no implica push.

## Límites de tamaño

Por declaración (Skevi no está vendorizado en este repo, ver README
"Decisiones de cascarón"): 800 líneas por archivo de texto, 200 para este
archivo, 300 para `README.md`. Sin gate automatizado corriendo todavía.

## Verificación antes de declarar terminado

1. `python3 -m unittest discover -s tests` en verde.
2. Diff leído completo, sin cambios fuera del alcance de la tarea.
3. Si el cambio toca specs/contratos (`docs/`), la implementación y los
   tests quedan consistentes con lo que esos documentos prometen.
