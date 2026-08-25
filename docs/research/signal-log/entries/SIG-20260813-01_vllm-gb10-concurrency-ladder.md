# SIG-20260813-01 — vLLM on GB10: a measured 5.5× concurrency ladder, and our own width evidence turns out to be void

```yaml
id: SIG-20260813-01
date: 2026-08-13
title: "MiaAI-Lab Muse-Glimmer-30B on DGX Spark via vLLM — 38.0 -> 209.1 aggregate tok/s across N=1..8, on our exact silicon"
index_title: "vLLM GB10 concurrency ladder 5.5x at N=8 — CORRECTS our 'width does not scale' claim, which traces to a ladder our own board marked VOID"
index_links: [repo]
source_url: "https://x.com/miaai_lab/status/2087176579126382826"
canonical_repo: "https://github.com/MiaAI-Lab/Muse-Glimmer-30B-DGX-Spark-RTX-5090-6000-PRO"
bucket: inference
posture: spike
steal_rank: P0
confidence: high            # post fetched verbatim via api.fxtwitter.com; repo, PR, fork and all 4 HF checkpoints read live
hardware_fit: [spark]       # GB10 sm_121 aarch64 is the repo's REFERENCE box. NOT caden (8 GB), NOT mbp (no CUDA)
stacks_touched: [t1000]
related_plans:
  - "t_9c7208c2"            # W3 Ryan NUM_PARALLEL width ladder — scheduled, NEVER RUN; this changes its premise
  - "t_89c72b32"            # W3 Kevin batched-session ladder — blocked; its body is what declares the prior ladder void
  - "t_13d79be5"            # ST-14 SGLang — the other continuous-batching engine candidate
  - "t_08e96127"            # LAB vLLM sm121 — Ryan's supply-chain STOP is live on this card
  - "B17"                   # Phase C2 concurrency ladder
status: open
distill: none
status_note: "P0 for the CORRECTION, not the recipe. Their GB10 ladder (all-DFlash, vLLM continuous batching, fp8 KV, 256 tok) is 38.0 -> 209.1 aggregate tok/s at N=8 with per-stream only -18% (38.0 -> 31.0). We have cited 'our own N=1->4 ladder found almost no aggregate gain (14-15 -> ~16 agg)' in STEALS, SIG-20260812-03 and repeatedly in chat as the disconfirming evidence against McNab-style width claims. TRACED TO SOURCE 2026-08-13: that number lives ONLY in the result field of t_a1da196d / t_618701e2, with no methodology, no engine, no N values, and no entry anywhere in this log — and t_89c72b32's own card body declares it 'void above N=2' because it ran against the OLLAMA_NUM_PARALLEL=2 cap. Both replacement ladders never ran (t_9c7208c2 scheduled, t_89c72b32 blocked). A flat width ladder measured on an engine with a hard 2-slot cap, or on upstream antirez/ds4 which ships NO batching implementation at all (SIG-20260808-06), is not evidence about GB10. FEASIBILITY: recipe needs util 0.42 x 121.63 = 51.1 GiB FREE at startup; ryan-spark has 43 GiB available with gpt-oss:120b pinned, so it REFUSES TO LAUNCH without the same consumer-paused window t_99c6388b / t_6e8222b2 / t_7cb87a81 already contest. SUPPLY CHAIN: components are well-sourced (Meta-org drafter 34.9k downloads, RedHatAI weights, official vLLM PR #51655 branch, VLLM_USE_PRECOMPILED official kernels) but the wrapper repo is 3 stars / 25 min older than the tweet and its start.sh clones a fork and hand-applies two uncommitted patches — do NOT run their start.sh; reproduce flags by hand if ever released."
```

## 1. Claim

