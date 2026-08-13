#!/usr/bin/env bash
# Daily model-call usage + success digest.
#
# Writes the markdown surface and the heartbeat status file EVERY run,
# whatever the outcome — a missing or stale heartbeat must unambiguously mean
# "the digest itself is dead", never be confusable with "ran fine, nothing to
# report". Same contract as deploy/kevin-spark/ds4-watchdog.sh.
#
# STDOUT IS THE DELIVERY BODY *ONLY UNDER A HERMES NO-AGENT CRON*
# (`hermes cron add ... --script <this> --no-agent --deliver telegram`), which
# sends what this prints. Under launchd, StandardOutPath is a LOG FILE and
# nothing is delivered to a human — launchd refreshes the pull-only surface.
# Arm one or both deliberately; see docs/telemetry/usage-surface.md and
# arm-hermes-cron.sh in this directory. Everything this script says about its
# own operation therefore goes to stderr, never stdout.
#
# Exit codes:
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

# Store root resolved EXACTLY as telemetry_dir() does — $T1000_TELEMETRY_DIR,
# else $HERMES_REAL_HOME/.t1000/telemetry, else ~/.t1000/telemetry. Do NOT
# derive this from $HERMES_HOME: under a Hermes worker session HERMES_HOME is
# the *profile* dir (~/.t1000/profiles/<name>), so that rule silently writes
# the archive somewhere the digest never reads.
STORE="${T1000_TELEMETRY_DIR:-${HERMES_REAL_HOME:-$HOME}/.t1000/telemetry}"
SNAPSHOT_DIR="${TELEMETRY_DIGEST_SNAPSHOT_DIR:-$STORE/digests}"
HEARTBEAT="${TELEMETRY_DIGEST_HEARTBEAT:-$STORE/telemetry-digest-heartbeat.json}"
# Commit the rendered rollup into the repo that tracks it (the home repo's
# curated .t1000 allowlist). Opt-in: a scheduled job that commits without
# being asked is a surprise, but a rollup that is never committed loses its
# own history the moment model_calls-*.jsonl rotates.
COMMIT="${TELEMETRY_DIGEST_COMMIT:-0}"

# --heartbeat is passed explicitly: commit_rollup below READS $HEARTBEAT to
# learn what the run wrote, so if the digest were left to its own default the
# two would disagree the moment TELEMETRY_DIGEST_HEARTBEAT is set — the digest
# would write one path, the commit step would read another, find nothing, and
# report "nothing committed" while every run still exited 0.
python3 "$REPO/scripts/telemetry_digest.py" \
  --since "$WINDOW" \
  --interval-seconds "$INTERVAL_S" \
  --snapshot-dir "$SNAPSHOT_DIR" \
  --heartbeat "$HEARTBEAT" \
  "$@"
code=$?

commit_rollup() {
  local repo_root written
  repo_root="$(git -C "$HOME" rev-parse --show-toplevel 2>/dev/null)" || {
    echo "telemetry-digest: \$HOME is not a git repo — nothing to commit" >&2
    return 0
  }

  # Ask the run itself what it wrote, rather than recomputing the paths here.
  # The heartbeat is the contract and records the real surface/snapshot, so a
  # caller that redirected --dir or --out is followed instead of guessed at.
  written="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
print("\n".join(p for p in (d.get("surface"), d.get("snapshot")) if p))' \
    "$HEARTBEAT" 2>/dev/null)" || {
    echo "telemetry-digest: cannot read $HEARTBEAT — nothing committed" >&2
    return 0
  }

  local paths=() path
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    [ -f "$path" ] || continue
    if git -C "$repo_root" check-ignore -q -- "$path"; then
      echo "telemetry-digest: $path is git-ignored — add the .t1000 allowlist" \
           "entry (see docs/telemetry/usage-surface.md) or the rollup stays" \
           "uncommitted" >&2
      continue
    fi
    paths+=("$path")
  done <<< "$written"
  [ ${#paths[@]} -gt 0 ] || return 0

  git -C "$repo_root" add -- "${paths[@]}" >&2 || return 0
  # Pathspec-scoped commit: only these files, never whatever else the home
  # repo happens to have staged or dirty.
  if git -C "$repo_root" diff --cached --quiet -- "${paths[@]}"; then
    echo "telemetry-digest: rollup unchanged — no commit" >&2
    return 0
  fi
  git -C "$repo_root" commit -q \
    -m "telemetry: usage digest $(date +%Y-%m-%d)" -- "${paths[@]}" >&2 \
    && echo "telemetry-digest: committed ${#paths[@]} rollup file(s)" >&2
}

if [ "$COMMIT" = "1" ]; then
  commit_rollup
fi

exit $code
