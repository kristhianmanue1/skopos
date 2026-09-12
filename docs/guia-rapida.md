# Guía rápida — arrancar contexto en 5 minutos

> Para un agente (o persona) que nunca vio este proyecto. Si tienes más
> tiempo, lee los documentos completos que se enlazan abajo — esto es el
> resumen que evita releer todo el historial de commits.

## Qué es Skopos, en una frase

Captura turnos de Codex, Claude Code, Cline, Kimi Code y OpenCode;
los indexa en MongoDB y permite analizarlos con un LLM (Ollama local por
defecto, multi-proveedor vía ADR-014). `search` consulta el índice de
turnos: devuelve texto indexado, redactado y acotado, sin releer el origen
ni verificar su sello. `query` consulta análisis y comprueba longitud y
sello del fragmento cuando existe; admite legado sin sello marcado
`sellado:false`. Ver la limitación histórica P-007.

## Estado ahora mismo

Implementado en el checkout verificado el 2026-09-12: parsers multi-CLI,
índice, vigilancia incremental y `analyze` sobre turnos ya indexados sin
análisis previo. Esto no certifica el estado de los servicios ni la
finalización de una corrida en vivo. P-007 registra offsets históricos
irrecuperables, sin reparación aprobada. Ver `docs/hoja-de-ruta.md`.

## Orden de lectura si vas a tocar código

1. `README.md` — comandos reales, decisiones de cascarón, pendientes.
2. `AGENTS.md` — convenciones, qué está prohibido sin autorización.
3. `docs/hoja-de-ruta.md` — qué ya está hecho, qué falta.
4. `docs/f0-analisis-y-requerimientos.md` — por qué existe cada REQ.
5. `docs/adr/` — decisiones con alternativas descartadas.
6. `docs/specs/f1-specs.md` + `docs/contratos/f1-contratos.md` — qué
   promete cada componente, exactamente.
7. `docs/f1-maquina-estados.md` — ciclo de vida de un turno.

No asumas el contenido de un documento que no leíste — si vas a tocar
`analisis.py`, lee SPEC-002 y el CONTRATO relacionado primero.

## Mapa de módulos → qué implementan

| Módulo | Spec | Qué hace |
|---|---|---|
| `src/skopos/captura.py` | SPEC-001 | Adaptador de rollouts Codex |
| `src/skopos/parseo.py` | SPEC-006 | Despacha los cinco adaptadores; OpenCode usa filas SQLite |
| `src/skopos/indexador.py` | P-004 | `index`: guarda turnos sin llamar al modelo |
| `src/skopos/busqueda.py` | ADR-009 | `search`: consulta turnos indexados |
| `src/skopos/analizador.py` | ADR-017 | `analyze`: primer análisis de turnos ya indexados |
| `src/skopos/analisis.py` | SPEC-002 | Llama al proveedor de análisis (Ollama por defecto; multi-proveedor, ADR-014) |
| `src/skopos/almacenamiento.py` | SPEC-003 | Guarda/busca en MongoDB local |
| `src/skopos/orquestador.py` | — (conecta 001→002→003) | Máquina de estados de un turno |
| `src/skopos/cli.py` | SPEC-004 | `skopos query <tema>` |
| `src/skopos/vigilante.py` | SPEC-005 | `skopos watch`, ciclo de polling |
| `src/skopos/__main__.py` | — | Dispatcher de comandos |

## Arrancar el entorno

```bash
brew services start mongodb/brew/mongodb-community   # si no está corriendo
ollama list                                            # confirma qwen3:8b
cd /Users/krisnova/www/aria/skopos
source .venv/bin/activate
python3 -m unittest discover -s tests   # el runner informa conteos y skips
python3 scripts/check_sizes.py && python3 scripts/check_plans.py   # gate de Skevi (ADR-015)
python3 -m skopos                        # ayuda + comandos
```

## Idioma y compatibilidad

ADR-018 fija inglés para identificadores nuevos y español predeterminado
para comunicación, producto y comentarios. La preferencia humana puede
cambiar el idioma de la respuesta sin migrar código o artefactos. Los
comandos `reanalyze`, `index` y `search` conservan alias españoles;
flags legados como `--solo-redaccion` siguen escritos así.

## Las tres reglas que más importan de AGENTS.md

- Instalar una dependencia nueva requiere autorización explícita, cada vez.
- Cero dependencias especulativas: confirma disponibilidad real antes de declarar.
- Un módulo por frontera de SPEC — no mezcles responsabilidades.

## Si algo en el código contradice un documento de `docs/`

El documento gana hasta que alguien registre un ADR nuevo que lo
sustituya (o corrija el documento con evidencia, como pasó en la ronda
del 2026-08-13 con dos contratos que prometían algo nunca implementado).
Nunca se asume que el código tiene razón sólo por existir.
