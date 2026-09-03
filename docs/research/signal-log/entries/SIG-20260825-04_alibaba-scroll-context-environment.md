# SIG-20260825-04 — Alibaba Scroll: context as a Python kernel + event log

```yaml
id: SIG-20260825-04
date: 2026-08-25
title: "elvis/DAIR promo of Alibaba Scroll (arXiv 2608.21690) — session = append-only Event Log + sandboxed persistent Python kernel. Only printed projections enter the prompt. Qwen3.8-Max: 94.8% LongMemEval_S / 73.1% BEAM_10M / 86.7% LOCA_256K. Pattern-mine; no code drop."
index_title: "Alibaba Scroll (arXiv 2608.21690) — Event Log + Python kernel; only prints enter the prompt. 94.8/73.1/86.7 on Qwen3.8-Max (API flagship, not our 27B). Steal P2: lossless log + projected view. Fold next to OpenViking S1. No install."
index_links: [docs]
source_url: "https://x.com/omarsar0/status/2092274559898755485"
canonical_repo: ""
canonical_docs: "https://arxiv.org/abs/2608.21690"
bucket: harness
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + figure OCR; arXiv abs/api abstract read live. No PDF full-read, no code.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260823-01"     # OpenViking L0/L1/L2
  - "SIG-20260809-03"     # OpenKB compile
  - "t_6c3fd131"          # capability projection
  - "memory-hygiene"
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. Numbers are Qwen3.8-Max (2.4T-class API), not Spark 27B. Do not stand up a model-written-exec memory plane. Fold: event log stays lossless; only a printed projection enters the working view."
distill: none
```

## 1. Claim

[@omarsar0](https://x.com/omarsar0/status/2092274559898755485) (elvis / DAIR.AI; ~315k followers; **92 likes / 13 RTs / 157 bookmarks / 7.2k views** at read; 2026-08-25 15:35 UTC; Typefully + paper figure). Fetched verbatim via `api.fxtwitter.com`:

> Impressive work from Alibaba. … treats agent context management as a programming task.
>
> … append-only event log and a sandboxed, persistent Python kernel.
> Tool outputs, retrieved history, and derived state bind to typed variables across model calls instead of being serialized into the prompt every turn.
> Model-written code searches and transforms that state, and only explicitly printed projections enter the working view.
>
> Results: with Qwen3.8-Max, 94.8% on LongMemEval_S, 73.1% on BEAM_10M (5.1 points over the best published memory system), and 86.7% on LOCA_256K.

Paper: **Context as an Environment: Programmatic Context Management for Long-Horizon Agents** — Yin Lin, Elaine Ang, Erkang Zhu, Bolin Ding, Jingren Zhou (Alibaba). arXiv **2608.21690**, submitted **2026-08-21**. System name: **Scroll**.

He is a **megaphone**.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter; figure OCR matches the abstract |
| Paper | arXiv **2608.21690v1**. Abstract numbers match the tweet exactly. **No official code link** in the abs page |
| Method | Session Environment = **Event Log** (lossless) + **sandboxed persistent Python kernel** (typed namespace). `exec` of model-written code; **only `print`ed projections** enter the next working view. Eviction index maps landmarks → exact log addresses |
| Ceiling arm | Claimed vs “best published memory system” (+5.1 BEAM_10M) and “best published long-horizon agent” (+37.4 LOCA_256K). Traffic is academic long-mem / long-horizon, not desk/kanban |
| Backbone | **Qwen3.8-Max** — the 2.4T-A95B API flagship (SIG-20260812-02 HARD NO locally). Not our 27B |
| Hardware pre-filter | **N/A / pass** |
| Duplicate URL | None. Sibling of OpenViking (runtime context DB) and OpenKB (compile), not a fork |

## 3. Takeaways (max 5)

- **elvis ≠ the artifact.** Alibaba paper, four days old.
- **94.8 / 73.1 / 86.7 are Max-class API numbers.** Do not quote them as a Spark-27B or Hermes-memory win.
- **We already own a crude version of the split.** USER/MEMORY = always-on projection; `session_search` / desk files = the lossless log. Missing is typed in-session variables that survive turns without being re-serialized.
- **OpenViking S1 (L0/L1 abstracts) is the cheaper cousin.** Scroll adds a Python kernel and `exec`. Do not merge into an OpenViking install.
- **Model-written `exec` as the memory plane is a new attack surface**, not a free win. Sandbox claims are paper-only.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Lossless log + printed projection** — never compress before you know what will matter; only an explicit view enters the prompt | Keep `session_search` / signal-log as the log. When `t_6c3fd131` is kicked, treat skill abstracts as the printed view. Do not add a kernel | **P2** | fold — already the OpenViking S1 shape |
| S2 | Eviction index: compact landmarks → exact log addresses | Citation-only. `session_search` bookends are this, poorly | P2 | log only |

**Primary steal (one only): S1.** Same family as SIG-20260823-01. No second card.

## 5. Do not

- **Do not stand up Scroll / a persistent `exec` kernel** in Hermes.
- **Do not quote 94.8% as our memory score.**
- **Do not `hermes memory setup` anything** because of this paper.
- **Do not grow USER/MEMORY.** The lever is *not* stuffing more into the always-on files.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card — OpenViking comment on `t_6c3fd131` already covers the projection half

## 7. Chat blurb

`SIG-20260825-04` · `harness` · **steal P2** · Alibaba **Scroll**: event log + Python kernel; only prints enter the prompt. Scores are **Qwen3.8-Max**. Same projection idea as OpenViking S1. No install.
