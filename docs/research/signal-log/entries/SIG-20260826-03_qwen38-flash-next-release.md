# SIG-20260826-03 — Qwen3.8-Flash-Next is out; 360 GB BF16; table vs DS4 is mixed

```yaml
id: SIG-20260826-03
date: 2026-08-26
title: "jun_song clip of ModelScope drop: Qwen3.8-Flash-Next live. Claims better than DS4-Flash-0731 at half size. First-party HF is Qwen4Exp, 131 BF16 shards, ~360 GB. 512 experts / 10 active, ngram_size 3. Vendor SWE-Pro 62.5 vs DS4 56.0 vs our 27B 61.7. Do not pull. Do not evict :8889."
index_title: "Qwen3.8-Flash-Next RELEASED (qwen4_exp, 360GB BF16, Qwen Community License). Vendor SWE-Pro 62.5 vs DS4 56 vs 27B 61.7. DS4 still wins NL2Repo + ALE Pass@1. Steal P1: don't evict Flash, don't pull 360GB. Wait a GB10 quant + header-read."
index_links: [repo]
source_url: "https://x.com/jun_song/status/2092594618118607199"
source_url_2: "https://x.com/ModelScope2022/status/2092590458711232757"
canonical_repo: "https://huggingface.co/Qwen/Qwen3.8-Flash-Next"
canonical_docs: "https://huggingface.co/Qwen/Qwen3.8-Flash-Next"
bucket: models
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim both posts + table OCR; HF API + config.json + 131-shard sum 360.0 GB + LICENSE head. No download.
hardware_fit: [none]      # BF16 360 GB vs Spark 121 GB. FP8/NVFP4/GGUF exist as same-day quants; not header-read.
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260825-03"     # yesterday's countdown — this is the drop
  - "SIG-20260811-04"     # do not reopen Nemotron as 'another Flash'
  - "exl3-k2-spark"       # Kevin :8889 stays
status: open
status_note: "**OPEN — steal P1, no card.** SUPERSEDED-on-fit: Bakeer SIG-20260826-06 shows Q4_K_XL + NVMe mmap **does** run on 1× Spark at **22 tok/s prose**. 97 is copy-file. Do not pull; see 26-06. BF16 360 GB still does not fit."
distill: none
```

## 1. Claim

