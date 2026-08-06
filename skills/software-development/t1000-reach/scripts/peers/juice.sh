#!/usr/bin/env bash
# A2 juice peer adapter — sovereign_juice CLI (NOT the Electron cockpit).
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

JUICE_LAUNCHER="${JUICE_LAUNCHER:-$HOME/Documents/T1000/scripts/juice}"
JUICE_DOCTOR="${JUICE_DOCTOR:-$HOME/Documents/T1000/scripts/juice-doctor}"
JUICE_ROOT="${JUICE_ROOT:-$HOME/Documents/sovereign-consulting/tools/juice}"
SPARK_TAGS_URL="${SPARK_BASE_URL:-http://127.0.0.1:11435}/api/tags"

find_juice_launcher() {
  local c
  for c in "$JUICE_LAUNCHER" "$HOME/.local/bin/juice" "$HOME/Documents/T1000/scripts/juice"; do
    [[ -n "$c" && -x "$c" ]] && { printf '%s\n' "$c"; return 0; }
    [[ -n "$c" && -f "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

run_sovereign_juice() {
  # Direct package invoke — avoids Electron path and keeps SPARK env.
  if [[ ! -f "$JUICE_ROOT/sovereign_juice/__main__.py" ]]; then
    return 127
  fi
  (
    cd "$JUICE_ROOT"
    export PYTHONPATH=".:sovereign_juice${PYTHONPATH:+:$PYTHONPATH}"
    # Classify/triage require the Spark lane gate (status/doctor do not).
    export SPARK_ENABLED="${SPARK_ENABLED:-true}"
    export SPARK_BASE_URL="${SPARK_BASE_URL:-http://127.0.0.1:11435}"
    python3 -m sovereign_juice "$@"
  )
}

spark_classify_up() {
  curl -sf --max-time 2 "${SPARK_TAGS_URL%/api/tags}/api/version" >/dev/null 2>&1 \
    || curl -sf --max-time 2 "$SPARK_TAGS_URL" >/dev/null 2>&1
}

# Build graded receipt detail from status v2 JSON on stdin / file
grade_status_json() {
  local status_file="$1"
  local spark_up="$2"
  SPARK_UP="$spark_up" python3 - "$status_file" <<'PY'
import json, os, sys
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8")
try:
    status = json.loads(raw)
except json.JSONDecodeError as e:
    print(json.dumps({
        "parse_ok": False,
        "error": str(e),
        "grade": "error",
        "ok": False,
        "code": "invalid_status_json",
        "message": "juice status did not return valid JSON",
    }))
    raise SystemExit(0)

boundaries = status.get("boundaries") or []
bset = set(boundaries)
# Safety contract: must be classify-only and no sends (wording may vary slightly)
has_classify_only = any("classify-only" in b for b in boundaries)
has_no_sends = any("no send" in b.lower() for b in boundaries)
has_no_drafts = any("no draft" in b.lower() for b in boundaries)
live_auth = any("live-authorized" in b for b in boundaries)
synthetic_only = any("synthetic-only" in b for b in boundaries)

r0 = status.get("r0_controls") or {}
baseline = (r0.get("baseline") or {}).get("state")
threshold = (r0.get("threshold") or {}).get("state")
eval_state = (status.get("evaluation") or {}).get("state")
ver_state = (status.get("verification") or {}).get("state")

spark_up = os.environ.get("SPARK_UP") == "true"
safety_ok = has_classify_only and has_no_sends and has_no_drafts
parse_ok = status.get("status_version") == 2 and status.get("display_name") == "Juice"

# Auth facet vs model facet (ops rule: never collapse)
auth_facet = "live-authorized" if live_auth else ("synthetic-only" if synthetic_only else "unknown")
model_facet = "up" if spark_up else "down"

# Grading
if not parse_ok or not safety_ok:
    grade, ok, code, msg = "error", False, "safety_or_schema", "Juice status unreadable or safety boundaries broken"
elif not spark_up:
    # status itself is fine; classify lane down → stale (not full error)
    grade, ok, code, msg = "stale", True, "spark_down", "Status OK; Spark classify lane down"
elif baseline == "unlocked" or threshold == "unset" or eval_state == "stale" or ver_state == "stale":
    grade, ok, code, msg = "stale", True, "r0_proving", "Status OK; R0 still proving (not fully operational)"
else:
    grade, ok, code, msg = "live", True, "", ""

detail = {
    "parse_ok": parse_ok,
    "safety_ok": safety_ok,
    "auth": {
        "facet": auth_facet,
        "live_authorized": live_auth,
        "boundaries": boundaries,
    },
    "model": {
        "facet": model_facet,
        "spark_classify_url": os.environ.get("SPARK_TAGS", "http://127.0.0.1:11435"),
        "spark_up": spark_up,
    },
    "ladder": {
        "build_frontier": status.get("build_frontier"),
        "promotion_frontier": status.get("promotion_frontier"),
        "current_gate": status.get("current_gate"),
        "next_action": status.get("next_action"),
        "baseline": baseline,
        "threshold": threshold,
        "evaluation_state": eval_state,
        "verification_state": ver_state,
        "r0_review_signed": (r0.get("review") or {}).get("signed_off"),
    },
    "capability_id": status.get("capability_id"),
    "prompt_version": status.get("prompt_version"),
    "generated_at": status.get("generated_at"),
    "status": status,  # full v2 blob for agents that need it
    "grade_hint": grade,
    "ok_hint": ok,
    "error_code": code,
    "error_message": msg,
}
print(json.dumps(detail))
PY
}

juice_status() {
  local out_file rc=0
  out_file="$(mktemp)"
  if ! run_sovereign_juice status >"$out_file" 2>/tmp/reach-juice-status.err; then
    rc=$?
    local err
    err="$(head -c 400 /tmp/reach-juice-status.err 2>/dev/null || true)"
    emit_receipt juice status false error L0 path "$JUICE_ROOT" \
      "$(python3 -c 'import json,sys; print(json.dumps({"rc":int(sys.argv[1]),"stderr_tail":sys.argv[2]}))' "$rc" "$err")" \
      juice_status_failed "sovereign_juice status failed (rc=$rc)"
    rm -f "$out_file"
    return 1
  fi

  local spark_up=false
  if spark_classify_up; then spark_up=true; fi

  local detail grade ok code msg
  detail="$(SPARK_TAGS="${SPARK_BASE_URL:-http://127.0.0.1:11435}" grade_status_json "$out_file" "$spark_up")"
  rm -f "$out_file"

  grade="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("grade_hint","error"))')"
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json; print("true" if json.load(sys.stdin).get("ok_hint") else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error_code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error_message") or "")')"

  # Strip grade hints from detail for cleaner receipt
  detail="$(printf '%s' "$detail" | python3 -c 'import sys,json; d=json.load(sys.stdin); [d.pop(k,None) for k in ("grade_hint","ok_hint","error_code","error_message")]; print(json.dumps(d))')"

  if [[ "$ok" == "true" && -z "$code" ]]; then
    emit_receipt juice status true "$grade" L0 local "sovereign_juice status" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt juice status true "$grade" L0 local "sovereign_juice status" "$detail" "$code" "$msg"
    return 0
  else
    emit_receipt juice status false "$grade" L0 local "sovereign_juice status" "$detail" "$code" "$msg"
    return 1
  fi
}

juice_doctor() {
  local launcher doctor_bin out_file rc=0
  out_file="$(mktemp)"
  doctor_bin="$JUICE_DOCTOR"
  if [[ ! -x "$doctor_bin" && ! -f "$doctor_bin" ]]; then
    if launcher="$(find_juice_launcher)"; then
      # juice --doctor
      if ! "$launcher" --doctor >"$out_file" 2>&1; then rc=$?; fi
    else
      emit_receipt juice doctor false error L0 none "-" "{}" no_doctor "juice-doctor not found"
      rm -f "$out_file"
      return 1
    fi
  else
    if ! bash "$doctor_bin" >"$out_file" 2>&1; then rc=$?; fi
  fi

  local detail
  detail="$(python3 - "$out_file" "$rc" <<'PY'
import json, re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
rc = int(sys.argv[2])
lines = text.splitlines()

def find_line(prefix):
    for ln in lines:
        if ln.startswith(prefix) or prefix in ln:
            return ln
    return None

spark_line = find_line("Juice classify lane") or ""
ollama_line = next((ln for ln in lines if ln.startswith("Ollama:")), "")
juice_status_line = find_line("Juice status:") or ""
operational = next((ln for ln in lines if ln.startswith("OPERATIONAL:")), "")
ok_line = next((ln for ln in lines if ln.startswith("OK:") or ln.startswith("NOT OK")), "")

spark_up = "UP" in spark_line and "DOWN" not in spark_line
boundaries_intact = "intact" in juice_status_line.lower() or "safety contract intact" in text.lower()
operational_yes = "OPERATIONAL: yes" in text

# Doctor is advisory readiness: fail only on hard script failure / missing source
if rc != 0 and "MISSING" in text and "Juice source" in text:
    grade, ok, code, msg = "error", False, "doctor_failed", "juice-doctor reported failure"
elif not boundaries_intact and "Juice status:" in text:
    grade, ok, code, msg = "error", False, "safety", "doctor: safety contract not intact"
elif not spark_up or not operational_yes:
    grade, ok, code, msg = "stale", True, "not_fully_operational", "doctor OK-ish; classify/R0 not fully green"
else:
    grade, ok, code, msg = "live", True, "", ""

detail = {
    "rc": rc,
    "spark_classify": spark_line.strip(),
    "spark_up": spark_up,
    "ollama": ollama_line.strip(),
    "juice_status_line": juice_status_line.strip(),
    "operational": operational.strip(),
    "summary": ok_line.strip() if ok_line else "",
    "output_tail": "\n".join(lines[-40:]),
    "grade_hint": grade,
    "ok_hint": ok,
    "error_code": code,
    "error_message": msg,
}
print(json.dumps(detail))
PY
)"

  local grade ok code msg
  grade="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("grade_hint","error"))')"
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json; print("true" if json.load(sys.stdin).get("ok_hint") else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error_code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error_message") or "")')"
  detail="$(printf '%s' "$detail" | python3 -c 'import sys,json; d=json.load(sys.stdin); [d.pop(k,None) for k in ("grade_hint","ok_hint","error_code","error_message")]; print(json.dumps(d))')"
  rm -f "$out_file"

  if [[ "$ok" == "true" && -z "$code" ]]; then
    emit_receipt juice doctor true "$grade" L0 local "juice-doctor" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt juice doctor true "$grade" L0 local "juice-doctor" "$detail" "$code" "$msg"
    return 0
  else
    emit_receipt juice doctor false "$grade" L0 local "juice-doctor" "$detail" "$code" "$msg"
    return 1
  fi
}

# classify: default SYNTHETIC only (safe). Usage via env/flags after verb.
#   reach juice classify -- --channel email --synthetic
#   echo "text" | reach juice classify -- --channel email --synthetic
#   REACH_JUICE_TEXT='...' reach juice classify -- --channel sms --synthetic
juice_classify() {
  local -a extra=("$@")
  # Defaults: require channel; default synthetic if neither flag present
  local has_channel=false has_mode=false
  local a
  for a in "${extra[@]+"${extra[@]}"}"; do
    [[ "$a" == "--channel" ]] && has_channel=true
    [[ "$a" == "--synthetic" || "$a" == "--real" ]] && has_mode=true
  done

  if [[ "$has_channel" != "true" ]]; then
    emit_receipt juice classify false error L0 none "-" \
      '{"hint":"reach juice classify -- --channel email|sms|call_transcript --synthetic"}' \
      usage "classify requires --channel"
    return 2
  fi
  if [[ "$has_mode" != "true" ]]; then
    extra+=(--synthetic)
  fi

  # Refuse --real without explicit REACH_JUICE_ALLOW_REAL=1 (extra seatbelt)
  for a in "${extra[@]+"${extra[@]}"}"; do
    if [[ "$a" == "--real" && "${REACH_JUICE_ALLOW_REAL:-}" != "1" ]]; then
      emit_receipt juice classify false error L0 none "-" "{}" \
        real_blocked "Set REACH_JUICE_ALLOW_REAL=1 to classify real comms via reach"
      return 1
    fi
  done

  if ! spark_classify_up; then
    emit_receipt juice classify false error L0 http "$SPARK_TAGS_URL" \
      '{"spark_up":false}' spark_down "Spark classify lane down — tunnel up first (reach spark tunnel-up)"
    return 1
  fi

  local out_file err_file rc=0
  out_file="$(mktemp)"
  err_file="$(mktemp)"

  if [[ -n "${REACH_JUICE_TEXT:-}" ]]; then
    if ! printf '%s' "$REACH_JUICE_TEXT" | run_sovereign_juice classify "${extra[@]}" >"$out_file" 2>"$err_file"; then
      rc=$?
    fi
  elif [[ ! -t 0 ]]; then
    # stdin has data
    if ! run_sovereign_juice classify "${extra[@]}" >"$out_file" 2>"$err_file"; then
      rc=$?
    fi
  else
    emit_receipt juice classify false error L0 none "-" \
      '{"hint":"pipe text on stdin or set REACH_JUICE_TEXT"}' \
      no_input "classify needs stdin text or REACH_JUICE_TEXT"
    rm -f "$out_file" "$err_file"
    return 2
  fi

  local detail
  detail="$(python3 - "$out_file" "$err_file" "$rc" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").strip()
err = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace").strip()
rc = int(sys.argv[3])
parsed = None
if out:
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        parsed = None
detail = {
    "rc": rc,
    "result": parsed,
    "stdout_tail": out[-2000:] if out else "",
    "stderr_tail": err[-800:] if err else "",
}
print(json.dumps(detail))
PY
)"
  rm -f "$out_file" "$err_file"

  if [[ "$rc" -eq 0 ]]; then
    # Juice may exit 0 with {"success": false, "error": "..."} — treat as failure
    local logical_ok
    logical_ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);r=d.get("result");
print("true" if isinstance(r,dict) and r.get("success") is not False and "error" not in r else ("true" if isinstance(r,dict) and "intent" in r else "false"))')"
    if [[ "$logical_ok" == "true" ]]; then
      emit_receipt juice classify true live L0 local "sovereign_juice classify" "$detail"
      return 0
    fi
    emit_receipt juice classify false error L0 local "sovereign_juice classify" "$detail" \
      classify_failed "classify returned success=false or missing intent"
    return 1
  fi
  emit_receipt juice classify false error L0 local "sovereign_juice classify" "$detail" \
    classify_failed "classify exited $rc"
  return 1
}

juice_triage() {
  local -a extra=("$@")
  local has_mode=false a
  for a in "${extra[@]+"${extra[@]}"}"; do
    [[ "$a" == "--synthetic" || "$a" == "--real" ]] && has_mode=true
  done
  if [[ "$has_mode" != "true" ]]; then
    extra+=(--synthetic)
  fi
  for a in "${extra[@]+"${extra[@]}"}"; do
    if [[ "$a" == "--real" && "${REACH_JUICE_ALLOW_REAL:-}" != "1" ]]; then
      emit_receipt juice triage false error L0 none "-" "{}" \
        real_blocked "Set REACH_JUICE_ALLOW_REAL=1 for real triage"
      return 1
    fi
  done

  if ! spark_classify_up; then
    emit_receipt juice triage false error L0 http "$SPARK_TAGS_URL" \
      '{"spark_up":false}' spark_down "Spark classify lane down"
    return 1
  fi

  local out_file err_file rc=0
  out_file="$(mktemp)"
  err_file="$(mktemp)"
  if [[ -n "${REACH_JUICE_TEXT:-}" ]]; then
    printf '%s' "$REACH_JUICE_TEXT" | run_sovereign_juice triage "${extra[@]}" >"$out_file" 2>"$err_file" || rc=$?
  elif [[ ! -t 0 ]]; then
    run_sovereign_juice triage "${extra[@]}" >"$out_file" 2>"$err_file" || rc=$?
  else
    # triage may accept empty batch differently — still try with no stdin synthetic
    run_sovereign_juice triage "${extra[@]}" >"$out_file" 2>"$err_file" || rc=$?
  fi

  local detail
  detail="$(python3 - "$out_file" "$err_file" "$rc" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").strip()
err = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace").strip()
rc = int(sys.argv[3])
parsed = None
if out:
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        parsed = {"raw": out[-2000:]}
detail = {"rc": rc, "result": parsed, "stderr_tail": err[-800:]}
print(json.dumps(detail))
PY
)"
  rm -f "$out_file" "$err_file"

  if [[ "$rc" -eq 0 ]]; then
    emit_receipt juice triage true live L0 local "sovereign_juice triage" "$detail"
    return 0
  fi
  emit_receipt juice triage false error L0 local "sovereign_juice triage" "$detail" \
    triage_failed "triage exited $rc"
  return 1
}

juice_dispatch() {
  local verb="$1"
  shift || true
  case "$verb" in
    status) juice_status ;;
    doctor) juice_doctor ;;
    classify) juice_classify "$@" ;;
    triage) juice_triage "$@" ;;
    *)
      emit_receipt juice "$verb" false error L0 none "-" "{}" \
        unknown_verb "juice verbs: status|doctor|classify|triage"
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  juice_dispatch "$@"
fi
