# SIG-20260808-04 — sparkDash multi-DGX Spark monitoring

```yaml
id: SIG-20260808-04
date: 2026-08-08
title: "sparkDash — multi-DGX Spark monitoring dashboard"
source_url: "https://x.com/miaai_lab/status/2085387359130972467"
canonical_repo: "https://github.com/MiaAI-Lab/sparkDash"
canonical_docs: ""
bucket: ops
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "B17"
  - "~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md"
  - "t1000-spark-tools"
  - "SIG-20260807-03"
status: open
distill: none
```

## 1. Claim
**sparkDash** (MiaAI-Lab): real-time web dashboard for **one or more NVIDIA DGX Spark (GB10)** — GPU/CPU/unified mem/storage/net + **local LLM metrics** (llama.cpp/vLLM/sglang/ds4), multi-concurrency decode bench, prompt showcase (up to 32), vLLM Prometheus health (KV%, TTFT p95, etc.), head/worker roles, Docker-first.

## 2. What we verified
- MIT, JS (React/Express), ARM64-oriented, ~150★
- Features match Ryan needs: multi-Spark, tok/s, decode concurrency bench, vLLM metrics
- Thread: dual Spark heavy load on deepseek-v4-flash, ~59 tok/s overall shown in UI
- SSH remote nodes; secrets encrypted; not a model/harness — pure ops surface
- Preview-quality open source; still review before privileged Docker on house Spark

## 3. Takeaways
- **Observability gap** on Ryan’s Spark is real (`reach` + tunnel is thin vs this)
- Built-in **decode multi-concurrency** overlaps B17 C2 — use or mirror metrics
- vLLM panel (KV cache %, TTFT/E2E p95, prefix cache) = free Phase B/F instrumentation ideas
- Head/worker labels ready for Ryan+Kevin multi-Spark later
- Install is optional product; **metric list is the steal** even without the UI

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Ops metric card** for Spark serve | B17 results template: GPU util, unified mem, tok/s, TTFT p95, KV% if vLLM | P1 | open |
| S2 | Multi-concurrency decode UI/bench | Align C2 harness fields with sparkDash-style agg + per-stream | P1 | open |
| S3 | Optional spike: run sparkDash read-only | Only if Ryan wants pretty multi-node eyes — sandbox first | P2 | open |
| S4 | Head/worker role labels | Kevin mesh topology naming later | P2 | open |

**Primary steal:** S1 (metric card into B17 / spark ops) — don’t need full dash day one.

## 5. Do not
- Privileged Docker on Spark without Ryan OK + network exposure review
- Replace `reach spark` without keeping CLI receipts
- Feed Distillery product
- Block on dashboard before router/B17 execute

## 6. Next action
- [x] signal-log + STEALS
- [ ] optional: one paragraph in B17 results TEMPLATE metrics list (when executing 0.1)
- [ ] no install unless Ryan says spike

## 7. Chat blurb
sparkDash = open multi-Spark monitor + LLM tok/s + concurrency bench + vLLM health. Steal **metric set** into B17/ops; optional later UI spike. Not required for desk.
