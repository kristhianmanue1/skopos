# Derivados PDF IMSS: operación bajo demanda — 2026-10-08

**Alcance observado:** Skopos `7f01eed9aa699d38de7c4587e5ea19e3cba428de`,
contrato `expertogobernanza/skopos-document-derivatives/v0.1`, política local
`expertogobernanza/imss-2000-002-001-derivatives@v0.1-2026-10-08`, digest
canónico `4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b`.
Usa el PDF ya custodiado por v0.2 y la base exclusiva del piloto. La política
vence `2026-11-08T00:00:00Z`; este procedimiento no la renueva. Sólo opera en
este Mac, con las rutas privadas ya preparadas y la misma cuenta de OS.

## Sesión completa

Ejecutar **un solo bloque** desde una terminal Bash; requiere las venv ya
instaladas. Si hay un controlador o socket previo, `start` falla: no se toma
control de otro proceso. El host de derivados es hijo de esta sesión; la
trampa de salida le envía `SIGTERM`, espera y detiene el Mongo dedicado.
Ningún servicio queda configurado para arranque continuo.

```bash
bash <<'BASH'
set -euo pipefail
umask 077
cd /Users/krisnova/www/aria/skopos
pilot=/Users/krisnova/www/aria/skopos/runs/pdf-document-imss-pilot-v1
consumer=/Users/krisnova/www/expertoGobernanza
policy_sha=4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b
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
    if ! .venv/bin/python scripts/pdf_custody_pilot.py stop; then result=1; fi
  fi
  if [[ -e "$pilot/document.sock" ]]; then
    echo 'document_host_stop_not_confirmed' >&2
    result=1
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

.venv/bin/python scripts/pdf_custody_pilot.py preflight
.venv/bin/python - "$pilot/host.json" "$policy_sha" <<'PY'
import hashlib
import sys
from pathlib import Path
from skopos.pdf_document_host import load_host_config
from skopos.pdf_document_store import _canonical, load_document_policy
config = load_host_config(sys.argv[1])
policy = load_document_policy(config['policy_path'])
actual = hashlib.sha256(_canonical(policy)).hexdigest()
if (actual != sys.argv[2]
        or config['socket_path'] != str(Path(sys.argv[1]).parent / 'document.sock')
        or config['database'] != 'skopos_pdf_imss_pilot_v1'
        or policy['custody_policy_sha256'] !=
           'a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160'):
    raise SystemExit('document_policy_or_host_mismatch')
print('document_policy_ready', actual)
PY

.venv/bin/python scripts/pdf_custody_pilot.py start
mongo_started=1
.venv/bin/python -m skopos document-host serve --config "$pilot/host.json" \
  > "$pilot/document-host.stdout.log" 2>&1 &
host_pid=$!
ready=0
for _ in {1..50}; do
  if ! kill -0 "$host_pid" 2>/dev/null; then break; fi
  if .venv/bin/python - "$pilot/document.sock" <<'PY' >/dev/null 2>&1
import socket
import sys
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(1)
    connection.connect(sys.argv[1])
PY
  then ready=1; break; fi
  sleep 0.2
done
[[ "$ready" == 1 ]] || { echo 'document_host_start_failed' >&2; exit 1; }

for mode in native ocr graph; do
  "$consumer/.venv/bin/python" "$consumer/scripts/skopos_document_pilot.py" \
    --socket "$pilot/document.sock" \
    --requests-root "$consumer/runs/pdf-custody-imss-pilot-v1/requests" \
    --delivery-root "$pilot/delivery" \
    --policy-id expertogobernanza/imss-2000-002-001-derivatives \
    --policy-version v0.1-2026-10-08 \
    --policy-sha256 "$policy_sha" --mode "$mode"
done
BASH
```

Cada modo debe emitir `consumer_smoke_passed` con `derivation_id` y
`manifest_sha256`; un estado `partial` del grafo sigue siendo parcial. El
cliente verifica bytes, procedencia, páginas, búsqueda, evidencia y el
organigrama p20. Los sobres de solicitud y recibos quedan en las raíces
privadas; el cliente retira las copias de entrega que él creó. No borrar
manifiestos, renders o solicitudes para «reiniciar» el ensayo.

## Respuesta perdida o interrupción

Un timeout no demuestra que la derivación falló. Antes de repetir, conservar
el archivo `*.request.json` exacto de `derive_document` que escribió el
cliente y su sobre `*.envelope.json`; comprobar el SHA-256 del archivo contra
`request_sha256` del sobre. Usar esos `request_id` y SHA-256 en
`derivation_receipt` con el mismo `source`. `duplicate` recupera el
`derivation_id` y `manifest_sha256`; `not_found` exige investigar estado del
host antes de un nuevo intento. Si no se puede identificar **una sola**
solicitud original, detenerse: no escoger «la última» en un directorio con
posible concurrencia. La CLI `document-host request` sólo envía un sobre ya
creado bajo la raíz preautorizada; no fabrica políticas ni permisos. El
consumidor puede crear un nuevo sobre para `derivation_receipt` con
`source`, `derivation_request_id` y `derivation_request_sha256` de la solicitud
persistida, y enviarlo mientras el host esté activo:

```bash
.venv/bin/python -m skopos document-host request \
  --socket /Users/krisnova/www/aria/skopos/runs/pdf-document-imss-pilot-v1/document.sock \
  --envelope-ref "$reconcile_envelope_ref"
```

`reconcile_envelope_ref` es una ruta **relativa** a `requests_root`, con
`request_file_ref`, SHA-256, ID y versión correlacionados; no es una ruta
arbitraria ni una autorización para volver a derivar.

Si el bloque se interrumpe, comprobar que `document.sock` y el socket de
control de custodia desaparecieron. Si `stop` informa fallo, examinar los
logs privados y la identidad de procesos antes de reintentar; no borrar un
socket ajeno ni usar `kill` indiscriminado. La base y los derivados persisten
en disco tras la parada, sujetos a sus políticas de retención y retiro.
La trampa cubre salida normal e INT/TERM del shell; SIGKILL, caída del host o
corte de energía requieren reconciliación manual y no prueban parada limpia.

## Ejecución observada y límite

Se ejecutó el bloque de esta guía sobre el commit y digest indicados. El
preflight confirmó ambas políticas; el cliente devolvió
`consumer_smoke_passed` para `native` (188 páginas), `ocr` (6) y `graph` (5),
con los mismos IDs y hashes de manifiesto de la ronda bilateral. La trampa
de salida devolvió `stopped`; después se observaron ambos sockets ausentes
y el puerto Mongo `37034` cerrado. La suite de Skopos pasó 502 pruebas en
Mongo temporal exclusivo antes de esta guía; editar este documento no cambió
el motor probado.

Esa ejecución no certifica fidelidad del OCR ni completitud de relaciones
en p19/21/22. El servicio se activa sólo por demanda. No hubo admisión
jurídica, promoción al corpus ni búsqueda vectorial.
