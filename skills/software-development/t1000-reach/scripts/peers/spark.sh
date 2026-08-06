#!/usr/bin/env bash
# A1 spark peer adapter — L0 compute substrate (not an agent soul).
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

LOCAL_URL="${SPARK_BASE_URL:-http://127.0.0.1:11435}"
TAGS_URL="${LOCAL_URL%/}/api/tags"
REASON_MODEL="${SPARK_REASON_MODEL:-gpt-oss:120b}"
FORMAT_MODEL="${SPARK_FORMAT_MODEL:-hermes3:8b-16k}"
SSH_HOST="${SPARK_SSH_HOST:-spark}"

find_tunnel_script() {
  local candidates=(
    "${SPARK_TUNNEL_SCRIPT:-}"
    "$HOME/Documents/sovereign-consulting/tools/juice/evals/spark_tunnel.sh"
    "$HOME/Documents/T1000/evals/comm_comprehension/spark_tunnel.sh"
    "/private/tmp/t1000-comm-comprehension/evals/comm_comprehension/spark_tunnel.sh"
  )
  local c
  for c in "${candidates[@]}"; do
    [[ -n "$c" && -x "$c" ]] && { printf '%s\n' "$c"; return 0; }
    [[ -n "$c" && -f "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

tunnel_pid_guess() {
  local pid_file
  pid_file="${TMPDIR:-/tmp}/sovereign-juice-spark-tunnel-$(id -u).pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    IFS= read -r pid <"$pid_file" || true
    if [[ "${pid:-}" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      printf '%s\n' "$pid"
      return 0
    fi
  fi
  printf '\n'
}

port_up() {
  curl -sf --max-time 3 "$TAGS_URL" >/dev/null 2>&1
}

fetch_tags_json() {
  curl -sf --max-time 5 "$TAGS_URL" 2>/dev/null || true
}

build_status_detail() {
  local tags_json state pid tags_ok
  tags_json="$(fetch_tags_json)"
  pid="$(tunnel_pid_guess)"
  if [[ -n "$tags_json" ]]; then
    state="up"
    tags_ok="true"
  else
    state="down"
    tags_ok="false"
    tags_json="{}"
  fi

  REACH_TAGS="$tags_json" REACH_STATE="$state" REACH_PID="$pid" \
  REACH_URL="$LOCAL_URL" REACH_HOST="$SSH_HOST" \
  REACH_REASON="$REASON_MODEL" REACH_FORMAT="$FORMAT_MODEL" \
  REACH_TAGS_OK="$tags_ok" python3 - <<'PY'
import json, os
tags_raw = os.environ.get("REACH_TAGS") or "{}"
try:
    tags = json.loads(tags_raw) if tags_raw.strip() else {}
except json.JSONDecodeError:
    tags = {}
names = []
for m in tags.get("models") or []:
    n = m.get("name") or m.get("model") or ""
    if n:
        names.append(n)

def present(want: str) -> str:
    # allow tag variants: name or name:tag prefix match
    base = want.split(":")[0]
    for n in names:
        if n == want or n.startswith(want) or n.startswith(base + ":"):
            # prefer exact-ish
            if n == want or n.startswith(want):
                return n
    for n in names:
        if n.startswith(base):
            return n
    return "missing"

reason = present(os.environ["REACH_REASON"])
fmt = present(os.environ["REACH_FORMAT"])
pid = os.environ.get("REACH_PID") or None
if pid == "":
    pid = None
else:
    try:
        pid = int(pid) if pid is not None else None
    except ValueError:
        pid = None

detail = {
    "tunnel": {
        "state": os.environ["REACH_STATE"],
        "local_url": os.environ["REACH_URL"],
        "pid": pid,
        "ssh_host": os.environ["REACH_HOST"],
    },
    "models": {
        "reason": reason if reason != "missing" else "missing",
        "format": fmt if fmt != "missing" else "missing",
        "expected_reason": os.environ["REACH_REASON"],
        "expected_format": os.environ["REACH_FORMAT"],
        "all": names,
    },
    "tags_ok": os.environ.get("REACH_TAGS_OK") == "true",
}
print(json.dumps(detail))
# grading hints on stderr via markers
if os.environ["REACH_STATE"] != "up":
    print("GRADE=error", file=__import__("sys").stderr)
elif reason == "missing" or fmt == "missing":
    print("GRADE=stale", file=__import__("sys").stderr)
else:
    print("GRADE=live", file=__import__("sys").stderr)
PY
}

spark_status() {
  local detail grade ok kind rid
  local tmp_err
  tmp_err="$(mktemp)"
  detail="$(build_status_detail 2>"$tmp_err")"
  grade="$(grep -E '^GRADE=' "$tmp_err" | tail -1 | cut -d= -f2 || true)"
  rm -f "$tmp_err"
  grade="${grade:-error}"

  if [[ "$grade" == "live" ]]; then
    ok="true"
    kind="http"
    rid="$TAGS_URL"
  elif [[ "$grade" == "stale" ]]; then
    ok="false"
    kind="http"
    rid="$TAGS_URL"
  else
    ok="false"
    kind="http"
    rid="$TAGS_URL"
  fi

  if [[ "$ok" == "true" ]]; then
    emit_receipt spark status true live L0 "$kind" "$rid" "$detail"
    return 0
  elif [[ "$grade" == "stale" ]]; then
    emit_receipt spark status false stale L0 "$kind" "$rid" "$detail" \
      missing_models "Tunnel up but expected reason/format models not both present"
    return 1
  else
    emit_receipt spark status false error L0 "$kind" "$rid" "$detail" \
      tunnel_down "Cannot reach Spark tags at $TAGS_URL"
    return 1
  fi
}

spark_models() {
  # Same probe as status; verb differs for agent clarity
  local detail grade
  local tmp_err
  tmp_err="$(mktemp)"
  detail="$(build_status_detail 2>"$tmp_err")"
  grade="$(grep -E '^GRADE=' "$tmp_err" | tail -1 | cut -d= -f2 || true)"
  rm -f "$tmp_err"
  grade="${grade:-error}"
  if [[ "$grade" == "live" ]]; then
    emit_receipt spark models true live L0 http "$TAGS_URL" "$detail"
    return 0
  elif [[ "$grade" == "stale" ]]; then
    emit_receipt spark models false stale L0 http "$TAGS_URL" "$detail" \
      missing_models "Expected models incomplete"
    return 1
  else
    emit_receipt spark models false error L0 http "$TAGS_URL" "$detail" \
      tunnel_down "Cannot reach Spark tags"
    return 1
  fi
}

spark_tunnel() {
  local action="$1"  # up|down
  local script
  if ! script="$(find_tunnel_script)"; then
    emit_receipt spark "tunnel-$action" false error L0 none "-" "{}" \
      no_tunnel_script "spark_tunnel.sh not found (set SPARK_TUNNEL_SCRIPT)"
    return 1
  fi

  local out rc=0
  out="$(bash "$script" "$action" 2>&1)" || rc=$?
  local detail
  detail=$(REACH_OUT="$out" REACH_SCRIPT="$script" REACH_RC="$rc" python3 - <<'PY'
import json, os
print(json.dumps({
    "tunnel_script": os.environ["REACH_SCRIPT"],
    "action_rc": int(os.environ["REACH_RC"]),
    "output_tail": os.environ.get("REACH_OUT","")[-800:],
}))
PY
)

  # Re-probe after action
  local status_detail grade
  local tmp_err
  tmp_err="$(mktemp)"
  status_detail="$(build_status_detail 2>"$tmp_err")"
  grade="$(grep -E '^GRADE=' "$tmp_err" | tail -1 | cut -d= -f2 || true)"
  rm -f "$tmp_err"
  grade="${grade:-error}"

  detail=$(REACH_A="$detail" REACH_B="$status_detail" python3 - <<'PY'
import json, os
a=json.loads(os.environ["REACH_A"]); b=json.loads(os.environ["REACH_B"])
a["post"]=b
print(json.dumps(a))
PY
)

  if [[ "$action" == "up" ]]; then
    if [[ "$grade" == "live" || "$grade" == "stale" ]]; then
      # up succeeded enough to open port
      local ok=true g=live
      [[ "$grade" == "stale" ]] && { ok=false; g=stale; }
      emit_receipt spark tunnel-up "$ok" "$g" L0 local "$script" "$detail" \
        $([[ "$ok" == "true" ]] && echo "" || echo "missing_models") \
        $([[ "$ok" == "true" ]] && echo "" || echo "Tunnel up; models incomplete")
      [[ "$ok" == "true" ]] && return 0 || return 1
    fi
    emit_receipt spark tunnel-up false error L0 local "$script" "$detail" \
      tunnel_up_failed "spark_tunnel.sh up did not yield reachable tags ($TAGS_URL)"
    return 1
  else
    # down: success if port no longer answers
    if ! port_up; then
      emit_receipt spark tunnel-down true live L0 local "$script" "$detail"
      return 0
    fi
    emit_receipt spark tunnel-down false error L0 local "$script" "$detail" \
      tunnel_down_failed "Port still reachable after down"
    return 1
  fi
}

spark_dispatch() {
  local verb="$1"
  case "$verb" in
    status) spark_status ;;
    models) spark_models ;;
    tunnel-up|up) spark_tunnel up ;;
    tunnel-down|down) spark_tunnel down ;;
    *)
      emit_receipt spark "$verb" false error L0 none "-" "{}" \
        unknown_verb "spark verbs: status|models|tunnel-up|tunnel-down"
      return 2
      ;;
  esac
}

# Allow direct execution
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  spark_dispatch "${1:-status}"
fi
