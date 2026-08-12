# SIG-20260811-04 — NVIDIA ships a 30B-A3B agent-execution model **with a first-party DSpark drafter, explicitly single-GPU on DGX Spark** — and DSpark is the one spec-dec method that already has a positive datapoint on our silicon

```yaml
id: SIG-20260811-04
date: 2026-08-11
title: "NVIDIA-Nemotron-3.5-Lightning-30B-A3B released 2026-08-11 (OpenMDW-1.1, commercial OK): 30B total / 3B active hybrid Mamba-2 + MoE + Attention, up to 1M ctx, model card names 'Single-GPU Deployment: 1x DGX Spark (GB10) or 1x H100' and 'Best For: long-running autonomous agents, sub-agent workhorse deployments'. Ships THREE first-party drafters — DSpark (967M, tuned for DGX Spark), DFlash, and MTP. Verified: base model is already on Ollama (11 tags, nvfp4 23GB) and ggml-org published GGUFs 4h before this read; the DSpark sidecar is vLLM-only and has NO GGUF anywhere"
index_title: "NVIDIA Nemotron 3.5 Lightning 30B-A3B (OpenMDW-1.1, released TODAY) — 3B active, Mamba-2+MoE hybrid, 1M ctx, card explicitly says 'Single-GPU: 1x DGX Spark (GB10)' and 'Best For: sub-agent workhorse deployments'. Ships a first-party 967M DSpark drafter — and DSpark is the ONLY spec-dec method with a positive datapoint on our fleet (Entrpi fork on kevin-spark: 72-73% accept, 16.07 -> 25-26 tok/s). SWE-bench Verified 52.80 NVFP4 (BEATS its own BF16 51.56). THE GATE IS THE DRAFTER, NOT THE MODEL: base is a one-line pull (Ollama 11 tags incl 30b-a3b-nvfp4 23GB; ggml-org GGUF published 13:26Z, NVFP4 22.46GB / Q4_K_M 25.43GB) and llama.cpp 62bf73d on ryan-spark ALREADY has LLM_ARCH_NEMOTRON_H_MOE + --spec-type draft-dspark; but the DSpark sidecar ships safetensors-only, llama.cpp resolves sidecars as `dspark-*` siblings IN THE SAME REPO, and ZERO of the 3 GGUF repos (42 files) carry one. Official recipe is vLLM (--speculative_config.model, --kv-cache-dtype fp8, --tool-call-parser qwen3_coder) => this hands t_08e96127 a first-party payload instead of a generic 'vLLM is faster' argument"
source_url: "https://x.com/miaai_lab/status/2087164607311831534"
source_url_2: "https://x.com/dogukanurker/status/2087281654456832306"
updated: "2026-08-11"
canonical_repo: "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4"
canonical_docs: "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-DSpark"
index_links: [src2, HF, HF]
bucket: models
posture: spike
steal_rank: P0
confidence: high          # post fetched verbatim via api.fxtwitter.com; both HF cards read as raw markdown; repo file manifests + blob sizes from the HF API; Ollama tags from the library page; llama.cpp arch/spec-type/sidecar-resolution grepped live in ~/llama.cpp @62bf73d on ryan-spark; all fleet memory/version numbers measured live
hardware_fit: [spark, mbp]
stacks_touched: [t1000]
related_plans:
  - "B17"                 # Spark inference experiments — the engine phase this feeds
  - "SIG-20260810-01"     # Muse Glimmer / DFlash — the other vendor-shipped drafter, and the contrast: that one HAD an ollama tag suffix, this one does not
  - "SIG-20260810-02"     # OoO-Spec — tool-call drafting; same thesis, this is the shipped version
  - "SIG-20260811-01"     # Qwen3.6 MTP — the sibling confound-free spec-dec arm
  - "SIG-20260810-07"     # TurboQuant — the other 'engine migration, not a download' finding
status: carded
status_note: "**CARDED `mesh` / `t_6e8222b2` (blocked/needs_input: consumer-paused window on ryan-spark; Phase 0 is free and releasable alone).** **The model is not the find — the drafter pairing is.** NVIDIA released (2026-08-11, OpenMDW-1.1, commercial OK) a 30B/3B-active Mamba-2+MoE hybrid whose card explicitly names `1x DGX Spark (GB10)` as a single-GPU target and `sub-agent workhorse deployments` as the intended use — i.e. it is purpose-built for exactly the lane where DS4 Flash currently costs us 13-16 tok/s. It ships a **967M first-party DSpark drafter**, and DSpark is **the only speculative-decoding method on this fleet with a positive result**: the Entrpi fork on kevin-spark banked 72-73% accept / 2.83-3.00 tok-per-step / 16.07 -> 25-26 tok/s (`t_716141c4` correction + `t_43e997d2`). **Availability is asymmetric and that is the whole story.** BASE MODEL = trivially available: Ollama carries 11 tags (`30b-a3b-nvfp4` 23GB, `30b-a3b-q4_K_M` 25GB, `30b-a3b-q8_0` 35GB, `30b-a3b-bf16` 66GB, plus `-mlx` variants for the MBP), and `ggml-org` published GGUFs at 13:26Z today (NVFP4 22.46GB, Q4_K_M 25.43GB, Q8_0 35.00GB, BF16 65.85GB, 0 downloads). llama.cpp `62bf73d` on ryan-spark already carries `LLM_ARCH_NEMOTRON_H` + `LLM_ARCH_NEMOTRON_H_MOE` and `--spec-type draft-dspark`. DRAFTER = **not available outside vLLM**: the sidecar is a single 1.349GB safetensors, its card lists `Supported Runtime Engine(s): vLLM` and nothing else, llama.cpp resolves drafters as `dspark-*`-prefixed **siblings in the same HF repo** (`common/download.cpp:659`), and **zero** of the three GGUF repos checked (ggml-org / bartowski / lmstudio-community, 42 files total) carry one. Ollama has **no `-dspark` suffix tag** — a direct contrast with Muse Glimmer, which shipped `30b-nvfp4-dflash` as a tag. So: the base model can be benched today with zero permission; the 2-3x drafter win needs vLLM, which makes this the first *first-party* payload for `t_08e96127` rather than a generic throughput argument. Second-order: the official recipe uses `--kv-cache-dtype fp8` and `--enable-prefix-caching`, the two levers we have separately deferred. **UPDATED 2026-08-11 late (§10) — second independent source with NUMBERS and a runnable llama.cpp config (@DogukanUrker): ~60 tok/s decode / ~1,400 tok/s prefill at full 262K ctx on a single RTX 3060 12GB while offloading 25 of 52 layers' MoE to CPU (--n-cpu-moe 25). VERIFIED from config.json: 52 layers, 2 KV heads, moe_intermediate_size 1856, max_position_embeddings 262144. TWO CORRECTIONS. (a) §5/§8-S4 said ZERO drafter GGUFs exist — STALE: `h1st0ry3D/...-MTP-GGUF` published 22:23Z carries `mtp-...gguf` at 4.088GB BF16, and a header range-read confirms arch `nemotron_h_moe` + `nextn_predict_layers=1`, so `--spec-type draft-mtp` is a FREE arm on our existing 62bf73d build — ceiling under 2x (n_max clamps to 1), take the BF16 not the 1.783GB Q4_K_M per SIG-20260810-03, and pass `-md` explicitly since cross-repo sidecar auto-resolution will not fire. Still NO dspark-* GGUF, so the 4x DSpark claim stays vLLM-gated on t_08e96127 and §5's core conclusion holds. (b) The post misattributes the quant to bartowski, who has NO Nemotron repo (author search n=0); real IQ4_XS is mradermacher 18.961GB / NANI-Nithin 18.718GB. His flat-ladder claim is RIGHT and understated — within one uploader, IQ1_S 17.865GB -> IQ4_XS 18.718GB is 853MB across THREE bits, because moe_intermediate_size 1856 does not divide the i-quant block size. ACTIONABLE: pull IQ4_XS 18.72GB, 4-7GB smaller than the ggml-org NVFP4/Q4_K_M this entry originally named, and nothing below 4-bit is worth taking. His 60 tok/s is a FLOOR for ryan-spark (121GB unified, 44GB free now, 3.3TB disk => --n-cpu-moe 0, zero offload) vs DS4 Flash production p50 13.46 tok/s = ~4.5x — but per §9 the honest comparison is qwen3-coder:30b on the same box (86.7 tok/s), and his own caveat that reasoning tokens are inside the 60 means t_6e058ca2's pin-reasoning rule applies. Also caveat 262K (config native) vs the 1M in this entry's §2 table (GGUF metadata / extended claim). Feeds t_6e8222b2 (quant target + known-good config + free MTP arm); NOT carded separately — same model, same box, same one window."
distill: none
```

