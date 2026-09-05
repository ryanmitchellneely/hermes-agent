#!/bin/bash
# run_arm.sh <label> — run the full flash-next battery against the bench tunnel.
# Runs ON THE VPS as t1000 (the only host that can see :11439).
# Env: BASE (endpoint), MODEL (served id), TAG (receipt prefix), LEDGER (identity ledger suffix).
#   e.g. BASE=http://127.0.0.1:11435/v1 MODEL=gpt-oss:120b TAG=gptoss120b LEDGER=lane run_arm.sh lane-ollama One label per
# served arm, e.g. pr28243-none, pr28243-mtp2, pr28243-mtp2-standalone.
# Same three instruments every arm, so within-battery ratios are sound:
#   1. flash_sidedoor_bakeoff.py   standard battery (code_c1 / devbot_fence / ping)
#   2. edit_vs_prose_bench.py      copyability A/B (the number that decides it)
#   3. temp0_identity_check.py     greedy token identity at n>=400 (compare arms later)
set -uo pipefail
L=${1:?label}
BASE=${BASE:-http://127.0.0.1:11439/v1}
M=${MODEL:-qwen3.8-flash-next}
TAG=${TAG:-qwen38fn}
OUT=/opt/t1000/src/docs/inference/experiments
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
curl -s -m 8 "$BASE/models" | grep -q "$M" || { echo "FAIL: $BASE does not serve $M"; exit 1; }
echo "=== ARM $L  $(date -u +%FT%TZ)"
# /metrics snapshot before and after: llamacpp:spec_decode_num_{draft_tokens,accepted_tokens,drafts}_total
# are cumulative since server start,
# so acceptance for THIS battery = delta(accepted)/delta(drafted).
MB=$(mktemp); curl -s -m 8 "${BASE%/v1}/metrics" > "$MB"
python3 /opt/t1000/home/scripts/flash_sidedoor_bakeoff.py --base "$BASE" --model "$M" \
  --label "$TAG-$L" --repeats 3 --out "$OUT/flash-sidedoor-$TAG-$L-$TS.json" 2>&1 | tail -25 \
  || echo "SIDEDOOR_FAIL $L"
python3 /opt/t1000/src/docs/inference/edit_vs_prose_bench.py --base "$BASE" --model "$M" \
  --label "$L" --repeats 3 --out "$OUT/edit-vs-prose-$TAG-$L-$TS.json" 2>&1 | tail -20 \
  || echo "EDITPROSE_FAIL $L"
python3 /opt/t1000/home/scripts/temp0_identity_check.py --base "$BASE" --model "$M" \
  --label "$L" --ledger "$OUT/temp0-identity-${LEDGER:-pr28243}.jsonl" 2>&1 | tail -3 \
  || echo "IDENTITY_FAIL $L"
MA="$OUT/metrics-$TAG-$L-$TS.prom"; curl -s -m 8 "${BASE%/v1}/metrics" > "$MA"
python3 - "$MB" "$MA" "$L" <<'PY'
import sys,re
def load(p):
    d={}
    for line in open(p):
        m=re.match(r'llamacpp:(\w+)(\{[^}]*\})? (\S+)',line)
        if m: d[m.group(1)+(m.group(2) or "")]=float(m.group(3))
    return d
b,a=load(sys.argv[1]),load(sys.argv[2])
dt=a.get("spec_decode_num_draft_tokens_total",0)-b.get("spec_decode_num_draft_tokens_total",0)
da=a.get("spec_decode_num_accepted_tokens_total",0)-b.get("spec_decode_num_accepted_tokens_total",0)
dv=a.get("spec_decode_num_drafts_total",0)-b.get("spec_decode_num_drafts_total",0)
acc = da/dt if dt else None
print(f"SPEC_STATS {sys.argv[3]}: drafted={dt:.0f} accepted={da:.0f} verif_steps={dv:.0f} "
      f"acceptance={acc if acc is None else round(acc,3)} mean_accepted_per_step={round(da/dv,2) if dv else None}")
pos=sorted((k,a[k]-b.get(k,0)) for k in a if "per_pos" in k)
if pos: print("  per_pos:", ", ".join(f"{re.search(r'\d+',k).group()}:{int(v)}" for k,v in pos))
PY
rm -f "$MB"
echo "=== ARM $L done $(date -u +%FT%TZ)"
ls -la "$OUT"/*"$L"* 2>/dev/null
