# Hoja de ruta

> Hitos reales, con commit de cierre. No es un plan a futuro especulativo:
> los primeros siete ya pasaron y quedan como registro; de ahí en
> adelante son próximos pasos, no promesas de fecha.

| Hito | Qué entrega | Estado | Commit |
|---|---|---|---|
| 0 | F0 — análisis, requisitos, evidencia | Cerrado | `7f032b7` |
| 1 | F1 — specs, ADR, contratos, máquina de estados | Cerrado | `40812c5` |
| 1.1 | REQ-10 — escrubery como fuente opcional | Cerrado | `797aaf1` |
| 2 | F2 — cascarón (captura, sin dependencias nuevas) | Cerrado | `8c14455` |
| 3 | Análisis (Ollama) + almacenamiento (Mongo) | Cerrado | `cdd5367` |
| 4 | Orquestador + `skopos query` (pipeline completo) | Cerrado | `647412d` |
| 5 | Vigilante en vivo (`skopos watch`) | Cerrado | `896959a` |
| 6 | Metadata vital: `cli`, `modelo_analisis`, `ocurrido_en` | Cerrado | `863e2ee` |
| 6.1 | Ayuda de comandos (`--help`) + próximos pasos por escrito | Cerrado | `7fa01f2` |
| 7 | Ronda adversarial de arquitectura + 7 correcciones | Cerrado | `ab9f51b` |
| 8 | Política de arranque del vigilante (backfill opt-in vs "desde ahora") | Pendiente | — |
| 9 | Herramienta de lectura por sesión/fecha/rango (`skopos read`) | Pendiente | — |
| 10 | Integración con escrubery probada contra el repo real | Pendiente | — |
| 11 | Búsqueda semántica (embeddings) — condicional a que `$text` (ADR-006) resulte insuficiente en uso real | Futuro, no decidido | — |
| 12 | Soporte multi-CLI (más allá de Codex) — explícitamente fuera de alcance hasta que el Hito 8 funcione de punta a punta | Futuro, no decidido | — |

## Criterio de cierre por hito

Igual que en F3 de Skevi: un hito no se cierra por declaración, se cierra
con evidencia — tests en verde, comando real ejecutado, o documento
actualizado. Los hitos 0-7 tienen commit porque ya pasaron esa barra.

## Detalle de los pendientes (8-10)

Ver `README.md` § "Próximos pasos" para el detalle de cada uno — esta
tabla es el mapa, esa sección es la letra chica. No se duplica aquí para
no tener dos lugares que puedan desincronizarse.