## 1. Claim

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2087164607311831534), 2026-08-11 13:09 UTC
(210 likes / 8,959 views at read time), fetched verbatim via `api.fxtwitter.com`:

> Just released: @NVIDIAAI Nemotron 3.5 Lightning 30B A3B, built specifically for the high-volume
> execution layer of long-running AI agents ✨
>
> Tool calls, validation, formatting, subagent work should run very fast while staying accurate.
>
> I've tested it it's super fast on a DGX Spark!
>
> A recipe and a review coming soon!
>
> NVFP4 & DSpark weights here: […]

**Same author as `SIG-20260808-04` (sparkDash), different subject — new entry, not an update.**

**What the post does not contain: a single number.** "Super fast on a DGX Spark" with a recipe and
review promised later. Treat the tweet as a *pointer*; everything below comes from the NVIDIA model
cards, the HF API, the Ollama registry, and live greps on ryan-spark.

## 2. Verified — the model

From `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4/README.md` (read raw):

| | |
|---|---|
| Parameters | **30B total / 3B active** |
| Architecture | **MoE — Mamba-2 + MoE + Attention hybrid** (LatentMoE) |
| Context | **up to 1M tokens** |
| **Single-GPU Deployment** | **1× DGX Spark (GB10)** or 1× H100 |
| Supported HW | Blackwell (**DGX Spark / GB10**, GB200, RTX 5090); Hopper; Ampere via W4A16 |
| Speculative decoding | **DSpark** for low-concurrency + DGX Spark workflows; also **MTP** and **DFlash** |
| **Best For** | *"Long-running autonomous agents, **sub-agent workhorse deployments**, and efficient local inference on personal hardware"* |
| License | **OpenMDW-1.1** — commercial use explicitly permitted |
| Release date | **2026-08-11** (today) |
| Repo | 21.58 GB, 52 safetensors shards, arch tag `nemotron_h`, **19,250 downloads** |

