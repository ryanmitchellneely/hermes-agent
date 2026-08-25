# SIG-20260814-04 — Tech2Wild tool-call board: Qwen3.8-27B dense #1 over MiMo 230B / GLM-5.2 / DS4 Flash / Kimi K2 (69 scenarios)

```yaml
id: SIG-20260814-04
date: 2026-08-14
title: "Tech2Wild: full local tool-calling benchmark — 138 points, 69 scenarios, same harness. #1 = Qwen3.8-27B dense (vLLM MTP3, AutoRound W4A16, 2× RTX 3090): Quality 97.1 / Deploy 97.5 / 66✅ 2⚠ 1❌ — beats MiMo-V2.5 Omni 230B-class (2nd, 3 Sparks NVFP4), GLM-5.2 744B-class rows, DeepSeek V4 Flash DSpark, Kimi K2. Live board 2wild-model-eval.pages.dev. Thesis: smallest on the board, top of the board. Our DS4 Flash rows sit ~8–15. Qwen3.8 NVFP4 on 1 Spark is only #16 (decode ~11 t/s)."
index_title: "Tech2Wild tool-call LB: Qwen3.8-27B dense #1 (2×3090 W4A16 MTP3) over multi-Spark MoEs + DS4 Flash. Steal = tool-call scoreboard ≠ param count; pin Qwen3.8 as candidate local tool/code worker when weights stable. Not auto-promote over Flash/120b."
source_url: "https://x.com/Tech2Wild/status/2088387064748265570"
canonical_repo: ""
canonical_docs: "https://2wild-model-eval.pages.dev/"
index_links: [docs]
bucket: models
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark, mbp, caden]
stacks_touched: [t1000]
related_plans:
  - "flash-lane-doctrine"
  - "B17"
  - "SIG-20260812-02"   # Qwen3.8 placeholder wave
  - "SIG-20260813-05"   # Tech2Wild + dsh
  - "agent-harness-compare"
status: open
status_note: "**OPEN — third-party leaderboard, high confidence on scrape.** Board fetched live 2026-08-14 (showing 34 of 52). Tweet low engagement (8 likes) but board is structured and multi-model. Hardware pre-filter: win is not PCIe-offload fiction; top row is 2×3090 not our GB10 — still transferable as *ranking shape*. Do not install unreleased weights without HF id pin."
distill: none
```

## 1. Claim

[@Tech2Wild](https://x.com/Tech2Wild/status/2088387064748265570) (8 likes / ~156 views — early):

> Full tool-calling benchmark across the local fleet. **138 points, 69 scenarios**, every model same way.  
> **#1 = 27B dense Qwen3.8-27B** — topped MiMo 230B, GLM-5.2 744B, DeepSeek V4 Flash, Kimi K2 1T.  
> Two RTX 3090s, zero API cost. *Smallest model on the board. Top of the board.*

Board: https://2wild-model-eval.pages.dev/

## 2. What we verified

Live board scrape (2026-08-14, “showing 34 of 52”):

| Rank | Model | Runtime / quant | Cluster | Deploy. | ✅/⚠/❌ | Decode (two cols) |
|---:|---|---|---|---:|---|---:|
| **1** | **Qwen3.8-27B** | vLLM (MTP3) · AutoRound **W4A16** | **2× 3090** | **97.5** | **66/2/1** | 77.8 / 60.2 |
| 2 | MiMo-V2.5 Omni TP=3 (think off) | vLLM · NVFP4 | 3 Sparks | 97.4 | 66/3/0 | 38.7 / 35.1 |
| 3 | MiMo-V2.5 TP=2 DFlash | vLLM DFlash · NVFP4 | 2 Sparks | 96.9 | 66/3/0 | 30.1 / 25.2 |
| 4 | Qwen3.6-35B-A3B | vLLM · AutoRound INT4 | 2× 3090 | 96.4 | 63/5/1 | **124 / 97** |
| 7 | GLM-5.2 655K MTP | vLLM MTP · Int4-Int8Mix | 4 Sparks | 94.6 | 65/3/1 | 22.9 / 19.1 |
| 8 | **DeepSeek-V4 Flash DSpark** (think off) | vLLM · FP8 | 2 Sparks | 94.2 | 64/2/3 | 43.3 / 35.3 |
| 14–15 | DS4 Flash 0731 / Bluey Lane A | — | — | ~92–91 | 62–60 / … | ~47–48 |
| 16 | Qwen3.8-27B **NVFP4** | vLLM qwen38 | **1 Spark** | 90.7 | 63/4/2 | **11.0 / 10.6** |
| 28 | Kimi K2.7 IQ2_M | llama.cpp | 3 Sparks | 80.9 | 63/3/3 | 10.6 / 9.5 |

- Scenarios: **69** (tweet); pass/warn/fail columns sum to 69 on top rows (66+2+1).
- Hardware pre-filter: **N/A** (not a host↔device offload paper). Top win is **2×3090**, not GB10 — treat ranking as cross-fleet, not our tok/s.
- Related: SIG-20260812-02 flagged Qwen3.8 as unreleased/placeholder risk — this board treats **qwen3.8-27b** as runnable (AutoRound + NVFP4 rows same day).

## 3. Takeaways (max 5)

- **Tool-call quality ≠ parameter count.** 27B dense W4A16 beats multi-Spark giant MoEs on *this* harness.
- **Engine+quant matter as much as weights:** same Qwen3.8 is #1 on 2×3090 MTP3 W4A16 and only **#16** NVFP4 on 1 Spark at ~11 tok/s — don’t promote the name without the stack.
- Our **DS4 Flash** is mid-pack (~top 10–15), not dead — still the right *speed* story on Spark; Qwen3.8 is the *tool-reliability* challenger if weights stay available.
- MiMo/GLM rows show Spark multi-node MoEs can nearly tie on quality but lose the #1 slot and often decode.
- Leaderboard hygiene: same 69 scenarios is the only reason cross-model claims are readable (pairs with our repair-battery doctrine).

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Agent/tool scoreboard over param folklore** — pin a fixed scenario set; rank local candidates including dense mid-size | When refreshing local code/tool worker shortlist, add **Qwen3.8-27B** (W4A16 path) as a named arm beside Flash/120b/qwen3-coder — only after HF id + license pin | **P1** | open |
| S2 | Never cite a model win without **runtime+quant+N-GPU** columns | Already in our bench cards; reinforce when reading 2wild | P2 | doctrine |

**Primary steal:** S1

## 5. Do not

- Yank DS4 Flash as default because of one third-party board.
- Assume 2×3090 W4A16 numbers appear on single GB10 NVFP4.
- Download mystery weights from a pages.dev host without first-party HF/model card.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] optional: one line on flash-lane / model-desk shortlist when next edited — **no card**

## 7. Chat blurb

**SIG-20260814-04** · models · steal **P1** · high  
Tech2Wild tool-call LB: **Qwen3.8-27B dense #1** (2×3090 W4A16 MTP3) over MiMo/GLM/DS4/Kimi.  
**Steal:** tool scoreboard ≠ size; shortlist Qwen3.8 only with stack pinned. DS4 still mid-pack.
