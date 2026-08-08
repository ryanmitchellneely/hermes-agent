# SIG-20260806-01 — Latent Space inference engineering masterclass

```yaml
id: SIG-20260806-01
date: 2026-08-06
title: "Latent Space inference engineering masterclass"
source_url: "https://www.latent.space/p/inference-eng"
canonical_repo: ""
canonical_docs: "https://www.baseten.co/inference-engineering/"
bucket: inference
posture: steal
steal_rank: P0
confidence: high
hardware_fit: [spark, cloud]
stacks_touched: [t1000, pulp]
related_plans:
  - "~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md"
  - "B17"
status: wired
```

## 1. Claim
Inference engineering is its own discipline (Baseten Kiely/Taha): cache-aware routing, PD disagg, quant, spec dec, KV movement, structured outputs — still 20–200%+ gains after “it runs.”

## 2. What we verified
- Episode + book site; production inference vocabulary
- Spec dec traffic-specific; quant errors can cancel; structured out = state machine
- Local = less dumb on private data; DC = less slow frontier

## 3. Takeaways
- Prefill ≠ decode — measure both
- Prefix/KV cache sacred (Hermes already)
- Spec dec 8B→120B best Spark speed bet
- Quant must pass tool golden
- Dedicated box mindset (you own Spark)

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Full B17 ladder A–F | Plan written deferred | P0 | **wired** |
| S2 | Spec-dec pilot | Phase C | P0 | wired |
| S3 | Schema-constrained tools | Phase E | P1 | wired in plan |

**Primary steal:** S1 (whole experiment plan)

## 5. Do not
- Chase datacenter PD disagg on one GB10 day one
- Optimize tok/s without golden tools

## 6. Next action
- [x] B17 plan
- [ ] execute on kickoff

## 7. Chat blurb
LS inference masterclass → B17 Spark plan (baseline, side-door, spec dec, golden). Still deferred until kickoff.
