# Propuesta: puente MCP del consumidor CTIM v0.1

Estado: **diseño de integración, no implementado ni activado**. Destino recomendado: `expertoGobernanza/scripts/`, junto a `ctim_next_consumer_smoke.py`. No cambia `skopos/ctim-source-access/v0.1`, los siete originales, políticas, derivados ni recibos históricos. El cliente puede ser OpenCode o una sesión MCP del Muse SDK; no se presupone acceso efectivo a un modelo.

## Propiedad y frontera

El consumidor ya posee `skopos_runtime()` y el arranque/cierre de `ctim-source-access serve`. Un único proceso adaptador `ctim_skopos_mcp.py` debe ser dueño de ambos durante **una conexión MCP stdio**. Skopos conserva la verificación de custodia, origen y derivados; el adaptador sólo traduce transporte, restringe herramientas, contabiliza respuestas y registra recibos. Su comando y rutas se fijan por el host, nunca son argumentos de herramienta. No se añade dependencia a Skopos.

La configuración de sesión debe ejecutar el Python local con un comando absoluto y un archivo de recibos privado del caso. Para Muse SDK, la forma ya usada por el ensayo V4 es `mcpServers: { ctim_skopos: { transport: 'stdio', command: PYTHON, args: [ADAPTER, RECEIPT], framing: 'lineDelimitedJson', mode: 'required' } }`. OpenCode admite servidores MCP locales mediante un arreglo `command`; cualquier perfil allí exige comprobar inventario efectivo y aislamiento. El nombre de servidor debe diferenciar este brazo de `ctim_exact_gate`.

## Herramientas exactas

`tools/list` anuncia solamente estas tres herramientas, con `inputSchema` de objeto y `additionalProperties: false`:

| Herramienta | Propiedades requeridas | Solicitud a Skopos |
| --- | --- | --- |
| `list_sources` | ninguna | `operation=list_sources` |
| `find_literal` | `term` cadena 1–128 caracteres; `limit` entero 1–10 | `operation=find_literal`, mismos argumentos |
| `fetch_fragment` | `source_id` cadena del inventario; `item_id` SHA-256 hex de 64 caracteres | `operation=fetch_fragment`, mismos argumentos |

El adaptador crea `request_id` único por llamada desde un nonce local y contador, nunca desde una ruta o texto del agente. Envía una línea JSON de hasta 4096 bytes al socket; lee como máximo 256 KiB y exige `request_id`, `request_sha256` y `policy_sha256` correlacionados con la solicitud y el perfil fijado. Conserva el sobre de Skopos completo dentro de `content:[{type:'text',text:JSON}]`; si Skopos devuelve un estado distinto de `ok`, marca `isError:true` y conserva código/etapa. Un nombre desconocido se rechaza como método/herramienta desconocida, sin tocar el socket. No anuncia recursos, prompts, shell, rutas ni `read_file`.

El transporte usa mensajes JSON-RPC UTF-8 delimitados por línea. `stdout` contiene sólo respuestas MCP; diagnósticos van a `stderr` o al recibo. Implementar `initialize`, `notifications/initialized`, `ping`, `tools/list` y `tools/call`; negociar sólo versiones de protocolo comprobadas en el cliente de prueba, sin copiar ciegamente una versión desconocida. Una llamada antes del inicio o con argumentos extra falla cerrada. El contrato de herramienta se valida en el adaptador y de nuevo en Skopos.

## Presupuesto y ciclo de vida

Definir sesión como **vida del proceso stdio**; iniciar un proceso nuevo por caso para que el presupuesto no se arrastre entre casos ni se reinicie dentro de uno. Acumular los bytes UTF-8 de cada línea de respuesta MCP emitida, incluido JSON-RPC, contenido y salto de línea, desde `initialize`. Límite: **65,536 bytes por proceso**. Construir y medir antes de escribir; si una respuesta lo excedería, sustituirla por un error pequeño `response_budget_exceeded` con `isError:true`. Si ni ese error cabe, cerrar el canal sin emitir una respuesta parcial y registrar el motivo. Nunca truncar texto o localizadores silenciosamente. El recibo guarda bytes previos, bytes intentados, bytes emitidos y SHA-256 de cada respuesta, además de conteo de llamadas.

Rechazar un socket previo o un Mongo 37034 ya activo: el adaptador no debe detener procesos cuya propiedad no puede atribuir. Tras preflight, iniciar Mongo dedicado y luego el host; en `finally` cerrar primero el host propio, confirmar retirada del socket, detener Mongo propio y comprobar el puerto cerrado. Tratar EOF, excepción, SIGINT y SIGTERM; si falla la confirmación, salir con error y conservar recibo. No es posible prometer limpieza ante `SIGKILL`, apagado del equipo o caída del kernel: un supervisor externo debe detectar esos residuos antes de cualquier siguiente caso.

## Recibos y controles antes de modelos

Congelar el código del adaptador, el perfil Skopos, el inventario de siete SHA y la configuración del cliente. Recibo por conexión: hashes de esos insumos, hora, versión MCP negociada, herramientas anunciadas, solicitudes y respuestas correlacionadas, presupuesto acumulado, estado de host/Mongo al inicio y cierre; evitar texto completo, secretos y rutas innecesarias. El costo de preparación suma arranque de Mongo/host, verificación inicial, llamadas, apagado, mantenimiento del adaptador y revisiones visuales, separado de tokens/tiempo del modelo.

Controles offline obligatorios: (1) `initialize`/`tools/list` anuncian sólo tres herramientas; (2) `list_sources` positivo verifica 7/7 y `fetch_fragment` positivo para PDF y HTML; (3) fuente externa, ítem inexistente, argumento `path`, herramienta `read_file` y hash/recibo alterado fallan con `result:null` o `isError:true` según la frontera; (4) repetición hasta 65,536 bytes demuestra rechazo antes de exceder; (5) EOF, error inyectado y SIGTERM cierran host y Mongo, sin tocar procesos preexistentes. Capturar stdout binario y comprobar que **cada línea** es JSON-RPC; conservar stderr separado. Sólo después probar inventario efectivo del cliente Muse/OpenCode y, con protocolo nuevo, N1–N5. Una respuesta MCP positiva no demuestra uso semántico, modelo efectivo, vigencia jurídica ni fidelidad visual.

Referencias de transporte: [MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports), [herramientas MCP](https://modelcontextprotocol.io/specification/2025-06-18/server/tools), [servidores locales OpenCode](https://opencode.ai/docs/mcp-servers). La configuración Muse citada procede del runner local V4, no de una garantía de compatibilidad futura.
