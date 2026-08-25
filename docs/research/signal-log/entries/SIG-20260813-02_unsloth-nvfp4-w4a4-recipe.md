# SIG-20260813-02 — Same Qwen3.6-27B family, three packs on DGX Spark: Unsloth NVFP4 W4A4 ~2× NVIDIA NVFP4 W4A16 on prefill because only the Unsloth recipe actually hits FP4 tensor cores

```yaml
id: SIG-20260813-02
date: 2026-08-13
title: "danpacary DGX Spark head-to-head — Qwen3.6-27B prefill@32k: Unsloth NVFP4 1,995 tok/s · NVIDIA NVFP4 1,039 · GGUF Q4_K_XL 723. Recipe, not brand: NVIDIA pack stores weights in 4-bit but computes in 16-bit (memory win, not math); Unsloth quantizes MLP activations to 4-bit too so matmuls hit FP4 tensor cores (~2×). Attention + last layers stay FP8. Edge fades with depth (2.76× over GGUF at 32k → 1.77× at 256k) because attention dominates and runs same precision across packs. Quality gate still pending in the post."
index_title: "Unsloth NVFP4 is W4A4 (FP4 tensor cores); NVIDIA NVFP4 is often W4A16 (memory-only). danpacary Spark prefill@32k Qwen3.6-27B: 1995 / 1039 / 723 tok/s (Unsloth / NVIDIA / GGUF). Primary steal = recipe discipline + Spark serve flags, not 'pull Unsloth'. Engine still gated (vLLM #51920 / SGLang ST-14). Quality gate open."
source_url: "https://x.com/danpacary/status/2087979416895041714"
source_url_2: "https://unsloth.ai/docs/basics/nvfp4"
canonical_repo: "https://huggingface.co/unsloth/Qwen3.6-27B-NVFP4"
canonical_docs: "https://unsloth.ai/docs/models/qwen3.6"
index_links: [HF, docs]
bucket: inference
posture: steal
steal_rank: P1
confidence: high          # post fetched verbatim via fxtwitter; Unsloth docs + HF model card + NVIDIA-forum corroboration read live; NO local re-bench on ryan-spark this turn
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "B17"                 # spark inference engine phase — this is a pack/recipe row once an engine can serve NVFP4
  - "t_13d79be5"          # ST-14 SGLang Unified Radix — preferred engine path
  - "t_08e96127"          # vLLM GB10 — still blocked on #51920; wheel arch question open
  - "t_6e058ca2"          # bench provenance contract — W4A4 vs W4A16 is a required field
  - "t_bf8fae81"          # fleet model ladder
  - "SIG-20260811-01"     # Qwen3.6 MTP / GGUF arch=qwen35
  - "SIG-20260811-03"     # Unsloth Desktop + hermes launcher (same vendor)
  - "SIG-20260812-01"     # SGLang
  - "SIG-20260812-03"     # vLLM 0.27 SM121
  - "SIG-20260813-01"     # vLLM GB10 concurrency ladder (same-day sibling)
status: open
status_note: "**OPEN — pattern banked, no card.** Engine phase still the gate; do not pull NVFP4 weights onto ryan-spark until SGLang Phase-0 or a cleared vLLM path exists. S1 is a provenance/recipe rule for the next NVFP4 arm, not an install."
distill: none
```

## 1. Claim

