# Ronda 11 — correcciones de Pinax sobre ADR-010 + SPEC-006 (2026-08-20)

**Origen:** revisión de Pinax contra `457d827` (canal del dueño).
Siete correcciones obligatorias; todas aplicadas. Sin commit (requiere
autorización nueva del dueño); sin push bajo ninguna circunstancia sin
autorización separada.

## Pasada 3 — fix-and-retry puntual (11c, misma fecha)

Pinax reprodujo que la regla genérica "tipo estructural desconocido
recurrente ≥N" (añadida en 11b) es **inválida**. Reproducción sobre los
616 rollouts (verificada independientemente por este agente, números
idénticos):

- Eventos de tipos no declarados por la ficha en rollouts perfectamente
  parseables por parser-codex v1: `world_state` **3,540** eventos,
  `compacted` **1,016**, `inter_agent_communication_metadata` **1,256**.
- **84/616 archivos** tienen ≥10 ocurrencias de al menos uno — N=10
  habría rechazado 84 rollouts actuales y compatibles.

Correcciones aplicadas:

| # | Corrección (11c) | Destino |
|---|---|---|
| 1 | Eliminar el umbral N y toda afirmación de que frecuencia implica incompatibilidad | ADR-010 §1 regla 4 reescrita; motivación con la reproducción citada |
| 2 | Eventos desconocidos/aditivos: ignorados para extracción, contabilizados explícitamente | Nueva cláusula en §1 + campo `eventos_no_reconocidos` en `ResultadoParseo` (§3) y SPEC-006 Salidas; son señal de evolución aditiva — revisar ficha es acto deliberado, no umbral automático |
| 3 | `version_no_soportada` exige predicado positivo y versionado de la ficha | Regla 4 enumera los tres válidos: marcador explícito incompatible / firma conocida mutuamente excluyente / violación de estructura obligatoria reconocida |
| 4 | Casos nuevos en SPEC | "Evento aditivo repetido conserva `ok`" (ejemplificado con world_state/compacted) y "estructura obligatoria incompatible produce `version_no_soportada`" |

Estado tras 11c: ADR-010 **propuesto**; sin commit ni push (esperando
autorización). `git diff --check` limpio. Suite (convención de reporte):
**102 descubiertos, OK, 0 saltados** en mi entorno (Mongo/Ollama
arriba); corrida independiente de Pinax del mismo día: 102
descubiertos, OK, 54 saltados.

## Pasada 2 — fix-and-retry documental (11b, misma fecha)

Pinax resolvió **FIX-AND-RETRY** sobre la pasada 1. Cuatro correcciones
nuevas, todas aplicadas:

| # | Corrección (11b) | Destino |
|---|---|---|
| 1 | Preservar `path.stem` como `session_id` de parser-codex/v1 (compatibilidad con documentos existentes); no cambiar a `payload.session_id` sin migración autorizada | Ficha corregida: `path.stem` es la decisión de v1; `payload.session_id` documentado como disponible-no-adoptado — cambiarlo exige migración autorizada explícita |
| 2 | Única instantánea materializada de bytes: detección, parseo, offsets y sello sobre ella; **eliminar tamaño/mtime como alternativa conforme** | ADR-010 §5 endurecido: una sola forma conforme; la verificación por tamaño/mtime se elimina con su razón (dos lecturas de un archivo vivo pueden diferir sin fallar); lectura cortada ⇒ `entrada_corrupta`; `captura.py` actual declarado **no conforme**, conversión a instantánea única = primer paso del plan de implementación |
| 3 | Reconciliar "todo formato no reconocido ⇒ `version_no_soportada`" con el fallback a `ok`; evidencia positiva concreta; observabilidad explícita para identidad reconocida con cero cierres | Frase contradictoria del §1 eliminada (era herencia de ronda 10); regla 4 define evidencia positiva operativa (patrón estructural no declarado, recurrente, ≥N ocurrencias con N por ficha — parser-codex N=10; excluye líneas corruptas y ocurrencias aisladas); regla 5 añade `detalle = "identidad_reconocida_sin_cierres"` y conteo separado — drift observable, nunca éxito opaco |
| 4 | Endurecer `^codex` con frontera o enum cerrado; corregir "3 formatos distintos" al número documentado | Frontera `(?i)^codex([ _-]|$)` (palabra completa; `codexfoo` no casa) + enum observado documentado; evidencia corregida: **2 formatos ajenos** (Claude Code projects + history.jsonl), con nota de corrección |

Estado tras 11b: ADR-010 **propuesto**; sin commit ni push (esperando
autorización). `git diff --check` limpio. Suite (convención de reporte,
corrección 7): **102 descubiertos, OK, 0 saltados** en mi entorno
(Mongo/Ollama arriba); corrida independiente de Pinax del mismo día:
102 descubiertos, OK, 54 saltados.

