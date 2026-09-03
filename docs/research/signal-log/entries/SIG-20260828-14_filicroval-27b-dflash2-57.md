# SIG-20260828-14 — Bakeer “57.1 must try” is filicroval 27B DFlash2, not Flash C1

```yaml
id: SIG-20260828-14
date: 2026-08-28
title: "Bakeer quotes filicroval: Qwen3.8-27B NVFP4 + DFlash2 on 1× Spark, SGLang. 12.34 → 57.11 whole-request tok/s (4.63×). Honest: prefill+TTFT included, not decode. 24/27 quality, 15/27 byte-identical. Fold MiaAI 25-02. Don't quote 57. Don't evict :8889. Leftover 27B stays Ollama :11435."
index_title: "filicroval 27B DFlash2 57.11 whole-request (12.34 no-spec). Bakeer 'must try'. Fold 25-02. Don't quote 57. Don't ./serve.sh. Leftover 27B stays :11435."
index_links: [repo]
source_url: "https://x.com/0xBakeer/status/2093358295868157983"
source_url_2: "https://x.com/filicroval/status/2093347044442202119"
canonical_repo: "https://github.com/sxuff/qwen38-27b-nvfp4-dflash2-dgx-spark"
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter + card OCR + GH README. ★6 MIT, created today. No docker, no pull.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260825-02"     # MiaAI 27B DSpark/DFlash2 — this is stock NVFP4 + whole-request clock
  - "SIG-20260828-13"     # jaita 59 is *different* 57 (Flash-Next 3-lane aggregate)
  - "SIG-20260826-06"     # Bakeer Flash-Next 97 — different model
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. 57.11 is 27B DFlash2 whole-request, not Flash C1. Don't quote it. Don't start DFlash2 on leftover :11435. Fold 25-02."
distill: none
```

## 1. Claim

[@0xBakeer](https://x.com/0xBakeer/status/2093358295868157983) (~1.1k fol; **37 likes / 2 RTs / 24 bookmarks / 3.0k views** at read; 2026-08-28 15:21 UTC):

> Wow! 57.1 tok/s is very interesting and must try

Quotes [@filicroval](https://x.com/filicroval/status/2093347044442202119) (~154k fol): **Qwen3.8-27B** stock NVFP4 + **DFlash2**, SGLang, one Spark. 12.34 → **57.11** whole-request, 4.63×, 10 concurrent validated.

Bakeer is a **megaphone**. Artifact is `sxuff/qwen38-27b-nvfp4-dflash2-dgx-spark`.

**Not Flash-Next.** Not jaita’s 57 aggregate. Not C1.

## 2. What we verified

| Check | Result |
|---|---|
| Card OCR | Median **whole-request** 12.3 → 57.1 (4.63×). Quality 24/27 (3 prose fails = checker artifact). Payloads 27/27. Swap 0 B. MemAvailable 29.7 / 27.6 GiB |
| README | Target `RadixArk/Qwen3.8-27B-NVFP4`. Draft `z-lab/Qwen3.8-27B-DFlash2`. Accept **3.95 tok / 42.14%**. Byte-identical **15/27**. ctx alloc 262k. mem fraction **0.70**. 10-wide smoke **146 agg tok/s** on one synthetic prompt — not the paired study |
| Repo | ★**6** MIT, created **today**. Scripts + manifests, not weights |
| Hardware pre-filter | **N/A / pass** (GB10) |
| Duplicate URL | None. Subject-class = MiaAI **25-02** (same 27B / DFlash2 family; different clock + packed NVFP4 vs BF16 lm_head) |

They **name the clock**: completion tokens ÷ whole-request wall, prefill + TTFT in. Good. Still not our leftover 27B (Ollama Q4_K_M **31.7** wall on `:11435`).

## 3. Takeaways (max 5)

- **57.11 ≠ Flash C1 54.8.** Different model (27B), different engine (SGLang+DFlash2), different clock (whole-request).
- **57.11 ≠ jaita 57.** That one is Flash-Next 3×19 ngram-mod aggregate (28-13).
- **Baseline 12.34 no-spec** is the honest N=1-ish cell. 4.63× is spec-dec on *this* stack.
- **Don’t `./serve.sh`.** 25-02 already: DFlash2 first boot builds an image, hard-reboot history. mem-frac 0.70, not 0.90.
- **Leftover 27B stays Ollama `:11435`.** No overnight NVFP4+draft pull.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Whole-request tok/s ≠ decode.** 57.11 includes prefill+TTFT; 146 agg is 10-wide smoke | Fold 25-02: don’t quote 57 / 146. Don’t start DFlash2 on `:11435`. Leave `:8889` | **P2** | fold into SIG-20260825-02 |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 57.1 / 4.63× / 146.**
- **Do not evict Kevin `:8889`.**
- **Do not `./scripts/serve.sh` / docker pull `lmsysorg/sglang` onto leftover Spark.**
- **Do not treat 15/27 byte-identical as quality parity.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card
- [ ] 25-02 related_plans += this ID

## 7. Chat blurb

`SIG-20260828-14` · `inference` · **steal P2** · Bakeer’s 57.1 is **filicroval 27B DFlash2 whole-request** (12.34 no-spec). Not Flash. Not C1. Don’t quote it. Leftover 27B stays `:11435`.
