#!/usr/bin/env bash
# Hermes no-agent cron entrypoint for the daily usage digest.
#
# WHY THIS FILE EXISTS AT ALL, rather than pointing --script at the launcher:
# cron/scheduler.py:_run_job_script resolves the --script value and then
# REQUIRES the result to sit inside $HERMES_HOME/scripts:
#
#     if raw.is_absolute(): path = raw.resolve()
#     else:                 path = (scripts_dir / raw).resolve()
#     path.relative_to(scripts_dir_resolved)   # else -> "Blocked: ..."
#
# An absolute path into the repo is NOT exempt from that check — it is
# resolved and then rejected. Verified against the live guard:
#   BLOCKED : ~/Documents/T1000/deploy/telemetry-digest/telemetry-digest.sh
#   ALLOWED : telemetry_digest_cron.sh
# A SYMLINK here does not work either: .resolve() follows it back out of the
# scripts dir and the same check rejects it (the guard names symlink escape
# explicitly). So this must be installed as a REAL FILE COPY under
# $HERMES_HOME/scripts/ — that is what arm-hermes-cron.sh does.
#
# The check runs at FIRE time, not creation time, so getting this wrong does
# not fail loudly when you arm it: the job is created happily and then never
# delivers.
#
# Stdout is the delivery body under `--no-agent`, so everything this wrapper
# says about its own operation goes to stderr.
set -uo pipefail

REPO="${T1000_REPO:-$HOME/Documents/T1000}"
LAUNCHER="$REPO/deploy/telemetry-digest/telemetry-digest.sh"

# Commit the rendered rollup so the surface keeps its own history. The digest
# recomputes week-over-week deltas from model_calls-*.jsonl on every run, so
# once those rows rotate the trend silently loses its past — committing the
# rendered markdown is what gives it a memory. The launcher's commit step is
# pathspec-scoped, refuses git-ignored paths, and NEVER pushes.
# Set to 0 to render without committing.
export TELEMETRY_DIGEST_COMMIT="${TELEMETRY_DIGEST_COMMIT:-1}"

if [ ! -x "$LAUNCHER" ]; then
  echo "telemetry-digest-cron: launcher missing or not executable: $LAUNCHER" >&2
  echo "telemetry-digest-cron: set \$T1000_REPO if the repo lives elsewhere" >&2
  exit 2
fi

# --compact: stdout becomes the delivered message, and a push channel rejects
# a body over its limit outright (Telegram: 4096). The full surface is still
# written to disk in full; only the delivered body is shortened.
exec "$LAUNCHER" --compact "$@"
