# Bakeoff: DS4-Flash vs Qwen3.8-Flash-Next (2026-08-26)

**Status:** re-run DONE 2026-09-05 with MTP engaged (section below). Next trigger named at the end.
**Board:** models card `t_3c3569cd` (08-26 trail, archived) · `t_d9e99989` (09-05 MTP re-run).
**Hardware:** ryan-spark (GB10, 121 GB unified) for the challenger; kevin-spark
vLLM for the incumbent. All numbers same-day, same instruments.

## Verdict

**2026-08-26:** DS4 stays the flash lane. Its advantage was *entirely* speculation
on copyable output, not raw model speed.

**2026-09-05 (MTP re-run, below):** that advantage is gone. With the NextN/MTP
head engaged, flash-next at n-max 3 does **60.2 tok/s edit-shaped / 35.5 prose**
against DS4's 69.8 / 29.8 — within 14 % on copyable work and **19 % faster on
novel generation**, from a 90 GB 3-bit build. The lane question is now open;
it is decided on models card `t_37efebbb`, not here.

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

## MTP re-run — 2026-09-05 (llama.cpp PR 28243)

**Trigger fired:** MTP for flash-next landed as ggml-org/llama.cpp **#28243**
(danielhanchen / unsloth, on top of #27836; head `d1a92352c`, mergeable, draft-
decode regression fixed the same morning). unsloth ships the head as sidecar
GGUFs: `MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` (2.79 GB, borrows the
target's embeddings) and a standalone `Q8_0` (4.14 GB). Built as a worktree at
`~/llama.cpp-mtp` on ryan-spark (CUDA, GB10); `build-qwen4exp` untouched.

**This is the first GB10 / DGX Spark data point for the head anywhere** — the
PR thread had 5090 (+25–40 %, acc 0.77), A6000 (no win, acc 0.37), Metal
(dn=2 −2 %) and nothing for unified-memory NVIDIA.

Same target (UD-Q3_K_XL 90 GB), same three instruments, same 16k ctx, thinking
off, served one arm after another inside one window (`bench_window.sh switch`).
Decode tok/s p50; every arm 9/9 content-ok and 6/6 validity guards.

| arm (shared Q8_0 head) | code_c1 | devbot_fence | ping | edit | prose | copyability | acceptance | accepted / verify step |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `none` (control, this build) | 29.8 | 30.2 | 55.3 | 29.9 | 29.2 | 1.02× | — | — |
| `draft-mtp` n-max 2 | 53.0 | 39.7 | 29.4 | 52.9 | 36.5 | 1.45× | 0.715 | 1.43 |
| `draft-mtp` n-max 3 | **60.2** | 38.4 | 27.6 | **60.2** | **35.5** | 1.70× | 0.658 | 1.97 |
| `draft-mtp` n-max 4 | 65.7 | 37.5 | 21.6 | 65.8 | 29.6 | 2.22× | 0.542 | 2.17 |
| DS4 EXL3-K2 (08-26 reference) | 70.1 | 32.7 | — | 69.8 | 29.8 | 2.34× | — | — |

Reading, against the bar written down before the window opened:

1. **MTP works on GB10.** Acceptance ≥ 0.6 at n-max ≤ 3 and edit-shaped decode
   1.77–2.2× the control. The control on the new build (29.8) is +5 % over the
   08-26 build (28.4) — master moved; that is why the control was re-run.
2. **The lane question flips open.** n-max 3 clears both halves of the bar:
   edit ≥ 60 **and** prose above control (35.5 vs 29.2, +22 %). n-max 2/3 are
   the sweet spots. n-max 4 buys edit speed but prose falls back to control and
   `ping` (one-word answers) halves — the draft overhead dominates tiny outputs.
3. **Greedy output is NOT identical under MTP on this backend.** temp 0, top_k 1,
   seed 7, n = 600: three control runs are **bit-identical** (same sha256), and
   **every MTP arm diverges from them** — first difference at character 21
   (n-max 2), 267 (n-max 3), 21 (n-max 4). Same class as the Metal
   batch-invariance report on the PR thread (MUL_MAT batch width changes
   accumulated rounding), and it is the reason a "which n-max is safe"
   recommendation must carry the length it was measured at. Quality probes
   still pass on every arm (tool calls parse structurally, Fibonacci executed).
   Treat MTP output as *equivalent in quality*, not *identical*.
4. Standalone-head arm skipped: the shared head loaded and accepted ≥ 0.5, the
   plan's only reasons to run it.

**Serving reality is unchanged:** 90 GB target + 2.8 GB head needs ollama fully
evicted on the 121 GB Spark. It cannot co-reside with the 120b lane.

### Operational lessons (this run)

- **`pkill -f` self-kill aborted three windows in a row.** The remote `bash -c`
  command line that runs `pkill -f 'R 127.0.0.1:11439'` contains that pattern,
  so pkill killed its own shell before the tunnel launched; the ERR trap then
  restored the box (correctly) each time. The bracket idiom did not save it.
  `bench_window.sh` now uses **pidfiles and port checks** and no `pkill -f` /
  `pgrep -f` at all. The trap did its job: the lane came back clean all three
  times, verified.
- The script *checked* the NOPASSWD `systemctl stop ollama` grant and never
  *called* it. It now stops the service after eviction and starts it on close.
- Acceptance comes from `/metrics` (`llamacpp:spec_decode_num_{draft_tokens,
  accepted_tokens,drafts}_total`, cumulative) — snapshot before and after each
  battery; `run_arm.sh` does this.
- A one-word `ping` is the wrong probe for a speculative arm: it measures draft
  overhead, not decode. Keep it (it is a regression tripwire) but do not rank
  on it.

### Receipts (this repo, `docs/inference/experiments/`)

`flash-sidedoor-qwen38fn-pr28243-{none,mtp2,mtp3,mtp4}-20260905T*.json`,
`edit-vs-prose-qwen38fn-pr28243-{none,mtp2,mtp3,mtp4}-20260905T*.json`,
`metrics-qwen38fn-pr28243-mtp{2,3,4}-*.prom`, `temp0-identity-pr28243.jsonl`
(six rows: none ×3, mtp2, mtp3, mtp4), `serverlog-pr28243-*.log`. Instruments:
`flash_sidedoor_bakeoff.py` (VPS `~/scripts`), `edit_vs_prose_bench.py`,
`temp0_identity_check.py`, `run_arm.sh` (this dir).

### Same-day follow-through (Ryan: "let's do that") — pilot staged, 2026-09-05 evening

- **Baselines over the live lane (ollama, same instruments, no window):** gpt-oss:120b code 57.1 /
  edit 51.6 / **prose 66.0** (ping + fence rows came back empty under `reasoning_effort: none`
  via ollama — a harmony-channel quirk, not a speed fact); qwen3.8:27b 37.5 / 41.2 / 18.4. So
  flash-next beats 120b on edit-shaped work and 27b everywhere, and **120b stays ~1.9× faster on
  novel prose.** That trade is now on the record (`t_37efebbb`).
- **Prefill on real ~20k-token cards, cold on unseen text:** PR 28243 234–244 tok/s (≈85–90 s to
  first token) regardless of MTP; **PR 28136 `--lazy-mode on-direct` 594 tok/s (35 s)**, cold ≈
  warm. Direct PLE reads are a requirement for the lane, not a nicety.
- **`flash-prod` branch** (`~/llama.cpp-prod`, `0a418d6c`) = 28243 + 28136 merged cleanly (the
  earlier "conflict" was git lacking a commit identity). Validated in one window at the pilot
  config (mtp3 + on-direct, 49k ctx, 1 slot): code 60.3 / fence 38.5 / edit 59.0 / prose 34.5,
  acceptance 0.657, greedy stream byte-identical to the 28243 mtp3 arm; cold prefill 560 tok/s on
  23.5k tokens (42 s). Receipts: `experiments/*flashprod*`, `*prefill-qwen38fn-*`, `*lane-ollama-*`.
- **Residency (measured):** ollama on ryan-spark keeps at most three residents; a fourth of any
  size evicts 120b, and loading 120b last evicts the rest. The tiny-aux move therefore went to
  `hermes3:8b-16k` (already resident) for the four kanban/title slots, compression stayed on 27b
  until the flip. Runbook, flip order, rollback: `~/models/flash-next/README-PILOT.md` on
  ryan-spark (copy in this dir as `PILOT-FLASH-NEXT-RYAN-SPARK.md`).

## Re-run trigger (updated 2026-09-05)

1. **PR 28243 merges** → rebuild from master (the worktree pin is a PR head, not
   a release) and re-run `none` + n-max 3 only, to confirm nothing regressed.
2. **PR 28136** (direct PLE reads, author measured prefill 300 → 750–800 tok/s
   on a DGX Spark) → card `t_ec2af07b`; prefill-heavy prompts, combine with MTP.
3. The lane decision itself lives on `t_37efebbb` (Ryan, 2026-09-05: thorough
   eval of replacing what runs on Ryan's box and on Kevin's box).

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
- Assets on ryan-spark: `~/llama.cpp-mtp/` (PR 28243 worktree + CUDA build),
  `~/models/flash-next-udq3/mtp-*.gguf` (both heads), `~/models/flash-next/serve-udq3-mtp.sh`,
  `~/models/flash-next-gguf/` (our mints),
  `~/models/flash-next-udq3/` (unsloth), `~/llama.cpp/build-qwen4exp/` (PR build,
  pinned `bea3b12` + local F32 converter patch), `~/models/flash-next/serve-*.sh`
