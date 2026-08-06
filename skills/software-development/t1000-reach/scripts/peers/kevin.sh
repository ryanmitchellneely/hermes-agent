#!/usr/bin/env bash
# A3 kevin peer — Chamberlain Telegram (L2) + kevin-claude inbox (L3).
# Notify is FAIL-CLOSED: dry-run unless --fire AND REACH_KEVIN_FIRE=1.
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

K2VPS_HOST="${K2VPS_HOST:-k2vps}"
K2_HUB_ENV_REMOTE="${K2_HUB_ENV_REMOTE:-/etc/k2-hub.env}"
INBOX_DIR="${KEVIN_INBOX_DIR:-$HOME/Documents/kevin-real-estate-tools/docs/agent-coordination/inbox-for-kevin-claude}"
FAILOVER_STATUS="${T1000_FAILOVER_STATUS:-$HOME/Documents/T1000/deploy/failover/status.sh}"

ha_snapshot() {
  FAILOVER_STATUS="$FAILOVER_STATUS" python3 - <<'PY'
import json, os, re, subprocess
from pathlib import Path

detail = {
    "mac_gateway": "unknown",
    "vps_gateway": "unknown",
    "claimed_by": "unknown",
    "hb_age_sec": None,
    "single_writer_ok": True,
    "notes": [],
}
status_sh = os.environ.get("FAILOVER_STATUS", "")
text = ""
if status_sh and Path(status_sh).exists():
    try:
        text = subprocess.check_output(
            ["bash", status_sh], text=True, timeout=25, stderr=subprocess.STDOUT
        )
    except Exception as e:
        detail["notes"].append(f"status_sh_error:{type(e).__name__}")
else:
    detail["notes"].append("no_failover_status_script")

if "gateway LaunchAgent: RUNNING" in text or re.search(r"gw=running", text):
    detail["mac_gateway"] = "running"
elif "gateway LaunchAgent" in text:
    detail["mac_gateway"] = "not_running"

if re.search(r"t1000-gateway:\s*inactive", text):
    detail["vps_gateway"] = "inactive"
elif re.search(r"t1000-gateway:\s*active", text):
    detail["vps_gateway"] = "active"

m = re.search(r"claimed_by=(\w+)", text)
if m:
    detail["claimed_by"] = m.group(1)
m = re.search(r"age_sec=(\d+)", text)
if m:
    detail["hb_age_sec"] = int(m.group(1))

if detail["vps_gateway"] == "active" and detail["mac_gateway"] == "running":
    detail["single_writer_ok"] = False
    detail["notes"].append("dual_t1000_gateway_suspected")
if detail["hb_age_sec"] is not None and detail["hb_age_sec"] > 180:
    detail["notes"].append("heartbeat_stale")

print(json.dumps(detail))
PY
}