[@MiaAI_lab](https://x.com/miaai_lab/status/2087176579126382826) (2026-08-11 13:57Z, 53♥ / 4,271 views):

> *"Run @AIatMeta's Muse Glimmer 30B on @NVIDIAAI DGX Spark, RTX 5090, & RTX 6000 PRO with easy ✨
> — RedHat's NVFP4 with DFlash — 256k context — 8 concurrent sessions (lower on a 5090).
> The performance with DFlash is insane even in a DGX Spark, especially concurrent."*

**The image attached to the post is the payload**, and it is a concurrency ladder on the reference box.

## 2. The measured ladder (their `bench.png`, read directly)

`Decode benchmark · Port 8888 · muse-glimmer-30b · COMPLETED · 256 tok · 1, 2, 4, 6, 8 conc · 44.8 s`

| Load | TTFT | Streams | **Aggregate tok/s** | Per-stream tok/s |
|---:|---:|---|---:|---:|
| ×1 | 359 ms | 1/1 | **38.0** | 38.0 |
| ×2 | 441 ms | 2/2 | **58.6** | 30.4 |
| ×4 | 511 ms | 4/4 | **113.2** | 30.7 |
| ×6 | 560 ms | 6/6 | **179.1** | 35.4 |
| ×8 | 625 ms | 8/8 | **209.1** | 31.0 |

**N=1 → N=8: aggregate ×5.5, per-stream −18%, TTFT +74% (359 → 625 ms), 8/8 streams completed.**

That is the shape continuous batching is supposed to produce, and it is on **GB10 `sm_121` aarch64** — the same silicon as ryan-spark and kevin-spark.

## 3. Why this is P0: it corrects **us**, not the field

We have repeatedly asserted a disconfirming result. Verbatim from `STEALS.md` and `SIG-20260812-03` §8:

> *"every prior 4-box argument we logged was an **aggregate-throughput** claim (McNab 32× width) and **our own N=1→4 ladder found almost no aggregate gain** — so the hardware thread had no surviving evidence on the buy side."*

**Traced to source today. It does not survive.**

| Question | Answer (read live from the mesh DB) |
|---|---|
| Where is the number recorded? | ONLY in the `result` field of `t_a1da196d` and a comment on `t_618701e2`: *"Width: prior ladder ~nothing (14-15 -> ~16 agg)"* |
| Methodology? | **None recorded.** No engine, no model, no N values, no prompt, no repeats |
| An entry in this log? | **No.** `grep` for `14-15` / `~16 agg` across all 33 entries → **zero hits** |
| Comments on the two "done" W3 cards? | `t_fd210e86`: **0 comments**. `t_a1da196d`: **0 comments** |
| What does our own board say about it? | `t_89c72b32` body, verbatim: *"**Prior 1-to-4 width ladder ran against the old NUM_PARALLEL=2 cap and is void above N=2** (defect 3) — this measures the real ceiling"* |
| Did the replacement ladders run? | **No.** `t_9c7208c2` = `scheduled` (never run) · `t_89c72b32` = `blocked` on Kevin's ack |

And the engines make the flatness unsurprising rather than informative:

- **Ollama** on ryan-spark runs `OLLAMA_NUM_PARALLEL=2` (measured, in `t_9c7208c2`'s own input comment). Above N=2 requests **queue**; they do not batch. A ladder to N=4 against a 2-slot cap measures the cap.
- **antirez/ds4** on kevin-spark has **no batching implementation at all** — `SIG-20260808-06` §: *"no `--mtp*`, no speculation, **no `--batched-session`**"*, and *"our DS4 lane is running the slow configuration… upstream engine, no drafter, no batching."*

> **The correction, stated plainly:** a flat width ladder measured on an engine that cannot batch is a fact about the **engine**, not about **GB10**. We turned it into a hardware verdict and then used that verdict to discount McNab (`SIG-20260807-03`), the Entrpi fork's continuous-batching claim (`SIG-20260808-06` S3), and the 4-box capability argument (`SIG-20260812-03` §8). **All three of those discounts are now unsupported.** They are not thereby *proven* — they are back to open.

This is the exact failure mode `STEALS.md` already names as a P1 steal — *"write measurement results back into the signal entry, not only the card"* — arriving one level worse: the measurement was never written down **anywhere**, was marked void by a sibling card, and got quoted for four days as settled.

## 4. What we verified about the recipe (all read live, nothing installed)

| Thing | State |
|---|---|
| Repo | `MiaAI-Lab/Muse-Glimmer-30B-DGX-Spark-RTX-5090-6000-PRO` — **MIT, ★3**, created 2026-08-11 13:32Z, pushed 14:00Z (25 min before the tweet), 153 KB, 6 files |
| Runtime | `xianbaoqian/vllm@tiezhen/new-model-support`, pinned commit `99a10304d` — a **real fork of vllm-project/vllm**, pushed today |
| Upstream PR | **[vllm-project/vllm#51655](https://github.com/vllm-project/vllm/pull/51655) "Add Muse Glimmer model support"** — **open, not merged**, 6 commits / 21 files / +4,339, author `xianbaoqian`, **updated 2026-08-13 09:25Z (today)** |
| Kernels | `VLLM_USE_PRECOMPILED=1` — **official vLLM precompiled kernels, no CUDA build**; only the Python layer is the fork |
| Target weights | `RedHatAI/Muse-Glimmer-30B-NVFP4` — **2,484 downloads**, 14 likes, `compressed-tensors nvfp4-pack-quantized`, W4A4, **vision tower intact in BF16** |
| Drafter | `meta-models/Muse-Glimmer-30B-assistant` — **34,890 downloads, 50 likes, official Meta org**. 5 layers, block size 16 |
| A16 alternative | `cloudnathan5/Muse-Glimmer-30B-NVFP4` — 566 downloads (W4A16 + GPTQ), one-line `MODEL_REPO` swap |

Their launch, verbatim from the README:

```bash
vllm serve <model> --served-model-name muse-glimmer-30b --trust-remote-code --port 8888 \
  --max-model-len 262144 --gpu-memory-utilization 0.42 --kv-cache-dtype fp8_e4m3 \
  --reasoning-parser muse_glimmer --tool-call-parser muse_glimmer --enable-auto-tool-choice \
  --speculative-config '{"method":"dflash","model":"<draft>","num_speculative_tokens":16}' \
  --no-enable-flashinfer-autotune
```

Reported GB10 figures: fixed overhead **~32.5 GiB**, KV **2,414,048 fp8 token slots = 9.21× 256K**, cold start ~5–6 min, DFlash *"per-window mean acceptance roughly 4–9, draft acceptance up to ~53%."*

### `num_speculative_tokens: 16` is a real nuance for `t_99c6388b`

We rejected EAGLE3 partly on *"`n_max` 16 against a measured mean accept length of ~3 wastes 13"*, and `SIG-20260810-01` §9 elevated **`n_max`** to the strongest hypothesis for our −32% DFlash result. **Here 16 is correct** — it is the drafter's own native block size, and DFlash drafts a block rather than a chain. So *"16 is wrong"* is **drafter-specific, not universal**. `t_99c6388b`'s arm A (BF16 EAGLE3 at `n_max 4`) is unaffected; the doctrine line that must not be over-generalised is *"n_max must match the drafter's design, not a global default."*

## 5. Honest marks against their numbers

- ⚠️ **The no-spec baseline is prose, not a table.** *"without speculation, ~13 tok/s, so DFlash is worth roughly 3×"* appears only in README text; `bench.png` shows the **DFlash arm only**. The **3× DFlash claim on GB10 is claimed, the concurrency ladder is shown.** They are not the same grade of evidence. The scaling result stands on its own because every rung is the same configuration.
- ⚠️ **Reasoning is not pinned** — `t_6e058ca2`'s rule. Muse Glimmer defaults to *"Reasoning strength: high"*, and their own troubleshooting table lists *"No output / empty content… the model is thinking in the reasoning channel and burned the token budget."* A 256-token bench with reasoning on is measuring a different content mix than one without. Not disclosed.
- ⚠️ **Aggregate ≠ per-stream × N, and the gap widens.** 30.4×2 = 60.8 vs 58.6 · 30.7×4 = 122.8 vs 113.2 · 35.4×6 = 212.4 vs **179.1** · 31.0×8 = 248 vs **209.1**. Consistent with aggregate measured over total wall while per-stream is measured over each stream's own active window (staggered start/finish). Not a fault — but the two columns have **different denominators** and should not be cross-multiplied.
- ⚠️ **Single run, no repeats.** Per-stream is non-monotonic (30.4 at N=2 vs 35.4 at N=6), implying ~±15% run-to-run variance. The 5.5× is far larger than that noise; the per-rung values are not.
- ⚠️ **Streamed-delta counting under spec-dec under-reports** (`SIG-20260812-06` S2). The image's "STREAM" column implies streaming. Direction of error favours their result being conservative, so it does not threaten the scaling conclusion.
- ⚠️ **256K is extrapolation.** Trained context is 131,072; their own "Known limitations" says so, and the drafter head is *also* trained only to 131K. The 256K headline needs `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` plus **two hand-applied, un-upstreamed RoPE patches** they warn a `git fetch` can reset.
- ⚠️ **RTX PRO 6000 / RTX 5090 rows are the checkpoint author's numbers, not theirs.** Their README labels this correctly. Only the GB10 row is their own measurement.

## 6. Feasibility on our box — measured, and it does **not** fit today

```
ryan-spark   121 GB total · 77 used · 43 available     (gpt-oss:120b 65 GB + hermes3:8b-16k 6.9 GB, both Forever)
             Python 3.12.3 ✅ (recipe requires 3.12, not 3.13+)   aarch64 ✅   disk 3.3 TB free ✅
             vllm: ModuleNotFoundError — not installed
recipe needs util 0.42 × 121.63 GiB = 51.1 GiB FREE AT STARTUP  →  we have 43 GiB  →  ENGINE REFUSES TO LAUNCH
downloads    ~19 GB weights + ~5.1 GB drafter + ~10 GB venv
```

So this is **not** a "run it now" — it needs the **same consumer-paused window** already contested by `t_99c6388b` (spec-dec sweep), `t_6e8222b2` (Nemotron) and `t_7cb87a81` (TurboQuant). Per the rule written after ryan-spark wedged badly enough that sshd died: pause **consumers**, not just the model, and **never `pkill -f llama-server`**.

## 7. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **A width ladder measured on an engine that cannot batch is void.** Ours ran against `OLLAMA_NUM_PARALLEL=2` and against a DS4 build with no batching at all; our own `t_89c72b32` already said so | Retract the "width does not scale on GB10" claim wherever it is asserted (`STEALS.md`, `SIG-20260812-03` §8, `SIG-20260807-03`). Add to the bench contract: **a concurrency row must record the engine's batching mode and slot cap, or the row is void** | **P0** | **wired** → `t_9c7208c2` comment + entries corrected below |
| S2 | **A ladder is only interpretable with both columns and their denominators** — aggregate over total wall, per-stream over each stream's active window, plus TTFT per rung | Field addition to `t_6e058ca2`: `n_concurrent`, `agg_tok_s`, `per_stream_tok_s`, `ttft_ms`, `streams_completed`, `batching_mode`, `slot_cap`. Their 5-rung table is the format to copy | **P1** | open |
| S3 | **`n_max` must match the drafter's design, not a global default** — 16 is *correct* for DFlash (native block size), *wrong* for EAGLE3 (accept length ~3) | One line in the bench contract; do **not** let `SIG-20260810-01` §9's "n_max is the strongest hypothesis" harden into "16 is always wrong" | P1 | open |
| S4 | **Precompiled-kernel install path** (`VLLM_USE_PRECOMPILED=1`) sidesteps the sm121 CUDA-build question entirely — official kernels, fork Python only | Note on `t_08e96127`, whose open question is literally *"is B17's engine phase a download, not a build?"* — the answer for this model is **neither: it is a fork's Python over official precompiled kernels** | P2 | open |

**Primary steal (one only): S1.**

## 8. Do not

- ⛔ **Do not run their `start.sh`.** It `git clone`s a fork, `pip install -e .`, downloads 24 GB, and hand-applies two uncommitted patches. Standing rule: no `curl|sh` onto our boxes. If this is ever released, reproduce the **flags** by hand from §4.
- ⛔ **Do not read this as reversing Ryan's supply-chain STOP on `t_08e96127`.** That veto was aimed at a third-party wheel with 10 downloads and it stands. This stack is *better sourced* (Meta-org drafter at 34.9k downloads, RedHatAI weights, an official open PR branch, official precompiled kernels) — but it is still a **fork plus a 3-star wrapper**, and the decision is Ryan's, not an inference from provenance.
- ⛔ **Do not treat 209.1 agg tok/s as a number we can expect.** Different model, different quant (NVFP4 W4A4), different engine, fp8 KV, unpinned reasoning, single run. It establishes **that continuous batching scales on GB10**, not **by how much for our models**.
- ⛔ **Do not conclude the McNab 32× claim is now confirmed.** Retracting our disconfirming evidence returns it to **open**, not to true. `SIG-20260807-03`'s own caveats stand.
- ⛔ **Do not load this on kevin-spark.** DS4 holds ~105 GiB in unified memory and the admission gate requires ≥105 GiB free and an empty Ollama.
- ⛔ **Do not fold this into `t_13d79be5` (SGLang).** Different engine, different failure modes — benching them together confounds both. SGLang's Phase 0 is still free and read-only and still goes first.
- ⛔ **Caden: still a clean NO** — 8 GB VRAM against a ~19 GB checkpoint plus a ~5 GB drafter.

## 9. Next action (mechanical)

- [x] `STEALS.md` — S1 as P0, plus retraction of the void-ladder claim in the two rows that assert it
- [x] correct `SIG-20260812-03` §8 and `SIG-20260807-03` where "our own N=1→4 ladder" is cited as settled
- [x] `SIG-20260810-01` §10 — one-paragraph pointer (third DFlash datapoint, same model), no duplicate write-up
- [x] **one** kanban comment → `t_9c7208c2` (the never-run ladder whose premise this changes)
- [ ] **no new card** — steals board is 15 deep, mesh 57 blocked, and this needs a window plus Ryan's supply-chain call, neither of which a card supplies

## 10. Chat blurb

`SIG-20260813-01` · `inference` · **spike P0** — MiaAI-Lab ships a vLLM recipe for Muse Glimmer 30B NVFP4 + DFlash on **GB10**, and the attached bench is a concurrency ladder: **38.0 → 209.1 aggregate tok/s from N=1 to N=8, per-stream only −18%.** The find is not the recipe — it is that **our own "width does not scale on GB10" evidence is void**: the `14-15 → ~16 agg` figure exists only in a card `result` field with no methodology, `t_89c72b32`'s body already declares that ladder *"void above N=2"* because it ran against `OLLAMA_NUM_PARALLEL=2`, and both replacement ladders never ran. Recipe **cannot launch on ryan-spark today** (needs 51.1 GiB free, we have 43 with the 120b pinned).

---

*Filed 2026-08-13. Post fetched verbatim via `api.fxtwitter.com`; bench image read directly. Repo, vLLM PR #51655, the `xianbaoqian/vllm` fork and all four HF checkpoints read live off their APIs. Card statuses and the void-ladder provenance read read-only from `~/.t1000/kanban/boards/mesh/kanban.db`. ryan-spark probed read-only. Nothing installed, downloaded, restarted, or changed on any box.*