Training is relevant here rather than decorative: **Stage 2 was continued pre-training specifically
to train the MTP layers**, and **Stage 4 was GRPO RL across "multi-step tool use, multi-turn
conversations, and structured output environments."** The drafters are not bolted on after the
fact, and the tool-call behaviour is what the RL optimised.

### Benchmarks (NVIDIA-measured, NeMo Gym / NeMo Evaluator)

| Task | BF16 | NVFP4 |
|---|---|---|
| MMLU Pro | 81.94 | 81.62 |
| GPQA Diamond | 75.44 | 75.57 |
| **SWE-bench Verified** | 51.56 | **52.80** |
| SWE-bench Multilingual | 39.33 | 36.47 |
| Terminal-Bench 2.1 | 24.58 | 23.46 |
| IFBench (loose) | 71.88 | **72.88** |
| τ³-bench (Banking) | 9.28 | 9.48 |
| AA-LCR (long ctx) | 52.00 | 49.19 |

**Read these as vendor numbers.** NVIDIA states plainly that they were "measured by NVIDIA under a
consistent harness… may differ from vendors' self-reported numbers" — which cuts both ways. To
their credit the full reproducibility recipes are published in NeMo Gym, which is more than most.

Two honest observations rather than cheerleading:

- **NVFP4 ≥ BF16 on SWE-bench Verified and IFBench.** That is quantisation *noise favouring the
  quantised build*, not evidence that 4-bit is better. It does support the weaker, useful claim
  that the NVFP4 checkpoint is not meaningfully degraded — which is the one that matters for a
  23 GB local deploy.
- **τ³-bench Banking 9.28/9.48 is very low in absolute terms**, and long-context AA-LCR *drops*
  under NVFP4 (52.00 → 49.19). A model sold on 1M context loses the most on the long-context
  benchmark when quantised. Do not pitch this as a 1M-context win without measuring.

## 3. Verified — the DSpark drafter

From `…-NVFP4-DSpark/README.md`:

| | |
|---|---|
| Size | **967M total params** (615M non-embedding) — **1.349 GB**, single `model.safetensors` |
| Architecture | Dense GQA — dense FFN MLP + GQA attention, **sliding window 1024**, per-head attention-sink bias |
| Paper | *DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation* (arXiv 2607.05147) |
| **Supported Runtime Engine(s)** | **vLLM** — and nothing else is listed |
| Intent | *"DSpark-assisted serving… rather than as a standalone target model checkpoint"* |
| Downloads | **64** (vs 19,250 for the base) |

