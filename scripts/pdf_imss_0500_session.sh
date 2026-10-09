#!/usr/bin/env bash
# Sesión local bajo demanda para ambos manuales IMSS; no instala servicios.
set -euo pipefail
umask 077

cd "$(dirname "$0")/.."
pilot="$PWD/runs/pdf-imss-0500-pilot-v1"
legacy="$PWD/runs/pdf-document-imss-pilot-v1"
controller_started=0
custody_pid=
document_pid=
legacy_pid=

cleanup() {
  result=$?
  trap - EXIT
  for pid in "$legacy_pid" "$document_pid" "$custody_pid"; do
    if [[ -n "$pid" ]]; then
      kill -TERM "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  if [[ "$controller_started" == 1 ]]; then
    if ! .venv/bin/python scripts/pdf_custody_pilot.py stop; then result=1; fi
  fi
  for socket in "$pilot/custody.sock" "$pilot/document.sock" "$legacy/document.sock"; do
    if [[ -e "$socket" ]]; then
      echo "socket_stop_not_confirmed:$socket" >&2
      result=1
    fi
  done
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ $# -eq 0 ]]; then
  echo 'usage: pdf_imss_0500_session.sh command [args...]' >&2
  exit 2
fi

.venv/bin/python scripts/pdf_custody_pilot.py preflight
.venv/bin/python - <<'PY'
from pathlib import Path
from skopos.pdf_custody import load_policy
from skopos.pdf_document_policy_v02 import load_document_policy_v02
root = Path('runs/pdf-imss-0500-pilot-v1').resolve()
load_policy(str(root / 'custody-policy.json'))
load_document_policy_v02(str(root / 'document-policy.json'))
PY
.venv/bin/python scripts/pdf_custody_pilot.py start
controller_started=1

.venv/bin/python -m skopos custody-host serve --config "$pilot/custody-host.json" \
  > "$pilot/custody-host.log" 2>&1 &
custody_pid=$!
.venv/bin/python -m skopos document-host serve --config "$pilot/document-host.json" \
  > "$pilot/document-host.log" 2>&1 &
document_pid=$!
.venv/bin/python -m skopos document-host serve --config "$legacy/host.json" \
  > "$pilot/legacy-document-host.log" 2>&1 &
legacy_pid=$!

for socket in "$pilot/custody.sock" "$pilot/document.sock" "$legacy/document.sock"; do
  ready=0
  for _ in {1..50}; do
    if [[ -S "$socket" ]]; then ready=1; break; fi
    if ! kill -0 "$custody_pid" 2>/dev/null ||
       ! kill -0 "$document_pid" 2>/dev/null ||
       ! kill -0 "$legacy_pid" 2>/dev/null; then
      break
    fi
    sleep 0.2
  done
  if [[ "$ready" != 1 ]]; then
    echo "host_start_failed:$socket" >&2
    exit 1
  fi
done

"$@"
