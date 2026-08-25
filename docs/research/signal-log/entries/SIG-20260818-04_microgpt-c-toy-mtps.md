# SIG-20260818-04 — microGPT-C: 4,192-param name generator at 10.1M tok/s on M5 Pro. Toy, not a 27B foil.

```yaml
id: SIG-20260818-04
date: 2026-08-18
title: "TheVixhal: implemented Karpathy microgpt from scratch in pure C. 6.9M tok/s Ryzen 5 5600H; 10.1M tok/s Apple M5 Pro. AVX2/NEON, column-major weights, prefix table, Schraudolph exp. Repo vixhal-baraiya/microgpt-c. README: 4192 parameters, character-level names, one C file + libc."
index_title: "microGPT-C 10.1M tok/s = 4k-param name toy, not 27B. Watch — do not compare to Spark/MTPLX. Don't clone onto desk."
source_url: "https://x.com/TheVixhal/status/2089311296391115020"
canonical_repo: "https://github.com/vixhal-baraiya/microgpt-c"
canonical_docs: ""
index_links: [repo]
bucket: inference
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "local-inference-fleet"
status: open
status_note: "**OPEN — toy.** README fetched: 4192 params, char-level names, MIT ★649. 10.1M tok/s is that model on M5 Pro, not Qwen 27B. Hardware pre-filter N/A. Don't quote next to 31.7 / 51.5."
distill: none
```

## 1. Claim

[@TheVixhal](https://x.com/TheVixhal/status/2089311296391115020) (22.8k fol; 623 likes / 40 RT / 551 bookmarks / 24k views):

Karpathy microgpt in pure C. **6.9M tok/s** Ryzen 5 5600H · **10.1M tok/s** M5 Pro. AVX2 + NEON, column-major, prefix table, Schraudolph exp.

https://github.com/vixhal-baraiya/microgpt-c

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `vixhal-baraiya/microgpt-c` MIT ★**649** / created 2026-02-14 / pushed 08-17 |
| Size | **4,192 parameters.** Character-level names (~32k). One C file + libc |
| README sample | `c fp32+NEON 10,168,430 tok/sec` after generating 10 names |
| Hardware pre-filter | **N/A** (CPU toy, not PCIe-offload) |

## 3. Takeaways (max 5)

- **10.1M ≠ 27B.** Four thousand params vs 27 billion.
- Do not put this next to MiaAI 51.5 / our Spark 31.7 / M5 MTPLX 73.
- Fine as a kernels curiosity. Not a fleet lane.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | None for the desk | Log only | **P2** | watch |

**Primary steal:** S1 (none)

## 5. Do not

- Clone onto `~/.t1000` or Spark.
- Quote 10.1M tok/s in a 27B / Flash / 120b sentence.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS row, no card**

## 7. Chat blurb

**SIG-20260818-04** · inference · **watch P2**
microGPT-C: **4,192 params**, 10.1M tok/s on M5 Pro. Name toy.
**Not a 27B number.**