Official DGX Spark recipe, verbatim from the base card:

```shell
vllm serve --model $MODEL_CKPT \
  --moe-backend marlin \
  --kv-cache-dtype fp8 \
  --enable-prefix-caching \
  --speculative_config.num_speculative_tokens 3 \
  --mamba-backend flashinfer \
  --mamba-cache-mode align \
  --reasoning-parser nemotron_v3 \
  --speculative_config.model $DSPARK_CKPT \
  --tool-call-parser qwen3_coder \
  --enable-auto-tool-choice
```

Note `--speculative_config.num_speculative_tokens 3` — the same **n=3** that llama.cpp defaults to
and that `t_227d09b2`'s EAGLE3 arm violated with `n_max 16` against a measured accept length of ~3.

## 4. Why this is P0 — DSpark is *our* one winner

The fleet's spec-dec record, corrected:

| attempt | engine | result |
|---|---|---|
| DSpark, upstream `antirez/ds4` | ds4 `b0309611` | ❌ no-op — Metal-only path, A/B 16.23 vs 16.39 = noise |
| **DSpark, Entrpi fork** | ds4 fork (cuda-spark sm_121a) | ✅ **72–73% accept, 2.83–3.00 tok/step, 16.07 → 25–26 tok/s** |
| DFlash, Ollama tag | ollama | ❌ −32% (drafter opted out; `drafted=1` of 255) |
| EAGLE3, llama.cpp `62bf73d` | llama.cpp | ❌ 11.7–14.2% accept → 2× slower (**Q8_0 draft, `n_max 16`**) |

**One win, and it is DSpark.** NVIDIA has now shipped a first-party DSpark drafter, trained jointly
with its target, for a model whose card names our exact box as the single-GPU target. That is the
"well-matched, well-configured drafter" that `t_99c6388b` was written to find.

⚠️ **Do not overclaim the transfer.** The kevin-spark win was DSpark-on-DeepSeek-V4-Flash under the
Entrpi ds4 fork. This is DSpark-on-Nemotron under vLLM. Same *method family*, different target,
different engine, different quantisation. It raises the prior; it is not a measurement.

⚠️ **And the fork win is currently not even running.** Live check today: `ds4.service` `ExecStart`
points at `app/ds4-server` (upstream `b0309611`), not `fork-src/`, with no spec env — journal decode
p50 **13.46 tok/s** over n=1652. The 25–26 is banked in a receipt, not in production.

## 5. Verified — availability is asymmetric, and that is the gate

### Base model: available three ways, today

**Ollama** — `ollama.com/library/nemotron-3.5-lightning`, **11 tags**:

```
30b · 30b-a3b · 30b-a3b-bf16 (66GB) · 30b-a3b-mlx · 30b-a3b-mlx-bf16
30b-a3b-mxfp8 · 30b-a3b-nvfp4 (23GB) · 30b-a3b-q4_K_M (25GB)
30b-a3b-q8_0 (35GB) · 30b-mlx · latest
```

**`ggml-org`** (the llama.cpp org itself) published GGUFs at **2026-08-11 13:26 UTC — under 4 hours
before this read, 0 downloads**:

```
NVFP4   22.460 GB      Q4_K_M  25.431 GB
Q8_0    35.005 GB      BF16    65.852 GB
```

**llama.cpp `62bf73d` on ryan-spark already supports the arch** — grepped live:

```
src/llama-arch.cpp:92  { LLM_ARCH_NEMOTRON_H,     "nemotron_h"     },
src/llama-arch.cpp:93  { LLM_ARCH_NEMOTRON_H_MOE, "nemotron_h_moe" },
```

No rebuild needed. Same property as Qwen3.6 in `SIG-20260811-01`.

### Drafter: not available outside vLLM

llama.cpp resolves drafters as **siblings inside the primary model's own HF repo**, by filename
prefix — `common/download.cpp:659`:

```cpp
static hf_cache::hf_file find_best_dspark(const hf_cache::hf_files & files, …)
    { return find_best_sibling(files, model, "dspark-", tag); }
```

