#!/usr/bin/env bash
# Hermes no-agent cron entrypoint for the weekly fleet-economics reader
# (t_da2f74c4, campaign option 3: "one reader, not four instruments").
#
# Must live as a REAL FILE under $HERMES_HOME/scripts (not a symlink), same
# contract as local_savings_ledger_cron.sh. Stdout is the delivery body under
# --no-agent; chatter goes to stderr.
set -uo pipefail
export HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
SCRIPT="/opt/t1000/src/scripts/t1000_fleet_economics_weekly.py"
if [ ! -f "$SCRIPT" ]; then
  echo "fleet-economics-weekly-cron: missing $SCRIPT" >&2
  exit 2
fi
export T1000_TELEMETRY_DIR="${T1000_TELEMETRY_DIR:-/opt/t1000/home/.t1000/telemetry}"
exec /opt/t1000/venv/bin/python "$SCRIPT" "$@"
