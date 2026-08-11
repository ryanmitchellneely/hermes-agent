#!/usr/bin/env bash
# Daily model-call usage + success digest.
#
# Writes the markdown surface and the heartbeat status file EVERY run,
# whatever the outcome — a missing or stale heartbeat must unambiguously mean
# "the digest itself is dead", never be confusable with "ran fine, nothing to
# report". Same contract as deploy/kevin-spark/ds4-watchdog.sh.
#
# Stdout is the delivery body (no-agent cron/launchd convention: what it prints
# is what gets delivered). Exit codes:
#   0  digest rendered, calls observed
#   1  NO calls in the window — the emit sites may have stopped firing. This is
#      deliberately an alert: a telemetry digest that silently reports nothing
#      manufactures false confidence, which is worse than no digest at all.
#   2  the digest itself failed; heartbeat carries status=error and the reason.
#
# Uses bare python3 on purpose — telemetry_digest.py degrades to stdlib-only
# (pricing is a soft import) so a broken venv cannot take the surface down.
set -uo pipefail

export HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
REPO="${T1000_REPO:-$HOME/Documents/T1000}"
WINDOW="${TELEMETRY_DIGEST_WINDOW:-24h}"
INTERVAL_S="${TELEMETRY_DIGEST_INTERVAL_S:-86400}"

exec python3 "$REPO/scripts/telemetry_digest.py" \
  --since "$WINDOW" \
  --interval-seconds "$INTERVAL_S" \
  "$@"
