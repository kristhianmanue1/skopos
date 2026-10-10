# CTIM source access v0.2 — página física PDF

Estado: implementado para el perfil local de siete originales CTIM. Extiende
`ctim-source-access-v0.1-local.md` con una operación; las solicitudes y respuestas
de `list_sources`, `find_literal` y `fetch_fragment` siguen en v0.1. No cambia
la política de acceso `skopos/ctim-source-access-policy/v0.1`, el inventario,
la custodia, la admisión al corpus ni la vigencia jurídica atribuida.

## Solicitud y respuesta

`read_pdf_page` acepta exactamente `request_id`, `operation`, `source_id` y
`page_number`. `source_id` debe pertenecer al perfil fijado por el host y ser
PDF; `page_number` es entero positivo (bool excluido) y página física 1 basada
dentro del conteo del inventario. El consumidor no aporta rutas, raíces,
políticas ni hashes alternativos. Ejemplo:

```json
{"request_id":"imss-p15","operation":"read_pdf_page","source_id":"imss-procedure-2900-003-001-2021","page_number":15}
```

La respuesta usa `schema: skopos/ctim-source-access/v0.2` y conserva los
campos de correlación de v0.1: `request_id`, `request_sha256`,
`policy_sha256`, `status`, `result`, `error`. En éxito, `result` incluye
`source_id`, `source_sha256`, `media_type`, `page_number`, `page_count`,
`page_width_points`, `page_height_points`, `page_rotation`, `native_text`,
`ocr_text`, `fidelity_status: unreviewed`, `line_order`, `coverage` y `cost`.
Cada modalidad conserva su `status` y la lista completa `lines` del manifiesto;
cada línea lleva `item_id`, `bbox` normalizada y `text`. `coverage` informa la
cobertura del documento completo bajo el mismo perfil v0.1. `cost` informa
tiempo y bytes originales/derivados verificados, no costo del proveedor.

`line_order: manifest_extraction_order` significa que se preserva el orden del
derivado; no afirma orden de lectura ni relación actor–actividad. En la página
15 del procedimiento IMSS, las etiquetas de responsables preceden a varias
actividades en ese orden. La geometría permite revisar el diseño visual, pero
la operación no infiere ni adjudica actores. El texto sigue sin revisión de
fidelidad (`unreviewed`).

## Fallo cerrado y tamaño

En cada llamada se comprueba el perfil vigente. La ruta existente verifica
inventario, recibo de custodia, bytes y SHA-256 originales, y manifiesto
fijado por hash antes de entregar la página. Identidad ajena al perfil:
`source_not_allowed`; fuente no PDF: `unsupported_format`; página fuera de
rango o tipo inválido: `invalid_page`. Un manifiesto inconsistente o inaccesible
falla con el código de integridad correspondiente y `result: null`.

La línea JSON de respuesta completa, incluido salto de línea, tiene límite de
64 KiB para esta operación. Una página mayor responde
`execution_failed`, `error.code: page_response_limit_exceeded`,
`error.stage: delivery` y `result: null`; no se recortan líneas ni texto.
El socket conserva el límite de solicitud de 4096 bytes y el máximo general
de transporte de 256 KiB. Un `ok` acredita entrega verificada bajo el perfil
local observado, no fidelidad semántica, orden visual ni atribución jurídica.