## Pasada 1 — correcciones originales

| # | Corrección exigida por Pinax | Destino |
|---|---|---|
| 1 | No clasificar como `version_no_soportada` un archivo vivo sin marcas tardías: formato soportado sin turnos cerrados ⇒ `ok` + cero turnos; `version_no_soportada` requiere evidencia positiva de incompatibilidad o parser retirado | ADR-010 §1 regla de decisión reescrita (regla 4 exige evidencia positiva; regla 5 = archivo vivo ⇒ `ok`); SPEC-006 caso nuevo |
| 2 | Sustituir `session_meta` como marca supuestamente exclusiva por un predicado Codex-específico con muestras positivas y controles negativos; campos exactos, alcance, conducta ante ausencia | Predicado adoptado: primer `session_meta` (≤10 líneas) con `payload.originator` `^codex` — **616/616 positivos, 11/11 controles negativos** (Claude Code projects, history.jsonl); evidencia nueva en `docs/evidencia/predicado-identidad-codex-2026-08-20.md`; exclusividad afirmada con evidencia, no como verdad absoluta (colisión ⇒ `deteccion_ambigua`) |
| 3 | `ResultadoParseo` estructurado (diagnostico, turnos, cli_producto/versiones observadas, detalle, descartes_linea) con precedencia total y testeable entre los cinco diagnósticos | ADR-010 §3 reescrito: estructura completa + precedencia `entrada_corrupta > deteccion_ambigua > formato_desconocido > version_no_soportada > ok` con justificación; SPEC-006 Salidas actualizadas |
| 4 | Ficha obligatoria completa: session_id, turn_id, timestamp_cierre, predicado de cierre, codificación/offsets en bytes, gramática inequívoca del ID calificado; Codex raw-id como excepción compatible y probabilística; adaptadores nuevos con ID calificado por defecto | ADR-010 §2 ampliado (lista completa de campos obligatorios) + §7 (gramática: primer dos puntos delimita, `cli_producto` sin dos puntos por construcción) + política de default; ficha parser-codex completada campo por campo (incl. `session_id` con la divergencia honesta `path.stem` vs `payload.session_id`) |
| 5 | Detección, parseo y sello sobre la misma instantánea de bytes — o detección de mutación concurrente incompatible | ADR-010 §5 nuevo párrafo: instantánea materializada (preferida) o verificación tamaño/mtime ⇒ `entrada_corrupta` con detalle `mutacion_concurrente`; nota honesta: `captura.py` hoy lee dos veces — deuda de implementación declarada, no del contrato; caso nuevo en SPEC-006 |
| 6 | Frontera escrubery precisa: listar=sólo candidatos sin procedencia; ficha=referencia con procedencia/caducidad; caducado no prueba vigencia; no selecciona parser, no infiere proyecto, nunca bloquea; memoizado por CLI/sesión; `cli_producto` vocabulario interno, no identidad canónica de Pinax | ADR-010 §9 reescrito punto por punto; autorización del dueño (2026-08-20, consumo opcional) citada |
| 7 | Reporte de pruebas: lo observado por Pinax = 102 descubiertos, OK, **54 skipped** — no describir "102/102 ejercitados" | Convención fijada en el plan (protocolo §1): reportar "N descubiertos, OK, S saltados"; el claim erróneo fue en reportes de canal del agente (el acta 10 no lo contenía); medición propia con servicios arriba: 102/0 saltados — ambos números se citan juntos |

## Verificaciones propias de esta ronda

- Evidencia empírica del predicado: corpus completo (616 archivos con
  `session_meta`; `originator ∈ {codex-tui, codex_exec, Codex
  Desktop}`, todos `^codex`) + 10 archivos Claude Code reales + 1
  `history.jsonl` como controles negativos.
- `cli_version` existe en el propio rollout (`0.146.0-alpha.3.1`…):
  documentado como `version_cli_observada` (no se persiste en v1).
- Suite en mi entorno: **102 descubiertos, OK, 0 saltados** (Mongo y
  Ollama arriba) — y el registro de Pinax (54 saltados) queda citado
  como dato de igual validez (corrección 7).

## Stop rules (estado)

- Sin código, dependencias ni migraciones: diff = sólo `.md` (ADR-010,
  SPEC-006 en f1-specs.md, plan, acta nueva, evidencia nueva).
- ADR-010 **propuesto** (decisión 🔒 pendiente; firma en blanco).
- Ningún contrato F1 vigente modificado; escrubery queda como consumo
  opcional, jamás dependencia crítica o autoridad sobre archivos
  observados.
- **Sin commit** (el paquete `457d827` es la base; estas correcciones
  quedan sin commitear hasta autorización nueva del dueño). **Sin
  push** (siempre requiere autorización separada).
