# Enmienda CTIM MCP v0.2: dueño externo del runtime

Estado: **propuesta documental para integración experimental**. `AMENDS` [ctim-mcp-consumer-bridge-v0.1.md](ctim-mcp-consumer-bridge-v0.1.md), únicamente en propiedad del ciclo de vida, cierre y evidencia temporal. La interfaz de tres herramientas, argumentos, respuesta, errores y presupuesto acumulado de 65,536 bytes permanece como en v0.1. No cambia el contrato `skopos/ctim-source-access/v0.1`, el código de Skopos ni los siete originales. No implica admisión, activación o comparación semántica.

## Falsador de v0.1

En la integración con proveedor falso V1, cuatro llamadas MCP funcionaron y `host.close()` retornó código 0. El adaptador no registró `closed`; inmediatamente después, Mongo 37034 y los sockets del host y controlador seguían activos. Recibo: `/Users/krisnova/www/playGround/muse_hack_1/experiments/ctim_muse_skopos_sdk_fake_2026-10-09/RECEIPT.json` (SHA-256 `3ee1bd83bf79316ac4f3c929b4ca53426307b5c5f1617da36ab2f58817f81a37`). Esto refuta la suficiencia del `finally` **dentro** del MCP para ese cliente. No registra señal ni salida del proceso adaptador; no adjudica una causa interna exacta. El código del SDK puede terminar el host Muse con un plazo y escalamiento, pero `host.close()` no es un recibo del cierre de Mongo ni de Skopos.

## Regla sustituida

En vez de v0.1 §«Propiedad y frontera» y §«Presupuesto y ciclo de vida» respecto del dueño:

1. Un supervisor **externo al proceso Muse y a sus servidores MCP**, residente en expertoGobernanza, comprueba que Mongo 37034 y el socket Skopos no estén ocupados, inicia el Mongo dedicado y después `ctim-source-access serve`. Conserva los procesos y su identidad como recursos propios. No adopta ni detiene procesos preexistentes.
2. El adaptador MCP stdio se ejecuta en modo `--external-runtime`: comprueba y usa el socket fijado por el perfil, traduce solamente `list_sources`, `find_literal` y `fetch_fragment`, aplica los 65,536 bytes por proceso y registra sus llamadas. No inicia ni detiene Mongo ni el host. El token efímero transmitido por el supervisor es una señal de coordinación, **no** autenticación o prueba de propiedad por sí mismo; perfil, socket y preflight siguen siendo controles separados.
3. El supervisor ejecuta una sesión Muse por caso bajo un grupo de procesos propio. Al salir o fallar el runner, termina ese grupo; luego cierra el host Skopos propio, confirma retirada del socket, detiene Mongo propio y confirma el puerto cerrado. El cierre está en `finally` del supervisor y debe producir recibo aunque el adaptador no alcance su `finally`. `SIGKILL`, caída del supervisor o un descendiente que abandone el grupo conservan riesgo residual; el siguiente caso falla cerrado ante recursos preexistentes y exige recuperación identificada.
4. El `RECEIPT` del runner antes de terminar el supervisor es una **instantánea intermedia**: puerto y socket aún abiertos allí son esperables. El estado final se afirma sólo con el evento `closed failures=[]` del supervisor y una comprobación posterior a su salida, con hora, PID/grupo y ausencia de puerto, sockets y procesos propios. `host.close() == 0` acredita únicamente la salida observada del host Muse.

## Evidencia y límites de la enmienda

El smoke local del supervisor en expertoGobernanza registró cinco escenarios: salida normal, hijo con error, timeout, nieto del grupo y SIGTERM; los cinco reportaron grupo y puerto cerrados. Su `summary.json` (SHA-256 `b40e3479668b45c7d19832b690a8b7584011cc2548778e9516e2907575454bbb`) declara que no cubre Muse SDK ni nietos que se separen con `setsid`.

La integración fake V5 usó supervisor externo y adaptador `--external-runtime`. El `RECEIPT.json` (SHA-256 `549bbfffe9dbfb9b1090d7427db3a612d095e864f35b8cbc009c554befbf9609`) observa tres herramientas **MCP** anunciadas, cuatro llamadas `ok` (inventario, búsqueda literal, fragmentos PDF y HTML), turno `completed`, `host.close()` código 0 y rechazo de `mcp__ctim_exact_gate__metadata`. La sesión también ofrecía herramientas propias del host, por lo que no se afirma que su inventario total tuviera sólo tres herramientas. `OUTER_EVENTS.jsonl` registra `child_group_closed` y `closed failures=[]`; `POSTCHECK.json` (SHA-256 `96a30749eda4bd6263f34a7e93595f76980e01efc142d10ed2a88f7b09601bd2`) confirma después puerto y sockets ausentes, procesos no encontrados y los siete SHA originales vigentes. El recibo del adaptador no incluye `closed`: en esta topología no es el dueño del runtime. Todo ocurrió con proveedor falso; no hubo Spark, N1–N5 ni adjudicación de respuestas.

## Controles antes de otro ensayo

- Positivo bajo supervisor: `list_sources` 7/7 y `fetch_fragment` PDF/HTML, con SHA y localizador cotejados contra originales.
- Negativos: herramienta MCP externa y argumento `path` no llegan al socket; fuente/ítem inexistentes devuelven error tipado; exceso de 65,536 bytes se rechaza antes de escribir. Los errores del adaptador no deben dejar el supervisor sin cierre.
- Ciclo de vida: repetir cierre normal, error del hijo, timeout, SIGTERM y un adaptador abortado después de iniciar runtime; comprobar **después** del supervisor, no sólo tras `host.close()`, ausencia de procesos propios, puerto y sockets. Probar que un recurso preexistente provoca rechazo sin detenerlo. Registrar salida/señal del adaptador cuando el cliente la exponga; mientras falte, su mecanismo exacto de terminación permanece `unknown`.
- Conservar V1–V5 y sus denominadores separados. Un positivo con proveedor falso prueba transporte y limpieza de esa configuración; no acredita seguridad general, fidelidad PDF visual, modelo efectivo ni utilidad semántica.
