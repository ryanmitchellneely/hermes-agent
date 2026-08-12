# SIG-20260812-02 — Qwen3.8 pre-release: a dated countdown, and six empty repos

```yaml
id: SIG-20260812-02
date: 2026-08-12
title: "Qwen3.8 — from empty placeholders to a shipped 2.4T flagship: 397 GB at 1.1875 bpw, unrunnable on our fleet; the 27B that fits lands Friday 2026-08-14"
source_url: "https://x.com/teksedge/status/2087403709412327907"
source_url_2: "https://x.com/unslothai/status/2087569665652580797"
canonical_repo: "https://huggingface.co/unsloth/Qwen3.8-2.4T-A95B-GGUF"
canonical_docs: "https://unsloth.ai/docs/models/qwen3.8"
bucket: models
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans: ["t_76235b2a", "t_99c6388b", "t_6e058ca2", "t_13d79be5"]
status: open
distill: none
updated: 2026-08-12

index_title: "Qwen3.8 — RESOLVED PARTIALLY 08-12 15:59Z. Flagship 2.4T-A95B shipped (4.892 TB BF16 -> 397.3 GB UD-Q1_0, all three post numbers verified exact); Qwen3.8-27B and 35B-A3B still 401. HARD NO on every box (guide wants >=450 GB; fleet sums to ~322 GB across four non-clustered hosts). Declares qwen35moe with nextn_predict_layers=1 and Mamba-style SSM layers. Headline 397 GB quant is the MOST degraded rung on Unsloth's own ladder (PPL +74%, KLD ~2x vs IQ1_S). 27B lands Friday 2026-08-14 at 16 GB+"
status_note: "**watch — flagship unrunnable, 27B dated.** No card, per this entry's own §6 rule. **Friday 2026-08-14**: header range-read the first 27B GGUF for `general.architecture` + `nextn_predict_layers`; if MTP on a supported arch, **append to `t_76235b2a`** — do not open a third competitor for the same ryan-spark window. Dense 27B still ~9× active params/token vs banked `qwen3-coder:30b`. §8.6: our `62bf73d` has `GGML_TYPE_Q1_0` kernels but `QK1_0=128` vs their implied 256-weight block — **format identity unconfirmed**. §8.8 corrects §2's org-recency method (repo `createdAt` 08-08, private; the control-tested 401 was the sound leg)"
```

## 1. Claim

