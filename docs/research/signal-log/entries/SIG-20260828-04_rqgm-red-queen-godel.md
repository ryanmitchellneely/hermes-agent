# SIG-20260828-04 — RQGM is Cambridge+NVIDIA, not “NVIDIA built a Gödel Machine”

```yaml
id: SIG-20260828-04
date: 2026-08-28
title: "HowToPrompt remix of Red Queen Gödel Machine (arXiv 2606.26294, June). Cambridge first; NVIDIA is an affiliation. Co-evolve agent + evaluator; freeze the judge within an epoch; promote it only if it beats held-out GT. Coding 69.9→71.7; 1.35–1.72× fewer tokens = reviewer queried once, not decode. Steal P2: fold into Recuris / no-self-vote. No install."
index_title: "RQGM (arXiv 2606.26294) — Cambridge+NVIDIA, not an NVIDIA product. Freeze judge within epoch; promote only on held-out GT. Coding +1.8pp; 1.72× is reviewer-once. Steal P2 fold into Recuris. Don't quote holy grail."
index_links: [docs]
source_url: "https://x.com/HowToPrompt__/status/2092983677919830336"
canonical_repo: ""
canonical_docs: "https://arxiv.org/abs/2606.26294"
bucket: harness
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + card OCR + arXiv abs v2. No first-party code (OpenRQGM ★0 unofficial).
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-04"     # Recuris — no model votes on its own patch
  - "SIG-20260824-01"     # Pass@1 / picker / Oracle
  - "SIG-20260826-01"     # /review ≠ implementer
  - "SIG-20260807-02"     # Prime /refine
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. Megaphone; artifact is Iacob et al. Cambridge CST + NVIDIA/Flower/MBZUAI/Inria. Coding delta is 69.9→71.7. 1.72× is one-shot reviewer vs multi-turn, not tok/s. Fold into Recuris. Do not quote holy grail."
distill: none
```

## 1. Claim

[@HowToPrompt__](https://x.com/HowToPrompt__/status/2092983677919830336) (“Trustworthy AI education”; ~33k followers; **592 likes / 133 RTs / 508 bookmarks / 26k views** at read; 2026-08-27 14:32 UTC; note-tweet + paper-card screenshot). Fetched verbatim via `api.fxtwitter.com`:

> NVIDIA did something terrifying.. They built the Red Queen Gödel Machine…
> blew past previous state-of-the-art benchmarks while burning up to 1.72× fewer compute tokens.
> This is the holy grail of recursive self-improvement.

He is a **megaphone**. No repo. Card is the paper abstract.

## 2. What we verified

| Check | Result |
|---|---|
| Post + card OCR | **verbatim**. Title *The Red Queen Gödel Machine: Co-Evolving Agents and Their Evaluators* |
| Authors | **Iacob / Jovanović / Shen** (equal) et al. **¹Cambridge ²NVIDIA ³Flower Labs ⁴MBZUAI ⁵Inria**. First author Cambridge CST, not an NVIDIA product blog |
| arXiv | **2606.26294** v2 29 Jun 2026. “Preliminary preprint; work in progress.” 13+21 pages |
| Code | **No first-party repo.** GH search: `DreamFallenFlowers/OpenRQGM` ★0 unofficial. Do not clone |
| Hardware pre-filter | **N/A / pass** |
| Duplicate URL | None. Same *family* as Recuris (26-04) and LLM-as-a-Verifier (24-01) |

**Named cells (abstract, not our traffic):**

| Claim in tweet | Paper cell |
|---|---|
| “blew past SOTA” coding | Held-out pass **71.7 vs prior 69.9** (+1.8pp) by adding a one-shot agent-as-judge review |
| **1.72× fewer tokens** | Reviewer queried **once**; standard coding agents are multi-turn. 1.35–1.72×. **Not decode tok/s** |
| Writers 1.78–1.86× | Acceptance under a **diverse agent-as-judge panel** — the panel they co-evolved |
| Graders +9% | Ground-truth accuracy on Olympiad proofs |
| 1.91× over-accept | Baseline reviewer accepts AI papers at up to 1.91× the human rate; adversarial objective is the fix |

Mechanism that is real: **controlled utility evolution** — freeze the evaluator *inside* an epoch so improvement is measurable; swap it at the boundary **only if** the candidate beats held-out human GT.

Ceiling arm exists (prior Darwin/Huxley Gödel Machine). Good. Magnitude on coding is small.

## 3. Takeaways (max 5)

- **Not “NVIDIA built.”** Cambridge paper, NVIDIA on the author list. Cite Iacob et al., not the tweet.
- **1.72× is reviewer-once vs multi-turn.** Do not quote as a Spark or Flash saving.
- **Coding delta is +1.8pp.** “Blew past SOTA” is the panel-acceptance cell (1.78–1.86×), which is circular if the panel co-evolved.
- **The sentence we already own:** freeze the checker while the worker runs; promote a new checker only against held-out labels. Recuris said it; this is the Gödel-machine writeup.
- **June preprint, Aug megaphone.** Two-month lag. No code to run.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Freeze the judge inside the loop; promote it only on held-out GT** | Already Recuris S1 + `/review` ≠ implementer + never GRPO the golden set. This paper is the citation, not a new card | **P2** | fold into SIG-20260826-04 |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not call this an NVIDIA product.**
- **Do not quote 1.72×, 1.86×, or “holy grail.”**
- **Do not clone OpenRQGM or run evolutionary epochs on Spark.**
- **Do not let an improver cron merge a skill the same session wrote.** Recuris already forbids it.
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2; Recuris row covers it)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-04` · `harness` · **steal P2** · RQGM is **Cambridge+NVIDIA**, not “NVIDIA built a Gödel Machine.” Freeze the judge within an epoch; promote only on held-out GT. Coding **69.9→71.7**. **1.72× = reviewer once**, not tok/s. Fold into Recuris. Don't quote holy grail.
