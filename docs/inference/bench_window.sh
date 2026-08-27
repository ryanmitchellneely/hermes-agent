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
SERVE=~/models/flash-next/serve-gptoss.sh   # on spark
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

open_window() {
  local mode="${1:-ngram-mod}"

  say "preflight: devbot lane must be quiet"
  local busy; busy=$(lane_busy)
  [ "$busy" = "0" ] || die "devbot lane has $busy dispatchable card(s). Wait for it to drain — evicting now would kill a running job."
  echo "lane quiet."

  say "evicting ollama residents"
  for m in "${RESIDENTS[@]}"; do ssh "$SPARK" "ollama stop $m" >/dev/null 2>&1; done
  sleep 4
  ssh "$SPARK" 'free -g | head -2'

  say "serving gpt-oss:120b via llama.cpp (spec: $mode)"
  ssh "$SPARK" "setsid nohup $SERVE $mode < /dev/null > ~/models/flash-next/bench-window.log 2>&1 & disown" >/dev/null
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
  local stray;    stray=$(ssh "$SPARK" "pgrep -fc '[b]uild-qwen4exp/bin/llama-server'" 2>/dev/null || echo 0)
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
