# Rótulos v0.5: comprobación local del productor

**Observación:** 2026-10-08, checkout
`/Users/krisnova/www/aria/skopos`, rama
`codex/skopos-labels-v05-operational` antes de commit. Fuente IMSS
`2000-002-001.pdf` SHA-256 `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.

La proyección v0.5 mantuvo el padre v0.4 (`07018142…`) y produjo
manifiesto `0d79b1e5d10219e844aa54b3d470ccf57a5868611a5a4fe8b5fb1d0fce58e20a`.
El registro visual de 86 recuadros se copió byte a byte desde
expertoGobernanza y conservó SHA-256 `a1792ce5f7458c84e10a88ba47857d480fb730dd354896f433bbe338aa198cfb`.
El host coteja ese hash al servir. En p21 `n5`, `literal_text` acaba en
`SALUID` y `normalized_text` en `SALUD`.

## Ejecuciones observadas

- `.venv/bin/python -m unittest discover -s tests`: **457 tests OK**, seis
  omitidos por sus condiciones de suite. Los gates de tamaños y planes:
  **485 archivos OK**, dos planes OK.
- Se inició el controlador Mongo dedicado con `pdf_custody_pilot.py
  preflight/start`, luego `skopos.pdf_graph_labels_v05_host serve` con
  `runs/pdf-document-imss-pilot-v1/graph-labels-v05-host.json`. El smoke
  `scripts/pdf_graph_labels_v05_smoke.py` recuperó las páginas 18–22
  (8+32+10+19+17 rótulos), tres ítems por ID, y verificó rechazo de fuente
  errónea, manifiesto erróneo, página 23, ítem desconocido y hash de sobre
  incorrecto. La repetición del mismo sobre fue determinista.
- El bloque de prueba envió `SIGTERM` al host hijo y `pdf_custody_pilot.py
  stop` devolvió `stopped`; no quedó `graph-labels-v05.sock`.

El smoke prueba identidad y transporte bajo esta política y este Mac. No
prueba vigencia institucional ni fidelidad fuera de los 86 recuadros cotejados
sin ceguera. La función de consumo y su recibo bilateral están en
`expertoGobernanza/docs/evidencia/skopos-imss-funcion-local-2026-10-08.md`.
La política local vence `2026-11-08T00:00:00Z`.
