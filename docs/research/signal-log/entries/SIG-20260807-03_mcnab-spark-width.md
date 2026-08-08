# SIG-20260807-03 — 32 Hermes agents on one DGX Spark (McNab)

```yaml
id: SIG-20260807-03
date: 2026-08-07
title: "32 Hermes agents on one DGX Spark (McNab)"
source_url: "https://x.com/jasonmcnab/status/2085593096243331193"
canonical_repo: ""
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P0
confidence: medium
hardware_fit: [spark]
stacks_touched: [t1000, k2]
related_plans:
  - "~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md"
  - "B17"
  - "t_99c5d345"
status: wired
```

## 1. Claim
One DGX Spark ran **32 concurrent Hermes coding agents** on **DeepSeek V4 Flash**: 3535 tokens / 56.53s ≈ **62.5 aggregate tok/s**, 32/32 ok, **~72.7% draft accept**, real streams (4× video).

## 2. What we verified
- Public metrics as claimed; ~110 tokens/agent mean → short bursts not full features
- Aggregate ≠ per-agent snappy UX (~2 tok/s/agent if even)
- Spec-dec likely in play (draft accept reported)
- “Hermes” ≠ guaranteed T1000 `~/.t1000` config
- Flash-class width ≠ 120B 32-wide on 128GB

## 3. Takeaways
- Spark is an **agent width** box, not only single 120B chat
- Measure **agg tok/s + fail rate + draft accept under N**
- Split lanes: width (Flash/coder/8B) vs depth (120B low N)
- Multi-agent coding needs **isolation** (worktrees/leases)
- Don’t ego-chase 62 agg with wrong model

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Concurrency ladder N=1..32 | B17 **Phase C2** | P0 | **wired** |
| S2 | Draft accept under load | Log in C2 when spec-dec on | P0 | wired |
| S3 | Swarm isolation policy | C2.4 footnote; kanban swarm later | P1 | noted |

**Primary steal:** S1

## 5. Do not
- Assume 120B matches Flash width numbers
- 32 agents one dirty git tree
- Skip side-door/batch serve and expect Ollama miracles

## 6. Next action
- [x] B17 Phase C2 written
- [x] kanban t_99c5d345 commented
- [ ] execute C2 when Ryan kicks off inference plan

## 7. Chat blurb
McNab: 32× agents, ~62.5 agg tok/s on Spark+Flash. Stolen into B17 **C2** (width vs 120B depth, HTTP-only). Run with inference plan — not a desk default UX.
