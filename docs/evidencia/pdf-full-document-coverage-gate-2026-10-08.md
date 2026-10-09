# Puerta de cobertura del PDF IMSS completo — 2026-10-08

## Alcance y resultado

**Resultado observado:** pasó la puerta técnica de cobertura de páginas del
PDF `2000-002-001.pdf` en este Mac, con el host Skopos v0.1 y la custodia
preexistente. `pdfinfo` informó 188 páginas físicas. El manifiesto nativo
enumeró exactamente las páginas 1–188: 187 con capa nativa `extracted` y
la portada 1 con `no_text`. Un derivado selectivo distinto permitió recuperar
20 líneas OCR de la portada; su fidelidad sigue `unreviewed`.

`187/188 = 99.47 %` es **presencia de texto nativo por página**, no porcentaje
de fidelidad del documento ni de exactitud OCR. La cobertura técnica
combinada nativo/OCR alcanza las 188 páginas con alguna capa de texto, pero
no demuestra que todo el contenido visual, las relaciones del organigrama,
el orden de lectura o cada palabra sean correctos. En las páginas 18–22, la
capa de organigrama sigue siendo parcial. Página 22 es el último organigrama;
la 23 inicia `7. Funciones Sustantivas`.

## Identidades y pruebas reproducibles

- Fuente atribuida a expertoGobernanza: SHA-256
  `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`;
  recibo de custodia
  `expertogobernanza:imss-2000-002-001:1:4fbed2bd3d2633aa`.
- Política de derivados local, digest canónico
  `4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b`;
  retención vigente hasta `2026-11-08T00:00:00Z`, sin renovación aquí.
- Derivado nativo: ID
  `372fdaef7fb1171ec8dce708b79ef1e32b38e43dfb1b079e6b27ae070d8f7587`,
  manifiesto SHA-256
  `7f81b1616b10549439cd536737e76663cfea7cec3bf7a6ec3fbf10241d8292ed`.
  Se verificaron 6007 identidades de línea derivadas de página, índice,
  modalidad, texto y caja normalizada.
- Derivado OCR: ID
  `7f132071b5e1c372e41d0ce9a83df7c966955c7fcb7036f80cdcbcecf5654a46`,
  manifiesto SHA-256
  `3ca9d7a5be5e451f63608015585a4eee92d2109046d390de99d793ac2f83651d`.
  Se verificaron 521 identidades de línea en sus seis páginas. La portada
  quedó recuperable por `fetch_evidence` de una línea OCR.
- El host entregó por `fetch_derivative` los bytes exactos del manifiesto
  nativo. La copia de entrega creada para esta comprobación se retiró.
  `fetch_evidence` y `search_document` devolvieron los ítems esperados en
  páginas 2, 17, 22, 23, 100 y 188, con fuente y página correlacionadas.
- Controles negativos observados: hash de manifiesto erróneo
  `manifest_integrity_failed`; fuente errónea `source_mismatch`; ítem
  inexistente `evidence_unavailable`; término ausente `no_match`; petición
  de página 189 `invalid_limits`. Dos mutaciones sólo en memoria del
  manifiesto, eliminación de página 23 y alteración de un `item_id`, fueron
  detectadas. Tras una respuesta deliberadamente no leída, dos repeticiones
  del mismo sobre dieron respuestas iguales. Solicitud persistida:
  `d7eceff6b9d83b5fb77ffcc6.request.json`, SHA-256
  `cdb66bcf05a6c92e121c650ea5cb4b086dc0b874240ef206571ce78205dda0ff`.

La ejecución final emitió `coverage_gate_passed`. Se apagaron el host y el
Mongo dedicado mediante el procedimiento de
`pdf-document-pilot-operations-2026-10-08.md`; el socket documental quedó
ausente. El script está en `scripts/pdf_full_document_gate.py`. Para repetir,
usar el bloque de arranque y limpieza del runbook y sustituir el bucle
`for mode in native ocr graph` por:

```bash
.venv/bin/python scripts/pdf_full_document_gate.py
```

Esta puerta reutiliza derivados existentes; no admite el PDF a corpus ni
crea una nueva custodia. El recibo y los sobres privados quedan para
trazabilidad bajo la política existente.

La suite aislada de Skopos ejecutó 511 pruebas sin fallos ni omisiones;
`check_sizes.py` y `check_plans.py` pasaron. El reporte del consumidor
`/Users/krisnova/www/expertoGobernanza/docs/evidencia/imss-full-188-page-coverage-2026-10-08.md`
declara una comparación adicional de los 187 folios textuales entre pypdf y
PDFKit: 55 158 palabras frente a 55 079, 54 997 compartidas por multiconjunto,
con mínimo por página 0,979 contra pypdf. Se inspeccionó su reporte, no se
volvió a ejecutar aquí su verificador; la comparación es técnica entre dos
extracciones de la misma capa del PDF, no una medida de fidelidad visual.

## Límite de la afirmación

La comprobación de todos los `item_id` prueba consistencia del manifiesto,
no comparación de todas las líneas contra la imagen. Las seis páginas de
muestra prueban recuperación puntual en inicio, transición, medio y final;
no son una muestra estadística de fidelidad. La OCR de portada tiene errores
observados y los grafos 18–22 omiten relaciones observadas en la revisión
visual anterior. La búsqueda literal excluye etiquetas de grafo, texto en
imagen no renderizado y coincidencias semánticas. No se ejecutó una segunda
auditoría visual independiente de las 188 páginas en esta puerta.

**Siguiente evaluación propuesta:** expertoGobernanza debe contrastar una
muestra estratificada y predefinida con el PDF visual, registrar errores por
modalidad y página, y calcular cualquier porcentaje de fidelidad con un
denominador y reglas de adjudicación explícitos. Hasta entonces, el estado
de fidelidad del producto permanece `unreviewed`.