vps_env_probe() {
  ssh -o BatchMode=yes -o ConnectTimeout=12 "$K2VPS_HOST" "python3 - <<'PY'
from pathlib import Path
import json
p = Path('${K2_HUB_ENV_REMOTE}')
env = {}
if p.is_file():
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('\"').strip(\"'\")
token = bool(env.get('TELEGRAM_BOT_TOKEN') or env.get('TELEGRAM_ALERT_BOT_TOKEN'))
chat = bool(env.get('TELEGRAM_KEVIN_CHAT_ID') or env.get('TELEGRAM_ALERT_CHAT_ID') or env.get('TELEGRAM_CHAT_ID'))
cn = Path('/opt/k2-hub/kevin-lab/lib/chamberlain_notify.py')
print(json.dumps({
    'env_file': str(p),
    'env_present': p.is_file(),
    'token_present': token,
    'kevin_chat_present': chat,
    'chamberlain_notify_py': cn.is_file(),
    'ready': token and chat,
}))
PY" 2>/dev/null || echo '{"ready":false,"error":"ssh_failed"}'
}

kevin_status() {
  local ha probe detail grade ok code msg
  ha="$(ha_snapshot)"
  probe="$(vps_env_probe)"
  detail="$(HA="$ha" PROBE="$probe" INBOX="$INBOX_DIR" python3 - <<'PY'
import json, os
from pathlib import Path
ha = json.loads(os.environ["HA"])
probe = json.loads(os.environ["PROBE"])
inbox = Path(os.environ["INBOX"])
ready = probe.get("ready") is True
sw = ha.get("single_writer_ok", True)
if not ready:
    grade, ok, code, msg = "error", False, "rail_not_ready", "VPS Chamberlain env missing token/chat or ssh failed"
elif not sw:
    grade, ok, code, msg = "error", False, "dual_gateway", "Refuse notify path while dual T1000 gateways suspected"
elif not inbox.is_dir():
    grade, ok, code, msg = "stale", True, "inbox_missing", "Chamberlain rail OK; inbox dir missing"
else:
    grade, ok, code, msg = "live", True, "", ""
detail = {
    "ha": ha,
    "chamberlain_rail": probe,
    "inbox_dir": str(inbox),
    "inbox_dir_exists": inbox.is_dir(),
    "path": "L2 Chamberlain Telegram on k2vps + L3 repo inbox",
    "_g": grade, "_ok": ok, "_code": code, "_msg": msg,
}
print(json.dumps(detail))
PY
)"
  grade="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin)["_g"])')"
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;print("true" if json.load(sys.stdin)["_ok"] else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_msg") or "")')"
  detail="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);[d.pop(k,None) for k in list(d) if k.startswith("_")];print(json.dumps(d))')"

  if [[ "$ok" == "true" && -z "$code" ]]; then
    emit_receipt kevin status true "$grade" L2 ssh "$K2VPS_HOST" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt kevin status true "$grade" L2 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
    return 0
  else
    emit_receipt kevin status false "$grade" L2 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
    return 1
  fi
}

parse_notify_args() {
  FIRE=0
  SUBJECT="${REACH_KEVIN_SUBJECT:-}"
  BODY="${REACH_KEVIN_BODY:-${REACH_KEVIN_TEXT:-}}"
  DOC_PATH="${REACH_KEVIN_FILE:-}"
  ALSO_INBOX=1
  SOURCE="${REACH_KEVIN_SOURCE:-from Ryan / T1000}"
  local -a rest=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fire) FIRE=1; shift ;;
      --dry-run) FIRE=0; shift ;;
      --subject) SUBJECT="${2:-}"; shift 2 ;;
      --body) BODY="${2:-}"; shift 2 ;;
      --file|--document) DOC_PATH="${2:-}"; shift 2 ;;
      --no-inbox) ALSO_INBOX=0; shift ;;
      --source) SOURCE="${2:-}"; shift 2 ;;
      --help|-h) return 2 ;;
      *) rest+=("$1"); shift ;;
    esac
  done
  if [[ -z "$BODY" && ${#rest[@]} -gt 0 ]]; then
    BODY="${rest[*]}"
  fi
  if [[ -z "$SUBJECT" && -n "$BODY" ]]; then
    SUBJECT="$(printf '%s' "$BODY" | head -c 80 | tr '\n' ' ')"
  fi
  return 0
}

next_inbox_nnn() {
  python3 - "$INBOX_DIR" <<'PY'
import re, sys
from pathlib import Path
d = Path(sys.argv[1])
nums = []
if d.is_dir():
    for p in d.iterdir():
        m = re.match(r"^(\d+)-", p.name)
        if m:
            nums.append(int(m.group(1)))
print(f"{(max(nums) + 1) if nums else 1:03d}")
PY
}

write_inbox() {
  local nnn subject body doc_rel slug path
  nnn="$(next_inbox_nnn)"
  subject="$1"
  body="$2"
  doc_rel="${3:-}"
  slug="$(printf '%s' "$subject" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g;s/^-+|-+$//g' | cut -c1-40)"
  [[ -n "$slug" ]] || slug="t1000-note"
  path="$INBOX_DIR/${nnn}-${slug}.md"
  mkdir -p "$INBOX_DIR"
  cat >"$path" <<EOF
---
status: open
from: ryan/T1000
to: kevin-claude
relay_to: Kevin
created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
channel: chamberlain-telegram + inbox
---

# ${subject}

${body}

## Please do
- [ ] Surface to Kevin
- [ ] Ack in inbox-for-ryan-claude if action needed

## Artifacts
- doc: ${doc_rel:-none}
- via: \`reach kevin notify\`
EOF
  printf '%s\n' "$path"
}

kevin_notify() {
  FIRE=0 SUBJECT="" BODY="" DOC_PATH="" ALSO_INBOX=1 SOURCE="from Ryan / T1000"
  if ! parse_notify_args "$@"; then
    emit_receipt kevin notify false error L2 none "-" \
      '{"hint":"reach kevin notify -- --dry-run --subject S --body B"}' \
      usage "bad notify args"
    return 2
  fi

  if [[ -z "$SUBJECT" && -z "$BODY" && -z "$DOC_PATH" ]]; then
    emit_receipt kevin notify false error L2 none "-" \
      '{"hint":"reach kevin notify -- --dry-run --subject \"Hi\" --body \"...\" "}' \
      usage "need --subject/--body or REACH_KEVIN_*"
    return 2
  fi

  local ha probe composed inbox_path=""
  ha="$(ha_snapshot)"
  probe="$(vps_env_probe)"
  composed="$(SUBJECT="$SUBJECT" BODY="$BODY" SOURCE="$SOURCE" python3 - <<'PY'
import os
mark = "\U0001F3DB️ Chamberlain"
src = os.environ.get("SOURCE") or ""
head = f"{mark} · {src}" if src else mark
text = f"{head}\n{os.environ.get('SUBJECT','')}"
body = os.environ.get("BODY") or ""
if body:
    text += f"\n\n{body}"
print(text)
PY
)"

  if [[ "$ALSO_INBOX" == "1" && ( "$FIRE" == "1" || "${REACH_KEVIN_INBOX_ALWAYS:-}" == "1" ) ]]; then
    if [[ -d "$(dirname "$INBOX_DIR")" ]]; then
      inbox_path="$(write_inbox "$SUBJECT" "$BODY" "${DOC_PATH:-}")"
    fi
  fi

  local detail
  detail="$(
    FIRE="$FIRE" SUBJECT="$SUBJECT" BODY="$BODY" SOURCE="$SOURCE" \
    DOC="$DOC_PATH" INBOX_PATH="$inbox_path" HA="$ha" PROBE="$probe" COMPOSED="$composed" \
    python3 - <<'PY'
import json, os
print(json.dumps({
    "mode": "fire" if os.environ.get("FIRE") == "1" else "dry-run",
    "subject": os.environ.get("SUBJECT", ""),
    "body_chars": len(os.environ.get("BODY") or ""),
    "source": os.environ.get("SOURCE", ""),
    "document": os.environ.get("DOC") or None,
    "composed_preview": (os.environ.get("COMPOSED") or "")[:500],
    "inbox_path": os.environ.get("INBOX_PATH") or None,
    "ha": json.loads(os.environ.get("HA") or "{}"),
    "chamberlain_rail": json.loads(os.environ.get("PROBE") or "{}"),
}))
PY
  )"

  local sw ready
  sw="$(printf '%s' "$ha" | python3 -c 'import sys,json; print("true" if json.load(sys.stdin).get("single_writer_ok",True) else "false")')"
  ready="$(printf '%s' "$probe" | python3 -c 'import sys,json; print("true" if json.load(sys.stdin).get("ready") else "false")')"

  if [[ "$sw" != "true" ]]; then
    emit_receipt kevin notify false error L2 none "-" "$detail" dual_gateway "Blocked: dual T1000 gateway suspected"
    return 1
  fi
  if [[ "$ready" != "true" ]]; then
    emit_receipt kevin notify false error L2 ssh "$K2VPS_HOST" "$detail" rail_not_ready "Chamberlain VPS rail not ready"
    return 1
  fi

  if [[ "$FIRE" != "1" ]]; then
    emit_receipt kevin notify true live L2 none "dry-run" "$detail" dry_run \
      "Dry-run only — pass --fire and REACH_KEVIN_FIRE=1 to send via Chamberlain"
    return 0
  fi

  if [[ "${REACH_KEVIN_FIRE:-}" != "1" && "${REACH_KEVIN_FIRE:-}" != "true" ]]; then
    emit_receipt kevin notify false error L2 none "-" "$detail" fire_gate \
      "Refusing send: set REACH_KEVIN_FIRE=1 with --fire (explicit dual gate)"
    return 1
  fi

  local remote_doc="" payload_file send_json
  payload_file="$(mktemp)"
  SUBJECT="$SUBJECT" BODY="$BODY" SOURCE="$SOURCE" DOC_LOCAL="$DOC_PATH" \
  python3 - <<'PY' >"$payload_file"
import json, os
print(json.dumps({
    "subject": os.environ.get("SUBJECT", ""),
    "body": os.environ.get("BODY", ""),
    "source": os.environ.get("SOURCE", "from Ryan / T1000"),
    "doc_remote": "",
}))
PY

  if [[ -n "$DOC_PATH" ]]; then
    if [[ ! -f "$DOC_PATH" ]]; then
      rm -f "$payload_file"
      emit_receipt kevin notify false error L2 none "-" "$detail" missing_file "Document not found"
      return 1
    fi
    remote_doc="/tmp/reach-kevin-$(basename "$DOC_PATH" | tr -cd 'A-Za-z0-9._-')"
    if ! scp -o BatchMode=yes -o ConnectTimeout=12 "$DOC_PATH" "${K2VPS_HOST}:${remote_doc}" >/dev/null 2>&1; then
      rm -f "$payload_file"
      emit_receipt kevin notify false error L2 ssh "$K2VPS_HOST" "$detail" scp_failed "scp document to VPS failed"
      return 1
    fi
    DOC_REMOTE="$remote_doc" python3 - <<'PY' >"$payload_file"
import json, os
print(json.dumps({
    "subject": os.environ["SUBJECT"],
    "body": os.environ.get("BODY", ""),
    "source": os.environ.get("SOURCE", "from Ryan / T1000"),
    "doc_remote": os.environ.get("DOC_REMOTE", ""),
}))
PY
    SUBJECT="$SUBJECT" BODY="$BODY" SOURCE="$SOURCE" DOC_REMOTE="$remote_doc" python3 - <<'PY' >"$payload_file"
import json, os
print(json.dumps({
    "subject": os.environ.get("SUBJECT", ""),
    "body": os.environ.get("BODY", ""),
    "source": os.environ.get("SOURCE", "from Ryan / T1000"),
    "doc_remote": os.environ.get("DOC_REMOTE", ""),
}))
PY
  fi

  # Ship payload + runner to VPS
  local remote_payload="/tmp/reach-kevin-payload-$$.json"
  local remote_runner="/tmp/reach-kevin-send-$$.py"
  scp -o BatchMode=yes -o ConnectTimeout=12 "$payload_file" "${K2VPS_HOST}:${remote_payload}" >/dev/null 2>&1 || {
    rm -f "$payload_file"
    emit_receipt kevin notify false error L2 ssh "$K2VPS_HOST" "$detail" scp_failed "scp payload failed"
    return 1
  }
  rm -f "$payload_file"

  # Write runner locally then scp
  local runner_local
  runner_local="$(mktemp)"
  cat >"$runner_local" <<'PY'
import json, os, sys, urllib.request, uuid
from pathlib import Path

def load_env(path):
    env = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
env = load_env(os.environ.get("K2_HUB_ENV", "/etc/k2-hub.env"))
token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_ALERT_BOT_TOKEN")
chat = env.get("TELEGRAM_KEVIN_CHAT_ID") or env.get("TELEGRAM_ALERT_CHAT_ID") or env.get("TELEGRAM_CHAT_ID")
if not token:
    print(json.dumps({"ok": False, "status": "skipped:no_token"})); raise SystemExit(0)
if not chat:
    print(json.dumps({"ok": False, "status": "skipped:no_chat"})); raise SystemExit(0)

subject = payload.get("subject") or ""
body = payload.get("body") or ""
source = payload.get("source") or "from Ryan / T1000"
doc = payload.get("doc_remote") or ""
mark = "\U0001F3DB️ Chamberlain"
text = f"{mark} · {source}\n{subject}"
if body:
    text += f"\n\n{body}"

try:
    if doc and Path(doc).is_file():
        boundary = uuid.uuid4().hex
        def part(name, value, filename=None, content_type=None):
            hdr = [f"--{boundary}"]
            if filename:
                hdr.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
            else:
                hdr.append(f'Content-Disposition: form-data; name="{name}"')
            if content_type:
                hdr.append(f"Content-Type: {content_type}")
            hdr.append("")
            if isinstance(value, bytes):
                return ("\r\n".join(hdr) + "\r\n").encode() + value + b"\r\n"
            return ("\r\n".join(hdr) + "\r\n" + value + "\r\n").encode()
        data = b"".join([
            part("chat_id", str(chat)),
            part("caption", text[:1024]),
            part("document", Path(doc).read_bytes(), filename=Path(doc).name, content_type="application/octet-stream"),
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=data, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "T1000-reach-kevin"},
        )
    else:
        payload_body = json.dumps({
            "chat_id": chat,
            "text": text,
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload_body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "T1000-reach-kevin"},
        )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())
    result = raw.get("result") or {}
    print(json.dumps({
        "ok": bool(raw.get("ok")),
        "status": "sent" if raw.get("ok") else "error:telegram_not_ok",
        "message_id": result.get("message_id"),
        "date": result.get("date"),
        "has_document": bool(result.get("document")),
    }))
except Exception as e:
    print(json.dumps({"ok": False, "status": f"error:{type(e).__name__}", "message": str(e)[:200]}))
PY
  scp -o BatchMode=yes -o ConnectTimeout=12 "$runner_local" "${K2VPS_HOST}:${remote_runner}" >/dev/null 2>&1 || {
    rm -f "$runner_local"
    emit_receipt kevin notify false error L2 ssh "$K2VPS_HOST" "$detail" scp_failed "scp runner failed"
    return 1
  }
  rm -f "$runner_local"

  send_json="$(
    ssh -o BatchMode=yes -o ConnectTimeout=20 "$K2VPS_HOST" \
      "K2_HUB_ENV=${K2_HUB_ENV_REMOTE} python3 ${remote_runner} ${remote_payload}; rm -f ${remote_runner} ${remote_payload} ${remote_doc:-}"
  )" || send_json='{"ok":false,"status":"error:ssh"}'

  detail="$(DETAIL="$detail" SEND="$send_json" python3 - <<'PY'
import json, os
d = json.loads(os.environ["DETAIL"])
try:
    s = json.loads(os.environ["SEND"])
except json.JSONDecodeError:
    s = {"ok": False, "status": "error:bad_json", "raw": (os.environ.get("SEND") or "")[:300]}
d["send"] = s
print(json.dumps(d))
PY
)"

  local sok mid st
  sok="$(printf '%s' "$send_json" | python3 -c 'import sys,json;print("true" if json.load(sys.stdin).get("ok") else "false")' 2>/dev/null || echo false)"
  mid="$(printf '%s' "$send_json" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("message_id") or "-")' 2>/dev/null || echo "-")"
  st="$(printf '%s' "$send_json" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status") or "error")' 2>/dev/null || echo error)"

  if [[ "$sok" == "true" ]]; then
    emit_receipt kevin notify true live L2 message_id "$mid" "$detail"
    return 0
  fi
  emit_receipt kevin notify false error L2 none "-" "$detail" "send_$st" "Chamberlain send failed ($st)"
  return 1
}

kevin_inbox() {
  local subject="${REACH_KEVIN_SUBJECT:-}" body="${REACH_KEVIN_BODY:-${REACH_KEVIN_TEXT:-}}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --subject) subject="${2:-}"; shift 2 ;;
      --body) body="${2:-}"; shift 2 ;;
      *) body="${body:+$body }$1"; shift ;;
    esac
  done
  [[ -n "$subject" ]] || subject="Note from T1000"
  if [[ -z "$body" ]]; then
    emit_receipt kevin inbox false error L3 none "-" "{}" usage "need body text"
    return 2
  fi
  if [[ ! -d "$(dirname "$INBOX_DIR")" ]]; then
    emit_receipt kevin inbox false error L3 path "$INBOX_DIR" "{}" no_repo "inbox parent missing"
    return 1
  fi
  local path detail
  path="$(write_inbox "$subject" "$body" "")"
  detail="$(python3 -c 'import json,sys; print(json.dumps({"inbox_path":sys.argv[1],"subject":sys.argv[2]}))' "$path" "$subject")"
  emit_receipt kevin inbox true live L3 path "$path" "$detail"
  return 0
}

kevin_dispatch() {
  local verb="$1"
  shift || true
  case "$verb" in
    status) kevin_status ;;
    notify) kevin_notify "$@" ;;
    inbox) kevin_inbox "$@" ;;
    *)
      emit_receipt kevin "$verb" false error L2 none "-" "{}" \
        unknown_verb "kevin verbs: status|notify|inbox"
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  kevin_dispatch "$@"
fi