Checked all three GGUF repos — **42 files, zero `dspark-*` / `dflash-*` / `mtp-*` / `eagle-*`
siblings**:

| repo | files | sidecars |
|---|---|---|
| `ggml-org/…-GGUF` | 6 | **NONE** |
| `bartowski/…-GGUF` | 31 | **NONE** |
| `lmstudio-community/…-GGUF` | 5 | **NONE** |

**And Ollama has no `-dspark` suffix tag** — a direct contrast with Muse Glimmer
(`SIG-20260810-01`), which shipped `30b-nvfp4-dflash` as a tag suffix. The drafter is
safetensors-only and vLLM-only.

**Net:** base model = free to bench today. Drafter = **needs vLLM**. Which makes this the first
*first-party* payload for `t_08e96127` (vLLM sm121 wheel spike) instead of a generic
"vLLM is faster" argument.

## 6. 🔧 Correction — "DSpark is Metal-only / NEGATIVE-FINAL"

I have repeated that line in this thread. It is **scope-limited to upstream `antirez/ds4`**, and
another session already posted the correction onto `t_716141c4` (2026-08-10):

> NEGATIVE-FINAL is scope-limited to UPSTREAM — do not cite it as "DSpark does not work on GB10".
> […] The Entrpi fork builds cuda-spark (sm_121a) and DSpark is LIVE on kevin-spark right now:
> accept 72-73%, tok_per_step 2.83-3.00, decode 16.07 -> 25-26 tok/s per INSTALL-RECEIPT.
> This is the fleet's FIRST clean positive spec-dec datapoint. It reverses the "three losses,
> drafters do not transfer to code" narrative […] — it is two losses and one win.

**In llama.cpp DSpark is not Metal-bound at all.** Grepped on ryan-spark: `ggml/src/ggml-metal/` →
**0 hits**, `ggml/src/ggml-cuda/` → **0 hits**. It is implemented in `src/models/dflash.cpp` from
generic ggml primitives — `ggml_get_rows`, `ggml_mul_mat`, `ggml_add` — which all have CUDA
kernels. `COMMON_SPECULATIVE_TYPE_DRAFT_DSPARK` is documented in-source as *"DFlash + Markov head"*,
and `common/arg.cpp:551` notes *"dspark outranks dflash, its sidecar carries the extra Markov head."*

So the correct statement is: **DSpark has one loss (upstream ds4), one win (Entrpi fork), and an
untested-but-fully-wired path in llama.cpp that is blocked only on a GGUF sidecar existing.**

## 7. Fleet fit — measured live

**ryan-spark `spark-6c82`** (the target):

```
Mem     121 GB total · 84 used · 36 available
GPU     llama-server 67,210 MiB (gpt-oss:120b) + 6,791 MiB (hermes3:8b-16k)
Disk    3.3 TB free
Ollama  0.31.2        llama.cpp  62bf73d, llama-server built 2026-08-10 06:13
```

- **NVFP4 (22.5 GB) or Q4_K_M (25.4 GB) fit in the 36 GB available *without* unloading `gpt-oss:120b`** — tight but real.
- Unloading 120b frees ~101 GB, enough for Q8_0 (35 GB) or even BF16 (65.9 GB).
- ⚠️ **Ollama 0.31.2 on ryan-spark is the fleet's oldest** (MBP 0.32.7, Kevin 0.32.0, Caden 0.32.5) and `nemotron_h_moe` shipped today. **Assume the Ollama path fails there until proven** — the llama.cpp path is the one verified to carry the arch. This is the cheap thing to check first.

**MBP** — Ollama 0.32.7, 366 GB disk free, and Ollama carries `30b-a3b-mlx` / `30b-a3b-mlx-bf16`
tags, so an MLX arm exists. But the MBP shelf is already **154.6 GB / 10 tags** and growing fastest
on the fleet; adding a 4th 30B-class family needs a reason, not just capacity.

**CadensPC** — clean **NO**. RTX 4060 / 8 GB; the smallest GGUF is 22.46 GB. Also still
unreachable (`:11436` refused, `ssh` host-key failure) — see `t_47f30baf`.

**Kevin** — out of scope. 8.6 GB free with DS4 holding ~105 GiB; and any change there is his call.

## 8. Steals

