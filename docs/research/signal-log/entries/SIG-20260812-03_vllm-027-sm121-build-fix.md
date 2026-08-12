# SIG-20260812-03 — vLLM v0.27.0: the SM121 fix is a *build* fix, and the same release crashes on GB10

```yaml
id: SIG-20260812-03
date: 2026-08-12
title: "vLLM v0.27.0 — official aarch64 wheel on PyPI, PR #49904 fixes kernel-less SM121 builds, and four open GB10/sm_121 bugs filed after release"
source_url: "https://x.com/mr_r0b0t/status/2087177620769120343"
canonical_repo: "https://github.com/vllm-project/vllm"
canonical_docs: "https://github.com/vllm-project/vllm/releases/tag/v0.27.0"
bucket: inference
posture: spike
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "t_08e96127"          # LAB spike: vLLM sm121 wheel on Ryan Spark — this answers its title question
  - "t_99c5d345"          # B17 engine phase
  - "SIG-20260810-04"     # the exo third-party sm121 wheel — its headline needs correcting
  - "SIG-20260812-01"     # SGLang unified radix cache — the competing engine candidate
status: open
index_title: "vLLM v0.27.0 — OFFICIAL aarch64 wheel on PyPI (kills the 10-download supply-chain objection) and PR #49904 fixes kernel-less SM121 builds. BUT #49904 is a SOURCE-BUILD fix, the released wheel is built 12.0-without-PTX, and FOUR open GB10/sm_121 bugs were filed AFTER release — incl. #51920 engine crash at startup on MLA models, which is exactly DS4 Flash. Verdict: engine phase is a BUILD not a download; do NOT spend the window on 0.27.0/0.27.1"
index_links: [repo, docs]
status_note: "**spike P0 — but WAIT.** Wired as a comment on `t_08e96127` (no new card, board 57 blocked). Gate: #51920 closing. Source build is now feasible on our box (CUDA 13.0 toolkit + gcc 13.3 present, CUDA-13 branch of CMakeLists lists 12.1) — the blocker is runtime breakage, not build feasibility"
distill: none
```

## 1. Claim

[@mr_r0b0t](https://x.com/mr_r0b0t/status/2087177620769120343) (9,590 followers, 2026-08-11 14:01Z,
66♥ / 15RT / 4,830 views) summarising the **vLLM v0.27.0** release notes:

> *"Full-stack Kimi K3 support · Qwen3.5 dense and MoE support · Major DeepSeek-V4 kernel, TTFT, and
> memory optimizations · Fault tolerance for large DP + EP deployments · Expanded prefill/decode
> disaggregation · Rubin SM107 and ROCm gfx1250 enablement · Model Runner V2 · Inkling NVFP4 …
> There is also an **important SM121 fix for CUDA architecture detection that could previously
> produce kernel-less builds** 👀👀 … One warning before upgrading: v0.27.0 moves to **PyTorch 2.13
> and Triton 3.7.1**, which is a breaking environment change ⚠️"*

Accurate as a summary of the notes. The 👀👀 line is the one that touches us — **SM121 is GB10**.

## 2. What we verified

### The release is real and official

