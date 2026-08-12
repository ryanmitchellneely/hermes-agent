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

SCHEDULE="${TELEMETRY_DIGEST_SCHEDULE:-30 8 * * *}"
DELIVER="${TELEMETRY_DIGEST_DELIVER:-telegram}"
NAME="${TELEMETRY_DIGEST_JOB_NAME:-telemetry-digest}"

[ -x "$LAUNCHER" ] || { echo "not executable: $LAUNCHER" >&2; exit 2; }

# Absolute path on purpose: `--script` resolves RELATIVE paths under
# $HERMES_HOME/scripts/, and this launcher lives in the repo.
cmd=(hermes cron add "$SCHEDULE"
     --name "$NAME"
     --script "$LAUNCHER"
     --no-agent
     --deliver "$DELIVER")

if [ "$CONFIRMED" = "1" ]; then
  exec "${cmd[@]}"
fi

{
  printf 'DRY RUN — nothing armed. Would create:\n\n  '
  printf '%q ' "${cmd[@]}"
  printf '\n\nDelivery target: %s (TELEMETRY_DIGEST_DELIVER to change).\n' "$DELIVER"
  printf 'Re-run with --yes to create it.\n'
} >&2