**S1 — P0 — bench the base model on ryan-spark via llama.cpp `62bf73d`.** Free of permissions, no
new engine. `30B-A3B` is directly comparable to `qwen3-coder:30b` (also A3B, measured **86.7 tok/s
decode / 3.2 s wall**), which is the honest yardstick — not DS4 Flash. If it lands anywhere near
coder-30b's speed *with* SWE-bench 52.8 and RL-trained tool calling, it is a candidate for the
worker lane that DS4 Flash currently serves at 13–16 tok/s.

**S2 — P0 — this is the first-party payload for `t_08e96127`.** The vLLM spike was previously
justified by generic width/prefill arguments. It now has a concrete, vendor-published, GB10-tuned
recipe whose *only* supported runtime is vLLM. Comment it onto that card rather than opening a
competing one.

**S3 — P1 — `--kv-cache-dtype fp8` + `--enable-prefix-caching` are in the official recipe.** Both
are levers we deferred (fp8 KV was explicitly not carded on 2026-08-10 because it needed a restart
on *Kevin's* box). NVIDIA shipping them as the default DGX Spark config is corroboration that they
are the right defaults on this silicon.

**S4 — P2 — watch for a `dspark-*` GGUF sidecar.** The moment one appears in a GGUF repo,
`--spec-type draft-dspark` auto-resolves and the drafter arm becomes free on llama.cpp. `ggml-org`
published the base GGUFs today; a sidecar is plausible within days. This is a cheap recurring check,
not work.

## 9. Do not

- **Do not pull the DSpark sidecar hoping llama.cpp will use it.** It is safetensors; llama.cpp
  needs a `dspark-`-prefixed **GGUF sibling in the same repo**. 1.35 GB of shelf-ware.
- **Do not cite the Entrpi 25–26 tok/s as evidence this will be fast.** Different target, different
  engine. It raises the prior only.
- **Do not compare it against DS4 Flash and call it a win.** Flash is currently running the
  *rollback* binary at 13.46 tok/s; beating a known-degraded lane proves nothing. Compare against
  `qwen3-coder:30b` on the same box.
- **Do not unload `gpt-oss:120b` without a window.** It is pinned `Forever` and costs a **~158 s**
  cold reload; it is the propose lane.
- **Do not `pkill -f llama-server`** on ryan-spark — that pattern matches Ollama's bundled runner
  (`/usr/local/lib/ollama/llama-server`, currently holding 67 GB) and would drop both models.
- **Do not treat this as unblocking B18.** Different program, still corpus-blocked at 2 trainable
  pointers vs 500.

---

## 10. 🔄 UPDATE 2026-08-11 late — independent bench + working llama.cpp config; drafter claim CORRECTED

**Second source, same model, ~8h later.**
[@DogukanUrker](https://x.com/dogukanurker/status/2087281654456832306) (536 followers, 31 likes /
1,294 views — small account, high density), fetched verbatim via `api.fxtwitter.com`. Quote-tweets
NVIDIA's own launch post. **This is the first post with numbers and a runnable config** — the
MiaAI post that opened this entry had neither ("super fast on a DGX Spark", recipe promised later).

> Running Nemotron 3.5 Lightning on a single RTX 3060: full 262K context at ~60 tok/s, ~1400 tok/s
> prefill. Pinned at 95% of the 12GB. […] 52 layers, only 6 of them attention with 2 KV heads.
> That's the whole trick: 46 layers carry no KV cache, so the full 262K costs well under a gig.
> Context was never the wall here, the compute buffer was. […] NVIDIA's 4x figure is with DSpark
> speculative decoding, which llama.cpp doesn't have, so this is the honest floor not the ceiling

His config, verbatim:

```shell
llama-server -m NVIDIA-Nemotron-3.5-Lightning-30B-A3B-IQ4_XS.gguf \
  -ngl 99 --n-cpu-moe 25 -c 262144 -fa on --jinja -np 1 \
  --cache-type-k q8_0 --cache-type-v q8_0 -b 2048 -ub 1024 \
  --temp 1.0 --top-p 0.95
```

### 10.1 Architecture claims — VERIFIED from `nvidia/…-BF16/config.json`

| his claim | config says | |
|---|---|---|
| 52 layers | `num_hidden_layers: 52` | ✅ |
| 2 KV heads | `num_key_value_heads: 2` | ✅ |
| `moe_intermediate_size` 1856 | `moe_intermediate_size: 1856` | ✅ (and 1856/128 = 14.5 — indeed not divisible) |
| full 262K | `max_position_embeddings: 262144` | ✅ |
| "only 6 of 52 are attention" | **not directly in config** | ⚠️ unverified — but the MTP GGUF header carries `attention.head_count_kv` as a **53-element array**, i.e. per-layer KV heads, which is the structure his claim describes |

Also: `n_routed_experts: 128`, `num_experts_per_tok: 6`, `hidden_size: 2688`, `mamba_num_heads: 64`.

⚠️ **262K vs 1M — the entry's own §2 table says "up to 1M tokens" and that needs a caveat.** The
HF `config.json` native window is **262,144**. The GGUF metadata declares
`nemotron_h_moe.context_length = 1048576`. Both numbers are real from different sources; the
*native trained* window is 262K and 1M is the extended claim. Doğukan ran 262K. **Do not pitch 1M
without measuring** — this compounds the existing §2 warning that AA-LCR long-context *drops* under
NVFP4 (52.00 → 49.19).

### 10.2 🔧 CORRECTION to §5 / §8-S4 — a drafter GGUF now exists (MTP, not DSpark)

§5 concluded *"ZERO of the 3 GGUF repos carry [a sidecar]"* and §9 says *"do not pull the DSpark
sidecar hoping llama.cpp will use it."* **Both were true when written and one is now stale.**
Re-swept the HF API tonight (40 repos):

| repo | file | size | published |
|---|---|---|---|
| **`h1st0ry3D/…-MTP-GGUF`** | **`mtp-NVIDIA-Nemotron-3.5-Lightning-30B-A3B.gguf`** | **4.088 GB** | **2026-08-11 22:23Z** |
| `h1st0ry3D/…-MTP-GGUF` | `…-Q4_K_M.gguf` | 1.783 GB | same |
| `mlx-community/…-DSpark-bf16` | `model.safetensors` | 1.935 GB | 16:46Z |
| `thoughtworks/…-Eagle3` | `model.safetensors` | 0.419 GB | 18:21Z |

**An MTP drafter in GGUF exists, and `llama.cpp 62bf73d` on ryan-spark has `--spec-type
draft-mtp`.** Verified from a 3 MB range-read of that GGUF's header — no download:

```
general.architecture              nemotron_h_moe        ← matches the base
general.name                      Nemotron35 Bf16 Mtp
nemotron_h_moe.block_count        53
nemotron_h_moe.nextn_predict_layers  1                  ← the ceiling
```

**Ceiling is the same as Qwen3.6 (`SIG-20260811-01`): `nextn_predict_layers = 1` ⇒ `n_max` clamps
to 1 ⇒ max 2 tokens/step ⇒ under 2×, not NVIDIA's 4×.** The 4× remains DSpark-only and DSpark
remains vLLM-only — **still no `dspark-*` GGUF anywhere**, so §5's central conclusion (base free,
DSpark gated on `t_08e96127`) survives intact. What changed is that a *cheap, correctly-clamped*
drafter arm is now free on llama.cpp.