| | |
|---|---|
| Release | `v0.27.0`, published **2026-08-10 21:18Z**, `prerelease: false` |
| **PyPI aarch64 wheel** | `vllm-0.27.0-cp38-abi3-manylinux_2_28_aarch64.whl` · **307.2 MB** · 2026-08-10 21:31Z |
| Patch | `v0.27.1` published 2026-08-11 10:47Z — **one line**: *"Support quantized DSpark Markov heads (#50424)"* |
| Env break | PyTorch **2.13.0** + torchvision 0.28.0 + Triton **3.7.1** (#48155) |

**This kills the supply-chain objection on `t_08e96127`.** That card was stopped with
*"dont install something with only 10 downloads. The earlier supply-chain OK on this card is
REVOKED"* — aimed at `exo-explore/exo-spark-assets`' third-party wheel (`SIG-20260810-04`).
An official PyPI wheel from the vLLM project is a different proposition entirely.

### PR #49904 — real, merged, and *explicitly a source-build fix*

`[Build] Fix CUDA arch detection producing kernel-less builds on SM121` — merged **2026-07-28**,
3 files, +40/−9. Its own body, verbatim:

> *"On GB10 / DGX Spark (compute capability 12.1, CUDA 13), this shows up on the **default
> source-build path from the docs, `uv pip install -e .`** with `TORCH_CUDA_ARCH_LIST` unset.
> No special flags or custom arch list needed. The build looks fine but has no CUTLASS kernels in
> it. The `.so` only contains `sm_75` cubins."*

```
RuntimeError: cutlass_scaled_mm, csrc/.../scaled_mm_entry.cu:265,
NotImplementedError: No compiled cutlass_scaled_mm for a compute capability
less than CUDA device capability: 121
```

Root cause is a Fermi-era line in torch's vendored `select_compute_arch.cmake`:
`string(REPLACE "2.1" "2.1(2.0)" ...)`. The string **`12.1` contains `2.1`**, so torch rewrites it
to `12.1(2.0)` and emits `-gencode arch=compute_20,code=sm_121`. The fix makes
`extract_unique_cuda_archs_ascending()` prefer `code=sm_*` over the corrupted `arch=compute_*`
half, and adds a hard `if(NOT CUDA_ARCHS)` build failure instead of silently shipping a
kernel-less `.so`.

### 🪤 …which means the fix does **not** apply to the published wheel

The release build arg (`docker/Dockerfile:288` and `:1016`):

```
# Do not add +PTX here: vLLM filters torch's top-level PTX flag when it
# converts global gencode flags into per-kernel arch lists.
ARG torch_cuda_arch_list='7.5 8.0 8.6 8.9 9.0 10.0 11.0 12.0'
```

**`12.1` is absent, and PTX is explicitly excluded.** Meanwhile the CUDA-13 branch of
`CMakeLists.txt:129` *does* support it —
`CUDA_SUPPORTED_ARCHS "7.5;8.0;8.6;8.7;8.9;9.0;10.0;10.1;10.3;12.0;12.1"` — and every
quantized/CUTLASS kernel is gated on **arch-specific** targets:

| kernel | CMakeLists arch list |
|---|---|
| `SCALED_MM_ARCHS` (FP8) | `12.0a;12.1a` (L799) |
| `FP4_SM120_ARCHS` | `12.0a;12.1a` (L973) |
| `MARLIN_ARCHS` / `_FP8` / `_MOE` | `…12.0a;12.1a` (L580/597/1239) |
| `DSV3_FUSED_A_GEMM_ARCHS` | `9.0a;…;12.0a;12.1a` (L713) |
| `CUTLASS_MOE_DATA_ARCHS` | `…12.0a;12.1a` (L942) |

**Inference, not measurement — flagged as such.** Plain cubins have minor-version forward
compatibility (a `sm_120` cubin runs on a `12.1` device), so the generic paths should load. But
`a`-suffixed targets are **arch-exact with no forward compat**, so a wheel built at `12.0` carries
`sm_120a` and *not* `sm_121a` — precisely the CUTLASS/FP8/FP4/Marlin family. **We have not run the
wheel.** Two live hypotheses: (H1) it imports and serves bf16/fp16 but fails on quantized/FP8
paths; (H2) it fails at startup outright. One `pip install` in a throwaway venv settles it.

### 🔴 Four open GB10/sm_121 bugs, all filed *after* both releases

GitHub issue search: **401 results for "DGX Spark", 411 for "GB10"** — this is an actively-hit
platform, not an exotic corner.

| issue | filed | what |
|---|---|---|
| **#51920** | **2026-08-12 04:03Z** | `FlashInferMLASparseSM120Impl` never sets `masked_mha_available`; the prefill dispatcher at `mla_attention.py:~780` reads it unconditionally → `AttributeError` → **engine core dies on startup profiling**. Under `--restart`, ranks crash-loop and desync |
| **#51921** | 2026-08-12 | v0.27.0 engine **permanently stalls after ~1 min idle** on 4-node TP=4 (GB10/sm_121, aarch64), `shm_broadcast` |
| **#51959** | 2026-08-12 | `[Build] DeepGEMM pin has no SM120 kernels: family-12 Blackwell cannot run hyperconnections` |
| **#51987** | 2026-08-12 | Revert *"[Attention] Add FlashInfer XQA decode support on SM12x"* (#49718) |
| #51758 | 2026-08-11 (11 comments) | `upgrade vllm from 0.26.0 to 0.27.0 run deepseek v4 flash error` — reporter is **x86_64**, so the DS4 regression is *not* GB10-specific |

**#51920 is the one that decides this.** `MLA` is DeepSeek's attention — **DS4 Flash is an MLA
model**. The single model we most want vLLM for is the one that crashes at startup on our exact
chip, in the release being celebrated. And `v0.27.1` (published 08-11 10:47Z) predates #51920 and
#51921 (08-12) and contains one unrelated DSpark line — **neither released version fixes this**.

Also open: **#51655 "Add Muse Glimmer model support"** — Muse Glimmer is not supported in vLLM.

### Our box — a source build is feasible today

Measured live on `spark` (`ryanneely1000@spark-6c82`):

```
GPU        NVIDIA GB10   compute_cap 12.1   driver 580.159.03   CUDA 13.0
toolchain  /usr/local/cuda-13.0 present (nvcc NOT on PATH)   gcc 13.3.0
python     3.12.3        aarch64
capacity   3.3 TB free   58 GB MemAvailable (63 used by resident gpt-oss:120b)
vllm       ModuleNotFoundError — not installed
```

CUDA 13 + gcc 13.3 + the CUDA-13 `CUDA_SUPPORTED_ARCHS` branch including `12.1` + #49904 means
`TORCH_CUDA_ARCH_LIST=12.1` from the tagged source is, for the first time, a **sanctioned** path.
The blocker is runtime breakage, not build feasibility.

### DS4 work landed in this release (relevant if we ever do build)

Sequence parallelism (#46789) · ~2× kernel from skipping empty c128 launches (#48957) · 3.4% E2E
TTFT skipping topk/router in decode (#49486) · 3.9% E2E TTFT workspace reuse (#49236) · 1.88×
kernel removing a redundant full launch. **All vendor-claimed, none reproduced by us**, and on
hardware that isn't ours.

## 3. Takeaways (max 5)

- **The engine phase is a BUILD, not a download.** `SIG-20260810-04`'s headline —
  *"B17's engine phase may be a download, not a build"* — is wrong as stated for the official
  wheel, and the third-party wheel it rested on was vetoed. Correcting it.
- **But the build is now supported**, from an official tag, with the GB10 breakage fixed at build
  level. That is a genuine change of state on `t_08e96127`, and it dissolves the supply-chain half
  of the veto.
- **Do not spend a Spark window on 0.27.0 or 0.27.1.** #51920 crashes MLA models at engine
  startup on sm_121, and MLA is DS4 Flash.
- **PyTorch 2.13 / Triton 3.7.1 is a breaking env change** — reinforces "throwaway venv, non-prod
  port, never the production lanes", which `t_08e96127` already specifies.
- **This is the second engine candidate in 24h.** `SIG-20260812-01` (SGLang) has an official
  aarch64 cp312 wheel *and* `deepseek_v4_dspark.py` in-tree. Its Phase 0 (import `sgl_kernel`,
  confirm sm121) is free and read-only; vLLM's equivalent now has a known startup crash. **If only
  one engine gets benched, the evidence currently favours starting with SGLang.**

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Official-source build ≠ published wheel | Correct `SIG-20260810-04`; retarget `t_08e96127` from "install a wheel" to "source-build v0.27.x with `TORCH_CUDA_ARCH_LIST=12.1`" | P0 | open |
| S2 | Gate a spike on the vendor's own open bug list, not the release notes | Add "search vendor issues for our arch before spending a window" to the bench contract `t_6e058ca2` | P0 | open |
| S3 | Prefer the engine whose blocking bug list is empty | Sequence SGLang Phase 0 (free, read-only) ahead of vLLM | P1 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- ⛔ **Do not install 0.27.0/0.27.1 on the Spark expecting it to serve DS4** — #51920 is an
  unfixed startup crash on sm_121 for MLA models.
- ⛔ **Do not quote "important SM121 fix" as meaning the wheel works on GB10.** #49904 fixes the
  *source build*; the wheel is compiled `12.0` with PTX explicitly excluded.
- ⛔ **Do not claim the wheel fails** either — that is inference from the build config, not a
  measurement. Say H1/H2 until one venv settles it.
- ⛔ Not on Kevin's box, not on `:11434`/`:11435`/`:8889`, never against the production lanes.
- ⛔ Do not bench vLLM and TurboQuant (`t_7cb87a81`) in the same window — both change the engine
  and the results confound.
- ⛔ Do not take the DS4 perf numbers (2×, 1.88×, 3.4/3.9% TTFT) as ours — vendor-claimed, other
  hardware, and #51758 shows a DS4 regression 0.26→0.27 on x86_64.

## 6. Next action (mechanical)

**One wire:** comment on **`t_08e96127`** — its title is literally *"is B17's engine phase a
download, not a build?"* and this answers it. Retarget to source-build, record the supply-chain
change, set the gate to **#51920 closing**. **No new card** (board 57 blocked).

## 7. Chat blurb

`SIG-20260812-03` · inference · spike **P0** — vLLM v0.27.0 ships an official PyPI **aarch64**
wheel and PR **#49904** fixing kernel-less **SM121** builds. But #49904 is a **source-build** fix,
the released wheel is compiled `12.0` with no PTX, and **four open GB10/sm_121 bugs** were filed
*after* release — including **#51920**, an engine crash at startup on **MLA** models, which is DS4
Flash. Engine phase is a **build, not a download** — and **wait** for #51920.
