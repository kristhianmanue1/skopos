# Evidencia · reconocimiento del formato de qwen-code (diferido)

**Fecha:** 2026-08-28. **Estado: DIFERIDO por decisión del dueño** el
mismo día — no se escribe adaptador. Este documento existe para que el
reconocimiento no haya que repetirlo cuando se retome.

**Origen:** el dueño reportó que ahora usa qwen y preguntó por el coste
de integrarlo. `qwen-code` había salido de la fase B de P-003 en la
corrección R3 de la ronda 22, por no estar en el mapa de adaptadores de
escrubery. Esto es **reconocimiento local propio**, no el mapa de
escrubery: no hay procedencia externa detrás.

## Dónde vive el historial

`~/.qwen/projects/<ruta-del-proyecto-codificada>/chats/<sessionId>.jsonl`,
con un `<sessionId>.runtime.json` acompañante. Snapshot de hoy:
**47 archivos `.jsonl`, 8,321 líneas, 85 mensajes de usuario real**.
Binario: `qwen` (fnm), versión 0.22.2 en `~/.qwen/sessions/*.json`.

## Vocabulario observado

- Claves presentes en **todas** las líneas: `cwd`, `parentUuid`,
  `sessionId`, `timestamp`, `type`, `uuid`, `version`.
- `type ∈ {user, system, assistant, tool_result}`.
- `provenance ∈ {real_user, system, assistant_output, tool_result}`.
- `message.role ∈ {user, model}`, con `parts` (estilo Gemini).
- `subtype` de los `system`: `ui_telemetry`, `attribution_snapshot`,
  `file_history_snapshot`.
- `version` por línea; en el corpus aparecen **once** versiones distintas
  (0.12.3 … 0.22.2).
- Primera línea: `user` en 41 archivos, `system` en 6.

## Lo que sería más fácil que en Codex

- **`proyecto` sale directo**: `cwd` viene en cada línea, sin necesidad
  de rastrear el último `turn_context` anterior (el dolor que produjo la
  corrección C2 de la ronda 23).
- **`provenance` separa la conversación real de lo inyectado** por
  declaración del propio formato — el equivalente explícito a excluir el
  rol `developer` en Codex.
- `sessionId` en cada línea, no sólo en el nombre del archivo.
- Es JSONL por línea: instantánea, offsets, sello P4a y cursor
  incremental sirven sin cambios.

## Lo que sería duro (y por qué se difiere)

1. **No hay marca de cierre de turno.** Codex tiene
   `event_msg.payload.type == "task_complete"`, y sobre esa marca se
   apoyan el turno, el fragmento, el sello y el avance del cursor. En
   qwen no aparece ningún equivalente. Habría que **derivar** la
   frontera (p. ej. de un `provenance: real_user` al siguiente), lo que
   exige declararlo en la ficha con evidencia y aceptar que **el último
   turno de una sesión viva nunca cierra** hasta que llegue el mensaje
   siguiente — diferencia semántica real frente a Codex.
2. **Predicado de identidad por construir.** No hay marca de producto
   evidente; habría que componerlo (combinación de claves de la primera
   línea) y **probarlo contra los otros formatos** con muestras
   positivas y controles negativos fechados, al estándar de Codex
   (616/616 y 11/11).
3. **Once versiones en el corpus**: antes de declarar un perfil base
   único hay que verificar si el esquema cambió entre ellas.

## Nota de tamaño

85 mensajes de usuario real, contra los 16,201 turnos del corpus Codex:
alcanza para escribir el adaptador, pero es **justo** para afirmar un
predicado de identidad con la solidez del de Codex. Si se retoma,
conviene volver a medir el corpus entonces.
