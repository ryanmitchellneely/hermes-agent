# SIG-20260812-06 — DSpark shared-expert loader bug: a silently half-speed drafter

```yaml
id: SIG-20260812-06
date: 2026-08-12
title: "DSpark shared-expert loader bug: a silently half-speed drafter on DeepSeek-V4-Flash-0731 (2x DGX Spark vLLM recipe)"
source_url: "https://x.com/tech2wild/status/2087663581357617388"
canonical_repo: "https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark"
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans: [t_6e058ca2, t_99c6388b, t_08e96127, t_227d09b2, t_e28b2c0e]
status: open
distill: none

# --- optional: INDEX.md rendering ---
index_title: "DSpark shared-expert loader bug — a handicapped drafter reads as 'spec-dec doesn't pay'; steal the acceptance-diagnostic contract, not the patch"
index_links: [repo]
```

## 1. Claim

A vLLM DSpark draft-weight loader silently dropped 12 checkpoint tensors on
`DeepSeek-V4-Flash-0731`, running the drafter with its always-on shared expert
uninitialised. **Output quality stayed perfect; only acceptance collapsed.** Two added
lines took acceptance **25.7% → 60.2%** and mean decode **32.7 → 55.4 tok/s** on
2× DGX Spark, TP=2.

## 2. What we verified

**Source (fetched via `api.fxtwitter.com`):** [@Tech2Wild](https://x.com/tech2wild/status/2087663581357617388),
2,575 followers, 2026-08-12 22:12Z, 24 likes / 1,322 views.

**Repo (GitHub API, live):** `tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark`
— **★367, 40 forks, MIT, 117 files, 8 open issues**, created 2026-06-29, pushed
2026-08-12T17:17Z. Not a fork (`parent: null`). Owner Tony DeAngelo (2Wild Agency),
44 public repos.

Quality is unusually high for a hype-adjacent repo: raw benchmark checkpoints under
`benchmarks/`, a `## What this was NOT` table of eight measured dead ends, and two
explicit self-corrections to its own earlier releases.

### Their measurement (2× DGX Spark GB10, TP=2, k=5, `nvfp4_ds_mla` KV, 1M ctx)

| | accept | tok/step | steps/s | mean tok/s | peak tok/s |
|---|---|---|---|---|---|
| 0731, stock loader | 25.7% | 2.28 | **14.4** | 32.7 | 42.0 |
| 0731, **Patch 4** | **60.2%** | **4.01** | **13.8** | **55.4** | **66.1** |
| preview `-DSpark`, stock | 57.8% | 3.89 | 14.3 | ~56 | — |

Per-position acceptance `0.631/0.282/0.181/0.114/0.067` → `0.826/0.725/0.572/0.471/0.399`.
By content, patched: structured **78.3% / 66.1 tok/s** · code **68.7% / 62.2** ·
prose reasoning **33.7% / 37.8**.

⚠️ **The tweet says "~2x". Their own numbers are +69% mean / +57% peak.** Real, large,
not 2×.

### Root cause (read in their patch + doc, both verbatim)

The draft FFN's shared expert is a `DeepseekV4MLP` with `gate_up_proj` (fed by checkpoint
`w1`+`w3`) and `down_proj` (fed by `w2`). The draft loader renamed only `w2`, and its
`_STACKED_PARAM_NAME_MAPPING` carried only the two attention rows — so `w1`/`w3` matched
nothing and fell into:

```python
param = params_dict.get(name)
if param is None:
    logger.debug("Skipping unknown DSpark weight %s", name)   # invisible at INFO
    continue
```

12 tensors lost (`w1`,`w3` × `weight`+`weight_scale_inv` × 3 draft stages), leaving
`model.layers.{43,44,45}.ffn.shared_experts.gate_up_proj.*` uninitialised.
`n_shared_experts: 1` and that expert is **always-on**, summed into every token. **The load
reported success.** Fix = 2 rows added to the mapping.

### ✅ Upstream vLLM v0.27.0 is NOT affected — verified by us, not assumed

- `vllm/v1/spec_decode/dspark.py` → **HTTP 404** at v0.27.0 *and* v0.26.0. That path is the
  **0.25.2 lineage** this overlay builds on, not current upstream.
- Upstream DSpark lives at `vllm/models/deepseek_v4/nvidia/dspark.py`, and its
  `stacked_params_mapping` (lines 401-403) **already carries** `("gate_up_proj","w1",0)` and
  `("gate_up_proj","w3",1)`, with an explicit `is_layer_param` guard and the comment
  *"otherwise e.g. `markov_w1` would collide with the `w1` shard rule."*
- Its fall-through indexes `params_dict[name]` **directly → `KeyError`**, not a silent skip.
  `grep -c 'Skipping unknown'` = **0**.

**So a future vLLM 0.27 build here does not inherit this bug.** Scope it to the overlay lineage.

### Their two measurement traps (both apply to us)

1. **`stream: false` when benching spec-dec.** Under speculative decoding vLLM emits at most
   one SSE chunk per decode *step*, carrying every token accepted in that step. Counting
   streamed deltas therefore measures **steps/s, not tok/s** — they record **14.7 vs 60.1
   tok/s on the identical request**, a ~4× under-report. Read `usage.completion_tokens` or
   divide `vllm:generation_tokens_total` by wall time.
2. **A single acceptance number without content mix is meaningless** — 78.3% structured vs
   33.7% prose reasoning in the same config.

### Framing correction on the post

