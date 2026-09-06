#!/usr/bin/env bash
# Hermes no-agent cron entrypoint for the local-vs-frontier savings ledger.
#
# Must live as a REAL FILE under $HERMES_HOME/scripts (not a symlink).
# Stdout is the delivery body under --no-agent; chatter goes to stderr.
set -uo pipefail
export HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
SCRIPT="$HERMES_HOME/scripts/local_savings_ledger.py"
if [ ! -f "$SCRIPT" ]; then
  echo "local-savings-cron: missing $SCRIPT" >&2
  exit 2
fi
# Whole-store backfill keeps the series idempotent as jsonl rotates.
export T1000_TELEMETRY_DIR="${T1000_TELEMETRY_DIR:-/opt/t1000/home/.t1000/telemetry}"
exec python3 "$SCRIPT" --backfill --compact "$@"
