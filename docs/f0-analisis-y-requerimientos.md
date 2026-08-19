# F0 — Análisis y requerimientos de Skopos

> Producido siguiendo el método Skevi (`AGENTS.md`/`docs/guia-agentes-ia/`
> de https://github.com/kristhianmanue1/Skevi). Fuente de cada requisito
> declarada junto al requisito.

## Problema y resultado observable

Problema: las conversaciones de un CLI de IA (Codex, para empezar) se
pierden al cerrarse; no hay forma de recuperar después qué se dijo sobre un
tema concreto sin releer sesiones enteras.

Resultado observable: dado un tema, un consumidor (el propio agente u otro
sistema) puede recuperar todo lo relevante dicho sobre ese tema en
conversaciones pasadas, con acceso al fragmento completo de origen si lo
necesita.

## Requisitos

```text
REQ-1 [funcional] [fuente: humano + evidencia del prototipo conversation_observer]
Enunciado: al cerrar cada turno (evento task_complete en un rollout de
Codex), Skopos extrae el texto real intercambiado en ese turno, no sólo el
marcador de cierre.
Criterio de aceptación: dado un rollout-*.jsonl con un evento task_complete,
Skopos produce el texto de usuario/agente de ese turno, verificable contra
los eventos response_item correspondientes del mismo archivo.
Prioridad: imprescindible

REQ-2 [funcional] [fuente: humano]
Enunciado: un modelo de IA (local, primera iteración) analiza el texto
capturado de un turno y extrae tema, resumen y referencia al origen.
Criterio de aceptación: dado un turno con contenido reconocible sobre un
tema, el análisis produce un registro con al menos tema/etiqueta, resumen
y referencia al fragmento de origen.
Prioridad: imprescindible

REQ-3 [funcional] [fuente: humano]
Enunciado: lo relevante extraído de cada turno se guarda en MongoDB local,
junto con una referencia recuperable al fragmento completo de origen.
Criterio de aceptación: tras procesar un turno existe un documento en
MongoDB consultable por tema, desde el cual se recupera el fragmento
original completo.
Prioridad: imprescindible

REQ-4 [funcional] [fuente: humano]
Enunciado: dado un tema, un consumidor recupera toda la información
relevante guardada sobre ese tema en conversaciones pasadas, incluidos los
fragmentos completos si los pide.
Criterio de aceptación: una consulta por tema devuelve todos los registros
relevantes que coinciden, cada uno con acceso al fragmento de origen
completo.
Prioridad: imprescindible

REQ-5 [funcional] [fuente: humano]
Enunciado: el análisis es configurable por dominio/tema (ej. arquitectura
de software y programación) para mejorar la precisión de la extracción.
Criterio de aceptación: existe un mecanismo de configuración (formato
definido en F1) que cambia el resultado del análisis según el dominio
declarado, verificable comparando salida con y sin configuración de
dominio sobre el mismo turno.
Prioridad: deseable — no bloquea el primer extremo a extremo

REQ-6 [no-funcional] [fuente: humano]
Enunciado: la detección de cierre de turno y el disparo del análisis
ocurren inmediatamente después de cada turno, no en un batch posterior.
Criterio de aceptación: umbral de tiempo máximo pendiente de acotar en F1.
Prioridad: deseable

REQ-7 [restricción] [fuente: humano]
Enunciado: Skopos se construye en Python.
Criterio de aceptación: manifiesto del proyecto declara Python; versión
del runtime confirmada en el entorno real antes de cerrar F2.
Prioridad: imprescindible

REQ-8 [restricción] [fuente: humano]
Enunciado: MongoDB corre local (no gestionado) en esta primera iteración.
Prioridad: imprescindible

REQ-9 [restricción] [fuente: humano]
Enunciado: el modelo de IA para el análisis es local en esta primera
iteración; soporte de proveedor externo queda fuera de alcance por ahora.
Prioridad: imprescindible (para el alcance inicial)

REQ-10 [funcional] [fuente: humano, agregado tras cierre inicial de F0]
Enunciado: al analizar un turno, Skopos puede enriquecer el análisis con
metadata de referencia sobre el CLI observado (comandos, versión,
comportamiento documentado), consultando el servicio escrubery
(`github.com/kristhianmanue1/escrubery`, clon local en
`/Users/krisnova/www/aria/escrubery`).
Criterio de aceptación: si escrubery está disponible y tiene ficha para el
CLI observado, el `Analisis` incluye esa metadata de referencia; si
escrubery no está disponible o no tiene datos, el turno se procesa igual,
sin ese campo — nunca bloquea el pipeline crítico (REQ-1..4).
Prioridad: deseable — explícitamente no bloqueante.
```

## No objetivos

- No se modifica el CLI de Codex ni su comportamiento; Skopos sólo observa
  sus archivos de sesión (`~/.codex/sessions/**/*.jsonl`).
- No se soporta más de un CLI en la primera iteración — sólo Codex, sobre
  el formato ya evidenciado. Otros CLIs quedan fuera hasta que éste
  funcione de punta a punta.
- No se decide en F0 el motor de IA local concreto (Ollama u otro) — F1.
- No se decide en F0 el formato de configuración por dominio — F1.
- No se define un umbral numérico de "tiempo real" — declarado como
  no-funcional pendiente de acotar en F1, no bloquea F0.
- No se construye interfaz de usuario para personas; el consumidor de la
  recuperación es programático (agente o sistema), no una UI.
- Skopos no reimplementa lo que escrubery ya resuelve (fichas de CLIs) —
  lo consulta como fuente de referencia opcional, no lo duplica.

## Restricciones

- Lenguaje: Python (REQ-7).
- MongoDB local, no gestionado (REQ-8).
- Modelo de IA local en la primera iteración (REQ-9).
- Se parte del prototipo existente
  `/Users/krisnova/www/kratos/prototypes/conversation_observer/` como
  evidencia del formato de datos de origen; no se descarta, se extiende.
- escrubery es un proyecto separado y privado, consultado en modo lectura
  vía su propio CLI (`scripts/consultar`); Skopos no lo modifica ni
  depende de él para su flujo crítico (REQ-10).

## Fronteras

- Entrada: archivos `rollout-*.jsonl` de Codex en `~/.codex/sessions/`.
- Entrada opcional: fichas de escrubery vía `scripts/consultar ficha cli
  <nombre>` (REQ-10), sólo para enriquecer el análisis.
- Salida: documentos en una colección de MongoDB local, consultables por
  tema, con referencia al fragmento de origen completo.
- Consumidores: el propio agente conversacional y/o otro sistema/agente,
  vía una interfaz por definir en F1 (API, función, o CLI de consulta).

## Preguntas abiertas (diferidas a F1, no bloquean el cierre de F0)

```text
PREGUNTA-1: ¿qué motor local ejecuta el análisis (Ollama u otro)?
Por qué importa: define una dependencia nueva y el contrato del
componente de análisis.
Opciones: Ollama está instalado en el entorno de desarrollo (evidencia:
`which ollama`); candidato por defecto salvo objeción.

PREGUNTA-2: ¿cómo se expone la recuperación a los consumidores — API
HTTP, función/tool local, CLI de consulta?
Por qué importa: define el contrato de interfaz (F1 §4).
Opciones: se decide en F1.

PREGUNTA-3: ¿formato de configuración por dominio (REQ-5) — archivo,
flag, variable de entorno?
Por qué importa: define un contrato/config schema.
Opciones: se decide en F1.
```

## Evidencia

```text
EV-1: Skopos no existía como repo antes de este análisis |
`ls -la /Users/krisnova/www/aria/skopos` (previo) → sólo .DS_Store, sin git

EV-2: existe un prototipo de captura, sin persistencia de texto |
lectura de
`/Users/krisnova/www/kratos/prototypes/conversation_observer/codex_rollout_watcher.py`
→ detecta cierre de turno (task_complete) por polling sobre JSONL; declara
explícitamente "no lee ni persiste el texto de la conversación"

EV-3: formato real de los rollouts de Codex, confirmado con datos reales |
inspección de un rollout-*.jsonl real en `~/.codex/sessions/` → tipos de
evento: turn_context, event_msg, session_meta, world_state, response_item;
payload.type incluye message, agent_message, user_message,
agent_reasoning, reasoning, task_complete, task_started, token_count

EV-4: runtime Python disponible | `python3 --version` → Python 3.9.6

EV-5: MongoDB no está instalado en el entorno de desarrollo |
`which mongod mongosh mongo` → ninguno encontrado; pendiente para F2

EV-6: hay un runtime de modelo local disponible |
`which ollama` → /opt/homebrew/bin/ollama

EV-7: escrubery existe como clon local y su CLI de consulta funciona |
`/Users/krisnova/www/aria/escrubery/scripts/consultar listar` → lista
CLIs y proveedores disponibles, incluido "codex-cli";
`.../consultar ficha cli codex-cli` → JSON real con comandos y bloque de
procedencia (fuente, fecha, hash) por cada uno

EV-8: el esquema de mensaje asumido en EV-3 estaba incompleto — corregido
durante F2 al validar contra un rollout real | primera implementación de
extracción de texto (payload.type en {message, agent_message,
user_message}, campo "text") devolvió texto vacío en los 5 turnos de un
rollout real; inspección directa del payload mostró el esquema real:
`payload = {type: "message", role: "user"|"assistant"|"developer",
content: [{type: "input_text"|"output_text", text: "..."}]}`. El rol
"developer" contiene instrucciones de sistema/permisos inyectadas por
Codex, no conversación, y se excluye deliberadamente de texto_usuario y
texto_agente. Tras la corrección, la extracción sobre un rollout real
produjo texto no vacío (verificado, sin imprimir contenido privado del
usuario en este documento).
```

## Reporte de fase

```text
FASE F0: OK
Gate: Definition of Ready (guía Skevi 01-analisis-y-requerimientos.md §3.2)
Evidencia: ver EV-1..EV-6 arriba
Pendientes: 3 preguntas diferidas explícitamente a F1 (PREGUNTA-1..3);
ninguna bloquea el cierre de F0
```
