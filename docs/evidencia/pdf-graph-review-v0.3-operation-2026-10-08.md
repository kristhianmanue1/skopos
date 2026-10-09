# Ensayo local del grafo IMSS v0.3 — 2026-10-08

**Alcance:** Skopos en este Mac, PDF IMSS SHA-256
`719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`;
padre gráfico v0.1 SHA-256
`8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee`.
Contratos y operación en
[`pdf-graph-review-v0.3-experimental.md`](../contratos/pdf-graph-review-v0.3-experimental.md).

## Construcción e identidad

`src/skopos/pdf_graph_review.py` generó de forma determinista el
[`manifiesto candidato`](pdf-imss-graph-review-v0.3-experimental.json) con
derivación
`3cd64933f11b0e64733565b4c7acf99423bca129fc7ee5526daf35962cd8504c`
y SHA-256 del archivo
`5b6db3341f0f6058356de157ea5bab74bbffeceb9d38cfb0892869f25d076884`.
Conserva los 86 nodos originales por `parent_item_id`, cinco rótulos
visuales candidatos y los 81 pares de la autorrevisión visual: 45 hipótesis
heredadas y 36 pares añadidos. Cada par nuevo tiene `item_id`, página,
extremos y `origin=nonblind_visual_review`; **todos** mantienen
`status=visual_candidate_unadjudicated` y cada página `graph_status=partial`.
No se modificó el manifiesto v0.1.

La configuración privada del host `graph-review-host.json` está en la
raíz ya preparada del piloto, modo 0600; digest canónico
`8ee6ec7b550dfcee2eb244425d39f8af8a15301fc89a074214eebfb695c02515`.
Fija hash de revisión
`6cabc661d0af44dafdc2859a64623317ac4d3a01f39b2feaf835c54862c8f058`,
proyector `3d4b726525f6409a9e5694dccde797dffd6447ba81fb41dfc21731b7eefc9905`
y host `ab0a5d29c973cf1d22c3cd06f906c1e47c9bdf9b479e45869aa40c120cbc8b9b`.
No se amplió la retención; vence `2026-11-08T00:00:00Z`.

## Prueba bajo demanda

Se inició el Mongo dedicado con `pdf_custody_pilot.py start` y el nuevo
host por socket Unix privado. `scripts/pdf_graph_review_smoke.py` obtuvo
`graph_review_smoke_passed`: cinco páginas 18–22, respectivamente
`8/7`, `32/31`, `10/9`, `19/18`, `17/16` nodos/aristas candidatas.
Recuperó individualmente p22 `n10`, rótulo candidato
«COORDINACIÓN TÉCNICA DE INFRAESTRUCTURA MÉDICA», `item_id`
`0d4d3ab6eb4b9df9322e2f2c75684c293e4c91e3d76b93134c01a67490363cb7`;
y el par añadido p22 `n3→n8`, `item_id`
`1cff57242c7ecd53e5f9a3b3c0f1ffc3480a43bc9489f1d29803d0f0cd51ce3b`.
Las respuestas incluyeron fuente, página, hash del render y estado parcial.

Controles negativos: fuente incorrecta `source_mismatch`, manifiesto
incorrecto `graph_identity_mismatch`, página 23 `page_out_of_scope`, ítem
inexistente `evidence_unavailable` y sobre con hash incorrecto
`request_hash_mismatch`. Replay del mismo sobre produjo respuesta idéntica.
Solicitud conservada en la raíz privada:
`de5537fe564bbb54ec1103d8.request.json`, SHA-256
`88c023e64902707cb4d793329b2bb990822cacbbc065373c0f85c7f6a2b587c4`.
Se apagaron host y Mongo; sockets ausentes.

Las pruebas unitarias del proyector comprueban identidad estable, linaje,
inmutabilidad del padre y rechazo de relación, rótulo y nodo ajenos. La
suite completa aislada ejecutó **513 pruebas, OK, sin omisiones**. Los gates
`check_sizes.py` y `check_plans.py` pasaron sobre estos archivos.

## Límite y siguiente control

El host verifica bytes de fuente, política, padre, revisión, manifiesto y
render; **no verifica por visión computacional los trazos del PDF**. El
mapa de 81 pares sigue siendo una anotación no ciega del productor. El
consumidor debe cotejar de forma independiente los extremos y rótulos que
quiera usar, con el PDF visual. Hasta ese control, no se afirma que los
organigramas estén completos ni que cada arista sea institucionalmente
válida. No hubo vectores, corpus ni servicio continuo.
