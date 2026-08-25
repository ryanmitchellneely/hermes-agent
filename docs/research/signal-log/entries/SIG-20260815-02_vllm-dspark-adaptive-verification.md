# SIG-20260815-02 — vLLM adaptive verification for DSpark: one `num_speculative_tokens`, trim per step (PR #47808)

```yaml
id: SIG-20260815-02
date: 2026-08-15
title: "vLLM official: DSpark adaptive verification. Set draft length once (num_speculative_tokens: 7); vLLM decides how much of the draft to verify each step via DSpark confidence head. DeepSeek-V4-Pro-0813: first token of a 7-draft survives >70%, last <10%. One config holds Pareto from concurrency 1–256 on 8×B300. Flag enable_adaptive_verification on main (PR #47808). Backends: DSpark + confidence head on Flash Attention or DSV4 attention. Blog first-party."
index_title: "vLLM DSpark adaptive verification (PR #47808): static spec-k is dead; one config trims verify budget by confidence×load. Pareto 1–256 on 8×B300. Steal = try flag when serving DSpark; GB10 may reject at startup (SM100 ALWAYS graphs). Our N=1 already wants long draft."
source_url: "https://x.com/vllm_project/status/2088425247112679794"
canonical_repo: "https://github.com/vllm-project/vllm/pull/47808"
canonical_docs: "https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification"
index_links: [repo, docs]
bucket: inference
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [cloud, spark]
stacks_touched: [t1000]
related_plans:
  - "B17"
  - "SIG-20260813-01"
  - "SIG-20260811-04"
  - "flash-lane-doctrine"
  - "SIG-20260815-01"
status: open
status_note: "**OPEN — first-party blog + merged PR.** Hardware pre-filter N/A (not PCIe-offload). Transfer to GB10 is the open question: blog Limitations say FULL varlen decode graphs need AttentionCGSupport.ALWAYS (DSV4 sparse-MLA / SWA / indexer on SM100); elsewhere flag is **rejected at startup**. 8×B300 ≠ one Spark. No install."
distill: none
```

## 1. Claim

[@vllm_project](https://x.com/vllm_project/status/2088425247112679794) (164 likes / 61 bookmarks / ~11k views):

Six weeks ago DSpark in vLLM meant **picking a draft length and living with it**. Now set length once; **vLLM decides how much of the draft to verify every step**.

On **DeepSeek-V4-Pro-0813**: first token of a 7-draft survives **>70%**, last **<10%**. Adaptive verify on (`num_speculative_tokens: 7`) holds the **Pareto frontier concurrency 1→256 on 8×B300**. Long draft at low load, short at high.

On `main` as `enable_adaptive_verification`. DSpark + confidence head on Flash Attention or DSV4 attention. More backends in bring-up.

Blog: https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification

## 2. What we verified

| Check | Result |
|---|---|
| Blog | First-party, 2026-08-14, fetched |
| PR | [#47808](https://github.com/vllm-project/vllm/pull/47808) merged; numbers at `73b8394` |
| Mechanism | Confidence head → per-position survival (prefix product) → global top-B slots; B maximizes E[tokens]/step-cost from **startup-profiled** verify+draft tables |
| Graphs | Varlen decode CUDA graphs; DeepGEMM varlen indexer |
| Bench | DS-V4-Pro-0813, **TP=8, 8×B300 SM100**, EP, FP8 KV, max_len 16k, 880 prompts, temp 1.0 |
| Hardware pre-filter | **N/A** — not a host↔device offload paper |
| Batch | Sweep **explicitly 1…256** — readable (unlike SparDA) |

**Limitations (blog, load-bearing):**
- Needs `AttentionCGSupport.ALWAYS` (SM100 DSV4 backends). **Else rejected at startup** (no PIECEWISE fallback).
- No `--enforce-eager`, LoRA, PP, or output logprobs.

## 3. Takeaways (max 5)

- Static `num_speculative_tokens` is the wrong product knob once a confidence head exists — matches our “report N=1 and N=k” hygiene.
- At **N=1** (our kanban/chat regime) the GPU is memory-bound; **long draft is already correct**. Adaptive shines when you also serve fat batches.
- **8×B300 ≠ GB10.** Do not cite 1–256 Pareto as a Spark number.
- Flag is a one-liner when the backend supports it — cheap experiment, fail-closed if Spark rejects.
- Pairs with MiaAI Qwen3.8 SGLang MTP (SIG-15-01): spec-dec is table-stakes; **adaptive verify** is the vLLM-specific next increment.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Adaptive verify, not static k** — one `num_speculative_tokens` + `enable_adaptive_verification` when DSpark/vLLM path is already up | Next time a Spark/vLLM DSpark or DS4-Flash serve is leased: add the flag; if startup rejects (SM121/ALWAYS), log and move on. Do not rebuild vLLM just for this. | **P1** | open |

**Primary steal:** S1

## 5. Do not

- Treat 8×B300 Pareto as a single-Spark tok/s claim.
- Force-enable on a backend that will refuse at boot.
- Swap SGLang Qwen3.8 recipe (SIG-15-01) for this — different model/engine.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] fold into next DSpark/vLLM serve note — **no card**

## 7. Chat blurb

**SIG-20260815-02** · inference · steal **P1** · high  
vLLM DSpark **adaptive verification** (PR #47808): one draft length, trim verify by confidence×load. Pareto 1–256 on 8×B300.  
**Steal:** try the flag on an already-up DSpark serve. GB10 may reject at startup. Not our N=1 speed story.
