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
#   ./bench_window.sh open [--model gptoss|flash] [mode]   # mode default: ngram-mod (gptoss) / none (flash)
#   ./bench_window.sh switch <mode>     # swap the served spec mode inside an open window (tunnel stays up)
#   CTX=32768 NP=1 ./bench_window.sh switch none   # flash: per-slot context / slot count overrides
#   ./bench_window.sh close
#   ./bench_window.sh status
# flash modes: none | mtp2 | mtp3 | mtp4 | mtp{2,3,4}-standalone  (see serve-udq3-mtp.sh)
#
# Run from a host with ssh access to BOTH spark and k2vps (the Mac). The VPS
# cannot reach spark directly — spark dials out.
set -uo pipefail

SPARK=spark
VPS=k2vps
# SINGLE-QUOTED on purpose: an unquoted ~ expands on the LOCAL machine and
# ships /Users/<you>/... to the Spark, which then cannot find it. Every path
# in this file is remote; let the REMOTE shell expand it.
# --model selects what the window serves. gptoss = the lane model (default);
# flash = Qwen3.8-Flash-Next UD-Q3_K_XL on the PR-28243 MTP build (added
# 2026-09-05 for the MTP bakeoff re-run). The selection is remembered in
# STATE_FILE so `switch` and `close` do not need it repeated.
STATE_FILE="${HOME}/.bench_window.model"
set_model() {
  case "$1" in
    gptoss) SERVE='~/models/flash-next/serve-gptoss.sh';   MODEL_GB_DEFAULT=64; READY_MATCH=gpt-oss;            LABEL='gpt-oss:120b' ;;
    flash)  SERVE='~/models/flash-next/serve-udq3-mtp.sh'; MODEL_GB_DEFAULT=93; READY_MATCH=qwen3.8-flash-next; LABEL='Qwen3.8-Flash-Next UD-Q3_K_XL (PR-28243 build)' ;;
    *) die "unknown --model '$1' (gptoss|flash)" ;;
  esac
  MODEL_SEL=$1
}
BENCH_PORT=11439                            # see THE PORT FENCE above
MODEL_PORT=8898                             # llama.cpp on spark
SERVER_PID='/tmp/bench-server.pid'          # remote pidfiles (see start_server for why not pkill -f)
TUNNEL_PID='/tmp/bench-tunnel.pid'
RESIDENTS=(hermes3:8b-16k)   # since the 2026-09-05 flip. Pre-flip set was (gpt-oss:120b qwen3.8:27b hermes3:8b-16k); ollama holds at most three, load 120b FIRST if you ever restore it
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

# Launch (or relaunch) the llama-server for the selected model in the given
# spec mode and wait until it answers. Log per mode so acceptance stats survive
# a switch. A 90 GB model takes ~2 min to load; 80 x 5 s = 400 s budget.
# PIDFILES, never pkill -f / pgrep -f: a pattern that names the port or binary
# also appears in the remote `bash -c` command line that runs pkill, which
# then kills its own shell first. That aborted three flash windows in a row on
# 2026-09-05 (no tunnel log, no tunnel process, ERR trap fired every time).
start_server() {
  local mode="$1"
  say "serving $LABEL via llama.cpp (spec: $mode)"
  # CTX / NP from the caller's environment reach the serve script (flash only honors them).
  ssh "$SPARK" "${CTX:+CTX=$CTX }${NP:+NP=$NP }setsid nohup $SERVE $mode < /dev/null > \$HOME/models/flash-next/bench-window-${MODEL_SEL}-${mode}.log 2>&1 & echo \$! > $SERVER_PID" >/dev/null
  local n=0
  until ssh "$SPARK" "curl -s -m 3 http://127.0.0.1:$MODEL_PORT/v1/models" 2>/dev/null | grep -q "$READY_MATCH"; do
    n=$((n+1)); [ $n -gt 80 ] && die "model never came up; see ~/models/flash-next/bench-window-${MODEL_SEL}-${mode}.log on spark"
    # a crashed server must not be waited on for 400 s
    ssh "$SPARK" "kill -0 \$(cat $SERVER_PID) 2>/dev/null" || die "llama-server exited during load; see ~/models/flash-next/bench-window-${MODEL_SEL}-${mode}.log on spark"
    sleep 5
  done
  echo "model up on spark :$MODEL_PORT (mode $mode)"
}

stop_server() {
  ssh "$SPARK" "p=\$(cat $SERVER_PID 2>/dev/null); if [ -n \"\$p\" ]; then kill \$p 2>/dev/null; sleep 3; kill -9 \$p 2>/dev/null; fi; rm -f $SERVER_PID; true" >/dev/null 2>&1
  local n=0
  while ssh "$SPARK" "ss -ltn | grep -q ':$MODEL_PORT '"; do
    n=$((n+1)); [ $n -gt 12 ] && die "something still listens on spark :$MODEL_PORT after kill"
    sleep 5
  done
}

stop_tunnel() {
  ssh "$SPARK" "p=\$(cat $TUNNEL_PID 2>/dev/null); if [ -n \"\$p\" ]; then kill \$p 2>/dev/null; fi; rm -f $TUNNEL_PID; true" >/dev/null 2>&1
}

# Swap spec modes inside an open window. The tunnel forwards a PORT, so it
# survives the server restart; only the model reload (~2 min) is paid.
switch_mode() {
  local mode="$1"; [ -n "$mode" ] || die "switch needs a mode"
  [ -f "$STATE_FILE" ] || die "no open window recorded ($STATE_FILE missing) — use open"
  set_model "$(cat "$STATE_FILE")"
  ssh "$SPARK" 'systemctl is-active ollama' 2>/dev/null | grep -q '^active' && die "ollama service is ACTIVE — this is not an open window; refuse to load on top of it"
  say "switching served mode -> $mode"
  stop_server
  start_server "$mode"
  ssh "$VPS" "curl -s -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:$BENCH_PORT/v1/models" | grep -q 200 \
    || die "VPS lost the bench endpoint after the switch; check /tmp/bench-tunnel.log on spark"
  echo "  worker endpoint (from the VPS): http://127.0.0.1:$BENCH_PORT/v1  (mode $mode)"
}

