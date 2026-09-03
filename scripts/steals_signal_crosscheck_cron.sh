#!/usr/bin/env bash
# Cron wrapper: weekly steals-board <-> signal-log cross-check (report-only).
# Silent-when-clean (no-agent cron: empty stdout = no delivery). Mesh t_7a891450.
set -euo pipefail
export HERMES_HOME="${HERMES_HOME:-/opt/t1000/home}"
exec /opt/t1000/venv/bin/python /opt/t1000/src/scripts/steals_signal_crosscheck.py \
  --repo-root /opt/t1000/src \
  --board-db /opt/t1000/home/kanban/boards/steals/kanban.db \
  --state /opt/t1000/home/cache/steals-signal-crosscheck-state.json "$@"
