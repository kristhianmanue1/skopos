# Guía rápida — arrancar contexto en 5 minutos

> Para un agente (o persona) que nunca vio este proyecto. Si tienes más
> tiempo, lee los documentos completos que se enlazan abajo — esto es el
> resumen que evita releer todo el historial de commits.

## Qué es Skopos, en una frase

Observa turnos de un CLI de IA (Codex), los analiza con un modelo local
(Ollama) y los guarda recuperables por tema en MongoDB local, con acceso
al fragmento completo de origen.

## Estado ahora mismo

Pipeline completo funcionando de punta a punta con datos reales, después
de una ronda adversarial de arquitectura que corrigió 7 hallazgos reales
(3 BLOCKER, 4 HIGH) el 2026-08-13. Ver `docs/hoja-de-ruta.md` para el
mapa completo de hitos.

## Orden de lectura si vas a tocar código

1. `README.md` — comandos reales, decisiones de cascarón, pendientes.
2. `AGENTS.md` — convenciones, qué está prohibido sin autorización.
3. `docs/hoja-de-ruta.md` — qué ya está hecho, qué falta.
4. `docs/f0-analisis-y-requerimientos.md` — por qué existe cada REQ.
5. `docs/adr/` (6 archivos) — decisiones con alternativas descartadas.
6. `docs/specs/f1-specs.md` + `docs/contratos/f1-contratos.md` — qué
   promete cada componente, exactamente.
7. `docs/f1-maquina-estados.md` — ciclo de vida de un turno.

No asumas el contenido de un documento que no leíste — si vas a tocar
`analisis.py`, lee SPEC-002 y el CONTRATO relacionado primero.

## Mapa de módulos → qué implementan

| Módulo | Spec | Qué hace |
|---|---|---|
| `src/skopos/captura.py` | SPEC-001 | Lee un rollout de Codex, extrae turnos con texto real |
| `src/skopos/analisis.py` | SPEC-002 | Llama a Ollama, produce tema/resumen/entidades |
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
python3 -m unittest discover -s tests   # 53 tests, ~5s si Mongo/Ollama están arriba
python3 -m skopos                        # ayuda + comandos
```

## Las tres reglas que más importan de AGENTS.md

- Instalar una dependencia nueva requiere autorización explícita, cada vez.
- Cero dependencias especulativas: confirma disponibilidad real antes de declarar.
- Un módulo por frontera de SPEC — no mezcles responsabilidades.

## Si algo en el código contradice un documento de `docs/`

El documento gana hasta que alguien registre un ADR nuevo que lo
sustituya (o corrija el documento con evidencia, como pasó en la ronda
del 2026-08-13 con dos contratos que prometían algo nunca implementado).
Nunca se asume que el código tiene razón sólo por existir.