[@jun_song](https://x.com/jun_song/status/2092594618118607199) (Jun Song / 0xSupergemma; ~42k followers; **201 likes / 10 RTs / 43 bookmarks / 14.7k views** at read; 2026-08-26 12:46 UTC). Quotes @ModelScope2022 drop. Fetched verbatim via `api.fxtwitter.com`:

> Why is it already out?
>
> Qwen3.8-Flash-Next is here.
>
> Much better performance than Deepseek-V4-Flash-0731 with only half of the size.
>
> Black magic.

ModelScope (first-party-adjacent): open-weight multimodal MoE, native **256K** / 1M YaRN; **125B + 51B n-gram, 6B active**; SWE-bench Pro **62.5 vs 53.4 Claude-Opus-4.6 Max**; 7.6× prefill / 4.9× decode kernel claim at 1M.

He is a **megaphone**. Artifact is `Qwen/Qwen3.8-Flash-Next`.

## 2. What we verified

| Check | Result |
|---|---|
| Posts | **verbatim** via fxtwitter; vendor table OCR'd |
| HF | `Qwen/Qwen3.8-Flash-Next` live **2026-08-26 12:29Z**, ★3,152, **2,551 dl**, `model_type: qwen4_exp`, architecture `Qwen4ExpForConditionalGeneration`, **not gated** |
| Weights | **131** `*.safetensors`, sum **360.0 GB** BF16. `dtype: bfloat16`. **Does not fit** a 121 GB Spark |
| Config | 48 layers · **512 experts / 10 per tok** · hidden 2560 · `max_position_embeddings` **262144** · `ngram_size: 3` · `ngram_vocab_size_base: 20000000` · MTP hybrid 1 layer · vision on |
| License | **Qwen Community License 1.0** (`license:other`) — not Apache-2.0 (unlike 27B) |
| Same-day quants | first-party `Qwen/Qwen3.8-Flash-Next-FP8`; `RadixArk/…-NVFP4`; `unsloth/…-GGUF` (**0 downloads**, created 12:29Z). None header-read |
| Yesterday | SIG-20260825-03 was a countdown with **0 artifacts**. That is now stale |

**Vendor table (OCR, first-party graphic). Bold = row winner among the five:**

| Bench | Flash-Next | Qwen3.8-27B | Qwen3.7-Plus | **DS4-0731** | Opus-4.6 Max |
|---|---:|---:|---:|---:|---:|
| DeepSWE 1.1 | **58.7** | 42.2 | 16.5 | 54.4 | — |
| SWE-bench Pro | **62.5** | 61.7 | 55.8 | 56.0 | 53.4 |
| SWE-bench Multilingual | **81.0** | 73.8 | 75.8 | — | 77.5 |
| NL2Repo-Bench | 48.1 | 42.3 | 41.1 | **54.2** | 47.6 |
| CoWorkBench | **73.9** | 70.7 | 65.1 | 45.1 | 68.2 |
| JobBench | **55.7** | 33.4 | 27.6 | 41.3 | 36.6 |
| ALE Pass@1 / Score | 24.3 / **51.2** | 20.4 / 42.9 | 13.2 / 33.6 | **25.2** / — | — |
| Toolathlon Verified | **73.5** | 67.1 | 50.6 | 70.3 | — |
| IFBench | **81.3** | 79.5 | 79.1 | 79.2 | 62.5 |
| GPQA Diamond | **91.7** | 89.2 | 90.3 | 90.8 | 91.3 |
| HLE | 35.9 | 30.8 | 34.7 | 33.8 | **40.0** |
| LiveCodeBench v6 | **91.9** | 90.3 | 89.6 | 90.6 | 88.8 |

“Much better than DS4 at half size” is **false as a blanket**. DS4 still wins **NL2Repo** and **ALE Pass@1**. SWE-Pro 62.5 vs leftover **27B 61.7 is 0.8**. CoWork/Job is where FN pulls away; DeepSWE FN only +4.3 on DS4.

“Half size” is 125B vs 284B **total params**, and ignores the **51B n-gram table**. BF16 residency is **360 GB**, not half of Flash.

Kernel 7.6× / 4.9× is **attention kernels at 1M**, not a Spark tok/s row. No batch, no engine, no C1.

## 3. Takeaways (max 5)

- **Release is real.** Countdown (SIG-20260825-03) is done. Cite this entry.
- **360 GB BF16 does not fit either Spark.** “Fits one Spark” was a Q4 guess with the n-gram unpriced.
- **Do not evict Kevin `:8889`.** Vendor table is mixed; DS4 still owns repo-level codegen.
- **Do not pull Unsloth GGUF today.** 0 downloads, same minute as the drop.
- **27B already captures almost all of SWE-Pro.** If the ask is “coding bench vs Flash,” leftover `:11435` is the cheap arm, not a 360 GB new arch (`qwen4_exp` — no llama.cpp/Ollama until a GGUF with that arch exists).

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Do not displace a measured Flash lane for a vendor table that our 27B nearly ties on the headline cell** | Leave `:8889` EXL3-K2. If a first-party GB10 quant appears: **header-range-read** (`general.architecture`, n-gram tensors, file GB) then decide. No overnight pull | **P1** | open — no card |
| S2 | `qwen4_exp` is a new arch (GDN + n-gram + MTP). GGUF/Ollama will lag | Do not assume `ollama pull` works. Same class as Glimmer needing a llama.cpp commit | P2 | log only |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not download the 131-shard BF16.** 360 GB.
- **Do not `ollama pull` Unsloth/vcruz305.**
- **Do not evict Flash or 120b.**
- **Do not quote 62.5 vs Opus 53.4 as if DS4 were 53.** DS4 is **56.0** on that row; 27B is **61.7**.
- **Do not quote 7.6× prefill as fleet tok/s.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md row
- [x] SIG-20260825-03 pointed forward
- [ ] no card
- [ ] no pull

## 7. Chat blurb

`SIG-20260826-03` · `models` · **steal P1** · Flash-Next is **out**. 360 GB BF16, new `qwen4_exp` arch. Vendor SWE-Pro 62.5 vs DS4 56 vs **our 27B 61.7**. DS4 still wins NL2Repo. Do not pull. Do not evict `:8889`.
