#!/usr/bin/env bash
# B mesh health strip — reach all|mesh status
# Aggregates peer status receipts. Missing peer = error row (never omit).
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"
# shellcheck source=spark.sh
source "$REACH_ROOT/scripts/peers/spark.sh"
# shellcheck source=juice.sh
source "$REACH_ROOT/scripts/peers/juice.sh"
# shellcheck source=kevin.sh
source "$REACH_ROOT/scripts/peers/kevin.sh"
# shellcheck source=pulp.sh
source "$REACH_ROOT/scripts/peers/pulp.sh"
# shellcheck source=popper.sh
source "$REACH_ROOT/scripts/peers/popper.sh"

# Critical path peers: mesh ok=false if any of these fail.
# Popper is non-critical (Cadens watched-not-paged).
_MESH_CRITICAL=(spark juice kevin pulp)
_MESH_OPTIONAL=(popper)
_MESH_ALL=(spark juice kevin pulp popper)

_run_peer_status() {
  local peer="$1"
  local out rc=0
  case "$peer" in
    spark) out="$(spark_status 2>/dev/null)" || rc=$? ;;
    juice) out="$(juice_dispatch status 2>/dev/null)" || rc=$? ;;
    kevin) out="$(kevin_dispatch status 2>/dev/null)" || rc=$? ;;
    pulp) out="$(pulp_status 2>/dev/null)" || rc=$? ;;
    popper) out="$(popper_status 2>/dev/null)" || rc=$? ;;
    *)
      out="$(emit_receipt "$peer" status false error L0 none "-" "{}" unknown_peer "not in mesh strip")"
      rc=2
      ;;
  esac
  # Ensure we always emit parseable JSON even if adapter crashed empty
  if [[ -z "${out// /}" ]]; then
    out="$(PEER="$peer" RC="$rc" python3 - <<'PY'
import json, os
from datetime import datetime, timezone
print(json.dumps({
  "schema_version": "reach.receipt.v1",
  "peer": os.environ["PEER"],
  "verb": "status",
  "ok": False,
  "grade": "error",
  "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "layer": "L0",
  "receipt": {"kind": "none", "id": "-"},
  "detail": {},
  "error": {"code": "empty_receipt", "message": f"adapter returned empty (rc={os.environ.get('RC')})"},
}))
PY
)"
    rc=1
  fi
  printf '%s\n' "$out"
  return "$rc"
}

