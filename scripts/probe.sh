#!/usr/bin/env bash
#
# probe.sh - inspect the Smart Pool Connect REST API with plain curl.
#
# Read-only: it only performs GET requests and never changes pool state.
#
# Usage:
#   SPC_KEY='spc_xxx' ./scripts/probe.sh            # list pools
#   SPC_KEY='spc_xxx' ./scripts/probe.sh <pool-id>  # full state + per-module
#
set -euo pipefail

BASE="${SPC_BASE:-https://api.smartpoolconnect.eu}"
KEY="${SPC_KEY:?set SPC_KEY (starts with spc_)}"
PID="${1:-}"

auth=(-H "X-API-Key: $KEY" -H "Accept: application/json")

if [ -z "$PID" ]; then
  echo "== GET /pool =="
  curl -s "${auth[@]}" "$BASE/pool" | jq '.items[] | {pid, name, status, mac_address}'
  echo
  echo "Pass a pool id as the first argument to dump its full state."
  exit 0
fi

echo "== GET /pool/$PID =="
curl -s "${auth[@]}" "$BASE/pool/$PID" | jq .

for m in ph cl filter temperature lighting cover; do
  echo "== GET /pool/$PID/$m =="
  curl -s "${auth[@]}" "$BASE/pool/$PID/$m" | jq '{status, config}'
done