The loader fix is **Patch 4, dated 2026-07-31** (commit `8a62e8b8`). Today's three merges are
**serving-layer and CI**: #17 tool-parser refactor, #21 Patch 5 (stop strings in reasoning),
#28 GHCR workflow / node-local JIT caches / `check-patch3` portability — whose own body says
*"No runtime behaviour changes to the serving path."* Don't read "7 PRs merged" and the ~2×
as one event.

### Patch 5 — checked against our stack, does not apply

Client `stop` strings evaluated inside `<think>` decapitate reasoning → `content: null`
(GSM8K n=50: 8–15 nulls / 0.66–0.84 → 1 null / 0.98). **Verified our harnesses send no stop
strings** — grep across `student-lab/`, `.sovereign/juice/`, `T1000/scripts/` for
`"stop":` / `stop_sequences` / `--stop` returns nothing but an unrelated CLI subcommand.
Recorded so nobody chases it; becomes live only if we ever add stops to a think-in-prompt eval.

## 3. Takeaways (max 5)

1. **A handicapped drafter presents as "the model got slower."** `tok/s = steps/s ×
   accepted-tokens-per-step`. Their `steps/s` never moved off ~14.4 — engine, fabric, KV and
   target were all healthy — and the entire deficit was acceptance. Because spec-dec is
   verified by the target, **a broken draft can never corrupt output, only cost speed**, so
   the symptom points at exactly the wrong place.
2. **This weakens our spec-dec family verdict — it does not reverse any measurement.**
   `t_227d09b2` (EAGLE3) recorded **11.7–14.2% accept** while running a **Q8_0 draft with BF16
   available** and `n_max 16` against a measured accept length of ~3. That is a *known*
   handicapped drafter, and 11.7–14.2% is the same shape as this repo's pre-patch 25.7%.
   Different engine (llama.cpp, not vLLM) and different drafter, so the patch is irrelevant —
   the diagnostic is not. We still hold **zero clean datapoints**.
3. **A negative spec-dec result needs proof the drafter loaded.** Nothing in our three
   rejections (`t_716141c4`, `t_e28b2c0e`, `t_227d09b2`) recorded per-position acceptance,
   drafted-vs-accepted throughput, or evidence the draft weights actually mounted.
4. **Second independent 2×-Spark capability datapoint**, and unlike `SIG-20260812-03` this one
   is a *working MIT recipe*, not a paper: DS4 Flash + DSpark + NVFP4 KV + 1M context needs
   **TP=2 across two GB10 boxes**. One workload; still doesn't decide the buy.
5. **`stream: false`, always.** A streaming bench row against a spec-dec arm is void by ~4×.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Acceptance-diagnostic contract** — decompose `tok/s = steps/s × tok/step`; require per-position acceptance, drafted-vs-accepted throughput, and **proof the draft weights loaded** before any low-acceptance number counts as a verdict | add fields to the bench contract `t_6e058ca2`; the sweep `t_99c6388b` must emit them or it cannot close the family | P0 | open |
| S2 | **`stream: false` on spec-dec benches** — SSE chunks are steps, not tokens (14.7 vs 60.1 on one request) | hard rule on `t_6e058ca2`, alongside engine-counters-not-wall-clock and pin-reasoning-or-void | P0 | open |
| S3 | **Acceptance is content-driven** — 78.3% structured / 68.7% code / 33.7% prose, same config | any acceptance figure carries its content mix or it is not a result | P1 | open |
| S4 | **2× Spark = capability, not throughput** — a working recipe that is impossible on one box | second datapoint under `SIG-20260812-03` §8; mini/Spark#2 brief input only | P1 | open |
| S5 | **Silent-drop loaders are a class** — `logger.debug` skip on unknown weights reports success; upstream's `params_dict[name]` KeyError is the correct shape | when we build any engine from source, prefer/verify loud-failure loaders | P2 | open |

**Primary steal (one only): S1.**

## 5. Do not

- **Don't apply Patch 4 anywhere.** We run no vLLM on any box, and upstream v0.27.0 already
  carries the two rows (verified above).
- **Don't read this as "our spec-dec rejections were wrong."** Different engines, different
  drafters. It raises the value of a clean re-test; it reverses nothing.
- **Don't adopt the recipe.** 2 boxes at TP=2, ~19 GB GB10 image, self-hosted arm64 GHCR
  runner, and it serves the 159.6 GB FP8 safetensors checkpoint — which does not fit one Spark
  (`SIG-20260812-03` §8).
- **Don't chase Patch 5** — verified our harnesses send no stop strings.
- **Don't quote "7 PRs merged → ~2x throughput" as one event**, and don't quote ~2× at all;
  their measured figure is **+69% mean / +57% peak**.
- **Don't touch Kevin's box on the back of this.** It runs `antirez/ds4`, not vLLM, and is
  separately still on the rollback `app/` binary at journal p50 **13.46 tok/s**.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] kanban comment `t_6e058ca2` (bench contract — S1 + S2 fields)
- [ ] AUTOMATION-ROADMAP row
- [ ] patch skill `…`
- [ ] patch plan `…`

## 7. Chat blurb

`SIG-20260812-06` · inference · steal P0. A vLLM DSpark draft loader silently dropped 12
tensors → acceptance 25.7%→60.2%, decode 32.7→55.4 tok/s, **output was perfect the whole
time**. Upstream v0.27.0 verified unaffected; nothing to patch here. The steal is the
diagnostic: `tok/s = steps/s × tok/step`, report per-position acceptance + drafted-vs-accepted
+ proof the draft weights loaded — our EAGLE3 rejection at 11.7–14.2% accept ran a Q8_0 draft
with BF16 available and never recorded any of it. Also: bench spec-dec with `stream:false`
(SSE chunks are steps, ~4× under-report).