[@danpacary](https://x.com/danpacary/status/2087979416895041714) (Daniel Isaac; 3,679 followers; 13 likes / 772 views at read; 2026-08-13 19:07 UTC), fetched verbatim via `api.fxtwitter.com`:

> DGX Spark · one model, 3 quants
>
> Qwen 3.6 27B prefill at 32k:
> **Unsloth NVFP4: 1,995 tok/s**
> **NVIDIA NVFP4: 1,039 tok/s**
> **GGUF Q4_K_XL: 723 tok/s**
>
> same weights family. the difference is the recipe:
>
> NVIDIA's pack stores weights in 4-bit but computes in 16-bit = you save memory, not math
>
> Unsloth's pack quantizes the MLP activations to 4-bit too = those matmuls actually execute on the FP4 tensor cores. that is the whole 2×. attention and the last layers stay FP8 for safety
>
> GGUF is 4-bit integer blocks, no FP4 hardware at all. slowest here, but the only pack that runs byte-identical on my Mac
>
> and the edge fades with depth: 2.76× over gguf at 32k, 1.77× at 256k. attention takes over the math at long context and every pack runs attention at the same precision
>
> faster prefill, not a smarter net. quality gate still pending

Chart image attached (`pic.x.com/dgJSHqeF8K`, 1200×958).

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter; note-tweet; media photo present |
| Unsloth first-party claim | Docs `unsloth.ai/docs/basics/nvfp4` + `…/models/qwen3.6`: Dynamic NVFP4 = important layers FP8/BF16, rest **W4A4 (not W4A16)**; "NVIDIA's which use W4A16"; claimed **~2.5× faster** than other NVFP4 on 27B / 24 GB |
| HF artifact | `unsloth/Qwen3.6-27B-NVFP4` — **Apache-2.0**, likes **273**, downloads API **~4.0M**, `compressed-tensors`, 5 safetensors shards, base `Qwen/Qwen3.6-27B`, lastModified **2026-07-12** |
| Spark serve flags (Unsloth) | Required or **2× slower**: `export CUTE_DSL_ARCH=sm_121a` + `vllm serve … --moe-backend flashinfer_b12x`. Preflight assert: `has_flashinfer_b12x_gemm` + `has_flashinfer_b12x_moe` must both be true on cap 12.x |
| Backend trap (Unsloth table) | **Marlin does not support W4A4 well** — forcing it ≈ **2.5× degradation**. Prefer CUTLASS / FlashInfer-TRTLLM / **Cute-DSL (auto)**. Their B200 table: unsloth 27B cute-DSL thr **6,863** out tok/s vs marlin **2,127** |
| Accuracy (Unsloth table, claimed) | Qwen3.6-27B: Unsloth MMLU-Pro **86.25** / GPQA **86.34** / AIME25 **93.12** vs NVIDIA 85.96 / 86.87 / 93.12 vs FP8 86.11 / 86.87 / 93.75 — **not a free quality win, not a collapse** |
| Independent Spark corroboration | NVIDIA dev forum (ttsiodras, 2× GX10): Unsloth Qwen3.6-27B-NVFP4 `llama-benchy` pp2048@d2048 ≈ **1.7–2.3k** pp tok/s range — same order of magnitude as danpacary's 1,995@32k prefill |
| Local re-bench | **Not run this turn.** ryan-spark still has no adopted NVFP4 engine path (vLLM blocked / SGLang carded not released). Numbers below = **claimed / third-party**, not fleet-measured |
| Hardware pre-filter | **Passes.** Win is FP4 tensor-core math on GB10, not PCIe host↔device transfer. Fits ATS coherent pool |

### Ratios from the post (claimed)

| Compare @32k prefill | Ratio |
|---|---|
| Unsloth / NVIDIA | **1.92×** |
| Unsloth / GGUF | **2.76×** |
| NVIDIA / GGUF | **1.44×** |
| Unsloth / GGUF @256k (stated) | **1.77×** |

Decode is **not** in the post. Unsloth's own decode claim is much smaller (≈1.03× on 27B vs other NVFP4) — do **not** cite 2× as a decode number.

## 3. Takeaways (max 5)

- **"NVFP4" is not one recipe.** W4A16 = smaller footprint, still mostly FP16/BF16 math. W4A4 = MLP matmuls on FP4 tensor cores. Same label, different product.
- **Prefill is where the 2× lives.** Long-context attention dilutes the edge; worker prompts that are attention-heavy will see less than the 32k headline.
- **Backend misconfig erases the pack.** Marlin or missing `flashinfer_b12x` / `CUTE_DSL_ARCH=sm_121a` on Spark can make Unsloth W4A4 slower than NVIDIA W4A16 — false negative in a bench.
- **GGUF remains the cross-box control** (Mac byte-identical). Keep it as the quality + portability arm, not the Spark speed champion.
- **Quality still open for *our* traffic.** Unsloth published MMLU/GPQA/AIME parity-ish; danpacary marks quality gate pending. Agent/tool-call pass rate is the gate we care about — not those three.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Quant recipe fields, not brand labels** — every NVFP4 / FP4 row must record `weight_dtype`, `activation_dtype` (W4A4 vs W4A16), `attn_dtype`, `backend` (cute-dsl / flashinfer_b12x / marlin / cutlass), `CUTE_DSL_ARCH`, and whether prefill vs decode | Extend `t_6e058ca2` bench-provenance contract with these columns; reject any "NVFP4 tok/s" row that omits W4A4 vs W4A16 | **P1** | open |
| S2 | **Spark NVFP4 serve checklist** — `CUTE_DSL_ARCH=sm_121a` + `--moe-backend flashinfer_b12x` + b12x gemm/moe preflight assert before any timed run | When ST-14 / vLLM path releases a consumer-paused window, first command is the Unsloth preflight snippet; fail the arm if b12x unavailable | P1 | fold into engine card, not separate |
| S3 | Prefer Unsloth Dynamic NVFP4 over vendor NVFP4 **once** an engine is approved — pack choice is free relative to engine choice | Ladder row only after SGLang or cleared vLLM; artifact `unsloth/Qwen3.6-27B-NVFP4` (or 35B-A3B Fast if MoE path) | P2 | blocked on engine |

**Primary steal (one only):** S1

## 5. Do not

- Do **not** install vLLM/SGLang or pull ~24 GB NVFP4 weights from this signal alone — engine gate unchanged (`t_13d79be5` / `#51920`).
- Do **not** quote 1,995 tok/s as fleet decode or as "Qwen3.6 is 2k tok/s" — it is **claimed prefill@32k**, third-party box.
- Do **not** treat NVIDIA-branded NVFP4 as equivalent to Unsloth NVFP4 in any ladder cell.
- Do **not** force Marlin "because it's the quant kernel" on W4A4.
- Do **not** curl\|sh Unsloth install onto the desk control plane (same HERMES_HOME footgun as SIG-20260811-03).

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [x] add S1 to STEALS.md rollup
- [ ] no new kanban card — comment S1 onto `t_6e058ca2` when that card is next touched; engine cards already own serve flags
- [ ] optional: when engine window opens, one arm = Unsloth W4A4 vs NVIDIA W4A16 vs GGUF Q4_K_XL, prefill **and** decode, same prompt set, quality gate = repair-battery / golden

## 7. Chat blurb (paste-ready, ≤6 lines)

**SIG-20260813-02** · inference · steal **P1** · high conf  
Unsloth NVFP4 ≠ NVIDIA NVFP4: W4A4 (FP4 cores) vs W4A16 (memory-only). Spark prefill@32k claimed 1995 / 1039 / 723.  
**Steal:** provenance must record W4A4 vs W4A16 + backend; Spark needs `sm_121a` + `flashinfer_b12x`.  
Engine still gated — no pull. Entry: `docs/research/signal-log/entries/SIG-20260813-02_unsloth-nvfp4-w4a4-recipe.md`
