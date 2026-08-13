#!/usr/bin/env bash
# Arm the daily usage digest as a Hermes NO-AGENT cron job.
#
# This is the only path that puts the digest in front of a human. The launchd
# plist in this directory refreshes the surface on disk and writes its stdout
# to a LOG FILE — useful, but nobody reads a log file, and the decision flags
# this digest exists to raise would reach no one. A Hermes no-agent cron runs
# the same launcher and delivers its stdout verbatim to the configured target.
#
# No LLM is involved: no_agent means the script IS the job (no tokens, no
# agent loop), so this costs nothing per fire.
#
# DRY RUN BY DEFAULT — it prints the command and exits. Pass --yes to actually
# create the job, because arming it starts a recurring outbound message.
#
#   ./arm-hermes-cron.sh              # show what would be created
#   ./arm-hermes-cron.sh --yes        # create it
#   TELEMETRY_DIGEST_DELIVER=local ./arm-hermes-cron.sh --yes   # save, no send
#
# Disarm:  hermes cron list  →  hermes cron remove <job_id>
set -euo pipefail

CONFIRMED=0
for arg in "$@"; do
  case "$arg" in
    --yes) CONFIRMED=1 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $arg (only --yes)" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$HERE/telemetry-digest.sh"
WRAPPER_SRC="$HERE/telemetry_digest_cron.sh"

SCHEDULE="${TELEMETRY_DIGEST_SCHEDULE:-30 8 * * *}"
DELIVER="${TELEMETRY_DIGEST_DELIVER:-telegram}"
NAME="${TELEMETRY_DIGEST_JOB_NAME:-telemetry-digest}"

# cron/scheduler.py:_run_job_script requires --script to resolve INSIDE
# $HERMES_HOME/scripts. An absolute path into this repo is resolved and then
# rejected ("Blocked: script path resolves outside the scripts directory"), and
# a symlink is followed back out and rejected the same way — so the wrapper is
# installed as a real file copy and named by its BARE filename.
#
# Cron is per-profile (scheduler resolves HERMES_HOME at call time), so the
# install target is computed here rather than hardcoded: arm this from the same
# profile whose gateway will run the job.
SCRIPTS_DIR="${HERMES_HOME:-$HOME/.t1000}/scripts"
WRAPPER_NAME="$(basename "$WRAPPER_SRC")"
WRAPPER_DST="$SCRIPTS_DIR/$WRAPPER_NAME"

[ -x "$LAUNCHER" ] || { echo "not executable: $LAUNCHER" >&2; exit 2; }
[ -f "$WRAPPER_SRC" ] || { echo "missing wrapper: $WRAPPER_SRC" >&2; exit 2; }

# Preflight the guard itself rather than trusting this comment to stay true.
python3 - "$SCRIPTS_DIR" "$WRAPPER_NAME" <<'PY' || exit 2
import sys
from pathlib import Path
scripts_dir = Path(sys.argv[1]).expanduser().resolve()
target = (scripts_dir / sys.argv[2]).resolve()
try:
    target.relative_to(scripts_dir)
except ValueError:
    sys.exit(f"preflight FAILED: {target} resolves outside {scripts_dir}")
PY

cmd=(hermes cron add "$SCHEDULE"
     --name "$NAME"
     --script "$WRAPPER_NAME"
     --no-agent
     --deliver "$DELIVER")

if [ "$CONFIRMED" = "1" ]; then
  mkdir -p "$SCRIPTS_DIR"
  # Real copy, never a symlink: .resolve() would follow a link back into the
  # repo and the sandbox check would reject it at fire time.
  cp -f "$WRAPPER_SRC" "$WRAPPER_DST"
  chmod +x "$WRAPPER_DST"
  echo "installed wrapper: $WRAPPER_DST" >&2
  exec "${cmd[@]}"
fi

{
  printf 'DRY RUN — nothing armed. Would install:\n\n  %s\n    -> %s\n' \
    "$WRAPPER_SRC" "$WRAPPER_DST"
  printf '\nand create:\n\n  '
  printf '%q ' "${cmd[@]}"
  printf '\n\nDelivery target: %s (TELEMETRY_DIGEST_DELIVER to change).\n' "$DELIVER"
  printf 'Scripts dir: %s (from $HERMES_HOME; cron is per-profile).\n' "$SCRIPTS_DIR"
  if [ "$SCRIPTS_DIR" != "$HOME/.t1000/scripts" ]; then
    printf '\nNOTE: that is NOT %s/.t1000/scripts, where the existing no-agent\n' "$HOME"
    printf 'jobs live. The scheduler resolves $HERMES_HOME at FIRE time, so arm\n'
    printf 'this from the same profile whose gateway runs cron, e.g.:\n'
    printf '  HERMES_HOME=%s/.t1000 %s --yes\n' "$HOME" "${BASH_SOURCE[0]}"
  fi
  printf 'Re-run with --yes to install and create it.\n'
} >&2
