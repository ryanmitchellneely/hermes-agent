#!/usr/bin/env bash
# bench_window.sh — open/close a model bench window on ryan-spark, safely.
#
# WHY THIS EXISTS
# Every model bench on this fleet needs the same five things done in the same
# order, and getting any of them wrong costs real work:
#   1. the devbot lane must be QUIET (evicting mid-card kills a running job)
#   2. all ollama residents must be evicted (a 60-120GB model needs the box)
#   3. llama.cpp serves on spark :8898
#   4. the VPS reaches it ONLY through a reverse tunnel spark -> vps :11439
#   5. everything is restored and VERIFIED afterwards
# Done by hand on 2026-08-27 this took five windows and two OOM kills. This
# script is that sequence, mechanised.
#
# THE PORT FENCE (read before changing a port number)
# The `sparklink` key on k2vps carries `restrict,port-forwarding` plus an
# explicit allow-list:
#     permitlisten="11435"  spark ollama  -> the LIVE devbot lane endpoint
#     permitlisten="11436"  cadenspc ollama
#     permitlisten="11439"  BENCH ONLY    <- added 2026-08-27, this script
# A reverse tunnel on any other port is refused by sshd. That fence is
# deliberate: it is what stops an experiment from quietly exposing a new
# service on the production box. Widen it only with a human decision, add one
# port at a time, and record why here. Never repoint 11435 — that is the lane.
#
# USAGE
#   ./bench_window.sh open [none|ngram-mod|eagle3]   # default ngram-mod
#   ./bench_window.sh close
#   ./bench_window.sh status
#
# Run from a host with ssh access to BOTH spark and k2vps (the Mac). The VPS
# cannot reach spark directly — spark dials out.
set -uo pipefail

SPARK=spark
VPS=k2vps
# SINGLE-QUOTED on purpose: an unquoted ~ expands on the LOCAL machine and
# ships /Users/<you>/... to the Spark, which then cannot find it. Every path
# in this file is remote; let the REMOTE shell expand it.
SERVE='~/models/flash-next/serve-gptoss.sh'
BENCH_PORT=11439                            # see THE PORT FENCE above
MODEL_PORT=8898                             # llama.cpp on spark
RESIDENTS=(gpt-oss:120b qwen3.8:27b hermes3:8b-16k)
HK="sudo -u t1000 env HERMES_HOME=/opt/t1000/home /opt/t1000/venv/bin/hermes kanban"

