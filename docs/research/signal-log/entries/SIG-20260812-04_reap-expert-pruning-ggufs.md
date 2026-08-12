# SIG-20260812-04 — REAP expert pruning: the first memory lever that needs no engine change

```yaml
id: SIG-20260812-04
date: 2026-08-12
title: "REAP expert pruning: a memory lever that needs no engine change — LLM Compressor v0.13.0, and a community GGUF shelf that already covers our exact models"
source_url: "https://x.com/redhat_ai/status/2087519343349305528"
canonical_repo: "https://github.com/vllm-project/llm-compressor"
canonical_docs: "https://github.com/vllm-project/llm-compressor/releases/tag/0.13.0"
bucket: models
posture: spike
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans: ["t_ee732ca8", "t_99c6388b", "t_6e8222b2", "t_7cb87a81", "t_13d79be5", "t_6e058ca2"]
status: carded
distill: none

index_title: "REAP expert pruning (llm-compressor 0.13.0) — **the first memory lever with no engine dependency.** Structurally drops low-saliency MoE experts; output stays a normal HF/GGUF checkpoint, so it runs on the llama.cpp/Ollama we already have — unlike every other lever this week (vLLM blocked on #51920, SGLang unbenched, DS4 fork unadopted). Community has ALREADY published REAP GGUFs for our exact models: gpt-oss-120b->58B (128->64 experts, 50% prune) and DeepSeek-V4-Flash-0731 K216 (82.94 GiB, tested on GB10 at 128K). Their own paper data predicts the DeepSeek-arch risk and the K160 build empirically failed — K216's gentler 15.6% prune is the response. Carded ST-15."
index_links: [repo, docs]
status_note: "**carded ST-15 `t_ee732ca8` (steals, blocked).** Phase 0 is free — GGUF header range-reads, no download, no window. Do NOT make this a fourth competitor for the one consumer-paused ryan-spark window already contested by `t_99c6388b` / `t_6e8222b2` / `t_7cb87a81`; the gpt-oss arm may A/B *without* evicting the incumbent (43 GB free measured, Q3_K_M is 36.31 GB)."
```

## 1. Claim

