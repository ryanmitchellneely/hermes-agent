#!/usr/bin/env bash
# dsh_probe.sh — run the REAL dsh worker against a chosen model, once, safely.
#
# THE PROBLEM
# dsh_kanban_worker.py needs its card in RUNNING: the wrapper owns the terminal
# kanban call from a `finally` block and block/complete refuse other statuses.
# But a hand-made probe card sitting in `ready` is exactly what the dispatcher
# claims — on 2026-08-27 it grabbed a probe within seconds and ran it on
# gpt-oss:120b instead of the model under test, which is a silent wrong answer:
# the run LOOKS like a successful bench of flash-next.
#
# THE EXEMPTION — a supported mechanism, not a workaround
# kanban_db.dispatch skips any ready task whose assignee is not a real Hermes
# profile, bucketing it as `skipped_nonspawnable`. The comment at that branch
# states the intent directly: such lanes "are pulled by terminals via claim_task
# directly and should NEVER auto-spawn". So assigning the probe to a lane name
# that is not a profile makes it PERMANENTLY invisible to the dispatcher — no
# race to win, no TTL to beat, and re-running is idempotent.
#
# Verified in kanban_db.py before relying on any of it:
#   claim_task     ready -> running, CAS on (status='ready' AND claim_lock IS NULL)
#   complete_task  accepts running|ready|blocked|review, does NOT check lock owner
#   dispatch       "Skip ready tasks whose assignee is not a real Hermes profile"
# So we may hold the lock ourselves and the worker's terminal call still lands.
#
# WHY NOT --initial-status running: create sets the status but leaves claim_lock
# NULL, and recompute_ready puts a parentless card back to `ready` — which is
# precisely the state the dispatcher claims. That trap is what burned the first
# two probes; the assignee is the durable fix.
#
# SAFETY
#   non-profile assignee - dispatcher can never spawn it
#   DSH_SKIP_PR=1        - worker commits in a worktree but opens no PR
#   trap on EXIT         - card archived + worktree removed even on failure
#   explicit workspace   - harness cards otherwise resolve to a T1000 worktree,
#                          which made an earlier probe unanswerable because its
#                          task referenced a K2 file
#
# USAGE
#   ./dsh_probe.sh <patch-yml-on-vps> "<task text>"
set -uo pipefail

VPS=k2vps
BOARD=harness
LANE=bench-probe          # deliberately NOT a hermes profile (see EXEMPTION)
WORKSPACE=/opt/t1000/home/src/kevin-real-estate-tools
WORKER="$WORKSPACE/docs/agent-coordination/devbot/harness-bench/dsh_kanban_worker.py"
HK="sudo -u t1000 env HERMES_HOME=/opt/t1000/home /opt/t1000/venv/bin/hermes kanban"

PATCH="${1:?usage: $0 <patch-yml-on-vps> \"<task text>\"}"
TASK="${2:?usage: $0 <patch-yml-on-vps> \"<task text>\"}"

say() { printf '\n=== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

say "guard: $LANE must NOT be a real profile, or the dispatcher can spawn it"
ssh "$VPS" "sudo -u t1000 env HERMES_HOME=/opt/t1000/home /opt/t1000/venv/bin/hermes profile list" 2>/dev/null \
  | awk '{print $1}' | grep -qx "$LANE" \
  && die "$LANE IS a profile — the dispatcher would claim the probe. Pick another lane name."
echo "  ok: '$LANE' is not a profile"

BODY="MANUAL BENCH PROBE, not real work — archived immediately after. Created by dsh_probe.sh to drive one real-worker run against a specific model. THE WORK: ${TASK} Do not modify any file. Then end the card per the lifecycle contract."

say "creating probe card on lane '$LANE'"
TASK_ID=$(ssh "$VPS" "$HK --board $BOARD create 'BENCH PROBE (manual): real-worker model check' \
    --body \"$BODY\" --assignee $LANE --created-by ryan-claude" 2>/dev/null \
  | grep -oE 't_[0-9a-f]+' | head -1)
[ -n "$TASK_ID" ] || die "could not create a probe card"
echo "  card: $TASK_ID"

cleanup() {
  say "cleanup"
  ssh "$VPS" "$HK --board $BOARD comment $TASK_ID 'Bench probe — archived by dsh_probe.sh.'" >/dev/null 2>&1
  ssh "$VPS" "$HK --board $BOARD archive $TASK_ID" 2>&1 | tail -1
  ssh "$VPS" "sudo -u t1000 git -C $WORKSPACE worktree remove --force $WORKSPACE.worktrees/$TASK_ID" >/dev/null 2>&1 \
    && echo "  worktree removed" || echo "  (no worktree to remove)"
}
trap cleanup EXIT

say "claiming it ourselves (ready -> running, our lock)"
ssh "$VPS" "$HK --board $BOARD claim $TASK_ID --ttl 1800" 2>&1 | tail -2
STATUS=$(ssh "$VPS" "$HK --board $BOARD show $TASK_ID" 2>/dev/null | awk '/^  status/{print $2}')
echo "  status: $STATUS"
[ "$STATUS" = "running" ] || die "card is '$STATUS', not running — the worker's terminal call needs running. Do not spend a model call."

say "running the real worker (patch: $(basename "$PATCH"), DSH_SKIP_PR=1)"
# HOME is load-bearing and NOT the same as HERMES_HOME. getent says t1000's home
# is /opt/t1000, but the actual content lives one level down in /opt/t1000/home,
# so every Path.home() lookup in the worker (DSH_BIN, NODE22, LOGS) resolves to a
# path that does not exist. The wrapper then dies with a bare
# FileNotFoundError(2) naming NO file and writing NO worker log — which reads
# exactly like the model failing to start. `sudo -u t1000` does not set HOME and
# neither does HERMES_HOME; only this does.
ssh "$VPS" "cd $WORKSPACE && sudo -u t1000 env HOME=/opt/t1000/home HERMES_HOME=/opt/t1000/home \
    HERMES_KANBAN_TASK=$TASK_ID HERMES_KANBAN_BOARD=$BOARD \
    HERMES_KANBAN_WORKSPACE=$WORKSPACE \
    DSH_WORKER_PATCH=$PATCH DSH_SKIP_PR=1 DSH_WORKER_WALL_SECS=600 \
    K2_LOCAL_API_KEY=local-bench timeout 700 python3 $WORKER" 2>&1 | tail -30

say "what the worker recorded on the card"
ssh "$VPS" "$HK --board $BOARD show $TASK_ID" 2>/dev/null | tail -25
