#!/usr/bin/env bash
#
# probe.sh - inspect the Smart Pool Control portal with plain curl.
#
# Useful for debugging / re-discovering the HTML structure the integration
# scrapes. It only performs GET requests (it never changes pool state).
#
# Usage:
#   SPC_USER='you@example.com' SPC_PASS='secret' ./scripts/probe.sh
#
set -euo pipefail

BASE="${SPC_BASE:-https://owner.smartpoolcontrol.eu}"
USER="${SPC_USER:?set SPC_USER}"
PASS="${SPC_PASS:?set SPC_PASS}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

echo "Fetching login page..."
PAGE=$(curl -s -c "$JAR" "$BASE/login/")
TOKEN=$(echo "$PAGE" | sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p')

echo "Logging in..."
curl -s -o /dev/null -b "$JAR" -c "$JAR" -e "$BASE/login/" \
  --data-urlencode "csrfmiddlewaretoken=$TOKEN" \
  --data-urlencode "username=$USER" \
  --data-urlencode "password=$PASS" \
  "$BASE/login/"

echo "Discovering pool id..."
POOL_URL=$(curl -s -o /dev/null -w '%{url_effective}' -L -b "$JAR" "$BASE/")
POOL_ID=$(echo "$POOL_URL" | sed -n 's#.*/pools/measurements/\([0-9]*\)/.*#\1#p')
echo "Pool id: $POOL_ID"

echo "Measurements page (stripped):"
curl -s -b "$JAR" "$BASE/pools/measurements/$POOL_ID/" \
  | sed -n 's/<[^>]*>//gp' | grep -vE '^[[:space:]]*$' | head -40
