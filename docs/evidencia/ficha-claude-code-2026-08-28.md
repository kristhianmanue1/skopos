# Evidencia · ficha del adaptador parser-claude-code/v1 (fase B, CLI 1 de 4)

**Fecha:** 2026-08-28. **Alcance:** primer adaptador de la fase B de
P-003 (aceptada 🔒 2026-08-28). Corpus: `~/.claude/projects/*/*.jsonl`
en la máquina del dueño, **205 archivos**.

## Dos decisiones de ficha que exigían evidencia

### 1 · Predicado de identidad

**Adoptado:** dentro de las **10 primeras líneas**, una línea JSON con
`sessionId` + `uuid` + `version` **y** al menos una marca del harness
(`isSidechain`, `userType`, `entrypoint`).

| Población | Resultado |
|---|---|
| `~/.claude/projects/*/*.jsonl` | **205/205 casan** |
| codex (`~/.codex/sessions`) | 0 falsos positivos de **643** |
| kimi (`~/.kimi*`) | 0 falsos positivos de **1,494** |
| qwen (`~/.qwen/projects/*/chats`) | 0 falsos positivos de **47** |
| cline (`~/.cline`) | 0 falsos positivos de **3** |

**2,187 archivos ajenos, cero falsos positivos** — control negativo
bastante más amplio que el de Codex en su día (11 archivos). No se
afirma exclusividad absoluta: se afirma **con evidencia**, y un formato
no registrado que imite la forma es el límite residual que ADR-010 §1 ya
declara.

### 2 · Predicado de cierre — **derivado, y por qué**

claude-code **no emite una marca de cierre fiable**. Lo que parecía
serla, `subtype: "turn_duration"`, se descartó con datos:

- Sólo aparece en **68 de 205** archivos, y **no es cuestión de
  versión**: dentro de 2.1.231, 30 archivos la traen y 26 no.
- Donde aparece, **cuenta menos turnos que los reales**: 33 de 68
  archivos coinciden; en el resto discrepa siempre a la baja (9 usuarios
  reales vs 4 marcas; 13 vs 7; 16 vs 12). Usarla como cierre **perdería
  turnos en silencio**, que es el modo de fallo que este contrato existe
  para impedir.

**Adoptado:** el turno va de un mensaje real del usuario hasta el
siguiente. **Consecuencia declarada:** el último turno de una sesión
viva **no cierra** hasta que llegue el mensaje siguiente — es el mismo
comportamiento que un rollout de Codex sin `task_complete` todavía
(`ok` con menos turnos, `identidad_reconocida_sin_cierres` si no hay
ninguno), y el cursor lo vuelve a mirar en el ciclo siguiente.

## El hallazgo que habría roto el adaptador en silencio

En este formato **los resultados de herramienta vuelven como mensajes de
usuario** (`type: "user"` con `content: [{type: tool_result}]`), y son el
**90 %**: 7,167 de 7,965 en el reconocimiento. Tratarlos como voz de la
persona habría multiplicado los turnos por nueve y llenado
`texto_usuario` de salidas de herramientas. La ficha los excluye
explícitamente, junto con `isSidechain` (transcripciones de subagentes)
y `isMeta`.

## Resto de la ficha

- **`cli`**: `claude-code` (constante, ADR-010 §2).
- **`turn_id`**: **ID calificado** `claude-code:{uuid}` del mensaje que
  abre el turno — ADR-010 §7 exige calificar por defecto; el id crudo es
  la excepción que Codex se ganó con evidencia de unicidad.
- **`session_id`**: `path.stem` (misma decisión de compatibilidad que
  parser-codex/v1).
- **`proyecto`**: `cwd` de la línea que abre el turno, con la **misma
  regla C-9** que Codex (≥2 niveles bajo `$HOME`; valor sin significado ⇒
  ausente). Aquí `cwd` viene en cada línea, así que no hace falta
  rastrear un evento anterior.
- **`timestamp_cierre`**: campo `timestamp` del último evento del turno.
- **`version_cli_observada`**: `version` de la línea (16 versiones en el
  corpus, 2.1.187 → 2.1.237).
- **Incompatibilidad declarada en v1: ninguna** — no hay marcador de
  versión del *formato* ni firma de otra versión registrada; igual que
  en parser-codex/v1, `version_no_soportada` es inalcanzable salvo por
  retiro.

## Resultado sobre el corpus real

| Medición | Valor |
|---|---|
| Diagnóstico | **205/205 `ok`** |
| Turnos extraídos | **1,800** |
| Turnos con `texto_usuario` vacío | **0** |
| Codex tras registrar la segunda ficha | 643/643 `ok`, `cli_producto=codex-cli`, 16,267 turnos |
| Detección cruzada | ninguna: claude → `claude-code`, codex → `codex-cli`, cero `deteccion_ambigua` |

La convivencia de dos fichas no alteró nada del adaptador de Codex, que
es lo que ADR-010 §8 promete de un registro aditivo.

## Verificación

**173 tests OK** (160 previos + 13 nuevos en `tests/test_claude_code.py`:
identidad, no-robo de identidad frente a un rollout de Codex, frontera
derivada del turno, exclusión de `tool_result`/`isSidechain`/`isMeta`,
ID calificado, regla de proyecto, sello del fragmento, sesión sin cerrar
y lectura incremental con cursor).
