# Rótulos de organigramas PDF v0.4 — contrato experimental

**Estado:** proyección versionada y host local probados bajo demanda en Skopos.
Consumidor candidato: expertoGobernanza. No modifica v0.3, no adjudica la
estructura institucional y no admite contenido al corpus.

## Identidad y significado

- Fuente PDF IMSS SHA-256 `719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
- Grafo padre v0.3, derivación `3cd64933f11b0e64733565b4c7acf99423bca129fc7ee5526daf35962cd8504c`,
  manifiesto SHA-256 `5b6db3341f0f6058356de157ea5bab74bbffeceb9d38cfb0892869f25d076884`.
- Anotaciones v0.4 SHA-256 de archivo `95dcb8d3cb40f5f06ec865712d5129d6f55c42ab495461c31bce53e638a94c46`.
- Derivación v0.4 `54ef4a35842a22896b1f881eb9a1c4c6076ac80e469d83dcbafa81f32e6c7e45`;
  manifiesto SHA-256 `07018142b74249edf0bc056f3b10bee5d1d004e43e77f556b3ef745027efaa98`.
- Contrato `expertogobernanza/skopos-graph-labels/v0.4-experimental`;
  respuesta `skopos/pdf-graph-labels-host/v0.4-experimental`.

La proyección lleva 86 rótulos candidatos: ocho de lectura visual no ciega
en p18, 77 reconstruidos de texto nativo dentro de su caja en p19–22 y uno
en p21 con corrección visual explícita de `SALUID` a `SALUD`. Cada registro
conserva `page_number`, `node_id`, `parent_item_id`, `bbox`, `render_sha256`,
`native_joined_label`, `label_candidate`, `method` e `item_id` nuevo. Todos
tienen `status=candidate_unadjudicated`; el manifiesto conserva
`fidelity_status=unreviewed_partial`. El PDF original y v0.3 no se mutan.

El extractor de preparación usa Poppler `pdftotext -bbox-layout` 26.05.0,
centro de palabra dentro de caja con margen de 3 puntos y unión de fragmentos
con distancia horizontal menor a 0.9 puntos. Es una heurística identificada,
no prueba visual completa. La corrección p21 n5 está separada del texto nativo
en los campos del registro. El host sirve el manifiesto fijado y verifica el
PDF/custodia, políticas, padre, anotaciones y manifiesto; al recuperar página
o ítem verifica además el PNG correspondiente. No vuelve a ejecutar el
extractor al consultar.

## Política y recuperación

Se reutilizan fuente, Mongo, `requests_root`, raíces y retención del piloto
v0.1/v0.2. La política vigente vence `2026-11-08T00:00:00Z`. No se añaden
raíces, egress, LLM, vectores, corpus ni almacenamiento de respuestas. Las
solicitudes y sobres del consumidor persisten bajo la política existente de
`requests_root`.

La configuración privada `runs/pdf-document-imss-pilot-v1/graph-labels-host.json`
está bajo raíz preautorizada, modo 0600, digest canónico
`1b21129583a5de8aac2938b00e594df36654452afc6e3c348983387ddd03803b`.
Fija hashes de anotaciones, manifiesto, proyector y host. El socket es
`graph-labels.sock` en la misma raíz. El servidor opera sólo mientras se
inicia expresamente.

El consumidor escribe una solicitud JSON y un sobre correlacionado 0600 en
`requests_root`, como en el [contrato gráfico v0.3](pdf-graph-review-v0.3-experimental.md).
Envía una línea JSON al socket con `envelope_ref`. El sobre lleva exactamente
`request_file_ref`, `request_sha256`, `request_id`, `contract_id` y
`contract_version`. Toda solicitud lleva `contract_id`, `contract_version`,
`request_id`, `project_id=expertogobernanza`, `operation`, los cinco campos
exactos de `source` y `labels_config_sha256`.

| Operación | Campos adicionales | Resultado |
| --- | --- | --- |
| `describe_graph_labels` | ninguno | identidad del derivado y padre, fuente, páginas, retención, estado |
| `get_graph_labels_page` | `derivation_id`, `manifest_sha256`, `page_number` | página y rótulos candidatos |
| `fetch_graph_label_item` | `derivation_id`, `manifest_sha256`, `item_id` | registro exacto, página, render y fuente |

Las respuestas válidas repiten `request_id` y `request_sha256`. Un mismo sobre
y bytes dan la misma respuesta mientras políticas y fuente sigan vigentes.
Si falta identidad, fuente, render o política, la respuesta no contiene un
rótulo parcial. Límite de respuesta: 64 KiB; si se excede,
`response_limit_exceeded`.

## Ejecución y cotejo bilateral

Desde `/Users/krisnova/www/aria/skopos`, en Bash, ejecutar un único bloque.
El controlador del Mongo dedicado se apaga aun si falla el smoke. No ejecuta
un servicio continuo.

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
  [[ ! -e "$pilot/graph-labels.sock" ]] || result=1
  exit "$result"
}
trap cleanup EXIT
.venv/bin/python scripts/pdf_custody_pilot.py preflight
.venv/bin/python scripts/pdf_custody_pilot.py start
mongo_started=1
.venv/bin/python -m skopos.pdf_graph_labels_host serve \
  --config "$pilot/graph-labels-host.json" \
  > "$pilot/graph-labels-host.stdout.log" 2>&1 &
host_pid=$!
ready=0
for _ in {1..50}; do
  if ! kill -0 "$host_pid" 2>/dev/null; then break; fi
  if .venv/bin/python - "$pilot/graph-labels.sock" <<'PY' >/dev/null 2>&1
import socket, sys
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.connect(sys.argv[1])
PY
  then ready=1; break; fi
  sleep 0.2
done
[[ "$ready" == 1 ]] || { cat "$pilot/graph-labels-host.stdout.log"; exit 1; }
.venv/bin/python scripts/pdf_graph_labels_smoke.py
# Ejecutar aquí el cliente independiente de expertoGobernanza.
BASH
```

El cliente debe cotejar `parent_item_id`, página, caja, `render_sha256`,
texto candidato y método con el PDF. Un cotejo independiente de los 86
rótulos permitiría medir acuerdo con un denominador explícito. El smoke
del productor comprueba transporte e identidad; no convierte las etiquetas
en hechos aprobados ni demuestra un porcentaje de exactitud visual.