say() { printf '\n=== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

lane_busy() {
  local n
  n=$(ssh -o ConnectTimeout=15 "$VPS" "$HK --board devbot list" 2>/dev/null \
        | grep -cE ' ready | running ')
  echo "${n:-1}"   # fail safe: unknown counts as busy
}

# Set once the evict has happened: any later failure must put the box back.
# A half-open window (models evicted, bench server never started) leaves the
# live lane with nothing loaded. That happened on 2026-08-27; hence this trap.
WINDOW_DIRTY=0
restore_on_failure() {
  [ "$WINDOW_DIRTY" = "1" ] || exit 1
  printf '\n!! open failed after eviction — restoring the box before exiting\n' >&2
  WINDOW_DIRTY=0
  close_window || true
  exit 1
}

open_window() {
  local mode="${1:-ngram-mod}"

  # ---- HARD BLOCK: proven crash mechanism, not yet fixable from here -------
  # 2026-08-27, TWICE. Root cause from the previous-boot kernel log:
  #   13:18:57 ollama: load_tensors: loading model tensors  (gpt-oss:120b)
  #   13:18:58 kernel: NVRM: Check failed: Out of memory [NV_ERR_NO_MEMORY]
  # Two ~64GB copies of the SAME model loading at once (ollama and ours)
  # exhausted the GPU allocator on a 121GB unified-memory box and wedged it:
  # kernel alive, userspace dead (LAN ping fine, sshd could not fork). Both
  # times needed a physical power cycle.
  #
  # `ollama stop <model>` EVICTS, it does not EXCLUDE: the daemon reloads on
  # the next request, and something does request 120b. The real fix is
  # stopping the ollama SERVICE for the window, which needs root on spark that
  # this account lacks. nvidia-smi also reports N/A for memory on GB10, so
  # there is no GPU-memory instrument to guard with; the old free -g check
  # measured system RAM while the failure was in the GPU allocator.
  #
  # Until one of those is solved, opening a window is a coin flip on the box
  # the devbot lane depends on. Refuse by default.
  if ! ssh "$SPARK" 'sudo -n systemctl is-active ollama' >/dev/null 2>&1; then
    [ "${BENCH_FORCE:-0}" = "1" ] || die "REFUSING to open a window.
  Cannot stop the ollama service on $SPARK (no passwordless sudo), so nothing
  prevents it reloading gpt-oss:120b while we load our own copy. That race
  hard-wedged this box twice on 2026-08-27 (NVRM out-of-memory, physical power
  cycle both times).
  Fix one first:
    - grant NOPASSWD for systemctl stop/start ollama on $SPARK, or
    - identify and quiesce whatever re-requests 120b during a window.
  Override with BENCH_FORCE=1 only if you are watching the box."
  fi

  say "preflight: devbot lane must be quiet"
  local busy; busy=$(lane_busy)
  [ "$busy" = "0" ] || die "devbot lane has $busy dispatchable card(s). Wait for it to drain — evicting now would kill a running job."
  echo "lane quiet."

  say "evicting ollama residents"
  WINDOW_DIRTY=1; trap restore_on_failure ERR EXIT
  for m in "${RESIDENTS[@]}"; do ssh "$SPARK" "ollama stop $m" >/dev/null 2>&1; done

  # ---- THE GUARD THIS SCRIPT EXISTS FOR (added after an outage) ------------
  # 2026-08-27: this step used to `sleep 4` and proceed. `ollama stop` returns
  # as soon as the unload is REQUESTED, not when the memory is actually free,
  # so the 63 GB llama.cpp allocation could start while the residents were
  # still resident. ryan-spark went down hard mid-load and needed a physical
  # power cycle; the devbot lane was dark for ~25 minutes. A timer is not a
  # guard — POLL for the memory, and refuse to serve without real headroom.
  local need_gb=${MODEL_GB:-64}
  local head_gb=${HEADROOM_GB:-12}
  local want=$(( need_gb + head_gb ))
  say "waiting for memory to actually free (need ${want}GB: ${need_gb} model + ${head_gb} headroom)"
  local free_gb=0 waited=0
  while [ "$waited" -lt 180 ]; do
    free_gb=$(ssh "$SPARK" "free -g | awk '/^Mem:/{print \$7}'" 2>/dev/null)
    free_gb=${free_gb:-0}
    echo "  available: ${free_gb}GB (want >= ${want}GB), ${waited}s"
    [ "$free_gb" -ge "$want" ] && break
    sleep 10; waited=$(( waited + 10 ))
  done
  [ "$free_gb" -ge "$want" ] || die "only ${free_gb}GB free after ${waited}s, need ${want}GB. REFUSING to load — this is the check whose absence took the box down on 2026-08-27. Investigate what still holds memory before retrying."
  echo "memory clear: ${free_gb}GB available."

  say "serving gpt-oss:120b via llama.cpp (spec: $mode)"
  ssh "$SPARK" "setsid nohup $SERVE $mode < /dev/null > \$HOME/models/flash-next/bench-window.log 2>&1 & disown" >/dev/null
  local n=0
  until ssh "$SPARK" "curl -s -m 3 http://127.0.0.1:$MODEL_PORT/v1/models" 2>/dev/null | grep -q gpt-oss; do
    n=$((n+1)); [ $n -gt 80 ] && die "model never came up; see ~/models/flash-next/bench-window.log on spark"
    sleep 5
  done
  echo "model up on spark :$MODEL_PORT"

  say "opening reverse tunnel spark -> vps :$BENCH_PORT"
  ssh "$SPARK" "pkill -f 'R 127.0.0.1:$BENCH_PORT' 2>/dev/null; setsid nohup ssh -N \
      -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o StrictHostKeyChecking=accept-new \
      -i ~/.ssh/id_ed25519_k2vps -R 127.0.0.1:$BENCH_PORT:127.0.0.1:$MODEL_PORT \
      sparklink@177.7.37.126 < /dev/null > /tmp/bench-tunnel.log 2>&1 & disown" >/dev/null
  sleep 8
  ssh "$VPS" "curl -s -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:$BENCH_PORT/v1/models" \
    | grep -q 200 || die "VPS cannot reach the bench endpoint. Check permitlisten on the sparklink key (see THE PORT FENCE) and /tmp/bench-tunnel.log on spark."

  WINDOW_DIRTY=0; trap - ERR EXIT
  say "WINDOW OPEN"
  echo "  worker endpoint (from the VPS): http://127.0.0.1:$BENCH_PORT/v1"
  echo "  close it with: $0 close"
}

close_window() {
  say "closing: tunnel + model"
  ssh "$SPARK" "pkill -f 'R 127.0.0.1:$BENCH_PORT' 2>/dev/null; pkill -f 'llama-server.*$MODEL_PORT' 2>/dev/null; sleep 3; pkill -9 -f 'llama-server.*$MODEL_PORT' 2>/dev/null" >/dev/null 2>&1

  say "restoring ollama residents (one at a time — parallel loads OOM this box)"
  for m in "${RESIDENTS[@]}"; do
    echo "  loading $m ..."
    ssh "$SPARK" "curl -s -m 600 http://127.0.0.1:11434/api/generate -d '{\"model\":\"$m\"}'" >/dev/null 2>&1
  done

  say "VERIFYING restoration (never assume it worked)"
  local resident; resident=$(ssh "$SPARK" 'ollama ps' 2>/dev/null | tail -n +2 | grep -c .)
  # Scope the stray check to OUR server. `pgrep -c llama-server` also counts
  # ollama's own internal workers (ollama runs /usr/local/lib/ollama/llama-server
  # per loaded model), so the naive check reports 3 on a perfectly healthy box
  # and would fail every clean close. The [b]racket idiom stops pgrep -f
  # from ALSO matching its own command string (that self-match cost real time
  # twice on 2026-08-27, reporting phantom processes).
  # pgrep -fc PRINTS 0 and EXITS 1 when nothing matches, so `|| echo 0` used to
  # append a second zero and the assertion compared "0\n0" against "0" — a clean
  # restore reported FAIL. Take the first line and default only if empty.
  local stray;    stray=$(ssh "$SPARK" "pgrep -fc '[b]uild-qwen4exp/bin/llama-server' 2>/dev/null; true" 2>/dev/null | head -1)
  stray=${stray:-0}
  local lane;     lane=$(ssh "$VPS" "curl -s -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:11435/v1/models" 2>/dev/null)
  echo "  ollama residents: $resident (want ${#RESIDENTS[@]})"
  echo "  stray llama-server: $stray (want 0)"
  echo "  lane endpoint :11435: HTTP $lane (want 200)"
  [ "$resident" = "${#RESIDENTS[@]}" ] && [ "$stray" = "0" ] && [ "$lane" = "200" ] \
    && say "WINDOW CLOSED CLEAN" \
    || die "restoration incomplete — fix before leaving. The lane depends on :11435."
}

status_window() {
  say "lane"; echo "  dispatchable devbot cards: $(lane_busy)"
  say "spark"; ssh "$SPARK" 'ollama ps; echo "bench llama-server procs: $(pgrep -fc "[b]uild-qwen4exp/bin/llama-server" || echo 0)  (ollama runs its own internal ones; those are normal)"; free -g | head -2'
  say "endpoints (from the VPS)"
  ssh "$VPS" "curl -s -m 6 -o /dev/null -w '  :11435 lane  HTTP %{http_code}\n' http://127.0.0.1:11435/v1/models; \
              curl -s -m 6 -o /dev/null -w '  :$BENCH_PORT bench HTTP %{http_code}\n' http://127.0.0.1:$BENCH_PORT/v1/models"
}

case "${1:-}" in
  open)   open_window "${2:-ngram-mod}" ;;
  close)  close_window ;;
  status) status_window ;;
  *) echo "usage: $0 {open [none|ngram-mod|eagle3] | close | status}"; exit 2 ;;
esac
