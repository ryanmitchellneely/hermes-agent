# SIG-20260902-01 — 200 tok/s is 8-wide aggregate on uncensored 27B. Not C1.

```yaml
id: SIG-20260902-01
date: 2026-09-02
title: "u1tra_instinct LFG 200 toks/sec — quotes SpaceTimeViking AEON Qwen3.8-27B-ULTIMATE-UNCENSORED-NVFP4 on 1× Spark. Card: AGGREGATE 213 tok/s, 8 active streams, peak 222, prefill 0. ~27/stream. Steal P2 fold 25-02/28-14. Don't quote 200. Don't evict :8889. Leftover 27B stays Ollama :11435 31.7. Don't pull uncensored."
index_title: "AEON 27B NVFP4 213 tok/s aggregate @ 8 streams (~27/stream). u1tra LFG. Fold 25-02. Don't quote 200. Don't pull uncensored. :11435 stays."
index_links: []
source_url: "https://x.com/u1tra_instinct/status/2094982743884988485"
source_url_2: "https://x.com/SpaceTimeViking/status/2094981702078611831"
canonical_repo: "https://huggingface.co/sakamakismile/Qwen3.8-27B-AEON-ULTIMATE-UNCENSORED-NVFP4"
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter + live-bench OCR (213 agg / 8 streams). No pull.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260825-02"     # MiaAI 27B DSpark — same leftover lane
  - "SIG-20260828-14"     # filicroval 57.11 whole-request DFlash2 27B
  - "SIG-20260828-13"     # jaita 59 = 3×19 Flash-Next aggregate
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A (GB10). 200 is 8-wide aggregate. Per-stream ~27 < leftover Ollama 31.7 N=1. Don't quote 200. Don't pull AEON uncensored. Don't evict :8889."
distill: none
```

## 1. Claim

[@u1tra_instinct](https://x.com/u1tra_instinct/status/2094982743884988485) (keys / drowzeys; ~3k fol; **45 likes / 3.3k views** at read; 2026-09-02 02:56 UTC):

> YES!!!!! LFG!!!!!!! 200 toks/sec unlock that concurrency

Quotes [@SpaceTimeViking](https://x.com/SpaceTimeViking/status/2094981702078611831) (ÆON FORGE):

> Qwen3.8-27B-AEON-ULTIMATE-UNCENSORED-NVFP4 … SINGLE DGX … well over 200 tok/s **c=8**

keys is a **megaphone**. Artifact is AEON 27B NVFP4 live bench.

## 2. What we verified

| Check | Result |
|---|---|
| Card OCR | Live bench: **AGGREGATE THROUGHPUT 213 TOK/S**. Active streams **8**. Peak **222**. Prefill tok/s **0**. GPU 94%. Unified mem **90.8 / 121.7 GB**. 8 math-reasoning panes. mean 100.0 on 4/174 (math only) |
| Per-stream | 213/8 ≈ **26.6 tok/s** |
| Weights | HF `sakamakismile/Qwen3.8-27B-AEON-ULTIMATE-UNCENSORED-NVFP4` (and AEON-7 BF16). **Uncensored** in the name |
| Hardware pre-filter | **N/A / pass** (GB10, not PCIe) |
| Duplicate URL | None. Slogan-class = jaita 59 agg / filicroval 57 whole-request |

Leftover 27B on this fleet: Ollama Q4_K_M **31.7 wall N=1** on `:11435`. 8-wide 27 tok/s is **not** a reason to swap.

## 3. Takeaways (max 5)

- **200 is aggregate at c=8.** Skill rule: throughput with no N=1 cell is unreadable. They named N=8. N=1 is ~27.
- **Don’t quote 200 next to C1 54.8.** Different model (27B vs Flash), different clock (8-wide vs single).
- **Uncensored is not a desk default.** Don’t pull AEON onto T1000/Pulp.
- **Don’t evict `:8889`.** Flash lane unchanged.
- **Concurrency slogan ≠ leftover upgrade.** `:11435` stays.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Name N when quoting tok/s.** 200 @ c=8 ≈ 27/stream | Fold 25-02 / 28-14. Don’t quote 200. Don’t `huggingface-cli download` AEON | **P2** | fold |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 200 / 213 / 222.**
- **Do not evict Kevin `:8889`.**
- **Do not pull AEON uncensored onto leftover Spark.**
- **Do not `./serve.sh` DFlash2** (25-02 hard-reboot class).
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260902-01` · `inference` · **steal P2** · 200 tok/s is **8-wide aggregate** (~27/stream) on AEON uncensored 27B. Don’t quote 200. Leftover stays `:11435`. Don’t pull.
