# SIG-20260812-05 — SparDA: decoupled sparse attention (Forecast projection)

```yaml
id: SIG-20260812-05
date: 2026-08-12
title: "SparDA (NVIDIA+MIT): a fourth per-layer projection (Forecast) decouples sparse block selection from the attention query, enabling one-layer-lookahead CPU->GPU KV prefetch"
source_url: "https://x.com/akshay_pachaar/status/2087519615132041522"
canonical_repo: "https://github.com/NVlabs/SparDA"
canonical_docs: "https://arxiv.org/abs/2606.04511"
bucket: inference
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans: [t_6e058ca2, t_13d79be5]
status: open
distill: none

index_title: "SparDA (arXiv 2606.04511, NVIDIA+MIT) — architecture change, not a lever we can pull. Adds a 4th per-layer Forecast projection so layer L predicts layer L+1's KV blocks, hiding the CPU->GPU prefetch behind compute. VERIFIED HARD-NO for our fleet on three independent grounds: (1) no checkpoints released (README: 'train Forecast/indexer weights yourself'; HF search n=0) and training is multi-GPU H100, ~48h; (2) it only applies to models ALREADY sparse-pretrained (MiniCPM4.1-8B / NOSA-8B on InfLLM-V2) — nothing on our fleet qualifies, and the paper explicitly does NOT evaluate DeepSeek's DSA family; (3) THE BOTTLENECK IT REMOVES DOES NOT EXIST ON GB10 — measured `Addressing Mode: ATS`, `memory.total [N/A]`, one coherent 121 GB pool, so there is no PCIe CPU->GPU hop to hide. Tweet's two headline numbers are both cherry-picked: '1.7x decode' is 128K/batch-8 vs the CPU-OFFLOAD baseline (at batch 4, SparDA is SLOWER than plain non-offload sparse at 32K and 64K), and '+6.5 accuracy' is one cell of one model on a suite where DENSE attention scores LOWEST (41.6 vs sparse 50.7) — the column measures sampling noise, not selection quality."
index_links: [repo, docs]
status_note: "**watch P2 — nothing to run, nothing to card.** No weights, wrong model family, and GB10's unified memory means the PCIe stall SparDA hides is not a bottleneck we have. Wired as ONE comment on `t_6e058ca2` (bench contract): this is the 5th signal in 6 days whose headline number collapses once you name the reference — and the first where the *accuracy* column fails the same way (Dense < Sparse on the reasoning suite ⇒ the metric is not discriminating). Second-order value is citation-only: the paper independently characterises DeepSeek-V4's CSA+HCA as cutting per-token KV ~10x vs V3.2, which corroborates our own measured 13.77 KB/tok (SIG-20260810-06)."
```

## 1. Claim

Every attention layer computes Q, K, V. SparDA adds a **fourth projection — Forecast** — where
layer `L`'s Forecast predicts which KV blocks layer `L+1` will need. Because the prediction is
available one layer early, the runtime prefetches those blocks from CPU memory on a separate CUDA
stream, overlapping the transfer with the current layer's compute. And because Forecast is
decoupled from the attention query, selection uses **one Forecast head per GQA group** instead of
one per query head — killing the per-query-head scoring loop and the softmax before top-k.

Post claims: **decoding 1.7× faster**, **long-reasoning accuracy up 6.5 points**.

## 2. What we verified

**The paper is real and the framing is not.** arXiv **2606.04511**, *"SparDA: Sparse Decoupled
Attention for Efficient Long-Context LLM Inference"*, **submitted 3 Jun 2026** — ten weeks old, not
news. Authors **Yaosheng Fu, Guangxuan Xiao, Xin Dong, Song Han, Oreste Villa** (NVIDIA + MIT;
Xiao and Han are the StreamingLLM / DuoAttention line, so "NVIDIA researchers" undersells the MIT
half). Repo `NVlabs/SparDA` — **★61, Apache-2.0**, created 2026-05-22, **last pushed 2026-06-04**.

### 2.1 Both headline numbers are the best cell of a table

**Decode 1.7× — the baseline is CPU-offloaded sparse attention, and the tweet omits that.**
Abstract: *"up to 1.25× prefill speedup and 1.7× decode speedup over the sparse-attention **offload
baseline**."* Located it in Table 4: MiniCPM4.1-8B, **128K context, batch 8** — Sparse 279.5 →
SparDA 471.2 tok/s = **1.686×**. Every other cell is smaller.

**At batch 4 — the single-worker regime we actually run — SparDA is often SLOWER than simply not
offloading** (Table 4, `Sparse†` = no offload):

| ctx | Sparse† (no offload) B4 | SparDA B4 | ratio |
|---|---:|---:|---:|
| 32K | 277.2 | 235.7 | **0.85×** |
| 64K | 246.5 | 234.9 | **0.95×** |
| 96K | 215.5 | 238.6 | 1.11× |
| 128K | 189.5 | 240.2 | 1.27× |

