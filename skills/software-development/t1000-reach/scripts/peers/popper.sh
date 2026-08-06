#!/usr/bin/env bash
# A5 popper peer — Sovereign Labs on k2vps (/opt/t1000-lab), READ-ONLY.
# Verbs: status | labs | findings. Never enqueue / promote / write labs.
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

K2VPS_HOST="${K2VPS_HOST:-k2vps}"
POPPER_UNIT="${POPPER_UNIT:-buzz-agent-t1000.service}"
POPPER_ROOT="${POPPER_ROOT:-/opt/t1000-lab}"
POPPER_LABS="${POPPER_LABS:-/opt/t1000-lab/labs}"
POPPER_EXPERIMENTS="${POPPER_EXPERIMENTS:-/opt/t1000-lab/labs/experiments}"
CADENS_URL="${POPPER_CADENS_URL:-http://127.0.0.1:11436}"
CADENS_WARM_STATUS="${POPPER_CADENS_WARM_STATUS:-/var/lib/juice/cadens_warm_status.json}"

_popper_remote_probe() {
  # Local heredoc → remote bash -s (avoids nested-quote hell inside ssh "...")
  ssh -o BatchMode=yes -o ConnectTimeout=15 "$K2VPS_HOST" bash -s \
    -- "$POPPER_UNIT" "$POPPER_ROOT" "$POPPER_LABS" "$POPPER_EXPERIMENTS" \
       "$CADENS_URL" "$CADENS_WARM_STATUS" <<'REMOTE' 2>/dev/null || echo '{"error":"ssh_failed"}'
set -euo pipefail
POPPER_UNIT="$1"
POPPER_ROOT="$2"
POPPER_LABS="$3"
POPPER_EXPERIMENTS="$4"
CADENS_URL="$5"
CADENS_WARM_STATUS="$6"

export U_ACTIVE
U_ACTIVE="$(systemctl is-active "$POPPER_UNIT" 2>/dev/null || true)"
export U_ENABLED
U_ENABLED="$(systemctl is-enabled "$POPPER_UNIT" 2>/dev/null || true)"
export U_PID
U_PID="$(systemctl show -p MainPID --value "$POPPER_UNIT" 2>/dev/null || true)"
export U_ENTER
U_ENTER="$(systemctl show -p ActiveEnterTimestamp --value "$POPPER_UNIT" 2>/dev/null || true)"
export U_USER
U_USER="$(systemctl show -p User --value "$POPPER_UNIT" 2>/dev/null || true)"
export U_GROUP
U_GROUP="$(systemctl show -p Group --value "$POPPER_UNIT" 2>/dev/null || true)"
export SPARK_UP=0
curl -sf --max-time 2 http://127.0.0.1:11435/api/version >/dev/null 2>&1 && SPARK_UP=1 || true
export SPARK_UP
export CADENS_UP=0
curl -sf --max-time 2 "${CADENS_URL%/}/api/version" >/dev/null 2>&1 && CADENS_UP=1 || true
export CADENS_UP
export RUNNER PROPOSER REVIEWER RUNNER_T REVIEWER_T
RUNNER="$(systemctl is-active sovereign-labs-runner.service 2>/dev/null || true)"
PROPOSER="$(systemctl is-active sovereign-labs-proposer.service 2>/dev/null || true)"
REVIEWER="$(systemctl is-active sovereign-labs-reviewer.service 2>/dev/null || true)"
RUNNER_T="$(systemctl is-enabled sovereign-labs-runner.timer 2>/dev/null || true)"
REVIEWER_T="$(systemctl is-enabled sovereign-labs-reviewer.timer 2>/dev/null || true)"
export POPPER_UNIT_NAME="$POPPER_UNIT"
export POPPER_ROOT_P="$POPPER_ROOT"
export POPPER_LABS_P="$POPPER_LABS"
export POPPER_EXPERIMENTS_P="$POPPER_EXPERIMENTS"
export CADENS_URL_P="$CADENS_URL"
export CADENS_WARM_P="$CADENS_WARM_STATUS"

python3 - <<'PY'
import json, os
from pathlib import Path
from datetime import datetime, timezone

root = Path(os.environ.get("POPPER_ROOT_P", "/opt/t1000-lab"))
labs = Path(os.environ.get("POPPER_LABS_P", "/opt/t1000-lab/labs"))
exp_root = Path(os.environ.get("POPPER_EXPERIMENTS_P", "/opt/t1000-lab/labs/experiments"))
warm_path = Path(os.environ.get("CADENS_WARM_P", "/var/lib/juice/cadens_warm_status.json"))
unit_name = os.environ.get("POPPER_UNIT_NAME", "buzz-agent-t1000.service")
cadens_url = os.environ.get("CADENS_URL_P", "http://127.0.0.1:11436")

def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None

def mtime_iso(p: Path):
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

experiments = []
if exp_root.is_dir():
    for d in sorted(exp_root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        result_md = d / "RESULT.md"
        results_json = d / "results.json"
        prereg = d / "PREREGISTRATION.md"
        readme = d / "README.md"
        verdict = None
        status = None
        if results_json.is_file():
            try:
                rj = json.loads(results_json.read_text(encoding="utf-8"))
                if isinstance(rj, dict):
                    verdict = rj.get("overall_verdict") or rj.get("verdict")
                    status = rj.get("status")
            except Exception:
                pass
        experiments.append({
            "id": d.name,
            "has_result_md": result_md.is_file(),
            "has_results_json": results_json.is_file(),
            "has_prereg": prereg.is_file(),
            "has_readme": readme.is_file(),
            "result_mtime": mtime_iso(result_md) if result_md.is_file() else (
                mtime_iso(results_json) if results_json.is_file() else None
            ),
            "dir_mtime": mtime_iso(d),
            "verdict": verdict,
            "run_status": status,
            "completed": result_md.is_file() or results_json.is_file(),
        })

completed = sum(1 for e in experiments if e["completed"])
with_result_md = sum(1 for e in experiments if e["has_result_md"])
tool_sel = next((e for e in experiments if "tool-selection" in e["id"]), None)

warm = load_json(warm_path)
warm_age_s = None
if isinstance(warm, dict) and warm.get("fired_at"):
    try:
        fired = datetime.fromisoformat(str(warm["fired_at"]).replace("Z", "+00:00"))
        warm_age_s = int((datetime.now(timezone.utc) - fired).total_seconds())
    except Exception:
        warm_age_s = None

print(json.dumps({
    "unit": {
        "name": unit_name,
        "active": os.environ.get("U_ACTIVE", ""),
        "enabled": os.environ.get("U_ENABLED", ""),
        "main_pid": os.environ.get("U_PID", ""),
        "active_enter": os.environ.get("U_ENTER", ""),
        "user": os.environ.get("U_USER", ""),
        "group": os.environ.get("U_GROUP", ""),
    },
    "paths": {
        "root": str(root),
        "labs": str(labs),
        "experiments": str(exp_root),
        "registry": str(labs / "registry"),
        "charter": str(labs / "CHARTER.md"),
        "exists_root": root.is_dir(),
        "exists_labs": labs.is_dir(),
        "exists_experiments": exp_root.is_dir(),
    },
    "identity": {
        "os_user_expected": "t1000lab",
        "role": "scientist",
        "write_policy": "read_only_via_reach",
        "no_auto_enqueue": True,
        "no_self_promote": True,
    },
    "inference": {
        "spark_loopback_11435": os.environ.get("SPARK_UP") == "1",
        "cadens_loopback_11436": os.environ.get("CADENS_UP") == "1",
        "cadens_url": cadens_url,
        "note": "Cadens is non-critical Popper warm path; Spark is fleet critical path",
    },
    "cadens_warm": warm,
    "cadens_warm_age_seconds": warm_age_s,
    "labs_timers": {
        "runner_service": os.environ.get("RUNNER", ""),
        "proposer_service": os.environ.get("PROPOSER", ""),
        "reviewer_service": os.environ.get("REVIEWER", ""),
        "runner_timer": os.environ.get("RUNNER_T", ""),
        "reviewer_timer": os.environ.get("REVIEWER_T", ""),
    },
    "experiments_summary": {
        "count": len(experiments),
        "completed": completed,
        "with_result_md": with_result_md,
        "tool_selection": tool_sel,
    },
    "experiments": experiments,
    "charter_limits": [
        "no_production_writes",
        "no_customer_contact",
        "no_self_promote",
        "human_gated_enqueue",
        "synthetic_or_lab_only",
    ],
}))
PY
REMOTE
}

popper_status() {
  local raw detail
  raw="$(_popper_remote_probe)"

  detail="$(RAW="$raw" python3 - <<'PY'
import json, os

try:
    raw = json.loads(os.environ["RAW"])
except json.JSONDecodeError:
    raw = {"error": "bad_json", "raw": (os.environ.get("RAW") or "")[:300]}

unit = raw.get("unit") or {}
paths = raw.get("paths") or {}
inf = raw.get("inference") or {}
active = unit.get("active") == "active"
user_ok = (unit.get("user") or "") == "t1000lab"
labs_ok = bool(paths.get("exists_experiments"))
cadens = bool(inf.get("cadens_loopback_11436"))
spark = bool(inf.get("spark_loopback_11435"))
warm_age = raw.get("cadens_warm_age_seconds")
warm_stale = isinstance(warm_age, int) and warm_age > 7200

if raw.get("error") in ("ssh_failed", "bad_json") or not unit:
    grade, ok, code, msg = "error", False, "ssh_failed", "Cannot reach VPS popper status"
elif not active:
    grade, ok, code, msg = "error", False, "unit_inactive", "buzz-agent-t1000 is not active"
elif not labs_ok:
    grade, ok, code, msg = "error", False, "labs_missing", "experiments tree missing under /opt/t1000-lab/labs"
elif not user_ok:
    grade, ok, code, msg = "stale", True, "user_not_isolated", f"unit user={unit.get('user')!r} expected t1000lab"
elif not cadens and not spark:
    grade, ok, code, msg = "stale", True, "inference_down", "Both Cadens :11436 and Spark :11435 down on VPS"
elif not cadens:
    grade, ok, code, msg = "stale", True, "cadens_down", "Popper unit live; Cadens :11436 down (non-critical)"
elif warm_stale:
    grade, ok, code, msg = "stale", True, "cadens_warm_stale", f"cadens_warm age {warm_age}s > 7200"
else:
    grade, ok, code, msg = "live", True, "", ""

summary = raw.get("experiments_summary") or {}
warm = raw.get("cadens_warm") if isinstance(raw.get("cadens_warm"), dict) else {}
out = {
    "unit": unit,
    "paths": {
        "root": paths.get("root"),
        "labs": paths.get("labs"),
        "experiments": paths.get("experiments"),
        "registry": paths.get("registry"),
        "exists_experiments": paths.get("exists_experiments"),
    },
    "identity": raw.get("identity"),
    "inference": inf,
    "cadens_warm": {
        "status": warm.get("status"),
        "fired_at": warm.get("fired_at"),
        "note": warm.get("note"),
        "age_seconds": warm_age,
    },
    "labs_timers": raw.get("labs_timers"),
    "experiments_summary": summary,
    "tool_selection": summary.get("tool_selection"),
    "charter_limits": raw.get("charter_limits"),
    "critical_path": False,
    "_g": grade, "_ok": ok, "_code": code, "_msg": msg,
}
print(json.dumps(out))
PY
)"

  local grade ok code msg
  grade="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin)["_g"])')"
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;print("true" if json.load(sys.stdin)["_ok"] else "false")')"
  code="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_code") or "")')"
  msg="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("_msg") or "")')"
  detail="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);[d.pop(k,None) for k in list(d) if k.startswith("_")];print(json.dumps(d))')"

  if [[ "$ok" == "true" && -z "$code" ]]; then
    emit_receipt popper status true "$grade" L0 ssh "$K2VPS_HOST" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt popper status true "$grade" L0 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
    return 0
  fi
  emit_receipt popper status false "$grade" L0 ssh "$K2VPS_HOST" "$detail" "$code" "$msg"
  return 1
}

