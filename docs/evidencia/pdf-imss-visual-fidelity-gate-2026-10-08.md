# IMSS 2000-002-001: gate visual acotado — 2026-10-08

## Protocolo fijado antes del cotejo visual

Fuente: PDF custodiado por expertoGobernanza, SHA-256
`719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
Derivado nativo: `372fdaef7fb1171ec8dce708b79ef1e32b38e43dfb1b079e6b27ae070d8f7587`,
manifiesto SHA-256
`7f81b1616b10549439cd536737e76663cfea7cec3bf7a6ec3fbf10241d8292ed`.
Derivado de grafo p18–22:
`1ef12d5a480075214369e9d19dcb6949370119e212b84007ce1b1a5ef1b7b8cf`,
manifiesto SHA-256
`8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee`.

### Páginas textuales

Muestra predefinida de ocho páginas físicas: **2, 8, 17** en el tramo
introductorio; **23, 61, 100, 145, 188** en funciones. Incluye el inicio,
el último folio previo al organigrama, el primer folio posterior, el último,
y p61 por ser el mínimo de concordancia técnica pypdf/PDFKit en la auditoría
del consumidor. La elección es deliberada y no aleatoria; no extrapolar al
documento completo.

En cada página: excluir por caja normalizada las líneas cuyo borde superior
sea `<=0,14` o cuyo borde inferior sea `>=0,90`; ordenar las líneas nativas
restantes por la secuencia almacenada y elegir posiciones
`floor((N-1)*q)` con q=0,25; 0,50; 0,75. El denominador previsto es
**24 líneas** y todas las palabras legibles en sus respectivas cajas
visuales. Renderizar a 200 DPI y conservar para cada unidad `page_number`,
`item_id`, `bbox`, texto Skopos, transcripción visual y decisión. Comparar
palabras con NFKC, minúsculas y puntuación ignorada; contar sustituciones,
omisiones e inserciones mediante distancia de edición de palabras. Si la
caja corta el texto o es ambigua, marcar `unassessable`, conservarla en el
denominador de selección y no puntuar sus palabras. Reportar numerador,
denominador evaluable y exclusiones; una coincidencia no prueba precisión de
líneas no seleccionadas. El cotejo visual lo realiza la misma instancia que
preparó el gate: autorrevisión, sin adjudicación independiente.

### Organigramas

Revisar **todas** las páginas 18–22, sin muestreo. Unidad de rótulo: cada
caja visual de organización legible; unidad de relación: cada conexión
visible entre dos cajas. Enumerar ambas sobre la imagen antes de comparar
con el grafo. Para una arista se exige continuidad visible del trazo y
extremos identificables; la mera proximidad o alineación no basta. Registrar
aristas omitidas, aristas emitidas sin respaldo, dirección incierta y rótulos
OCR erróneos por página con `node_id`/`item_id`/`connector_id` cuando existan.
Si alguna relación no puede justificarse, el veredicto de grafo sigue
`partial`; no completar por inferencia.

## Resultado observado

Se renderizaron las 13 páginas a 200 DPI con `pdftoppm` sobre el PDF fijado.
Las imágenes temporales se usaron para inspección y no se incorporaron al
repositorio; las cajas normalizadas y la selección están en el
[`recibo JSON`](pdf-imss-visual-self-review-2026-10-08.json). El recibo
contiene la transcripción visual realizada por esta misma instancia, con el
texto extraído a la vista. El ejecutor
[`pdf_visual_fidelity_gate.py`](../../scripts/pdf_visual_fidelity_gate.py)
comprueba selección, identidades, transcripción y pares de nodos.

| Modalidad y denominador | Observación | Veredicto limitado |
| --- | --- | --- |
| Texto nativo: 24 líneas, 264 palabras de referencia visual en ocho páginas | 0 ediciones de palabra frente a los recortes; 24/24 líneas concordaron | Concordancia diagnóstica de la muestra, no porcentaje estimado para las 188 páginas |
| Detección de cajas de organigrama: 86 cajas contadas en cinco páginas | 86 nodos en el derivado | Cobertura de cajas en este cotejo; rótulos OCR no adjudicados |
| Relaciones visuales: 81 pares anotados, uno por caja salvo la raíz de cada página | 45 pares emitidos; faltan 36; 0 pares emitidos fuera del mapa visual de esta autorrevisión | `partial`; ninguna arista se promueve a relación aceptada |

Desglose de relaciones por página (`visibles / emitidas / omitidas`): p18
`7 / 7 / 0`, p19 `31 / 19 / 12`, p20 `9 / 9 / 0`, p21 `18 / 5 / 13`, p22
`16 / 5 / 11`. Los pares visuales completos y sus extremos `node_id` están
en el JSON. Contraejemplos visibles que faltan en el manifiesto: p19
`n2→n3` (Unidad de Atención Médica a una coordinación); p21 `n3→n7`
(Coordinación de Innovación a División de Proyectos); p22 `n3→n8`
(Coordinación de Gestión de Calidad a División de Gestión de Calidad).
Esos pares son observaciones visuales de esta instancia, no nuevas aristas
del producto. p22 tiene ramales inferiores que el derivado omite; su `n6`
reduce «Coordinación de Planeación de Infraestructura Médica» a `MÉDICA`.
Hay un rótulo OCR erróneo o vacío registrado con `item_id` en **cada** una
de las cinco páginas, incluido p18 y p20 aunque sus conteos de pares coincidan.

Con Mongo y host bajo demanda, `visual_receipt_gate_passed` recuperó por
`fetch_evidence` los 24 `item_id` de texto y cinco nodos usados como
contraejemplos OCR. La misma sesión apagó host y Mongo; no quedaron sockets
activos. Un control positivo del recibo pasó, y mutaciones en memoria de
`item_id`, eliminación de un par visual y adición de un nodo inexistente
fallaron con `sample_identity`, `visual_edge_count` y `visual_child`.

**Límite:** la transcripción fue no ciega y la revisión del grafo fue una
autorrevisión; el código comprueba consistencia y recuperación de la
anotación, no si el ojo leyó bien la imagen. El 0/264 es una medida local
de concordancia de palabras de la muestra deliberada, no una fidelidad
certificada. El 45/81 tampoco acredita esas 45 relaciones como verdad del
organigrama: el manifiesto las sigue marcando `topology_hypothesis`.
Se requiere cotejo independiente para usar rótulos o relaciones como hechos
institucionales. La política vigente vence `2026-11-08T00:00:00Z` y esta
ronda no la renueva.
