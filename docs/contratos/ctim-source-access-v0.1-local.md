# CTIM source access v0.1 — perfil local de laboratorio

Estado: implementado para el piloto local; sin admisión jurídica ni al corpus. El perfil privado del host fija exactamente siete originales del inventario de expertoGobernanza y sus derivados. No crea políticas, raíces, permisos ni retención.

## Frontera

`skopos ctim-source-access serve --policy ABSOLUTE_PATH` abre un socket Unix con modo `0600`. El agente envía una línea JSON, máximo 4096 bytes. No puede aportar rutas ni elegir fuentes fuera del perfil. El host verifica en cada llamada el hash del perfil y del inventario; antes de entregar datos verifica custodia, bytes originales y derivados fijados por hash. El perfil se crea localmente con `scripts/source_ctim_access_prepare.py`, en `runs/source-imss-ctim-pilot-v1/seven-source-access/policy.json` (ignorado por Git).

Operaciones:

| Operación | Campos de solicitud | Resultado |
| --- | --- | --- |
| `list_sources` | `request_id`, `operation` | Siete identidades, SHA original, tipo, cobertura y costo de verificación. |
| `find_literal` | anteriores, `term` (1–128 caracteres), `limit` (1–10) | Coincidencias literales `casefold`, alternadas por fuente; total, límite, conteo por fuente y cobertura. |
| `fetch_fragment` | `request_id`, `operation`, `source_id`, `item_id` | Un fragmento por identidad admitida, con SHA original y página física PDF o rango de bytes HTML. |

La respuesta incluye `schema`, `request_id`, `request_sha256`, `policy_sha256`, `status`, `result` y `error`. Un fallo de integridad, falta de recibo o identidad no admitida devuelve `result: null`. `find_literal` no equivale a búsqueda semántica; una subcadena puede producir ruido y la ausencia de coincidencia no prueba ausencia de contenido visual o no extraído.

Para PDF, `page_number` es la página física (1 basada), `bbox` la localización de la línea y `modality` distingue texto nativo u OCR. Para HTML, `start_byte` es inclusivo y `end_byte` exclusivo sobre los bytes originales. El texto HTML es visible para el parser; CSS/JavaScript no se evalúan. `fidelity_status: unreviewed` se conserva en todos los casos. `derived_pages` no acredita fidelidad textual ni visual. Los textos y procedencias siguen siendo evidencia atribuida, no vigencia jurídica.

La respuesta puede ser `ok`, `invalid_input` o `execution_failed`; los errores tienen código y etapa. No existe recuperación por ruta elegida por el consumidor. El socket requiere acceso local efectivo y debe cerrarse tras el ensayo.
