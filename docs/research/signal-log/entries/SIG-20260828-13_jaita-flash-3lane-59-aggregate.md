# SIG-20260828-13 — jaita 59 t/s is 3-lane aggregate. Single lane ~22.

```yaml
id: SIG-20260828-13
date: 2026-08-28
title: "jaita / styles01 sparkrun: Qwen3.8-Flash-Next UD-Q3_K_XL, llama.cpp qwen4exp, 3 lanes × 220k, thinking on. Tweet 59 t/s; recipe ~57 aggregate = 19+19+19. Single lane ~22. Same ngram-mod class as Bakeer 97-vs-22. Steal P2 fold. Don't quote 59. Don't evict :8889. Don't pull 90 GB / PR 27742."
index_title: "jaita Flash-Next 3-lane 59 t/s — 19+19+19 aggregate, single ~22. Q3_K_XL 90GB llama.cpp. Fold Bakeer. Don't quote 59. Don't evict :8889."
index_links: [repo]
source_url: "https://x.com/jaita/status/2093494958636359739"
source_url_2: "https://x.com/jaita/status/2093073757417926686"
canonical_repo: "https://github.com/styles01/sparkrun-recipes"
canonical_docs: "https://github.com/styles01/sparkrun-recipes/blob/main/recipes/qwen3.8-flash-next-q3-3lane.yaml"
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter + card OCR 57 t/s + GH README/yaml. No clone, no pull.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-06"     # Bakeer 97 copy / 22 prose — this is the concurrent-aggregate slogan of the same engine
  - "SIG-20260828-01"     # filicroval 82.6 copy-Python
  - "SIG-20260826-03"     # don't evict measured Flash
  - "SIG-20260828-03"     # paged-KV ceiling ≠ EXL3 reservation
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A (GB10, not PCIe). 59 is 3-wide ngram-mod aggregate. Single lane ~22 = Bakeer prose. Leave Kevin :8889. Do not quote 59. Do not overnight-pull Unsloth Q3 90GB."
distill: none
```

## 1. Claim

[@jaita](https://x.com/jaita/status/2093494958636359739) (James Aita; ~507 fol; Spark recipes; **6 likes / 1 RT / 7 bookmarks / 599 views** at read; 2026-08-29 00:24 UTC). Fetched verbatim via `api.fxtwitter.com`:

> Single Spark owners! Updated Qwen 3.8 Flash recipe: 3 lanes 220 context - 59 t/s peak aggregate - thinking on
> https://github.com/styles01/sparkrun-recipes

Card: **57 t/s · 180B MoE · 3 lanes · 220K context · llama.cpp**. Quotes his own 27 Aug “2 lanes 200k still best / Unsloth Q3_K_XL / builds on Bakeer.”

He is a **recipe author**, not a megaphone. Numbers disagree with themselves (59 tweet vs 57 card vs 19+19+19 yaml).

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `styles01/sparkrun-recipes` **★58**, no license, pushed 2026-08-28. Recipe file `recipes/qwen3.8-flash-next-q3-3lane.yaml` |
| Engine | llama.cpp **qwen4exp** (`ef6876693` + Han slot fix `8b3ed0a40`). `--spec-type ngram-mod`. **Same fork as Bakeer PR #27742** |
| Quant | Unsloth `UD-Q3_K_XL` **90 GB / 3 shards**, whole model in RAM (no NVMe pin). ~114 GB used / ~5 GB headroom on 119 GB |
| Ctx | `--ctx-size 660000 --parallel 3` = **220k per slot**. Lanes 2–3 idle unless concurrent |
| Named cells | README: **~22 tok/s single lane, ~57 aggregate**. YAML: **19+19+19 = ~57**. Tweet **59**. Card **57** |
| Hardware pre-filter | **N/A / pass** (GB10, not a PCIe-offload win) |
| Duplicate URL | None. **Same class as Bakeer 26-06 + filicroval 28-01** |

Throughput win **with batch/concurrency stated**. Good. At N=1 it is **~22**, which is Bakeer’s prose cell, **not** C1 54.8.

## 3. Takeaways (max 5)

- **59 is 3×19.** Peak *aggregate* under concurrent load. Per-stream is Bakeer-prose. Don’t quote 59 as a Spark decode number.
- **ngram-mod still on.** Same 75-class as Bakeer 97 (copy) / 22 (prose). Thinking-on is honest; it does not make aggregate = single-stream.
- **Q3_K_XL 90 GB is a quality cut**, not a reason to evict EXL3-K2 Flash on `:8889`.
- **660k ctx-size is llama.cpp reservation**, not Tech2Wild “ceiling.” EXL3 still preallocates. Don’t load Flash at 660k.
- **Don’t merge #27742 / don’t overnight-pull Unsloth.** Already the Bakeer P1.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Aggregate tok/s with N=3 is not C1** — name the per-lane cell | Already Bakeer: don’t quote 97. This is the concurrent slogan of the same engine. Leave `:8889` 256k @ 0.85 | **P2** | fold into SIG-20260826-06 |

**Primary steal (one only): S1.** No second STEALS row.

## 5. Do not

- **Do not quote 59 / 57 / 3×220k as fleet.**
- **Do not evict Kevin `:8889`.**
- **Do not `huggingface-cli download` the 90 GB Q3.**
- **Do not merge llama.cpp PR #27742.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2; Bakeer row covers it)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-13` · `inference` · **steal P2** · jaita 59 t/s is **3×~19 aggregate** (recipe 57). Single lane **~22** = Bakeer prose. Don’t quote 59. Don’t evict `:8889`.