popper_labs() {
  local raw detail
  raw="$(_popper_remote_probe)"
  detail="$(RAW="$raw" python3 - <<'PY'
import json, os
try:
    raw = json.loads(os.environ["RAW"])
except json.JSONDecodeError:
    raw = {"error": "bad_json"}

exps = raw.get("experiments") or []
exps_sorted = sorted(exps, key=lambda e: e.get("dir_mtime") or "", reverse=True)
print(json.dumps({
    "count": len(exps_sorted),
    "completed": sum(1 for e in exps_sorted if e.get("completed")),
    "labs": exps_sorted,
    "paths": raw.get("paths"),
    "unit_active": (raw.get("unit") or {}).get("active"),
    "error": raw.get("error"),
    "write_policy": "read_only",
}))
PY
)"

  local ok
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("true" if d.get("count",0)>0 and not d.get("error") else "false")')"
  if [[ "$ok" == "true" ]]; then
    emit_receipt popper labs true live L0 ssh "$K2VPS_HOST" "$detail"
    return 0
  fi
  emit_receipt popper labs false error L0 ssh "$K2VPS_HOST" "$detail" \
    labs_list_failed "Could not list /opt/t1000-lab/labs/experiments"
  return 1
}

popper_findings() {
  local lab_filter="${REACH_POPPER_LAB:-}"
  local limit="${REACH_POPPER_FINDINGS_LIMIT:-8}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --lab|-l) lab_filter="${2:-}"; shift 2 ;;
      --limit|-n) limit="${2:-8}"; shift 2 ;;
      --help|-h)
        emit_receipt popper findings false error L0 none "-" \
          '{"hint":"reach popper findings [-- --lab lab-0021-tool-selection] [-- --limit 5]"}' \
          usage "help"
        return 2
        ;;
      *) lab_filter="$1"; shift ;;
    esac
  done

  local raw
  raw="$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$K2VPS_HOST" bash -s \
    -- "$POPPER_EXPERIMENTS" "$lab_filter" "$limit" <<'REMOTE' 2>/dev/null || echo '{"error":"ssh_failed"}'
