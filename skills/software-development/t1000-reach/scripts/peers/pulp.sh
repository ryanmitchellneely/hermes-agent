#!/usr/bin/env bash
# A4 pulp peer — VPS buzz-agent-pulp status + auth-gated oneshot ask (no send).
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

K2VPS_HOST="${K2VPS_HOST:-k2vps}"
PULP_UNIT="${PULP_UNIT:-buzz-agent-pulp.service}"
PULP_BRIDGES="${PULP_BRIDGES:-/opt/juice/bridges}"
PULP_VENV_PY="${PULP_VENV_PY:-/opt/juice/venv/bin/python}"
PULP_AUTH_REMOTE="${PULP_AUTH_REMOTE:-/var/lib/pulp/auth_status.json}"

pulp_status() {
  local raw detail
  raw="$(ssh -o BatchMode=yes -o ConnectTimeout=15 "$K2VPS_HOST" \
    "export U_ACTIVE=\$(systemctl is-active ${PULP_UNIT} 2>/dev/null);
     export U_ENABLED=\$(systemctl is-enabled ${PULP_UNIT} 2>/dev/null);
     export U_PID=\$(systemctl show -p MainPID --value ${PULP_UNIT} 2>/dev/null);
     export U_ENTER=\$(systemctl show -p ActiveEnterTimestamp --value ${PULP_UNIT} 2>/dev/null);
     export U_USER=\$(systemctl show -p User --value ${PULP_UNIT} 2>/dev/null);
     export SPARK_UP=0; curl -sf --max-time 2 http://127.0.0.1:11435/api/version >/dev/null 2>&1 && export SPARK_UP=1;
     python3 - <<'PY'
import json, os
from pathlib import Path

def load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return None

print(json.dumps({
    'unit': {
        'name': 'buzz-agent-pulp.service',
        'active': os.environ.get('U_ACTIVE',''),
        'enabled': os.environ.get('U_ENABLED',''),
        'main_pid': os.environ.get('U_PID',''),
        'active_enter': os.environ.get('U_ENTER',''),
        'user': os.environ.get('U_USER',''),
    },
    'spark_loopback_11435': os.environ.get('SPARK_UP') == '1',
    'auth': load('/var/lib/pulp/auth_status.json'),
    'auth_readiness': load('/var/lib/pulp/auth_readiness_status.json'),
    'quality': load('/var/lib/pulp/quality_status.json'),
    'paths': {
        'auth': '/var/lib/pulp/auth_status.json',
        'memory': '/var/lib/pulp/memory.db',
        'charter': '/opt/buzz/charters/pulp.md',
    },
    'charter_limits': ['no_sends','no_drafts','no_mail','no_sierra','converse_only'],
}))
PY" 2>/dev/null)" || raw='{"error":"ssh_failed"}'

  detail="$(RAW="$raw" python3 - <<'PY'
import json, os
from datetime import datetime, timezone
try:
    raw = json.loads(os.environ["RAW"])
except json.JSONDecodeError:
    raw = {"error": "bad_json", "raw": (os.environ.get("RAW") or "")[:300]}

auth = raw.get("auth") or {}
unit = raw.get("unit") or {}
spark = bool(raw.get("spark_loopback_11435"))
active = unit.get("active") == "active"
authorized = (
    auth.get("state") == "authorized"
    and (auth.get("scope") or {}).get("converse") is True
)
expired = False
exp = auth.get("expires_at")
if isinstance(exp, str):
    try:
        expired = datetime.fromisoformat(exp) <= datetime.now(timezone.utc)
    except ValueError:
        expired = False

quality = raw.get("quality") or {}
q_summary = None
if isinstance(quality, dict) and quality:
    q_summary = {
        "replies_verified": quality.get("replies_verified"),
        "flagged": quality.get("flagged"),
        "panel_any_block": quality.get("panel_any_block"),
        "last_run": quality.get("last_run"),
    }

if raw.get("error") in ("ssh_failed", "bad_json") or not unit:
    grade, ok, code, msg = "error", False, "ssh_failed", "Cannot reach VPS pulp status"
elif not active:
    grade, ok, code, msg = "error", False, "unit_inactive", "buzz-agent-pulp is not active"
elif not authorized or expired:
    grade, ok, code, msg = "stale", True, "not_authorized", "Unit up but auth missing/expired"
elif not spark:
    grade, ok, code, msg = "stale", True, "spark_down", "Pulp authorized; Spark 11435 down on VPS"
else:
    grade, ok, code, msg = "live", True, "", ""

print(json.dumps({
    "unit": unit,
    "authorized": authorized and not expired,
    "auth_state": auth.get("state"),
    "auth_expires_at": exp,
    "auth_scope": auth.get("scope"),
    "auth_readiness": raw.get("auth_readiness"),
    "spark_loopback_11435": spark,
    "quality_summary": q_summary,
    "charter_limits": raw.get("charter_limits"),
    "paths": raw.get("paths"),
    "_g": grade, "_ok": ok, "_code": code, "_msg": msg,
}))
PY
)"

  local grade ok code msg
  grade="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin)["_g"])')"
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;print("true" if json.load(sys.stdin)["_ok"] else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_msg") or "")')"
  detail="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);[d.pop(k,None) for k in list(d) if k.startswith("_")];print(json.dumps(d))')"

  if [[ "$ok" == "true" && -z "$code" ]]; then
    emit_receipt pulp status true "$grade" L1 ssh "$K2VPS_HOST" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt pulp status true "$grade" L1 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
    return 0
  fi
  emit_receipt pulp status false "$grade" L1 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
  return 1
}