NOSA-8B is the same shape (0.89× / 0.94× / 1.06× / 1.22×). The wins live at batch ≥8 **with** an
offloaded cache.

**The 5.3× is a batch-capacity claim, not a speed claim.** SparDA at 128K/**B64** = 1000.1 tok/s vs
non-offload sparse at 128K/**B4** = 189.5 → 5.28×. The baseline **OOMs past batch 4**; SparDA reaches
64. Honest, but it is "we fit a bigger batch," not "we decode faster."

**+6.5 accuracy is one cell of one model — and the column is broken.** Table 1 aggregate averages:

| | MiniCPM4.1-8B Reasoning | NOSA-8B Reasoning |
|---|---:|---:|
| **Dense** (the ceiling) | 82.3 | **41.6** |
| Sparse | 83.6 | 50.7 |
| SparDA | 84.7 | **57.2** |

On **both** models, **dense attention scores worst on the reasoning suite** — on NOSA-8B by
**9.1 points**. Dense is the accuracy ceiling by construction; if it loses to two lossy
approximations of itself, the metric is not measuring selection quality. Setup explains why: the
suite is **MATH-500 + AIME 2024 (n=30) + AIME 2025 (n=30)**, run with **sampling** (temp 0.9–1.0)
and graded by a **GPT-5.2 judge**. One AIME problem is worth 3.3 points on that benchmark.

The paper's own abstract says the honest version — *"matches or slightly improves accuracy"* — and
the aggregate deltas are **+0.3** (MiniCPM) and **+2.3** (NOSA). The tweet promoted the outlier.

### 2.2 There is nothing to run — three independent blockers

**(a) No weights.** README, verbatim: *"SparDA checkpoints are not source files and are not included
in the release package. **Train Forecast/indexer weights yourself** or provide a checkpoint from
your own run."* HF API `?search=SparDA` → **n=0**. Training is multi-GPU (`--gpus N`, single-node
only), on retokenized **ProLong**, and the paper says MiniCPM4.1-8B at 64K *"completes within 48
hours"* on H100s at effective batch 32 accumulated across GPUs.

**(b) Wrong model family.** SparDA trains Forecast projections on models that are **already
sparse-pretrained** — MiniCPM4.1-8B (InfLLM-V2 backbone) and NOSA-8B. Nothing on our fleet
qualifies: `gpt-oss:120b`, `qwen3-coder:30b`, `hermes3:8b-16k`, Muse Glimmer, Nemotron Lightning
are all dense-attention or MoE-FFN models, not block-sparse-attention backbones. **DS4 Flash is
genuinely sparse — and the paper explicitly excludes it**: §5.1 says they do not compare against
DSA-specific accelerators *"which target token-level DSA rather than the block-sparse backbones
used here."* SparDA is InfLLM-V2 block-sparse; DeepSeek is token-level DSA/CSA/HCA. Related, not
transferable.

**(c) The bottleneck does not exist on our hardware.** This is the decisive one, and it is measured,
not argued. SparDA hides a **PCIe CPU→GPU transfer**; the paper's rigs are *"H100 80 GB HBM3 with
PCIe Gen5×16"* and *"A100 80 GB HBM2e with PCIe Gen4×16,"* each with 2 TB of CPU RAM. On ryan-spark:

```
nvidia-smi:  Product Name    NVIDIA GB10
             Addressing Mode ATS          <- coherent unified addressing
             memory.total    [N/A]        <- there is no separate GPU pool
free -g:     121 total / 43 available     <- one pool, CPU and GPU both see it
```

GB10 is Grace-Blackwell over NVLink-C2C: **one coherent 121 GB pool, no host-to-device hop to
overlap.** "Offload the KV cache to CPU memory" is not a configuration our Spark can enter, so the
baseline SparDA beats is one we never run. Kevin's box shows the same shape from the other side —
`ps` RSS reports 1.04 GiB for `ds4-server` while `nvidia-smi` shows 105 GiB, because the model
lives in unified memory.

**(d) Minor, but it would have bitten:** the Docker build defaults to `CUDA_ARCH_LIST="8.0;9.0"` /
`FLASH_ATTN_CUDA_ARCHS="80;90"` — **A100/H100 only**. sm_121 is an untested port of a fused
CUTLASS + FlashAttention + `infllmv2_cuda_impl` stack. Exactly the class that produced vLLM's
kernel-less SM121 builds (`SIG-20260812-03`, PR #49904).

### 2.3 What is genuinely worth citing

The related-work section characterises **our production model** from a third party:

> *"DeepSeek Sparse Attention (DSA) moves to token-level sparsity, and **DeepSeek-V4** further
> interleaves Compressed Sparse Attention (CSA) with Heavily Compressed Attention (HCA), **cutting
> per-token KV cache ~10× over DeepSeek-V3.2**; yet its 8× longer context still leaves absolute
> capacity a bottleneck."*

That independently corroborates `SIG-20260810-06`, where we measured **13.77 KB/token** for DS4
Flash off the live journal against a third party's projected ~44 KB/token — a 3.2× gap we resolved
in our favour. An NVIDIA/MIT paper saying V4 cut per-token KV ~10× is the mechanism behind our
number. It also names the residual we are living with: capacity, not per-token cost.

## 3. Takeaways (max 5)

1. **Architecture changes are not levers.** SparDA needs a new projection trained into the model.
   Every other inference signal this week (REAP, TurboQuant, MTP/DFlash, SGLang) operates on
   weights or engines we can obtain; this one requires 48 H100-hours before you have anything.
2. **GB10 unified memory retires an entire literature.** Any paper whose win is "hide the
   CPU→GPU PCIe transfer" — SparDA, InfiniGen, SparseServe, HiSparse — is solving a problem our
   Spark does not have. Useful filter for future signals; check for a PCIe hop before reading.
3. **The tweet's two numbers fail in two different ways** — one against an unnamed baseline
   (offload), one against an undiscriminating metric (Dense loses on the reasoning suite). Both
   are visible in the paper's own tables in under ten minutes.
4. **Batch size is the hidden variable.** SparDA's gains grow with batch and vanish (or invert) at
   batch 4. Our agent-card workload is batch 1–2. Serving-throughput papers rarely state which
   regime their win lives in.
5. The DS4 CSA+HCA / ~10× KV characterisation is the one durable artifact here — a citable
   third-party account of the model we run in production.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **A speedup needs a named baseline; an accuracy delta needs a sanity ceiling.** SparDA's 1.7× is vs *offload*, and its +6.5 sits in a column where Dense scores lowest — i.e. the reference is unnamed in one case and self-invalidating in the other | Extend `t_6e058ca2` (bench contract): alongside `pct_of_reference`, require accuracy arms to report the **ceiling arm** (dense / full-context / unquantised) in the same table. If the ceiling does not win, the metric is void — same disposition as an unpinned-reasoning throughput row | P2 | open |
| S2 | **Pre-read filter: does the claimed win remove a PCIe host↔device hop?** If yes, it cannot transfer to GB10 (ATS, one coherent pool) | One line in the `signal-log` skill's triage step, so offload-overlap papers get classified `watch` without a full workup | P2 | open |
| S3 | Third-party characterisation of DeepSeek-V4 KV economics (CSA+HCA, ~10× vs V3.2) | Citation into `SIG-20260810-06` / DS4 KV work — corroborates our measured 13.77 KB/tok | P2 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- **Do not build `NVlabs/SparDA`.** No checkpoints ship; the build is Docker + CUTLASS submodule +
  FlashAttention at `sm_80/sm_90`; and even a successful build would have no weights to load.
- **Do not train Forecast projections.** Multi-GPU H100, ~48 h, on models we do not run.
- **Do not claim this applies to DS4 Flash.** The paper explicitly scopes itself out of the DSA
  family, and our DS4 lane has open items with real value (fork binary regression, cold-max-tokens)
  that this cannot touch.
- **Do not card it.** Board is deep and there is no runnable arm — S1 is a field on a card that
  already exists.
- **Do not cite "1.7× faster decode" or "+6.5 accuracy" without their qualifiers.**

## 6. Next action (mechanical)

- [x] STEALS.md **Parked** line (all three steals are P2; the rollup is P0/P1 only per README)
- [x] kanban comment `t_6e058ca2` (bench contract — S1 ceiling-arm rule)
- [ ] ~~new card~~ — deliberately none
- [ ] ~~AUTOMATION-ROADMAP row~~
- [x] patch skill `signal-log` (S2 PCIe pre-filter + batch-size + ceiling-arm claim shapes, step 2)

## 7. Chat blurb

SparDA (arXiv 2606.04511, NVIDIA+MIT, **submitted 3 Jun**, not new): a 4th per-layer "Forecast"
projection predicts layer L+1's KV blocks so the CPU→GPU prefetch hides behind compute. Real paper,
Apache-2.0 repo (★61), but **hard no for us on three counts**: no checkpoints released (train them
yourself, ~48 h multi-GPU H100), it only applies to already-sparse-pretrained models (ours aren't;
DS4's DSA is explicitly out of scope), and **GB10 has no PCIe hop to hide** — measured
`Addressing Mode: ATS`, one coherent 121 GB pool. Both tweet numbers are cherry-picked: the 1.7× is
128K/batch-8 vs the *offload* baseline (at batch 4 SparDA is **slower** than not offloading), and
the +6.5 is one cell of one model on a suite where **Dense scores lowest** (41.6 vs sparse 50.7) —
the metric isn't discriminating. Steal is methodological: accuracy arms must report the ceiling arm.
