#!/usr/bin/env bash
# Cron wrapper: Distillery review (cluster+judge) pass against the canonical
# store. Writes reviews/<date>.md AND one HUMAN card on the `distillery`
# board (create → block needs_input); Ryan answers on the card and
# t1000_distillery_review_apply.py applies it (mesh t_d3afec09).
set -euo pipefail
export HERMES_HOME="${HERMES_HOME:-/opt/t1000/home}"
exec /opt/t1000/venv/bin/python /opt/t1000/src/scripts/distillery_review_agent.py \
  --intake-dir /opt/t1000/home/distillery-intake \
  --repo-root /opt/t1000/src \
  --pending-cache /opt/t1000/home/cache/distillery-review-pending.json \
  --batch-size 24 \
  --card-board distillery \
  --hermes-bin /opt/t1000/venv/bin/hermes \
  --hermes-home /opt/t1000/home "$@"