all_status() {
  local tmp dir
  dir="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '$dir'" RETURN

  local peer
  for peer in "${_MESH_ALL[@]}"; do
    local rc=0
    _run_peer_status "$peer" >"$dir/$peer.json" 2>"$dir/$peer.err" || rc=$?
    printf '%s' "$rc" >"$dir/$peer.rc"
  done

  local detail
  detail="$(DIR="$dir" CRITICAL="${_MESH_CRITICAL[*]}" OPTIONAL="${_MESH_OPTIONAL[*]}" ALL="${_MESH_ALL[*]}" python3 - <<'PY'
import json, os
from pathlib import Path

dirp = Path(os.environ["DIR"])
all_peers = (os.environ.get("ALL") or "").split()
critical = set((os.environ.get("CRITICAL") or "").split())
optional = set((os.environ.get("OPTIONAL") or "").split())

rows = []
for peer in all_peers:
    p = dirp / f"{peer}.json"
    rc_path = dirp / f"{peer}.rc"
    try:
        rc = int(rc_path.read_text().strip() or "1")
    except Exception:
        rc = 1
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        rec = {
            "peer": peer,
            "verb": "status",
            "ok": False,
            "grade": "error",
            "error": {"code": "parse_failed", "message": str(e)},
            "detail": {},
        }
        rc = 1

    err = rec.get("error") or {}
    detail = rec.get("detail") or {}
    # compact per-peer highlight (no secrets)
    highlight = {}
    if peer == "spark":
        tun = (detail.get("tunnel") or {})
        mods = (detail.get("models") or {})
        highlight = {
            "tunnel": tun.get("state"),
            "reason": mods.get("reason"),
            "format": mods.get("format"),
        }
    elif peer == "juice":
        highlight = {
            "auth_facet": (detail.get("auth") or detail).get("facet") if isinstance(detail.get("auth"), dict) else detail.get("auth_facet"),
            "model_facet": (detail.get("model") or detail).get("facet") if isinstance(detail.get("model"), dict) else detail.get("model_facet"),
            "spark": detail.get("spark") or detail.get("spark_up"),
        }
        # juice adapters vary — keep a few known keys
        for k in ("auth", "model", "r0", "safety"):
            if k in detail and k not in highlight:
                v = detail[k]
                if isinstance(v, dict):
                    highlight[k] = {kk: v.get(kk) for kk in list(v)[:6]}
                else:
                    highlight[k] = v
    elif peer == "kevin":
        highlight = {
            "token_present": detail.get("token_present") or (detail.get("rail") or {}).get("token_present"),
            "kevin_chat_present": detail.get("kevin_chat_present") or (detail.get("rail") or {}).get("kevin_chat_present"),
            "single_writer_ok": detail.get("single_writer_ok") or (detail.get("ha") or {}).get("single_writer_ok"),
            "inbox_dir": detail.get("inbox_dir") or (detail.get("inbox") or {}).get("dir"),
        }
    elif peer == "pulp":
        highlight = {
            "unit_active": (detail.get("unit") or {}).get("active"),
            "authorized": detail.get("authorized"),
            "spark_loopback_11435": detail.get("spark_loopback_11435"),
            "auth_expires_at": detail.get("auth_expires_at"),
        }
    elif peer == "popper":
        es = detail.get("experiments_summary") or {}
        highlight = {
            "unit_active": (detail.get("unit") or {}).get("active"),
            "user": (detail.get("unit") or {}).get("user"),
            "cadens": (detail.get("inference") or {}).get("cadens_loopback_11436"),
            "spark": (detail.get("inference") or {}).get("spark_loopback_11435"),
            "labs_completed": es.get("completed"),
            "labs_count": es.get("count"),
            "tool_selection": es.get("tool_selection"),
            "critical_path": detail.get("critical_path"),
        }

    rows.append({
        "peer": peer,
        "ok": bool(rec.get("ok")),
        "grade": rec.get("grade") or "error",
        "layer": rec.get("layer"),
        "as_of": rec.get("as_of"),
        "receipt_id": (rec.get("receipt") or {}).get("id"),
        "error_code": err.get("code"),
        "error_message": err.get("message"),
        "rc": rc,
        "critical": peer in critical,
        "optional": peer in optional,
        "highlight": highlight,
    })

# Ensure every expected peer present (already iterating ALL)
present = {r["peer"] for r in rows}
for peer in all_peers:
    if peer not in present:
        rows.append({
            "peer": peer,
            "ok": False,
            "grade": "error",
            "error_code": "omitted",
            "error_message": "peer missing from strip — bug",
            "critical": peer in critical,
            "optional": peer in optional,
            "highlight": {},
        })

def rank(g):
    return {"live": 0, "stale": 1, "error": 2}.get(g or "error", 2)

crit_rows = [r for r in rows if r.get("critical")]
opt_rows = [r for r in rows if r.get("optional")]

crit_ok = all(r.get("ok") for r in crit_rows) if crit_rows else False
worst_crit = max((rank(r.get("grade")) for r in crit_rows), default=2)
worst_all = max((rank(r.get("grade")) for r in rows), default=2)
worst_opt = max((rank(r.get("grade")) for r in opt_rows), default=0)

if not crit_ok or worst_crit >= 2:
    mesh_ok = False
    mesh_grade = "error"
    code = "critical_peer_down"
    # name first critical failure
    bad = next((r for r in crit_rows if not r.get("ok") or rank(r.get("grade")) >= 2), None)
    msg = f"critical peer issue: {(bad or {}).get('peer')} ({(bad or {}).get('error_code') or (bad or {}).get('grade')})"
elif worst_crit == 1 or worst_opt >= 1:
    mesh_ok = True
    mesh_grade = "stale"
    code = "degraded"
    bad = next((r for r in rows if rank(r.get("grade")) >= 1), None)
    msg = f"mesh degraded: {(bad or {}).get('peer')} grade={(bad or {}).get('grade')} code={(bad or {}).get('error_code')}"
else:
    mesh_ok = True
    mesh_grade = "live"
    code = ""
    msg = ""

print(json.dumps({
    "mesh_ok": mesh_ok,
    "mesh_grade": mesh_grade,
    "critical_peers": sorted(critical),
    "optional_peers": sorted(optional),
    "peers": rows,
    "counts": {
        "total": len(rows),
        "ok": sum(1 for r in rows if r.get("ok")),
        "live": sum(1 for r in rows if r.get("grade") == "live"),
        "stale": sum(1 for r in rows if r.get("grade") == "stale"),
        "error": sum(1 for r in rows if r.get("grade") == "error"),
    },
    "_g": mesh_grade,
    "_ok": mesh_ok,
    "_code": code,
    "_msg": msg,
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
    emit_receipt all status true "$grade" L0 local "mesh-status" "$detail"
    return 0
  elif [[ "$ok" == "true" ]]; then
    emit_receipt all status true "$grade" L0 local "mesh-status" "$detail" "$code" "$msg"
    return 0
  fi
  emit_receipt all status false "$grade" L0 local "mesh-status" "$detail" "$code" "$msg"
  return 1
}

all_dispatch() {
  local verb="$1"
  shift || true
  case "$verb" in
    status) all_status ;;
    *)
      emit_receipt all "$verb" false error L0 none "-" "{}" \
        unknown_verb "all verbs: status"
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  all_dispatch "${1:-status}"
fi
