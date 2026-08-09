# SIG-20260808-03 — Cross-model KV cache transfer (NVIDIA)

```yaml
id: SIG-20260808-03
date: 2026-08-08
title: "Cross-model KV cache transfer within LLM families (NVIDIA)"
source_url: "https://x.com/_avichawla/status/2085632663902412985"
canonical_repo: ""
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [spark, cloud]
stacks_touched: [t1000]
related_plans:
  - "~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md"
  - "B17"
  - "local-inference-fleet"
  - "SIG-20260806-01"
status: open
distill: none
```

## 1. Claim
NVIDIA research: **map KV cache from model A → model B inside the same family** (e.g. Qwen3 14B→32B) with **training-free closed-form linear maps** (per head/layer, RoPE stripped then reapplied). Target **skips prefill**; conversion **~2.7–25× faster** than re-prefill; accuracy retention often high when head dims match.

## 2. What we verified
- Avi Chawla summary of NVIDIA “Cross-Model KV Cache Transfer in LLM Families”
- Motivation: stateless APIs + multi-model routing kill same-model prompt cache
- Method: layer selection (top predictive source layers), linear regression K/V maps, RoPE-aware
- Limits: **same family**, same KV head count/dim; dense full-attn; cross-family = future
- Claimed metrics from paper/summary — **not measured on our Spark**

## 3. Takeaways
- Multi-model routers pay a **hidden prefill tax** every hop — this attacks that
- Same-family size ladders (8B↔32B↔70B class) are the realistic steal zone first
- Complements LS masterclass **cache-aware routing** and B17 prefix/KV work
- Hermes prompt-cache sacredness is same-model; **cross-model needs new infra**
- Not day-one prod — research → watch engines (vLLM/SGLang/Dynamo) for adoption

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Same-family cascade** without full re-prefill | Future: format 8B → coder 30B → reason 120B *if* family-aligned maps exist; else keep sticky same-model sessions | P1 | open |
| S2 | Prefer **sticky model** for multi-turn before switching | Router policy: don’t bounce models mid-thread unless worth prefill cost | P1 | open |
| S3 | Track **prefill cost of model switches** in benches | B17/D: optional metric “switch tax” | P2 | open |
| S4 | Wait for engine-native support | Don’t hand-roll NVIDIA maps on desk | P1 | open |

**Primary steal:** S2 now (policy); S1 when stack supports it.

## 5. Do not
- Build custom KV mappers on T1000 day job
- Assume gpt-oss ↔ hermes3 ↔ qwen cross-family transfer works
- Drop same-model prefix stability work (still #1)

## 6. Next action
- [x] signal-log + STEALS
- [ ] fold one line into B17 Phase D notes (switch tax / sticky model) — optional light plan patch
- [ ] no implement

## 7. Chat blurb
NVIDIA cross-model KV transfer = skip prefill when hopping **within** a model family (training-free maps). Steal **sticky-model policy** now; cascade-without-reprefill later if engines ship it. Not a DIY Spark project.