set -euo pipefail
export POPPER_EXPERIMENTS_P="$1"
export LAB_FILTER="$2"
export LIMIT="$3"
python3 - <<'PY'
import json, os, re
from pathlib import Path
from datetime import datetime, timezone

exp_root = Path(os.environ.get("POPPER_EXPERIMENTS_P", "/opt/t1000-lab/labs/experiments"))
lab_filter = (os.environ.get("LAB_FILTER") or "").strip()
try:
    limit = max(1, min(30, int(os.environ.get("LIMIT") or "8")))
except ValueError:
    limit = 8

def mtime_iso(p: Path):
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def head_text(p: Path, n=40):
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[:n])
    except Exception as e:
        return f"[read_error: {type(e).__name__}: {e}]"

def extract_verdict_from_md(text: str):
    for line in text.splitlines():
        if re.search(r"overall\s+outcome|overall_verdict|\*\*Verdict", line, re.I):
            return line.strip()[:240]
        m = re.search(r"verdict\s*[:=]\s*\*\*([^*]+)\*\*", line, re.I)
        if m:
            return m.group(0)[:240]
    return None

if not exp_root.is_dir():
    print(json.dumps({"error": "experiments_missing", "path": str(exp_root)}))
    raise SystemExit(0)

cands = []
for d in exp_root.iterdir():
    if not d.is_dir() or d.name.startswith("."):
        continue
    if lab_filter and lab_filter not in d.name and lab_filter.lower() not in d.name.lower():
        continue
    cands.append(d)