[@RedHat_AI](https://x.com/redhat_ai/status/2087519343349305528) (85 likes / 5,840 views, 2026-08-12 12:39Z) —
**LLM Compressor v0.13.0** ships **REAP expert pruning**: *"structurally shrink MoE models by removing
whole experts based on calibration saliency, then quantize what's left to FP8 or NVFP4."* Plus arbitrary
bit-width quantization (3/5/6/7-bit, no wasted bits), 16 new WxAy presets, and **calibration support for
DeepSeek V4 Pro**, GLM 5.2, Hy3.

## 2. What we verified

**The release is real and first-party.** `vllm-project/llm-compressor` — **★3,662, Apache-2.0**,
created 2024-06-20, pushed today. Tag `0.13.0` published **2026-08-11 21:08Z**, `prerelease: false`,
`draft: false`. The tweet is one day behind the release.

**REAP is a structural prune, not a quantization format — that is the whole finding.**
PR [#2864](https://github.com/vllm-project/llm-compressor/pull/2864) (merged 2026-06-30, 10 files,
+1,823/−0) implements the saliency score from
[REAP the Experts, arXiv 2510.13999](https://arxiv.org/pdf/2510.13999):

```
S_j = (1/N_j) Σ_t  g_j(t) · ‖f_j(t)‖₂
```

— router gate weight × L2 norm of the expert's output activation, averaged over the tokens routed to
expert *j* during calibration. Lowest-saliency experts are deleted per layer up to a target sparsity.
**The result is still a standard checkpoint with fewer experts.** Quantizing to FP8/NVFP4 afterwards is
an *optional second step* that locks the artifact to vLLM. Stop after the prune and the model converts
to GGUF like any other.

**Their own results table — and the part that matters most for us:**

| Model | Config | GSM8K strict | Recovery | Size (GiB) |
|---|---|---|---|---|
| Qwen3-30B-A3B (128e) | baseline | 0.9672 | — | 56.93 |
| | REAP 25% → 96e | 0.9562 | **98.86%** | 43.43 |
| | REAP 50% → 64e | 0.9653 | **99.80%** | 29.92 |
| Moonlight-16B-A3B (**DeepSeek-V3 arch**, 64e) | baseline | 0.8326 | — | 29.88 |
| | REAP 25% → 48e | 0.6642 | **79.77%** | 23.17 |
| | REAP 50% → 32e | 0.1414 | **16.99%** | 16.47 |

Their own words: *"REAP is only effective to the extent to which the original model's experts are
redundant."* **The DeepSeek-arch model is the one that collapses.** Hold that thought — §2.4.

### 2.1 The steal is already done: REAP GGUFs exist for our exact models

I did not need to run llm-compressor. HF search (`?search=REAP&sort=downloads`) returns a live shelf,
and **three of the top twenty are our fleet's models or our silicon**:

| repo | dl | note |
|---|---:|---|
| `mradermacher/OpenAI_GPT-OSS-120B_Pruned_REAP_58B-…-i1-GGUF` | 4,144 | **our pinned ryan-spark model** |
| `heath0xFF/DeepSeek-V4-Flash-0731-REAP-GGUF` (K160) | 4,812 | **our exact DS4 checkpoint**, MIT |
| `heath0xFF/…-REAP-K216-GGUF` | 386 | the maintainer's own replacement for K160 |
| `saricles/MiniMax-M2.5-REAP-139B-A10B-NVFP4-GB10` | 23,196 | **GB10** = our Spark silicon |
| `0xTank/Kimi-K3-IQ1S-REAP568-64K-4XSPARKS` | 3,808 | 4× Spark cluster |
| `unsloth/GLM-4.7-Flash-REAP-23B-A3B-GGUF` | 21,192 | first-party Unsloth, 266 likes |

This is the significant structural fact: **REAP is the only lever surfaced this week whose payoff
requires no engine we do not already run.** vLLM is blocked (#51920, MLA startup crash on sm_121 —
`SIG-20260812-03`), SGLang is unbenched (`t_13d79be5`), the Entrpi DS4 fork is unadopted, DSpark
upstream is NEGATIVE-FINAL. A REAP'd GGUF loads in the llama.cpp `62bf73d` and Ollama we have today.

### 2.2 gpt-oss-120b → REAP 58B — measured provenance

Base `12bitmisfit/OpenAI_GPT-OSS-120B_Pruned_REAP_58B-SafeTensors` (200 OK). Its `config.json`:

```json
architectures: ["GptOssForCausalLM"]   num_hidden_layers: 36
num_local_experts: 64                  num_experts_per_tok: 4
```

Stock gpt-oss-120b is **128 experts, 4 active** → this is a **50% prune**, the aggressive rung.
No `quantization_config`, so the base is unquantized safetensors.

GGUF ladder (mradermacher, i1/imatrix, 28 files):
`Q5_K_M 47.85` · `Q4_K_M 44.75` · `Q3_K_L 37.49` · `Q3_K_M 36.31` · `Q2_K_S 34.02` GB.

**Measured on ryan-spark right now:** `gpt-oss:120b` is resident at **65 GB** (`ctx 131072`, pinned
`Forever`) alongside `hermes3:8b-16k` 6.9 GB; **121 total / 78 used / 43 available**; disk 3.3 TB free.

So `Q3_K_M` at **36.31 GB fits inside the 43 GB currently free** — the A/B may be runnable **without
evicting the incumbent**, which is the property that makes this cheap. Verify headroom before assuming
it; KV at 131k is not free.

### 2.3 DeepSeek-V4-Flash-0731 REAP — and the maintainer's own retraction

`heath0xFF/DeepSeek-V4-Flash-0731-REAP-GGUF` is **K160** — 160 of 256 routed experts retained
(**37.5% prune**), arch `deepseek4`, ~193B params, MIT, from `0xSero/DeepSeek-V4-Flash-0731-REAP` (200 OK).

**Its own card says do not use it.** Verbatim `[!WARNING]` (updated 2026-08-01): `Q2_K` and `Q4_K_M`
*"repeatedly exhausted the output budget restating their plans without reaching an answer"* in controlled
llama.cpp testing, including with the source sampling config; full GPU offload of `Q2_K` **and** `MXFP4`
*"exposed backend kernel failures on NVIDIA GB10."* A Strix Halo user reported the same looping.

The card redirects to **`heath0xFF/DeepSeek-V4-Flash-0731-REAP-K216-GGUF`** — 216/256 experts
(**15.6% prune**), `UD-IQ3_XXS`, 3 shards summing to **82.94 GiB**, MIT, created 2026-08-02.
Its method is materially better and is the reason to prefer it: it *"applies 0xSero's K216 map directly
to Unsloth's stock quantized GGUF and copies retained expert rows **byte-for-byte**, avoiding the
REAP-checkpoint → GGUF quantization path used here."* The repo ships `metadata/REAP_K216_PLAN.json`,
`metadata/REAP_K216_STRUCTURED_REPORT.json` and `tools/reap_k216_gguf.py` — the transformation is
auditable, which is unusual for this shelf. Reported working on GB10 at **32K, 64K and 128K** contexts
(128K recommended); a 256K slot initializes but crashes on first prompt.

**Against what we run:** Kevin's DS4 file is `…IQ2XXS…imatrix-0731.gguf` at **86.7 GB**. K216 is
**82.94 GiB ≈ 89 GB** — comparable size at a *higher* bpw rung (IQ3_XXS vs IQ2_XXS) with 15.6% of
experts gone. That is the trade actually worth measuring.

### 2.4 The paper predicted the K160 failure — corroboration, not coincidence

The PR's own table shows the **DeepSeek-V3-arch** model losing 20% of GSM8K at 25% prune and
**collapsing to 17%** at 50%, while the Qwen3 MoE recovered ~99% at both. DS4 is DeepSeek-family.
K160 is a 37.5% prune — between those two rungs — and it empirically produced non-answering loops.
Two independent lines of evidence agree that **DeepSeek-arch MoE carries less expert redundancy**,
and K216's much gentler 15.6% is the coherent response to exactly that. This is the strongest reason
to test the gpt-oss (Qwen-like, high-redundancy) arm first and treat DS4 as the speculative one —
not the reverse, which is what the size numbers alone would suggest.

### 2.5 🪤 `twaggs88/DeepSeek-V4-Flash-REAP25-DSpark-ds4-GGUF` is a trap — do not pull it

12,197 downloads, MIT, 92.50 GB single file, and the name reads like the DSpark GGUF we swept 40 repos
for and never found. Four checks, all failing:

1. **Its declared base does not exist.** `deepseek-ai/DeepSeek-V4-Flash-DSpark-0731` → **401**, against
   the control pair `deepseek-ai/DeepSeek-V4-Flash-0731` → **200** and a known-fake repo → **401**.
   Same control method as `SIG-20260812-02`: under an existing org, 401 = absent.
2. **It is not REAP.** Its own card: *"The repo name carries the earlier v3 line's REAP-25 branding;
   the v4 line is **not** expert-pruned — it ships the full 256-expert set."*
3. **No GGUF loader we own can read it.** *"Runs **only** on the [pulsar engine]… custom tensor formats
   (IQ2_XXS_MMQ aligned pre-store, MXFP4/MXFP8 microscaling, embedded drafter) that **llama.cpp and other
   GGUF loaders will not accept**."* (`github.com/tylerwagler/pulsar` does return 200 — the engine exists;
   it is simply a fourth runtime we would be adopting sight-unseen.)
4. Its `config.json` is literally `{}`.

**So `SIG-20260811-04` §5 stands: there is still no DSpark drafter GGUF we can run.** The claimed
embedded 0731 drafter is unverifiable and unusable without adopting pulsar. Worth knowing precisely
because the repo name is engineered to look like the answer.

## 3. Takeaways (max 5)

- **REAP's output is a checkpoint, not a format.** Prune → still HF/GGUF-convertible. Quantize to
  FP8/NVFP4 → vLLM-only. Everything upstream of that fork is engine-agnostic, and that is what makes
  this the week's only unblocked lever.
- **The compression is already done for us.** A community shelf covers gpt-oss-120b, DS4-Flash-0731,
  GLM, MiniMax-on-GB10 and 4×Spark Kimi. This is a *download-and-bench*, not a calibration run — no
  vLLM, no Kevin, no restart.
- **Expert redundancy is architecture-specific and it is measured, not assumed.** Qwen3 MoE recovers
  ~99% at 50%; DeepSeek-arch collapses. Prune ratio is not portable between families.
- **Aggressive-prune artifacts are failing in the field on our exact silicon.** K160's maintainer
  withdrew it after repetition loops and GB10 MMQ kernel failures. Gentle prunes (K216, 15.6%) plus
  byte-for-byte row copying from a stock GGUF is the safer construction.
- **Download count is not provenance.** The 12,197-download repo is the unusable one; the 386-download
  repo ships an auditable plan JSON and the script that produced it.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Structural expert pruning is orthogonal to the engine — it shrinks the checkpoint, not the runtime | **ST-15**: bench a REAP'd GGUF against its unpruned incumbent on ryan-spark. Phase 0 = header range-reads only. gpt-oss arm first (high-redundancy family, may A/B without eviction); DS4 K216 arm second and only if the window is free | P0 | carded |
| S2 | Recovery-vs-sparsity is a *per-architecture* curve with a published shape | Add `prune_ratio` + `experts_retained/total` + `recovery_vs_baseline` to the bench contract on `t_6e058ca2`. A REAP row without its expert count is unreadable — same class as a spec-dec row without `n_max` | P1 | open |
| S3 | Auditable transformation > download count as a trust signal for third-party weights | Extend the supply-chain rule: prefer artifacts shipping the plan/script that produced them (K216) over high-download opaque ones (twaggs88). Cheap, and it would have caught this trap by construction | P1 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- **Do not pull `twaggs88/DeepSeek-V4-Flash-REAP25-DSpark-ds4-GGUF`** — §2.5. Nonexistent base, not
  REAP, unreadable by any engine we run, and it would mean adopting a fourth runtime.
- **Do not run llm-compressor to make our own REAP checkpoints.** Calibration needs the full model
  resident plus a dataset, and the output's natural home is vLLM — which is the blocked engine. The
  shelf already has our models; do the free thing first.
- **Do not treat this as a fourth claimant on the one consumer-paused ryan-spark window.**
  `t_99c6388b` (spec-dec sweep), `t_6e8222b2` (Nemotron) and `t_7cb87a81` (TurboQuant) are already
  queued for it. The gpt-oss arm's value is that it *might not need the window at all*.
- **Do not carry K160's numbers or the 50%-prune rung to DS4.** §2.4 — the maintainer withdrew K160
  and the paper's DeepSeek-arch row explains why.
- **Do not score a REAP arm against DS4 Flash's live p50.** That lane is still on the `app/` rollback
  binary (~13.5 t/s vs the fork's banked 25–26). `pct_of_reference` needs a *named* ceiling —
  `SIG-20260811-05` S1.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup — S1/S2/S3
- [x] card **ST-15** on the `steals` board (blocked; force-blocked after create per the known gotcha)
- [ ] kanban comment — none beyond the card; `t_6e058ca2` picks up S2 when a REAP row is first written
- [ ] patch skill — none

## 7. Chat blurb

`SIG-20260812-04` · `models` · **spike P0** — REAP (llm-compressor 0.13.0, Apache-2.0, ★3,662) drops
whole MoE experts by calibration saliency. Output stays a normal checkpoint → **runs on llama.cpp/Ollama
we already have**, unlike every other lever this week. Community GGUFs already exist for **our** models:
gpt-oss-120b→58B (128→64 experts) and DS4-Flash-0731 **K216** (82.94 GiB, GB10-tested at 128K).
Their own paper predicts the DeepSeek-arch risk and K160 failed in the field — so gpt-oss arm first.
⚠️ `twaggs88/…DSpark-ds4-GGUF` (12k dl) is a trap: base repo 401, not REAP, pulsar-engine-only.
