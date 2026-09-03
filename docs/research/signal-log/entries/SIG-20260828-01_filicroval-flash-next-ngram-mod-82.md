# SIG-20260828-01 — filicroval 82.6 is copy-Python; novel code is 0.99×

```yaml
id: SIG-20260828-01
date: 2026-08-28
title: "filicroval (GX10/Spark): Qwen3.8-Flash-Next UD-Q3_K_XL ngram-mod 27.3 → 82.6 tok/s. Card names the mix: Copy Python 3.80× / 98% accept; novel code (control) 0.99× / none drafted. Tweet '3x' and 'efficient for agentic work' is the copy cell. Same class as Bakeer 97. Steal P2. Don't evict Flash."
index_title: "filicroval Flash-Next ngram-mod 82.6 — Copy Python 98% accept; novel-code control 0.99×. Spec-off is 27.3. Corroborates Bakeer SIG-20260826-06. Steal P2. Don't quote 82.6. Don't evict :8889."
index_links: [repo]
source_url: "https://x.com/filicroval/status/2092966320551653787"
source_url_2: "https://x.com/filicroval/status/2092698625226785200"
canonical_repo: "https://github.com/sxuff/qwen38-flash-next-dgx-spark"
canonical_docs: "https://github.com/sxuff/qwen38-flash-next-dgx-spark"
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter both posts + card OCR. GH ★1 MIT. No clone.
hardware_fit: [spark]
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260826-06"     # Bakeer 97 vs 22 — same ngram-mod class
  - "SIG-20260826-03"
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. 82.6 is 4-case aggregate; novel code gets no draft. Don't quote 3×. Don't evict :8889."
distill: none
```

## 1. Claim

[@filicroval](https://x.com/filicroval/status/2092966320551653787) (filipe; ~153k followers; GX10 bench account; **29 likes / 2 RTs / 34 bookmarks / 3.9k views** at read; 2026-08-27 13:23 UTC). Quotes own Q3 add. Fetched verbatim via `api.fxtwitter.com`:

> … now decodes at 82.6 tok/s instead of 27.3, that's a 3x speedup.
> vision is also enabled.
> the recipe now uses llama.cpp's ngram-mod draftless speculation. very efficient for agentic work

## 2. What we verified

| Check | Result |
|---|---|
| Posts | **verbatim**; card OCR'd |
| Repo | `sxuff/qwen38-flash-next-dgx-spark` — **★1 MIT**, Spark **or** Ascent GX10. Created 08-26 |
| Card protocol | UD-Q3_K_XL · llama.cpp · single 64k slot · temp 0 · seed 42 · thinking **off** · one four-case sweep, 3,496 completion tokens |
| Hardware pre-filter | **N/A / pass** |
| Local run | **Not run** |

**Named cells (his card):**

| Case | Out toks | Speedup | Drafts accepted |
|---|---:|---:|---:|
| Copy Python | 1,189 | **3.80×** | **98%** |
| Copy JSON | 1,552 | 2.64× | 60% |
| Structured transform | 520 | 1.94× | 52% |
| **Novel code (control)** | 235 | **0.99×** | **none drafted** |

Headline **82.6** = ngram-mod **on**, server-reported, **2.49× aggregate** of those four. **27.3** = speculation **off**. Footer: “Gains scale with how much of the output repeats the input; **novel text gets no speedup.** Not a broad benchmark.”

Prior post (Q3, no ngram-mod): 27.7 @ 512-in / 20.3 @ 32k-in.

Same class as Bakeer SIG-20260826-06 (97.4 copy-file / 22.1 prose).

## 3. Takeaways (max 5)

- **He published the control.** Novel code 0.99×. “Efficient for agentic work” is the copy-Python cell (98% accept).
- **82.6 is not C1.** Aggregate of 4 cases, copy-heavy, think-off.
- **Spec-off ~27 tok/s** still loses to leftover 27B (31.7 wall) and Flash C1 (~55).
- **Don't merge a second llama.cpp Flash-Next recipe** (Bakeer already has PR #27742).
- **Vision 904 MB F16 projector** is a footnote, not a reason to pull.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **ngram-mod speedup is copy-span; novel-code row must be on the card** | Already the Bakeer P1. This is the corroborating named control. No second STEALS row | **P2** | fold into SIG-20260826-06 |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 82.6 or 3×.**
- **Do not evict `:8889`.**
- **Do not `./run.sh` this recipe.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2; Bakeer row covers it)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-01` · `inference` · **steal P2** · filicroval 82.6 is **copy-Python ngram-mod** (98% accept). Novel-code control **0.99×**. Spec-off is 27.3. Same as Bakeer 97 vs 22. Don't quote 82.6.