def sort_key(d: Path):
    res = d / "RESULT.md"
    rj = d / "results.json"
    stamp = 0.0
    for p in (res, rj, d):
        try:
            stamp = max(stamp, p.stat().st_mtime)
        except Exception:
            pass
    completed = 1 if res.is_file() or rj.is_file() else 0
    return (completed, stamp)

cands.sort(key=sort_key, reverse=True)
findings = []
for d in cands[:limit]:
    result_md = d / "RESULT.md"
    results_json = d / "results.json"
    item = {
        "id": d.name,
        "path": str(d),
        "has_result_md": result_md.is_file(),
        "has_results_json": results_json.is_file(),
        "mtime": mtime_iso(result_md if result_md.is_file() else (results_json if results_json.is_file() else d)),
        "verdict": None,
        "run_status": None,
        "summary": None,
        "result_head": None,
        "results_json_summary": None,
    }
    if results_json.is_file():
        try:
            rj = json.loads(results_json.read_text(encoding="utf-8"))
            if isinstance(rj, dict):
                item["verdict"] = rj.get("overall_verdict") or rj.get("verdict")
                item["run_status"] = rj.get("status")
                arms = rj.get("arms") or {}
                arm_sum = []
                if isinstance(arms, dict):
                    for k, v in list(arms.items())[:12]:
                        if not isinstance(v, dict):
                            continue
                        arm_sum.append({
                            "arm": k,
                            "verdict": v.get("verdict"),
                            "first_tool_accuracy": v.get("first_tool_accuracy"),
                            "full_sequence_accuracy": v.get("full_sequence_accuracy"),
                            "n": v.get("n"),
                        })
                item["results_json_summary"] = {
                    "experiment": rj.get("experiment"),
                    "models": rj.get("models"),
                    "mechanisms": rj.get("mechanisms"),
                    "n_cases": rj.get("n_cases"),
                    "preregistered_bars": rj.get("preregistered_bars"),
                    "overall_verdict": item["verdict"],
                    "status": item["run_status"],
                    "arms": arm_sum,
                }
                exp_name = rj.get("experiment") or d.name
                item["summary"] = (
                    f"{exp_name}: status={item['run_status']} "
                    f"verdict={item['verdict']} n={rj.get('n_cases')}"
                )
        except Exception as e:
            item["results_json_summary"] = {"error": f"{type(e).__name__}: {e}"}
    if result_md.is_file():
        head = head_text(result_md, 35)
        item["result_head"] = head
        if not item["verdict"]:
            item["verdict"] = extract_verdict_from_md(head)
        if not item["summary"]:
            first = head.splitlines()[0] if head else d.name
            item["summary"] = (item["verdict"] or first)[:240]
    if item["has_result_md"] or item["has_results_json"]:
        findings.append(item)

