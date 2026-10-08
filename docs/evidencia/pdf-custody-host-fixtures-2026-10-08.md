# Canal de host PDF: evidencia de fixtures — 2026-10-08

**Estado:** mecanismo candidato probado con fixtures locales; ninguna
política operativa instalada y ninguna admisión del PDF IMSS real. Los
detalles de campos y límites están en
[`perfil-host-pdf-binario-v0.1`](../propuestas/2026-10-08-perfil-host-pdf-binario-v0.1.md).

**Repositorio probado:** Skopos `main@be95df0` más el diff de este
incremento, antes del commit. La prueba usa `.venv/bin/python`, sin
dependencias nuevas, con replica set Mongo temporal exclusivo en
`127.0.0.1:37029` y bases `skopos_test*`; el proceso se detuvo y su
directorio temporal se retiró al terminar. No se usó Mongo operativo.

## Resultado observado

| Comprobación | Resultado | Límite |
| --- | --- | --- |
| `scripts/run_isolated_tests.py --mongo-uri mongodb://127.0.0.1:37029 --pattern test_pdf_custody_host.py` | 10 pruebas, OK, sin omisiones sobre el código final | Fixture PDF pequeño y misma identidad de OS |
| Suite completa en el mismo Mongo temporal | 497 pruebas, OK, sin omisiones sobre el código final | No prueba instalación en host consumidor |
| `python3 scripts/check_sizes.py` / `python3 scripts/check_plans.py` | Gates verdes, 339 archivos de texto y dos planes | Estructura, no semántica |
| Proceso `custody-host serve` + cliente `request` por Unix socket | `describe_capabilities` devolvió `status=ok`, esquema `skopos/pdf-custody-host/v0.1` | Ambos procesos bajo el mismo usuario; no prueba ACL entre identidades |
| Compilación Python | Sintaxis válida con caché en `/tmp` | La caché predeterminada fue bloqueada por sandbox; no es defecto del código |

El primer intento de Mongo temporal dentro del sandbox no pudo abrir el
puerto; la aprobación automática de un reintento caducó. La ejecución final
con permiso elevado local sí levantó la instancia de ensayo y concluyó en
verde. Eso es evidencia del entorno de pruebas, no de una autorización de
servicio persistente.

## Falsadores ejercidos

El control positivo admitió el PDF fixture, obtuvo el mismo `receipt_id`
tras simular respuesta perdida y recuperó bytes idénticos. La consulta de
recibo usó `admission_request_sha256` diferente de su digest de solicitud.
Se rechazaron cambios de configuración enviados por el agente, versión de
contrato antigua, política v0.1 sin lista, lista duplicada, otro material
dentro de la raíz, otra ruta y SHA, ficha declarada distinta, política
caducada/cambiada, `max_pages`, ausencia de `recovery_requirement`, original
o ficha mutados, enlace en la ruta admitida, fallo de publicación de salida
y cliente que deja incompleta una llamada al socket (rechazo en dos segundos).
La base retuvo una sola revisión en la secuencia de control. La autorrevisión
añadió verificación del digest de política y de la ruta/ficha al consultar
recibo, con un control negativo de política distinta; las corridas finales
anteriores incluyeron esa corrección.

## Límites y siguiente puerta

El canal fija valores fuera del mensaje del agente, pero la CLI directa
permanece accesible para quien tenga shell y credenciales. El socket `0600`
no permite por sí mismo acceso desde otra identidad de OS. Aún faltan
política real aprobada, raíz/ACL/credenciales separadas, vida y limpieza de
salida, prueba negativa ejecutada con la identidad efectiva del consumidor
y corrida bilateral con el PDF y ficha reales. La copia original de
expertoGobernanza sigue siendo la única fuente recuperable en el modo
`while_reference_available`; no se afirma restauración independiente.
