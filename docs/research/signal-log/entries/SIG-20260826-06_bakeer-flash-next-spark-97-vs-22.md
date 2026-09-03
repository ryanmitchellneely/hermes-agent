# SIG-20260826-06 — Bakeer Flash-Next on Spark: 97 is copy-edit, prose is 22

```yaml
id: SIG-20260826-06
date: 2026-08-26
title: "0xBakeer: Qwen3.8-Flash-Next on 1× Spark. Tweet 97 tok/s is 'reproduce a given file with one change' (94.7% ngram accept). Prose control is 22.1 / 5.8% accept. Q4_K_XL 103.7 GiB, 51B n-gram mmap'd from NVMe. llama.cpp unmerged PR #27742. Do not evict Flash. Do not merge that PR."
index_title: "Bakeer Flash-Next Spark — 97.4 is copy-one-change (94.7% accept); prose 22.1. Same 75-class as SIG-20260816-02. NVMe mmap of 51B n-gram fits 180B in 128GB. Steal P1: don't quote 97. Don't pull 104 GB / PR 27742. Leave :8889."
index_links: [repo]
source_url: "https://x.com/0xBakeer/status/2092709567503229015"
source_url_2: "https://x.com/0xBakeer/status/2092673033559286049"
canonical_repo: "https://github.com/0xBakeer/qwen38-flash-next-spark"
canonical_docs: "https://github.com/0xBakeer/qwen38-flash-next-spark#measured-results"
bucket: inference
posture: steal
steal_rank: P1
confidence: high          # fxtwitter both posts + table OCR; GH API + README measured table. No clone, no PR merge, no pull.
hardware_fit: [spark]
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260826-03"     # release / 360GB BF16 / don't pull
  - "SIG-20260816-02"     # Bakeer's last 75 tok/s was synthetic edit
  - "exl3-k2-spark"
status: open
status_note: "**OPEN — steal P1, no card.** Hardware pre-filter N/A (NVMe mmap of a lookup table, not PCIe KV-offload). 97 is ngram copy-span. Named row is 22 tok/s. Do not evict :8889 (C1 54.8). Do not build llama.cpp #27742 on the fleet."
distill: none
```

## 1. Claim

[@0xBakeer](https://x.com/0xBakeer/status/2092709567503229015) (~846 followers; **152 likes / 15 RTs / 142 bookmarks / 12.5k views** at read; 2026-08-26 20:23 UTC). Quotes his own day-one run. Fetched verbatim via `api.fxtwitter.com`:

> Qwen3.8-Flash-Next on a single DGX Spark: up to 97 tok/s.
>
> 180B params in 128GB with the full 262k context, because 51B of them are an n-gram table that can sit on NVMe instead of in RAM.
>
> The 97 is editing a file you pasted in, where ngram speculation accepts 60-token spans. **Prose is 22.**

Earlier same day: Unsloth Q4_K_XL, llama.cpp **unmerged PR**, ~22 decode, ~500–660 prefill, 1–3 major faults/token, decode −13% from 226→19k prompt tokens.

**He named the 97.** Same author as SIG-20260816-02 (75 tok/s “edit”).

## 2. What we verified

| Check | Result |
|---|---|
| Both posts | **verbatim** via fxtwitter; table OCR'd |
| Repo | `0xBakeer/qwen38-flash-next-spark` — **★19 / MIT**, created **2026-08-26 19:21Z**. Recipe + patches, not weights |
| Weights | `unsloth/Qwen3.8-Flash-Next-GGUF` **UD-Q4_K_XL**, 4 shards, **103.7 GiB** |
| Engine | llama.cpp + unmerged [PR #27742](https://github.com/ggml-org/llama.cpp/pull/27742) (`qwen4exp`) + two local patches |
| Fit trick | `-ot "per_layer_token_embd=CPU" -lm mmap` — 51.2B `per_layer_token_embd.weight` `[160, 320001536]` lookup-only. File 103.7 GiB, **~76.9 GiB resident**, RSS ~1.4 GiB |
| Hardware pre-filter | **N/A / pass.** Not a PCIe host↔device KV-offload win. NVMe mmap of a gather table into Spark’s coherent pool. Still a GB10-valid residency trick — **not** a reason to copy the PR |
| Local run | **Not run** |

**His own table (tweet image):**

| Task | tok/s | ngram accept |
|---|---:|---:|
| Reproduce a given file with one change | **97.4** | 94.7% |
| Targeted bug fix | 68.6 | 81.4% |
| Add a function | 31.4 | 56.9% |
| **Free-form prose (control)** | **22.1** | **5.8%** |

README decode vs ctx (speculation off / server timings): 22.34 @ 226 tok → **19.50 @ 19k**. Prefill 355–662. KV **24 KB/token** → 262k ≈ **6 GiB**.

**Vs our live lanes (not this stack):** leftover 27B Ollama **31.7 wall**; Flash C1 **54.8–55.8** @ 256k/0.85. Flash-Next prose **22** loses both.

## 3. Takeaways (max 5)

- **97 is copy-span ngram, and he said so.** Same class as his 75 tok/s edit (SIG-20260816-02). Quote 22.1 or nothing.
- **It does run on one Spark.** Tech2Wild “should fit” is no longer a guess — Q4_K_XL + mmap, ~77 GiB resident. That does **not** make it a Flash replacement.
- **Do not merge llama.cpp #27742 onto the fleet** for a 22 tok/s lane.
- **NVMe mmap of a lookup table is the only reusable pattern** if `qwen4_exp` ever lands in a distro build. Not a pull today.
- **Unsloth GGUF is now a real file (103.7 GiB),** not the 0-dl trap from this morning. Still don’t overnight-pull it.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **A tok/s number with 90%+ ngram accept on “reproduce this file” is not decode** | Leave `:8889`. If a first-party `qwen4exp` GGUF is ever benched here, the control row is **prose / accept ~5%**, not copy-file | **P1** | open — no card |
| S2 | Pin a gather-only tensor to CPU mmap (`-ot …=CPU -lm mmap`) | Citation-only until llama.cpp in-tree supports `qwen4exp` | P2 | log only |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 97 tok/s.**
- **Do not `git clone` + `./run.sh`** (unmerged PR + 104 GB + patches).
- **Do not evict Flash or 120b.**
- **Do not treat RSS 1.4 GiB as model size.** (We already know this on Spark; README even says it.)
- **Do not pull Unsloth overnight** just because the file is real now.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md row
- [ ] no card
- [ ] no pull / no PR

## 7. Chat blurb

`SIG-20260826-06` · `inference` · **steal P1** · Bakeer: Flash-Next **does** run on 1× Spark. **97.4 is copy-file (94.7% accept). Prose is 22.1.** Don’t quote 97. Don’t evict `:8889`. Don’t merge llama.cpp #27742.
