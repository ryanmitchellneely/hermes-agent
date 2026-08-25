# SIG-20260819-01 — Ornith-1.5 397B MoE (author benches vs Opus 4.8). Q4 ~241GB. Not a 2-Spark closer. 35B-A3B is the only 1-box sibling.

```yaml
id: SIG-20260819-01
date: 2026-08-19
title: "TeksEdge + ornith_: Ornith-1.5 family (9B dense / 35B-A3B MoE / 397B MoE), MIT, self-improvement loop (invent task → harness → rollout → RL → harder task). Author: 397B TB2.1 86.1 / SWE-Verified 86.0 / BrowseComp 86.6 vs Opus 4.8 85.0 / 85.8 / 84.3; beats GLM-5.2 and DS4 Flash-0731 on those. Q4 GGUF ~241GB. Official NVFP4/FP8/GGUF/MLX. HF collection ornith-ai/ornith-15."
index_title: "Ornith-1.5 397B author benches (TB2.1 86.1). Q4 ~241GB = no KV on 2×121G. 35B-A3B is the 1-Spark sibling. Watch — 0 dl day-of. Don't pull."
source_url: "https://x.com/TeksEdge/status/2090096376390844668"
source_url_2: "https://x.com/ornith_/status/2090074077084127302"
canonical_repo: "https://huggingface.co/collections/ornith-ai/ornith-15"
canonical_docs: "https://ornith.ai/ornith_1_5.html"
index_links: [repo, docs]
bucket: models
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260809-01"
  - "local-inference-fleet"
  - "residency-matrix"
status: open
status_note: "**OPEN — author suite, 0 HF downloads.** Collection 12 items live 2026-08-19. Sibling file sizes not in HF API (LFS?). Q4 241GB is tweet, not weighed. Hardware pre-filter N/A. 241G + KV does not fit 2×121G. No pull. Ornith-1.0 was unidentifiable on SIG-09-01; 1.5 has real HF."
distill: none
```

## 1. Claim

[@TeksEdge](https://x.com/TeksEdge/status/2090096376390844668) (9.7k fol; 156 likes / 93 bookmarks / 14k views) quoting [@ornith_](https://x.com/ornith_/status/2090074077084127302):

397B MoE MIT. Self-improvement loop. Author: beats GLM-5.2 and DS4 Flash-0731 on the listed benches. Competitive with Opus 4.8. Q4 GGUF **~241GB**. Weights now.

## 2. What we verified

| Check | Result |
|---|---|
| Blog | [ornith.ai/ornith_1_5.html](https://ornith.ai/ornith_1_5.html) Aug 2026. Same numbers. 397B TB2.1 **86.1** vs Opus 4.8 **85.0** / GLM-5.2 **82.7** / Flash-0731 **82.7**. DeepSWE 56 vs Opus 59 |
| 35B-A3B (author) | TB2.1 **68.5** / SWE-V **79.0** vs Qwen3.6-35B / Gemma4-31B / Muse-30B |
| 9B (author) | TB2.1 **47.0** / SWE-V **70.6**. Mobile SKU claimed |
| HF | Collection **12** models, lastUpdated today. Likes 3–69. **downloads 0** |
| Sizes | HF API `size=0` this turn. **241GB is the tweet**, not a `safetensors` sum |
| Hardware pre-filter | **N/A** |
| 2× Spark math | 2×121 = **242G**. 241G Q4 leaves **no KV**. Same fail class as GLM-on-2 |

## 3. Takeaways (max 5)

- **397B is not the Ryan 2-box closer.** Even if 241G is exact, it is a weights-only squeeze.
- GLM on 2 Sparks stays no. This is the same shape with a new name.
- **35B-A3B** is the only sibling that could sit on one Spark next to 120b/27B — **author benches, 0 dl, don’t pull tonight.**
- Self-improvement loop is a **train** story, not a desk install.
- Author vs Opus 4.8 = same class as AEON God Mode until an independent board (Tech2Wild / our gym).

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **35B-A3B as a later 1-Spark foil**, not 397B | If we ever add a third Spark name next to Qwen3.8-27B, score 35B-A3B NVFP4 on the same N=1 battery. **No card** | **P2** | watch |

**Primary steal:** S1 (not P1)

## 5. Do not

- `huggingface-cli download` 397B GGUF/NVFP4/FP8 onto any Spark.
- Treat 241GB as “fits the cable.”
- Swap 120b or 27B because TB2.1 said 86.1.
- Quote “beats Flash / GLM” as our worker verdict.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260819-01** · models · **watch P2** · high
Ornith-1.5 397B: author 86.1 TB2.1. Q4 **~241GB**.
**Does not fit 2×121G with KV.** 35B-A3B is the 1-box sibling. **Don’t pull.**
