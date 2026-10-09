# Revisión visual de organigramas PDF v0.3 — contrato experimental

**Estado:** implementado y probado bajo demanda en el Mac del piloto.
Productor: Skopos. Consumidor candidato: expertoGobernanza. No constituye
adjudicación institucional, admisión al corpus ni operación continua.
Conserva inmutables los derivados v0.1 y el host de rótulos v0.2.

## Identidad, alcance y autoridad

- `contract_id=expertogobernanza/skopos-graph-review`,
  `contract_version=v0.3-experimental`, respuesta
  `schema=skopos/pdf-graph-review-host/v0.3-experimental`.
- Fuente original SHA-256:
  `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
- Padre gráfico v0.1: derivación
  `1ef12d5a480075214369e9d19dcb6949370119e212b84007ce1b1a5ef1b7b8cf`,
  manifiesto SHA-256
  `8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee`.
- Revisión visual no ciega SHA-256
  `6cabc661d0af44dafdc2859a64623317ac4d3a01f39b2feaf835c54862c8f058`.
- Nuevo derivado `3cd64933f11b0e64733565b4c7acf99423bca129fc7ee5526daf35962cd8504c`;
  manifiesto SHA-256
  `5b6db3341f0f6058356de157ea5bab74bbffeceb9d38cfb0892869f25d076884`,
  guardado en `docs/evidencia/pdf-imss-graph-review-v0.3-experimental.json`.
- Configuración privada del host bajo la raíz ya preparada del piloto:
  `runs/pdf-document-imss-pilot-v1/graph-review-host.json`, digest canónico
  `8ee6ec7b550dfcee2eb244425d39f8af8a15301fc89a074214eebfb695c02515`.
  Fija rutas exactas y hashes del manifiesto, revisión, proyector y host.

La fuente, base Mongo, `requests_root` y retención son las aceptadas por la
política documental v0.1 y la política de rótulos v0.2. No se agregan raíces,
egress, LLM ni almacenamiento de respuestas. Vence
`2026-11-08T00:00:00Z`; el host bloquea al vencer, no renueva. Los sobres y
solicitudes que escribe el consumidor sí persisten en `requests_root` bajo
`block_then_explicit_retirement`. El manifiesto v0.3 queda versionado en Git.

## Significado de la proyección

Sólo páginas físicas 18–22. Cada nodo lleva `node_id`, `item_id` nuevo,
`parent_item_id` del v0.1, caja, `raw_ocr_label` intacto y, para cinco
rótulos cotejados, `visual_label_candidate` con
`review_status=nonblind_visual_candidate`. Los demás conservan
`review_status=unreviewed`; texto vacío no se rellena por inferencia.

Cada arista lleva `item_id` nuevo, extremos por `node_id` e `item_id`,
`origin=v0.1_topology_hypothesis|nonblind_visual_review`,
`status=visual_candidate_unadjudicated` y
`direction=layout_parent_to_child_candidate`. Esta dirección describe la
posición en el dibujo, no acredita mando jurídico ni reporte funcional.
El manifiesto incluye 81 pares candidatos: 45 heredados y 36 añadidos por
la autorrevisión. Cada página conserva `render_sha256` y
`coverage.graph_status=partial`. **La lista completa de la autorrevisión no
es una lista institucional adjudicada.** El recibo visual documenta los 81
pares y los rótulos con `node_id`/`item_id`.

`derivation_id` es SHA-256 canónico de esquema, derivación padre, hash del
manifiesto padre y hash de la revisión. Los `item_id` nuevos vinculan
derivación, página y extremos o nodo padre. El host recomputa el derivado a
partir de los padres fijados y rechaza una discrepancia del archivo servido.

## Handshake y recuperación

El consumidor escribe solicitud JSON y sobre correlacionado bajo el
`requests_root` preautorizado, ambos modo 0600. El socket privado
`graph-review.sock` recibe una línea JSON
`{"envelope_ref":"nombre.envelope.json"}`. El sobre exige exactamente
`request_file_ref`, `request_sha256`, `request_id`, `contract_id` y
`contract_version`; el hash corresponde a los bytes de la solicitud.
Toda solicitud incluye `contract_id`, `contract_version`, `request_id`,
`project_id=expertogobernanza`, `operation`, `source` exacto con sus cinco
campos de custodia y `graph_config_sha256`.

| Operación | Campos adicionales | Respuesta |
| --- | --- | --- |
| `describe_graph_review` | ninguno | identidad del derivado y padre, páginas, fuente, retención y estado |
| `get_graph_review_page` | `derivation_id`, `manifest_sha256`, `page_number` | página completa, nodos/aristas, fuente y estado |
| `fetch_graph_review_item` | `derivation_id`, `manifest_sha256`, `item_id` | nodo o arista exacto, página, modalidad, `render_sha256`, fuente y estado |

Cada respuesta válida repite `request_id` y `request_sha256`. Antes de servir,
el host revalida política y caducidad, recibo Mongo y bytes del PDF y ficha,
manifiesto padre, revisión, proyección y PNG de la página. Ante fallo no
devuelve contenido parcial. Reenviar el mismo sobre con los mismos bytes
produce la misma respuesta mientras fuente y políticas sigan vigentes.

Rechazos tipados observados: `source_mismatch`, `graph_identity_mismatch`,
`page_out_of_scope`, `evidence_unavailable`; también se comprueban
`request_hash_mismatch`, `graph_config_mismatch`, integridad de manifiesto,
render y políticas. Respuesta máxima 64 KiB; `response_limit_exceeded` falla
sin contenido. El host no ofrece búsqueda, citas jurídicas, escritura de
revisiones ni promoción de `visual_candidate_unadjudicated`.

## Procedimiento bilateral

En Skopos, desde `/Users/krisnova/www/aria/skopos`, ejecutar un solo bloque
en Bash. Usa el controlador del Mongo dedicado existente y siempre apaga
los procesos propios. Falla si un controlador previo está activo.

```bash
bash <<'BASH'
set -euo pipefail
umask 077
cd /Users/krisnova/www/aria/skopos
pilot=$PWD/runs/pdf-document-imss-pilot-v1
host_pid=
mongo_started=0
cleanup() {
  result=$?
  trap - EXIT
  if [[ -n "$host_pid" ]]; then
    kill -TERM "$host_pid" 2>/dev/null || true
    wait "$host_pid" 2>/dev/null || true
  fi
  if [[ "$mongo_started" == 1 ]]; then
    .venv/bin/python scripts/pdf_custody_pilot.py stop || result=1
  fi
  [[ ! -e "$pilot/graph-review.sock" ]] || result=1
  exit "$result"
}
trap cleanup EXIT
.venv/bin/python scripts/pdf_custody_pilot.py preflight
.venv/bin/python scripts/pdf_custody_pilot.py start
mongo_started=1
.venv/bin/python -m skopos.pdf_graph_review_host serve \
  --config "$pilot/graph-review-host.json" \
  > "$pilot/graph-review-host.stdout.log" 2>&1 &
host_pid=$!
ready=0
for _ in {1..50}; do
  if ! kill -0 "$host_pid" 2>/dev/null; then break; fi
  if .venv/bin/python - "$pilot/graph-review.sock" <<'PY' >/dev/null 2>&1
import socket, sys
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(1)
    connection.connect(sys.argv[1])
PY
  then ready=1; break; fi
  sleep 0.2
done
[[ "$ready" == 1 ]] || { cat "$pilot/graph-review-host.stdout.log"; exit 1; }
.venv/bin/python scripts/pdf_graph_review_smoke.py
# Ejecutar aquí el cliente independiente de expertoGobernanza contra el
# mismo socket, con los cinco campos de fuente y los pins de arriba.
BASH
```

El smoke local recupera las cinco páginas, un nodo corregido y una arista
añadida p22, prueba cinco rechazos y replay. El consumidor debe cotejar
`render_sha256`, `parent_item_id`, extremos y estado con el PDF antes de
usar una relación. Una lectura independiente o una decisión del Operador
sería una etapa posterior; este contrato no la presume.