print(json.dumps({
    "filter": lab_filter or None,
    "limit": limit,
    "count": len(findings),
    "findings": findings,
    "note": "read-only; no enqueue/promote via reach",
}))
PY
REMOTE
)"

  local detail
  detail="$(RAW="$raw" LAB="$lab_filter" python3 - <<'PY'
import json, os
try:
    raw = json.loads(os.environ["RAW"])
except json.JSONDecodeError:
    raw = {"error": "bad_json", "raw": (os.environ.get("RAW") or "")[:400]}
raw["requested_lab"] = os.environ.get("LAB") or None
print(json.dumps(raw))
PY
)"

  local ok count
  ok="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("true" if "count" in d and not d.get("error") else "false")')"
  if [[ "$ok" != "true" ]]; then
    local code
    code="$(printf '%s' "$detail" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("error") or "findings_failed")')"
    emit_receipt popper findings false error L0 ssh "$K2VPS_HOST" "$detail" "$code" "findings probe failed"
    return 1
  fi
  count="$(printf '%s' "$detail" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("count") or 0)')"
  if [[ "$count" -eq 0 ]]; then
    emit_receipt popper findings true stale L0 ssh "$K2VPS_HOST" "$detail" \
      no_findings "No RESULT.md/results.json matched filter"
    return 0
  fi
  emit_receipt popper findings true live L0 ssh "$K2VPS_HOST" "$detail"
  return 0
}

popper_dispatch() {
  local verb="$1"
  shift || true
  case "$verb" in
    status) popper_status ;;
    labs) popper_labs ;;
    findings) popper_findings "$@" ;;
    enqueue|run|promote|write)
      emit_receipt popper "$verb" false error L0 none "-" \
        '{"policy":"human_gated","hint":"reach never enqueues/promotes labs"}' \
        write_forbidden "Popper writes/enqueue are human-gated — not exposed on reach"
      return 1
      ;;
    *)
      emit_receipt popper "$verb" false error L0 none "-" "{}" \
        unknown_verb "popper verbs: status|labs|findings"
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  popper_dispatch "$@"
fi