Two constraints on using it:
- **Take the 4.088 GB BF16 file, not the 1.783 GB Q4_K_M.** `SIG-20260810-03` is explicit — a
  quantised draft head is what produced `t_227d09b2`'s 11.7–14.2% accept. This is our own prior
  finding applied directly.
- **Auto-resolution will not fire.** `common/download.cpp:659` resolves `mtp-*` siblings **in the
  same repo**; this file is in `h1st0ry3D`, no base GGUF beside it. Pass `-md <path>` explicitly,
  the way `SIG-20260810-01`'s RTX 4090 source did with `-md dflash-kquant.gguf`.

### 10.3 🔧 CORRECTION to the post — the bartowski attribution is wrong, and the ladder is *flatter* than he says

He credits *"bartowski's IQ4_XS at 18.2GB"* and reports **IQ2_XXS 18.09 GB vs IQ4_XS 18.17 GB, an
80 MB spread across two bits.**

**`bartowski` has no Nemotron 3.5 repo** — `?author=bartowski&search=Nemotron-3.5` returns **n=0**,
and no bartowski repo appears in the 40-result sweep. Neither of his sizes matches any file I can
find. The real IQ4_XS builds are `mradermacher/…-BF16-GGUF` (**18.961 GB**) and
`NANI-Nithin/…-GGUF` (**18.718 GB**).

