#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="${HERMES_HOME:-/opt/t1000/home}"
export HERMES_BIN="${HERMES_BIN:-/opt/t1000/venv/bin/hermes}"
export DISTILLERY_INTAKE_DIR="${DISTILLERY_INTAKE_DIR:-/opt/t1000/home/distillery-intake}"

exec /opt/t1000/venv/bin/python /opt/t1000/src/scripts/t1000_distillery_review_apply.py "$@"
