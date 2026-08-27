# Bakeoff: DS4-Flash vs Qwen3.8-Flash-Next (2026-08-26)

**Status:** complete for this runtime generation. Re-run trigger named below.
**Board:** models card `t_3c3569cd` (full session trail in comments).
**Hardware:** ryan-spark (GB10, 121 GB unified) for the challenger; kevin-spark
vLLM for the incumbent. All numbers same-day, same instruments.

## Verdict

**DS4 stays the flash lane today.** But its advantage is *entirely* speculation
on copyable output, not raw model speed — and that reframes what a re-run means.

## The measurement that changed the reading

Built after SIG-20260826-06 (Bakeer's "97.4 tok/s" claim). Matched A/B:
identical file in both prompts, matched output length (~230 tokens), only
**copyability** differs. Validity guards assert the edit really reproduced the
file *with* the change, and the control really did *not* copy.

| build | edit-shaped | prose control | copyability speedup |
|---|---:|---:|---:|
| DS4 EXL3-K2 | **69.8** | 29.8 | **2.34×** |
| flash-next K2MIX q3 (ours) | 33.1 | 32.9 | **1.00×** |
| flash-next UD-Q3_K_XL (unsloth) | 27.5 | 27.6 | **1.00×** |

Two consequences:

1. **DS4's headline numbers are partly a speculation artifact.** Its morning
   `code_c1` was 70.1 (≈ edit-shaped 69.8) and `devbot_fence` 32.7 (≈ prose
   29.8). The Fibonacci task was *itself* speculation-friendly. **DS4's honest
   novel-generation rate is ~30 tok/s, not 70** — the same artifact class as
   Bakeer's 97, which is why that entry says "22 is the number."
2. **On novel generation flash-next is competitive-to-faster** (27.6–32.9 vs
   ~30), while running with **no speculation at all** in this runtime. It loses
   only where DS4 can speculate.

## Standard battery (decode tok/s p50, thinking off via `reasoning_effort: none`)

| build | size | BPW | code_c1 | devbot_fence |
|---|---:|---:|---:|---:|
| DS4 EXL3-K2 | — | ~2.5 | 70.1 | 32.7 |
| flash-next UD-IQ1_S | 72.5 GB | 1.56 | 33.3 | 33.2 |
| flash-next K2MIX q3 (ours) | 94.4 GB | 4.27 | 27.6 | 27.7 |
| flash-next UD-Q3_K_XL | 90.0 GB | ~4.1 | 28.4 | 28.4 |

Quality probes pass on every flash-next build **including 1-bit**: tool calls
parse structurally (`finish_reason: tool_calls`, valid JSON args) and generated
Fibonacci code is correct including edge cases — **executed, not eyeballed**.

⚠️ **Cross-battery numbers are not interchangeable.** K2MIX read 27.6 on
`code_c1` but ~33 in the edit/prose battery (different prompt and completion
lengths). Only **within-battery ratios** are sound; that is what the A/B was
built to measure.

## Self-minting: what it proved, and what it did not

We converted our own 456 GB bf16 GGUF and minted two quants before unsloth's
ladder existed. Outcome, stated plainly: **unsloth's UD-Q3_K_XL (90.0 GB) beats
our K2MIX (94.4 GB) — smaller and marginally faster.** Ours had no imatrix;
theirs is calibrated. Use theirs.

Our probes are pass/fail smoke, far too coarse to detect the perplexity-level
quality an imatrix buys, so this is **no evidence either way on quality** —
theirs simply wins on size-efficiency. The mint's lasting value is the pipeline
proof and the architecture findings below.

### Architecture findings (constrain every future recipe)

1. **`per_layer_token_embd` has `ncols=160`** — not divisible by 256, so
   K-quants can **never** apply to it. Stuck on 32-block legacy quants
   (Q4_0 4.5 bpw / IQ4_NL 4.25), giving the table a **hard floor ~26–27 GB**.
2. **194 of 1224 tensors fall back** (`ncols` 320/640, same rule): `q2_K`/`q3_K`
   silently become `q4_0`, `q5_K` becomes `q5_1`. ~16% of tensors ignore the
   requested recipe.

Together: practical floor for a **3-bit-class build is ~88 GB** (UD-Q3_K_XL at
90 GB agrees). A Q2-class build *does* fit under 85 GB (UD-Q2_K_XL 78.9 GB).
This also explains why the "1-bit" IQ1_S is 72.5 GB rather than ~35 GB.

**Serving reality:** any ≥3-bit flash-next build needs ollama fully evicted on
the 121 GB Spark. It cannot coexist with the 120b lane.

## Re-run trigger

**Re-run this bakeoff the day MTP or lookup decoding lands for flash-next** —
in llama.cpp PR #27742 (danielhanchen: "adding MTP — still WIP"; closed PR
#27739 already had MTP + PLE offload) or via ollama support, where MTP engages
for `qwen3.8:27b` today. Nothing else plausibly flips the verdict.

Why it matters: flash-next currently loses *while carrying no speculation*, from
an equal-or-higher base. With speculation it starts from ~33, not ~30 — the
direction Bakeer's edit-shaped numbers point, and above DS4's 70.

⚠️ **llama.cpp does not run MTP for *any* Qwen model** — our own prior finding:
`qwen3.8:27b` runs MTP under ollama (`blk.64.nextn.*`) but side-door llama.cpp
leaves those tensors unused (12.9 vs 42.8 decode). There is no reference
implementation to port from.

## Operational lessons (cost real time today)

- **`OLLAMA_KEEP_ALIVE=-1` prevents expiry, not fresh loads.** `gpt-oss:120b`
  silently reloaded mid-run and OOM-killed a quantize step. Verify residency
  immediately before any memory-critical step, not once at the start.
- **The stock PR-27742 converter cannot convert this model under ~230 GB RAM**
  (the writer casts the 205 GB f32 PLE memmap to bf16). Already reported and
  **better fixed upstream** by ServeurpersoCom (commit `af93545`, bounds memory
  in three places). Our local F32-pin workaround inflated the intermediate to
  456 GB vs their 354 GB — **do not upstream ours.**
- **A fast-moving day-old PR is live state, not a fixed premise.** Both that bug
  report *and* unsloth's full quant ladder landed **during our 4-hour download**;
  we only found out by re-reading the thread before posting. Re-check upstream
  before claiming any finding is novel.
- **Grader inversion:** the A/B validator put a negative check inside an
  `all()` aggregate, scoring a *perfect* edit as invalid. Caught only by
  printing per-field detail. Never trust a rollup boolean you have not
  spot-checked against a known-good case.

## Receipts

- Instrument (standard battery): `~/.t1000/scripts/flash_sidedoor_bakeoff.py`
- Instrument (copyability A/B): `docs/inference/edit_vs_prose_bench.py` (this repo)
- Result JSONs: `docs/inference/experiments/` (this repo)
- ⚠️ Earlier same-day receipts (morning DS4 baseline, IQ1_S, K2MIX standard
  battery) were written to the **Mac** checkout `~/Documents/T1000/docs/inference/
  experiments/`, which became sandbox-unreadable mid-session. Their numbers are
  preserved in this doc and in card `t_3c3569cd`; the raw files still need
  moving here from a session with Mac access.
- Assets on ryan-spark: `~/models/flash-next-gguf/` (our mints),
  `~/models/flash-next-udq3/` (unsloth), `~/llama.cpp/build-qwen4exp/` (PR build,
  pinned `bea3b12` + local F32 converter patch), `~/models/flash-next/serve-*.sh`