**But the qualitative claim is right, and understated.** Within `NANI-Nithin` alone (one uploader,
one toolchain — better methodology than his cross-repo comparison):

```
IQ1_S    17.865 GB      IQ3_XXS  18.665 GB
IQ2_XXS  17.881 GB      IQ4_XS   18.718 GB
IQ2_S    18.642 GB      Q4_0     18.729 GB
```

**IQ1_S → IQ4_XS is 853 MB across three bits.** His mechanism holds: `moe_intermediate_size = 1856`
doesn't divide by the i-quant block size, so the expert tensors fall back to a higher-bit format and
the ladder collapses.

➡️ **Actionable: download IQ4_XS (18.72 GB) or Q4_0. Anything below 4-bit buys ~0.85 GB and costs
real quality.** That is a genuinely useful decision this entry did not previously have — §5 listed
only ggml-org's NVFP4 22.46 / Q4_K_M 25.43, and IQ4_XS is **~4–7 GB smaller than either**.

### 10.4 Why 60 tok/s is a floor for our box, not a target

**He is running a 18.7 GB model on a 12 GB card.** `--n-cpu-moe 25` pushes 25 of 52 layers' expert
weights to system RAM across PCIe — and he still gets 60 tok/s decode / 1,400 tok/s prefill at
262K context.

Measured on ryan-spark tonight: **121 GB unified, 44 GB available right now** with `gpt-oss:120b`
(65.1 GB) still resident, **3.3 TB free disk**. The whole IQ4_XS fits in GPU-addressable memory
**with zero CPU offload** — `--n-cpu-moe 0`. And `llama.cpp 62bf73d` already carries both
`--n-cpu-moe` (`arg.cpp:2668`) and `--spec-draft-n-cpu-moe` (`arg.cpp:3989`), so his config runs
as-written.

For scale — **his floor vs what we actually run for agent work**:

| lane | measured | note |
|---|---|---|
| DS4 Flash, kevin-spark **production** | **13.46 tok/s** p50 (n=1652) | running the *rollback* binary |
| Doğukan, RTX 3060, **25 layers on CPU** | **~60 tok/s** | reasoning tokens included in that 60 |
| ryan-spark projection, no offload | **not measured** | ≥ his number by construction |

That is **~4.5×** the lane we're paying for today, from a model NVIDIA labels *"sub-agent workhorse
deployments"* — and it needs no fork, no vLLM, no Kevin, and no permission beyond a window and a
18.7 GB download.

⚠️ **Keep §9's rule: do not score this against DS4 Flash and call it a win.** Flash is degraded
(wrong binary). The honest comparison remains `qwen3-coder:30b` on the *same* box — banked at
**86.7 tok/s decode / 3.2 s wall** on a 256-token smoke. Nemotron is a **dense-attention-light
30B-A3B with 3B active**; qwen3-coder:30b is also A3B. That is the real race, and Nemotron's edge
would be the 262K context at near-zero KV cost, not raw decode.

⚠️ **"Reasoning is on, template default, so the thinking tokens are in that 60."** His own caveat,
and it matters: 60 tok/s of *reasoning* is not 60 tok/s of answer. This is the fourth signal in
five days where reasoning tokens distort a throughput number — the `t_6e058ca2` bench contract
already requires reasoning be pinned or the arm is void.

### 10.5 What this changes on the card

`t_6e8222b2` (blocked, `needs_input`: consumer-paused window on ryan-spark) gets **three concrete
upgrades** and no change to its gate:

1. **Phase 0 download target changes** — IQ4_XS (18.72 GB) instead of ggml-org NVFP4 (22.46 GB) or
   Q4_K_M (25.43 GB). Smaller, and 4-bit is the floor of the useful ladder.
2. **A known-good starting config** rather than a guess — his flags, with `--n-cpu-moe 0` since we
   are not memory-constrained, and reasoning pinned per `t_6e058ca2`.
3. **A free drafter arm** — `--spec-type draft-mtp -md mtp-…BF16.gguf` (4.088 GB), expected under
   2× from `nextn_predict_layers=1`. Sits alongside `t_76235b2a` (Qwen3.6 MTP) as a second
   confound-free MTP datapoint on identical hardware.

**Not carded separately.** Same model, same box, same window as `t_6e8222b2` — a second card would
compete for the one consumer-paused window, which is how the box wedged on 08-11 07:57.