write_ask_runner() {
  cat <<'PY'
#!/usr/bin/env python3
"""T1000-lane Pulp oneshot ask — auth-gated, no Buzz post, no send, no memory write."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

BRIDGES = Path(os.environ.get("PULP_BRIDGES", "/opt/juice/bridges"))
sys.path.insert(0, str(BRIDGES))

AUTH_PATH = os.environ.get("PULP_AUTH_STATUS_PATH", "/var/lib/pulp/auth_status.json")
SPARK_CHAT_URL = os.environ.get("SPARK_CHAT_URL", "http://127.0.0.1:11435/api/chat")
QUESTION = os.environ.get("PULP_QUESTION", "").strip()
TIMEOUT = int(os.environ.get("PULP_CHAT_TIMEOUT", "180"))


def fail(code: str, message: str, **extra):
    print(json.dumps({"ok": False, "code": code, "message": message, **extra}))
    raise SystemExit(0)


if not QUESTION:
    fail("no_question", "empty question")

low = QUESTION.lower().lstrip()
if low.startswith("remember:") or low.startswith("done:"):
    fail("mutating_prefix_blocked", "reach pulp ask refuses remember:/done: (owner ceremony only)")

try:
    from pulp_core import Envelope, auth_status, plan
except Exception as e:
    fail("import_core", f"{type(e).__name__}: {e}")

ok, reason = auth_status(AUTH_PATH)
if not ok:
    fail("not_authorized", reason)

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "buzz_acp_pulp_mod", BRIDGES / "buzz_acp_pulp.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
except Exception as e:
    fail("import_shell", f"{type(e).__name__}: {e}")


class _NullMem:
    def recall(self, q, k=6):
        return []

    def remember(self, fact, source):
        raise RuntimeError("no memory")

    def log_turn(self, sender, text):
        pass


envelope = Envelope(channel=None, reply_to=None, sender="t1000-reach", body=QUESTION)
memory = _NullMem()

tool_context = ""
llm_context = ""
confidential = False
stamps = []
try:
    tool_context, llm_context, confidential = mod._gather_tools(
        envelope.body, envelope.channel, stamps
    )
except Exception as e:
    tool_context = f"tool_gather_error: {type(e).__name__}: {e}"

if confidential:
    llm_context = ""
    tool_context = (
        tool_context
        + "\n\n[confidential commitments omitted — T1000 lane has no allowlisted Buzz channel]"
    ).strip()

combined = "\n".join(p for p in (tool_context, llm_context) if p)
owner = os.environ.get("PULP_OWNER_PUBKEY", "owner-not-t1000")
decided = plan(
    envelope,
    owner=owner,
    auth_path=AUTH_PATH,
    memory=memory,
    tool_context=combined,
    close_commitment=None,
)

result = {
    "ok": True,
    "plan_kind": decided.kind,
    "model": getattr(decided, "model", None),
    "tool_context_chars": len(combined),
    "confidential_omitted": bool(confidential),
    "answer": None,
}

if decided.kind != "chat":
    result["answer"] = decided.body or ""
    print(json.dumps(result))
    raise SystemExit(0)

payload = {
    "model": decided.model,
    "stream": False,
    "messages": [
        {"role": "system", "content": decided.system_prompt or ""},
        {"role": "user", "content": QUESTION},
    ],
}
try:
    req = urllib.request.Request(
        SPARK_CHAT_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode())
    msg = (data.get("message") or {}).get("content") or data.get("response") or ""
    if not msg and isinstance(data.get("choices"), list) and data["choices"]:
        msg = data["choices"][0].get("message", {}).get("content") or ""
except Exception as e:
    fail("spark_chat_failed", f"{type(e).__name__}: {e}", plan_kind="chat", model=decided.model)

try:
    body = mod._ground_reply(msg, QUESTION, tool_context, llm_context, decided)
except Exception:
    body = msg
try:
    from pulp_verify import flag_stamps
    body = flag_stamps(body, stamps)
except Exception:
    pass

result["answer"] = body
print(json.dumps(result))
PY
}

pulp_ask() {
  local question="${REACH_PULP_QUESTION:-${REACH_PULP_TEXT:-}}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --question|-q) question="${2:-}"; shift 2 ;;
      --help|-h)
        emit_receipt pulp ask false error L1 none "-" \
          '{"hint":"reach pulp ask -- --question \"What is down?\""}' usage "help"
        return 2
        ;;
      *) question="${question:+$question }$1"; shift ;;
    esac
  done
  if [[ -z "$question" && ! -t 0 ]]; then
    question="$(cat)"
  fi
  if [[ -z "${question// /}" ]]; then
    emit_receipt pulp ask false error L1 none "-" \
      '{"hint":"reach pulp ask -- --question \"...\""}' usage "need question"
    return 2
  fi

  local runner_local remote_runner out_file rc=0
  runner_local="$(mktemp)"
  out_file="$(mktemp)"
  write_ask_runner >"$runner_local"
  remote_runner="/tmp/reach-pulp-ask-$$.py"
  if ! scp -o BatchMode=yes -o ConnectTimeout=12 "$runner_local" "${K2VPS_HOST}:${remote_runner}" >/dev/null 2>&1; then
    rm -f "$runner_local" "$out_file"
    emit_receipt pulp ask false error L1 ssh "$K2VPS_HOST" "{}" scp_failed "scp ask runner failed"
    return 1
  fi
  rm -f "$runner_local"

  # shellcheck disable=SC2029
  ssh -o BatchMode=yes -o ConnectTimeout=40 "$K2VPS_HOST" \
    "export PULP_QUESTION=$(printf %q "$question");
     export PULP_BRIDGES=$(printf %q "$PULP_BRIDGES");
     export PULP_AUTH_STATUS_PATH=$(printf %q "$PULP_AUTH_REMOTE");
     ${PULP_VENV_PY} ${remote_runner}; rc=\$?; rm -f ${remote_runner}; exit \$rc" \
    >"$out_file" 2>/tmp/reach-pulp-ask.err || rc=$?

  local detail
  detail="$(OUT="$(cat "$out_file")" ERR="$(head -c 1200 /tmp/reach-pulp-ask.err 2>/dev/null || true)" RC="$rc" Q="$question" python3 - <<'PY'
import json, os
raw = os.environ.get("OUT") or ""
err = os.environ.get("ERR") or ""
rc = int(os.environ.get("RC") or "1")
q = os.environ.get("Q") or ""
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    data = {"ok": False, "code": "bad_json", "message": (raw or err)[:500], "rc": rc}
print(json.dumps({
    "question": q[:500],
    "rc": rc,
    "result": data,
    "stderr_tail": err[-800:] if err else "",
}))
PY
)"
  rm -f "$out_file"

  local ok code msg
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);r=d.get("result") or {};print("true" if r.get("ok") and r.get("answer") is not None else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);r=d.get("result") or {};print(r.get("code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);r=d.get("result") or {};print(r.get("message") or "ask failed")')"

  if [[ "$ok" == "true" ]]; then
    emit_receipt pulp ask true live L1 ssh "$K2VPS_HOST" "$detail"
    return 0
  fi
  emit_receipt pulp ask false error L1 ssh "$K2VPS_HOST" "$detail" \
    "${code:-ask_failed}" "$msg"
  return 1
}

pulp_dispatch() {
  local verb="$1"
  shift || true
  case "$verb" in
    status) pulp_status ;;
    ask) pulp_ask "$@" ;;
    *)
      emit_receipt pulp "$verb" false error L1 none "-" "{}" \
        unknown_verb "pulp verbs: status|ask"
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  pulp_dispatch "$@"
fi