[@TeksEdge](https://x.com/teksedge/status/2087403709412327907) (9,296 followers · 103 likes / 6,308 views, posted 2026-08-12 05:00Z):
*"Never seen such honest excitement for a model release! I hope **Qwen3.8-27B** meets expectations,
and I also hope it's accompanied by an **MoE-like Qwen3.8-35B**. Qwen3.5 also gave us some
exceptionally strong smaller models that became a reference point for much of the small ecosystem."*

The attached screenshot is a **vendor countdown page**, not a benchmark:

> **Upcoming Open-Release** — **Qwen 3.8**
> *"A New Bar for Coding and Cowork, Open to All"*
> `00 Days · 10 Hours · 00 Min · 33 Sec`
> **Estimated Release Time: 2026-08-12 08:00 (UTC-07:00)** → **15:00Z**
> *Waiting souls for the release: 456*

## 2. What we verified

**Timing.** Countdown target = **2026-08-12 15:00Z** = 08:00 PDT = **10:00 CDT**. Checked at
**12:08Z** (07:08 CDT): **+2.87 h, still upcoming.** Screenshot's 10h33m remaining puts its
capture at ~04:27Z, ~33 min before the post.

**It does not exist yet — and the 401 is not ambiguous.** HF returns `401`, not `404`, for
missing repos under an existing org, so a bare 401 proves nothing. Control-tested:

| repo | HTTP |
|---|---|
| `Qwen/Qwen3.8-27B` · `-Instruct` · `Qwen/Qwen3.8` · `Qwen3.8-35B-A3B` · `Qwen3.8-Coder-27B` | **401** |
| `Qwen/Qwen-DefinitelyNotARealRepo-99B` *(control — cannot exist)* | **401** |
| `Qwen/Qwen3.5-27B` · `Qwen/Qwen3-30B-A3B` *(control — known real)* | **200** |

The control run is what makes this conclusive: **401 = absent.** Corroborated independently —
the official `Qwen` org's newest model by `createdAt` is `Qwen3-ForcedAligner-0.6B-hf`
(**2026-06-26**), and `ollama.com/library/qwen3.8` → **404** while `qwen3.6` → **200**.

**🪤 All six `Qwen3.8-27B` repos on HF are empty placeholders.** Every one holds exactly
**2 files** — `.gitattributes` + `README.md`. **Zero weight files, zero configs, 0 downloads:**

| repo | created | files | weights |
|---|---|---|---|
| `huginnfork/Qwen3.8-27B-FP8` · `-NVFP4A16` | 2026-08-05 06:15Z | 2 | **0** |
| `neroued/Qwen3.8-27B-NInfer` · `-nvfp4-NInfer` | 2026-08-06 08:09Z | 2 | **0** |
| `barozp/Qwen3.8-27B-GGUF` · `-MTP-GGUF` · `-Opus-Distill-GGUF` · `-Opus-Distill-MTP-GGUF` | **2026-08-12 07:10Z** | 2 | **0** |

barozp's README says it outright: *"**Placeholder — not yet available.** This repo is reserved
ahead of the `Qwen/Qwen3.8-27B` release and will be filled in once that model ships."*

**Those placeholders assert architecture facts about a model nobody has seen.** barozp claims
*"**Multi-Token Prediction (MTP) head preserved** for self-speculative decoding in llama.cpp"* and
*"**Dense architecture (not MoE)**, so this is a straightforward tensor extraction, no expert
remapping."* Both are **unverifiable until 15:00Z** and neither is sourced. They are consequential
for us (see §3), which is exactly why they should not be repeated as fact.

**🪤 The high-download trap — 41,259 downloads on a model whose parent does not exist.**
`Ma7ee7/Qwen3.8_4B_Distilled_GGUF` (41,259 dl) and `Ma7ee7/Qwen3.8_4B_Distilled` (545 dl) hold
**real weights** — but read the card and the config and they are **not Qwen3.8**:

```json
"architectures": ["Qwen3ForCausalLM"],  "hidden_size": 2560,
"layer_types": ["full_attention", ...]           // Qwen3, dense, not 3.8
```
```yaml
base_model: Qwen/Qwen3-4B-Thinking-2507
datasets:  [r0b0tlab/qwen3.8-max-distillation-50k]
teacher:   qwen3.8-max-preview
```

It is **Qwen3-4B-Thinking-2507 SFT'd on a dataset of responses *claimed* to come from
`qwen3.8-max-preview`.** The "3.8" is **lineage naming, not architecture** — and the teacher's
provenance is one unverifiable hop (an anonymous 50k dataset). Downstream re-uploads
(`thebbg/…-v2`, 11,815 dl) compound it.

**Fleet position, measured live:**

```
ryan-spark :11435   qwen3-coder:30b 18.6G · qwen2.5-coder:32b(-64k) 19.9G · gpt-oss:120b 65.4G
MBP        :11434   qwen3.6:35b-a3b 23.9G · qwen3.6:35b-a3b-q8_0 38.7G · qwen3-coder:30b 18.6G
```

We already hold **`qwen3.6:35b-a3b` (23.9 GB) on the MBP and it has never been benched** — the
nearest-neighbour of the "MoE-like 35B" TeksEdge is hoping for is sitting on our own disk, unmeasured.

## 3. Takeaways (max 5)

1. **Nothing is runnable until 15:00Z.** This is a countdown, not a release. Every artifact on HF
   bearing the name today is either empty or misnamed.
2. **The MTP claim is the only line that would matter to us — and it is unverified.** If
   Qwen3.8-27B ships `nextn_predict_layers` like Qwen3.6 does, `--spec-type draft-mtp` is a **free
   arm on the `62bf73d` build already on ryan-spark**, with llama.cpp auto-resolving the matched
   sidecar and auto-clamping `n_max` — the two bugs that killed `t_227d09b2`'s EAGLE3 run
   (`SIG-20260811-01`). That folds into **`t_76235b2a`**, it does not deserve its own card.
3. **A dense 27B is not a swap-in for our A3B coder.** `qwen3-coder:30b` is A3B (~3B active/token)
   and banked at **86.7 tok/s decode / 3.2 s wall** on ryan-spark. Dense 27B is roughly **9× the
   FLOPs per token** — the same architectural argument made against Muse Glimmer
   (`SIG-20260810-01`). *Inference from parameter counts, not a measurement.* **The 35B-A3B
   variant TeksEdge is hoping for is the one worth benching**, if it ships.
4. **"Coding and Cowork, Open to All" is a positioning line with no numbers behind it.** Treat the
   tagline as marketing until the model card lands.
5. **Download count is not provenance.** 41,259 downloads accrued to a GGUF named after a model
   that has never been published. This is the mirror image of the veto on `t_08e96127` (*"dont
   install something with only 10 downloads"*) — the failure mode is **name trust**, and it runs in
   both directions.

## 4. Steals (patterns only)

**S1 (P2) — Availability evidence must count weight files, not repo existence.**
Six repos matched a name search; **zero** held weights. Our own entries cite HF repos as
availability evidence (`SIG-20260811-04` §5 asserted GGUF drafter availability and went stale
within hours; the correction came from actually listing files). Cheap rule for the bench-provenance
contract: *a repo cited as "available" must record `weight_file_count` and total bytes* — an empty
repo and a 22 GB repo are indistinguishable from a search hit alone. Folds into **`t_6e058ca2`**.

**S2 (P2) — Cite the release *time*, not the release.** The countdown gives a falsifiable
timestamp (15:00Z). Entries about unreleased things should carry the claimed date so a later
session can check the claim rather than re-derive the hype. Applies to this entry's own re-check.

## 5. Do not

- ⛔ **Do not pull `Ma7ee7/Qwen3.8_4B_Distilled*`** or its re-uploads. Named after a model that does
  not exist; teacher provenance is one unverifiable hop; 41k downloads is popularity, not lineage.
- ⛔ **Do not pre-card an unreleased model.** Board is **57 blocked / 9 todo** on mesh; the
  spec-dec sweep (`t_99c6388b`) and the Qwen3.6 MTP card (`t_76235b2a`) are both already parked on
  the *same* consumer-paused window on ryan-spark. A third competitor for that window is how the
  box wedged at 07:57 on 08-11.
- ⛔ **Do not repeat "dense, MTP head preserved" as fact.** It is a placeholder README's claim about
  weights that do not exist yet.
- ⛔ **Do not treat this as corroboration of anything.** Zero measurements, zero repo, zero card.

## 6. Next action (mechanical)

- **None before 15:00Z.** After release: (a) `GET /api/models/Qwen/Qwen3.8-27B` for real file list,
  (b) 3 MB **header range-read** of any GGUF for `general.architecture` + `nextn_predict_layers`
  (method from `SIG-20260811-01`, no download), (c) check for a **35B-A3B** variant.
- If (b) shows an MTP head on a supported arch → **append to `t_76235b2a`**, do not create a card.
- If a 35B-A3B ships → the honest comparison is against **`qwen3-coder:30b` at 86.7 tok/s on the
  same box**, not against DS4 Flash (which is currently degraded on its rollback binary).

## 7. Chat blurb

Qwen3.8 is a **countdown, not a release** — open-release targeted **today 15:00Z** ("A New Bar for
Coding and Cowork"). Verified unreleased via a **control-tested 401**, and **all six `Qwen3.8-27B`
repos on HF are empty 2-file placeholders**. The trap: `Ma7ee7/Qwen3.8_4B_Distilled_GGUF` has
**41,259 downloads** and is **not Qwen3.8** — it is `Qwen3-4B-Thinking-2507` SFT'd on claimed
`qwen3.8-max-preview` outputs. Two things to check at release: an **MTP head** (free arm on the
existing `62bf73d` build → folds into `t_76235b2a`), and a **35B-A3B** variant (the only shape that
competes with our banked `qwen3-coder:30b`). Dense 27B ≈ 9× the active params of an A3B coder.
**No card.**

---

## 8. UPDATE 2026-08-12 16:20Z — the countdown resolved, **partially**. Flagship shipped; the variants we care about did not.

**Second source:** [@UnslothAI](https://x.com/UnslothAI/status/2087569665652580797) (posted **15:59Z**, 1,758 likes / 105,375 views) —
*"Qwen3.8 can now be run locally! We shrank Qwen3.8-2.4T-A95B from 4.9TB to 397GB (-91% size) via Dynamic
1-bit by selectively quantizing layers. Run on 410GB+ RAM/VRAM via Unsloth Desktop. Qwen3.8 rivals GPT-5.6 Sol."*
Guide: `unsloth.ai/docs/models/qwen3.8` · GGUF: `unsloth/Qwen3.8-2.4T-A95B-GGUF`

### 8.1 What shipped — and what did not

Re-ran §2's control-tested probe at 16:05Z:

| repo | HTTP | note |
|---|---|---|
| `Qwen/Qwen3.8-2.4T-A95B` | **200** | **released** — 224 files, 213 safetensors shards |
| `Qwen/Qwen3.8-2.4T-A95B-FP8` | 200 | 3,851 dl |
| `unsloth/Qwen3.8-2.4T-A95B-GGUF` | **200** | modified **15:54:39Z**, 5 min before the post; 0 dl, 56 likes |
| **`Qwen/Qwen3.8-27B`** | **401** | **still absent** |
| **`Qwen/Qwen3.8-35B-A3B`** | **401** | **still absent** |
| `Qwen/Qwen-DefinitelyNotAModel-999B` *(control)* | 401 | — |

**Both questions §6 told a later session to ask are still unanswered, because those models do not exist yet.**
The org sweep confirms it: the only Qwen3.8 repos under the official org are the 2.4T flagship and its FP8 twin.

### 8.2 The post's numbers are exact — verified against the API, not the card

| claim | measured | |
|---|---|---|
| "4.9TB" | `sum(siblings.size)` = **4,892,388,741,252 B = 4.892 TB** over 213 shards | ✅ |
| "397GB" | `UD-Q1_0/` = **397.3 GB** over 10 shards | ✅ |
| "-91%" | 397.3 / 4892.4 = 8.12% → **−91.9%** | ✅ |

Full ladder in the GGUF repo (measured, not quoted): **BF16 4,893.2 GB** (140 shards) · **Q8_0 2,600.2 GB** (56) ·
**UD-IQ1_S 508.4 GB** (12) · **UD-Q1_0 397.3 GB** (10). Repo total **8.4 TB**.

### 8.3 Architecture — read live from `config.json` **and** a 3 MB GGUF header range-read

```
architectures        Qwen3_5MoeForCausalLM        GGUF general.architecture   qwen35moe
model_type           qwen3_5_moe_text             GGUF qwen35moe.block_count  93   (92 + 1 MTP)
num_experts          512                          num_experts_per_tok         10
num_hidden_layers    92                           hidden_size                 8192
head_dim             256                          num_key_value_heads         4
max_position_embeddings  262144                   (docs claim up to 1,010,000)
mtp_num_hidden_layers    1        <-- GGUF qwen35moe.nextn_predict_layers = 1
full_attention_interval  4        layer_types = 3x linear_attention + 1x full_attention
GGUF ssm.conv_kernel 4 · ssm.state_size 128 · ssm.group_count 16 · ssm.inner_size 16384
```

Three facts fall out, in descending order of usefulness to us:

1. **It declares `qwen35moe`** — the arch family already compiled into **`62bf73d` on ryan-spark**
   (`LLM_ARCH_QWEN35MOE` present). Same pattern as `SIG-20260811-01`, where Qwen3.6 declared `qwen35`.
   The *naming* generation is ahead of the *architecture* generation, so support lands before the badge does.
2. **An MTP head ships** (`nextn_predict_layers = 1`). Same single-head shape as Qwen3.6 → `n_max` clamps
   to 1, **max 2 tokens/step, under 2×**. Real but bounded; not the 2.9–3.1× of tree/multi-head methods.
3. **It is a hybrid SSM/attention model** — 69 linear-attention layers to 23 full-attention, plus Mamba-style
   SSM state. That is *exactly* the FULL + MAMBA reuse-rule composition `SIG-20260812-01` (SGLang unified
   radix cache) added components for, and a single-boundary disk cache cannot represent it. **Independent
   corroboration for ST-14** (`t_13d79be5`) from the model side rather than the engine side.

### 8.4 ⛔ Hard NO on every box we own — and the vendor's own two numbers disagree

Tweet says **"410GB+"**; the guide says the 397 GB quant *"will require at least **450GB** RAM."*
Take the stricter one. Against measured fleet capacity:

```
ryan-spark   121 GB total / 43 GB available / 3,290 GB free disk
kevin-spark  121 GB total (DS4 holds ~105 GiB)
MBP           64 GB        CadensPC 16 GB
fleet sum    ~322 GB  <  397 GB   -- and they are four hosts, not a cluster
```

**Disk-offload arithmetic** (their guide explicitly permits it — *"it'll still work, just much slower"*):
95B active params at 1.1875 bpw ≈ **14.1 GB of weights touched per token**. With 121 GB resident against a
397 GB file the routed-expert working set misses heavily; at NVMe 3–5 GB/s that lands near
**~0.2–0.5 tok/s**. *This is arithmetic from the config, not a measurement — but it is two orders of
magnitude below anything usable, so the conclusion does not hinge on precision.*
For scale, their own figure is **~20 tok/s single-stream on B200s**.

### 8.5 🪤 The headline quant is the worst rung on their own ladder

Unsloth's published degradation table — note **they state these are measured on *other* large models, with
Qwen3.8 benchmarks still running**, so treat as directional:

| dtype | GiB | PPL | KLD | top-p |
|---|---:|---:|---:|---:|
| IQ1_S | 553.2 | 2.579 | 0.565 | 78.9 |
| UD-IQ1_XS | 513.6 | 2.931 | 0.690 | 75.7 |
| UD-IQ1_XXS | 474.0 | 3.540 | 0.876 | 71.3 |
| **UD-IQ1_XXXS** *(the 397 GB headline)* | **434.3** | **4.489** | **1.110** | **66.3** |

Against IQ1_S that is **PPL +74%, KLD ~2×, top-p −12.6 points**. The number in the tweet is the *most
degraded* rung, chosen for the size headline. **Record the rung, not just the byte count.**

### 8.6 🪤 Build compatibility is **unconfirmed** — do not assume our build reads these files

`62bf73d` on ryan-spark does carry the new low-bit family with real CUDA kernels:

```
ggml.h        GGML_TYPE_Q1_0, Q2_0, TQ1_0, TQ2_0, IQ1_S, IQ1_M
convert.cu    6 x  case GGML_TYPE_Q1_0:      (dequant paths present)
ggml.c        [GGML_TYPE_Q1_0] blck_size=QK1_0  type_size=sizeof(block_q1_0)
```

**But `QK1_0 = 128`**, while Unsloth's table implies a **256-weight / 38-byte** block at 1.1875 bpw — and
their guide says the IQ1_XXXS quant needs *"the specific IQ1_XXXS branch."* Enum presence is not format
identity. Worse, they state outright: *"Due to naming issues, we used TQ2_0, TQ1_0 and Q1_0 otherwise it
won't pop up in the HF repo"* — i.e. **existing type names reused for new bit layouts**. A stock build that
loads such a file may not fail loudly. Same class as every other name-trust trap in this entry.

### 8.7 ✅ The one thing here with a date and a real fit — **Friday 2026-08-14**

From the guide, verbatim: *"**Qwen3.8-27B** the upcoming 27B parameter model will be released **this
Friday**"* and *"**Qwen3.8-27B will run locally on 16GB+ VRAM/RAM setups**."* Also: *"Qwen3.8 has vision and
thinking capabilities, a 256K context window (up to 1M tokens)"*, and *"Open Qwen3.8 models are
**thinking-only**; Qwen3.8-max is hybrid."*

**Thinking-only matters for us specifically** — it is the fourth model family in six days where reasoning
tokens distort a throughput number (`t_6e058ca2`: pin reasoning or the arm is void). And a **dense 27B is
still ~9× the active params/token of our banked `qwen3-coder:30b` A3B** (86.7 tok/s decode / 3.2 s wall on
the same box). §3.3 stands unchanged.

**No card, per this entry's own §6 rule.** On Friday: header range-read the first 27B GGUF for
`general.architecture` + `nextn_predict_layers`; if it declares a supported arch with an MTP head, **append
to `t_76235b2a`** (Qwen3.6 MTP) as a second confound-free MTP arm. Do not open a third competitor for the
same consumer-paused window on ryan-spark.

### 8.8 Correction to §2's own method

§2 corroborated non-release with: *"the official Qwen org's newest model by `createdAt` is
`Qwen3-ForcedAligner-0.6B-hf` (2026-06-26)."* The flagship's `createdAt` is **2026-08-08 01:50Z** — it
existed, privately, four days before I asserted the org's newest was June.

**The conclusion was right; that leg of the reasoning was not.** Private/gated repos are invisible to the
API, and `createdAt` is repo *creation*, not publication. The **control-tested 401** was the sound part and
it held perfectly. Keep the control; drop org-recency as corroboration.

Also new since §2: `RadixArk/Qwen3.8-2.4T-A95B-DSpark` (created 08-10, 0 dl) — a DSpark drafter variant of
the flagship, i.e. the drafter family from `t_716141c4`. Unrunnable here, noted only so a later sweep
does not treat it as a discovery.
