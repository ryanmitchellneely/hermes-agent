#!/usr/bin/env bash
# Cron wrapper: Distillery intake sweep against the CANONICAL T1000 checkout.
# Silent-when-clean (no-agent cron: empty stdout = no delivery); a missing
# source path exits 2 and is delivered — never a silent zero (mesh t_a4d3ea5b).
set -euo pipefail
export HERMES_HOME="${HERMES_HOME:-/opt/t1000/home}"
exec /opt/t1000/venv/bin/python /opt/t1000/src/scripts/distillery_intake_sweep.py \
  --repo-root /opt/t1000/src \
  --intake-dir /opt/t1000/home/distillery-intake "$@"
