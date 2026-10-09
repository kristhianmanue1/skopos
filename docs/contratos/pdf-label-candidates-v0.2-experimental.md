# Candidatos de rótulo PDF v0.2 — contrato experimental local

**Estado:** implementado para ensayo bilateral, sin aceptación de fidelidad,
admisión al corpus ni operación continua. No sustituye el contrato
`expertogobernanza/skopos-document-derivatives/v0.1` ni cambia sus
manifiestos. Productor: Skopos; consumidor candidato: expertoGobernanza.

## Alcance y autoridad

`contract_id=expertogobernanza/skopos-label-candidates`,
`contract_version=v0.2-experimental`, respuesta
`schema=skopos/pdf-label-host/v0.2-experimental`. El host lee una política
propia desde `runs/pdf-document-imss-pilot-v1/label-policy.json`, vinculada
al digest de la política de derivados v0.1. La configuración fija por SHA:

| Vínculo del piloto | Valor |
| --- | --- |
| Política de rótulos | `21540db84c1b6b10cdbd433392caa6ed66b26d9820814c227d2d08dec948be1d` |
| Política de derivados v0.1 | `4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b` |
| Manifiesto gráfico v0.1 | `8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee` |
| Original custodiado | `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323` |

El manifiesto fijado contiene sólo las páginas físicas **18–22**. P1 queda
fuera: su OCR pertenece a otro derivado v0.1 y no tiene nodos de grafo en
éste. Cada solicitud admite una página y hasta 40 nodos; respuesta máxima
64 KiB. El host usa el socket Unix privado `label.sock`, sin egress, LLM ni
búsqueda vectorial. No acepta nuevas raíces, otro PDF, revisión o política
desde una solicitud. La vigencia `2026-11-08T00:00:00Z` se hereda de la
política aceptada v0.1; vencer bloquea, no renueva ni retira archivos.
La política fija además SHA-256 de este host y de la proyección de candidatos;
un cambio de código exige nueva política y digest, no reutilizar el anterior.

## Handshake y consulta

El consumidor escribe un JSON y un sobre correlacionado bajo el
`requests_root` **preautorizado**. El socket recibe sólo
`{"envelope_ref":"ruta-relativa-del-sobre"}`. El sobre tiene exactamente
`request_file_ref`, `request_sha256`, `request_id`, `contract_id` y
`contract_version`; el SHA se calcula sobre bytes del JSON de solicitud.
El host coteja los tres identificadores con el contenido. No admite rutas
absolutas o symlinks como referencias de solicitud.

`describe_label_capabilities` recibe `request_id`, contrato/version,
`project_id`, `operation`, `source` y `label_policy_sha256`. Anuncia páginas,
límites, digests, `fidelity_status`, vencimiento y retención **real** de
solicitudes. Comprueba antes el recibo de custodia y los bytes actuales de
PDF y ficha.

`get_label_candidates` añade `derivation_id`, `manifest_sha256`,
`page_number` y `max_nodes`. `source` conserva exactamente `material_id`,
`source_revision`, `source_sha256`, `custody_receipt_id` y
`custody_policy_sha256`. Para este piloto los IDs y hashes son los de la
política; `page_number` debe estar en 18–22. El host vuelve a cargar las
políticas, comprueba la fuente contra Mongo y bytes, coteja manifiesto y
digest lateral, y rehashea el PNG exacto antes de devolver cajas.

Cada respuesta `ok` repite `request_id` y `request_sha256`; incluye
`derivation_id`, SHA del manifiesto, SHA de política de rótulos, SHA de
original, página y `render_sha256`. Cada nodo tiene `node_id`,
`parent_item_id`, `bbox` normalizada y **dos** `label_candidates`:
`native_text` y `selective_ocr`, sin fusión ni preferencia implícita.
Cada candidato conserva `text`, `line_item_ids`, `line_bboxes` y estado
`unreviewed|no_lines`. Un texto vacío es dato faltante, no un rótulo válido.
`fidelity_status=unreviewed` cubre toda la respuesta.
La asociación de líneas a una caja usa el **centro** de la caja de línea
dentro de la caja de nodo del manifiesto; es una proyección geométrica,
no una transcripción validada ni una corrección de errores del motor.

La respuesta copia aristas y conectores no resueltos del manifiesto padre
para localización, pero `coverage.graph_status=partial` y
`topology_completeness=unreviewed_partial` impiden leer la lista como
inventario completo. `connector_count`, `edge_count` y
`unresolved_connector_count` describen lo detectado, **no** la recuperación
frente a una verdad visual independiente. El número de conectores omitidos
es desconocido. También se declaran `missing_native_labels` y
`missing_ocr_labels` por página.

## Persistencia y recuperación

El host de rótulos no escribe proyecciones ni respuestas en disco. **Sí
persisten** los JSON/sobres que escribe el consumidor bajo el
`requests_root` existente; su retención es la de la política de derivados
v0.1 (`block_then_explicit_retirement`, hasta 2026-11-08). Los manifiestos y
renders v0.1 ya persistidos permanecen intactos. El protocolo no ofrece
borrado automático ni recibo nuevo en Mongo.

Si se pierde una respuesta, el consumidor puede reenviar **el mismo**
`envelope_ref` y `request_sha256`. La consulta se recalcula sin reejecutar
OCR ni escribir un derivado. Bajo los mismos bytes/políticas entrega la
misma respuesta, incluso tras reiniciar. `request_id` correlaciona;
la identidad de replay incluye los bytes/SHA de la solicitud. No se promete
un registro global de unicidad de `request_id` para solicitudes distintas.

## Errores y límites de uso

Rechazos tipados: `page_out_of_scope`, `limit_exceeded`,
`label_policy_mismatch`, `document_policy_mismatch`, `source_mismatch`,
`manifest_mismatch`, `manifest_integrity_failed`, `render_integrity_failed`,
`request_hash_mismatch`, `request_mismatch` y errores heredados de custodia.
Un cambio en el host o en la proyección frente a sus hashes de política
produce `label_engine_mismatch`.
No se devuelve una lista parcial de candidatos ante cualquiera de ellos.
La política y el documento se revalidan por consulta. La respuesta puede
fallar `response_limit_exceeded` sin contenido si supera el presupuesto.

La medición p20 de 7/10 rótulos nativos y 1/10 OCR proviene de la
autorreferencia experimental de una página. No certifica p18–22 ni 188
páginas, vigencia normativa, exhaustividad del grafo, validez de citas ni
admisión al corpus. expertoGobernanza debe cotejar visualmente cada uso.