open_window() {
  local mode="${1:-}"
  if [ -z "$mode" ]; then [ "$MODEL_SEL" = flash ] && mode=none || mode=ngram-mod; fi

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

  # 2026-09-05: spark :8898 is the flash-next PRODUCTION server (cron+flock). A window would
  # evict it and fight its supervisor. Refuse unless the operator has stopped the pilot.
  if ssh "$SPARK" "ss -ltn | grep -q ':$MODEL_PORT '"; then
    die "spark :$MODEL_PORT is already serving (the flash-next pilot). Stop its cron lines + process first (see README-PILOT.md) — a bench window is now a production outage."
  fi
  say "preflight: devbot lane must be quiet"
  local busy; busy=$(lane_busy)
  [ "$busy" = "0" ] || die "devbot lane has $busy dispatchable card(s). Wait for it to drain — evicting now would kill a running job."
  echo "lane quiet."

  say "evicting ollama residents"
  WINDOW_DIRTY=1; trap restore_on_failure ERR EXIT
  for m in "${RESIDENTS[@]}"; do ssh "$SPARK" "ollama stop $m" >/dev/null 2>&1; done
  # `ollama stop` evicts; it does not EXCLUDE. Only a stopped SERVICE prevents a
  # client from re-pinning 120b under our load (the 2026-08-27 wedge). The
  # HARD BLOCK above proved the NOPASSWD grant exists; this is where it is used.
  # Before 2026-09-05 the script checked the grant and then never called it.
  ssh "$SPARK" 'sudo -n systemctl stop ollama' || die "could not stop the ollama service on $SPARK"
  echo "ollama service stopped for the window."

  # ---- THE GUARD THIS SCRIPT EXISTS FOR (added after an outage) ------------
  # 2026-08-27: this step used to `sleep 4` and proceed. `ollama stop` returns
  # as soon as the unload is REQUESTED, not when the memory is actually free,
  # so the 63 GB llama.cpp allocation could start while the residents were
  # still resident. ryan-spark went down hard mid-load and needed a physical
  # power cycle; the devbot lane was dark for ~25 minutes. A timer is not a
  # guard — POLL for the memory, and refuse to serve without real headroom.
  local need_gb=${MODEL_GB:-$MODEL_GB_DEFAULT}
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

  start_server "$mode"
  echo "$MODEL_SEL" > "$STATE_FILE"

  say "opening reverse tunnel spark -> vps :$BENCH_PORT"
  stop_tunnel
  ssh "$SPARK" "setsid nohup ssh -N -o BatchMode=yes \
      -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o StrictHostKeyChecking=accept-new \
      -i ~/.ssh/id_ed25519_k2vps -R 127.0.0.1:$BENCH_PORT:127.0.0.1:$MODEL_PORT \
      sparklink@177.7.37.126 < /dev/null > /tmp/bench-tunnel.log 2>&1 & echo \$! > $TUNNEL_PID" >/dev/null
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
  stop_tunnel
  stop_server
  rm -f "$STATE_FILE"

  say "starting the ollama service"
  ssh "$SPARK" 'sudo -n systemctl start ollama' || die "could not start the ollama service on $SPARK — the lane is DOWN until this is fixed"
  local n=0
  until ssh "$SPARK" "curl -s -m 3 http://127.0.0.1:11434/api/version" 2>/dev/null | grep -q version; do
    n=$((n+1)); [ $n -gt 24 ] && die "ollama service did not answer on :11434 after start"
    sleep 5
  done

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
  # Scope by PORT, not build path: the flash arm runs ~/llama.cpp-mtp/build,
  # the gptoss arm ~/llama.cpp/build-qwen4exp. Ollama's workers never bind 8898.
  local stray;    stray=$(ssh "$SPARK" "ss -ltn | grep -c ':$MODEL_PORT '; true" 2>/dev/null | head -1)
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
  say "spark"; ssh "$SPARK" 'echo "ollama service: $(systemctl is-active ollama)"; ollama ps 2>/dev/null; echo "bench servers on :8898: $(ss -ltn | grep -c ":8898 ")"; free -g | head -2'
  say "endpoints (from the VPS)"
  ssh "$VPS" "curl -s -m 6 -o /dev/null -w '  :11435 lane  HTTP %{http_code}\n' http://127.0.0.1:11435/v1/models; \
              curl -s -m 6 -o /dev/null -w '  :$BENCH_PORT bench HTTP %{http_code}\n' http://127.0.0.1:$BENCH_PORT/v1/models"
}

verb="${1:-}"; shift || true
model_arg=gptoss
if [ "${1:-}" = "--model" ]; then model_arg="${2:-}"; shift 2 || true; fi
case "$verb" in
  open)   set_model "$model_arg"; open_window "${1:-}" ;;
  switch) switch_mode "${1:-}" ;;
  close)  [ -f "$STATE_FILE" ] && set_model "$(cat "$STATE_FILE")" || set_model "$model_arg"; close_window ;;
  status) [ -f "$STATE_FILE" ] && set_model "$(cat "$STATE_FILE")" || set_model "$model_arg"; status_window ;;
  *) echo "usage: $0 {open [--model gptoss|flash] [mode] | switch <mode> | close | status}"; exit 2 ;;
esac
