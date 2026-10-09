# Rótulos PDF v0.5: literal y normalización separados

**Estado:** implementación local para expertoGobernanza. **Fuente:** manual IMSS
`2000-002-001.pdf`, SHA-256 `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
**Padre inmutable:** manifiesto v0.4 SHA-256
`07018142b74249edf0bc056f3b10bee5d1d004e43e77f556b3ef745027efaa98`.

## Enmienda de procedencia

El expediente v0.4 afirmó que el recuadro p21 `n5` muestra `SALUD`. El
cotejo visual de expertoGobernanza, copiado byte a byte a
`docs/evidencia/pdf-imss-graph-labels-v04-visual-audit-2026-10-08.jsonl`
(SHA-256 `a1792ce5f7458c84e10a88ba47857d480fb730dd354896f433bbe338aa198cfb`),
observó `SALUID`, que también conserva el campo nativo de v0.4. Esa afirmación
del expediente queda refutada para este recuadro. No se editan v0.4, su
manifiesto ni sus IDs. v0.5 proyecta 86 registros desde ese padre y desde
el registro de cotejo no ciego, cuyo hash consta en las anotaciones.

Cada registro v0.5 entrega `literal_text`, `normalized_text`, `bbox`,
`render_sha256`, `parent_item_id` e `item_id`. En p21 `n5`, `literal_text`
termina en `SALUID` y `normalized_text` en `SALUD`. En los otros 85 registros
ambos campos coinciden según el cotejo. `normalized_text` sirve como ayuda de
búsqueda y lectura; nunca se presenta como cita literal. El estado
`bounded_nonblind_review` significa revisión posterior con el candidato
visible, no validación ciega ni fidelidad global del documento.

## Canal local

Contrato `expertogobernanza/skopos-graph-labels/v0.5-local`; host
`skopos/pdf-graph-labels-host/v0.5-local`. Las operaciones y forma del sobre
son las de v0.4: `describe_graph_labels`, `get_graph_labels_page` (p18–22) y
`fetch_graph_label_item`. La configuración privada
`runs/pdf-document-imss-pilot-v1/graph-labels-v05-host.json` fija hashes de
host, proyector, anotaciones, manifiesto y configuración padre v0.4. Se usa
el mismo Mongo exclusivo, fuente y políticas de custodia/derivación; la
política vence `2026-11-08T00:00:00Z`. No se añaden vectores, LLM, red ni
admisión al corpus.

El host revalida padre, PDF, política, hashes y render antes de devolver una
página o ítem. La consulta del agente debe informar página física, caja e ID.
El operador o agente debe cotejar visualmente cada fragmento nuevo antes de
citarlo como texto normativo. Un rótulo validado aquí no demuestra vigencia
institucional de atribuciones.
