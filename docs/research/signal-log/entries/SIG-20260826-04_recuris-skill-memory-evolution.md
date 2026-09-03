# SIG-20260826-04 — Recuris: evolve skill memory, freeze the weights

```yaml
id: SIG-20260826-04
date: 2026-08-26
title: "Ling Yang (Princeton/NUS, author) drops Recuris — two loops around a frozen LLM: verified EM–WM coupling within a task, validation-gated skill-memory evolution across tasks. tau2-Retail Opus 5 72.4→87.9. Apache-2.0 ★22. Steal P1: no model votes on its own memory patch. Do not pip install."
index_title: "Recuris (★22 Apache, arXiv 2608.24876) — freeze weights, evolve Skill Memory M=(E,W,ρ,C) behind a held-out gate. 35/37 pairs up. Steal P1: verified WM + no self-vote on patches. Not OpenViking (load) or Scroll (kernel). No install."
index_links: [repo, docs]
source_url: "https://x.com/LingYang_PU/status/2092432103954841925"
canonical_repo: "https://github.com/Gen-Verse/Recuris"
canonical_docs: "https://arxiv.org/abs/2608.24876"
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim + figure OCR; GH API + README + arXiv abs. No clone.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260823-01"     # OpenViking L0/L1 load-depth — different lever
  - "SIG-20260825-04"     # Scroll event-log + Python kernel
  - "SIG-20260824-01"     # LLM-as-a-Verifier — same 'no self-grade without a ceiling' family
  - "SIG-20260828-08"     # Warp Improver — merge-shape of this steal. Not a second steal
  - "SIG-20260828-15"     # Anthropic SDLC — verifier subagent reports, does not fix. Same steal, enterprise playbook
  - "SIG-20260830-01"     # ECC 286-skill dump — don't install the catalog. Same steal
  - "t_6c3fd131"
status: open
status_note: "**OPEN — steal P1, no card.** Hardware pre-filter N/A. Author drop, not a megaphone. Numbers are their tau2/SkillFlow/TB 2.1, avg@4. Do not clone Recuris into Hermes. Fold: verified WM writes + held-out gate before any skill mutation."
distill: none
```

## 1. Claim

[@LingYang_PU](https://x.com/LingYang_PU/status/2092432103954841925) (Ling Yang; incoming PKU AP / Princeton postdoc; ~3.5k followers; **302 likes / 48 RTs / 245 bookmarks / 44k views** at read; 2026-08-26 02:01 UTC; note-tweet + paper card). **Author**, not a clip. Fetched verbatim via `api.fxtwitter.com`.

Two loops around a **frozen** LLM:

1. **Within-task — Verified EM–WM coupling.** Working Memory = compact evidence-grounded task state. It picks which Experiential-Memory skill to fire. Env feedback must verify progress **before** WM updates. `Task State → Skill → Exec → Verify → Updated State`
2. **Across-task — Recursive skill-memory evolution.** A fixed Meta-Agent localizes failures to a *component* of Skill Memory `M = (E, W, ρ, C)` (stored skill / working-state / invocation policy / checker) and proposes a patch. **Admitted only after a fixed validation gate.**

Headline: 4 benches × 10 models, **35 / 37** pairs improve. τ²-Retail: GPT-5.6 Sol **58.3 → 76.1 (+17.8)** · Claude Opus 5 **72.4 → 87.9 (+15.6)**. Longest tasks **+32.2**. Failure modes cut **20–86%**. Evolved memory **transfers across models** unchanged.

Paper arXiv **2608.24876** (v1, 25 Aug 2026). Code `Gen-Verse/Recuris`.

## 2. What we verified

| Check | Result |
|---|---|
| Post + card | **verbatim** + OCR. Authors: Yu / Wu / Yin / Chen / Zhao / Wang / Yan / **Yang** — NUS, Stanford, Oxford, Princeton |
| Repo | `Gen-Verse/Recuris` — **★22 / 6 forks**, **Apache-2.0**, created **2026-08-25**, pushed **2026-08-26**. Eval + evolution code + evolved Skill Memory packages. Language Python |
| README | Training-free, model-agnostic. Gate is **paired held-out arithmetic — “No model votes on its own patch.”** |
| Hardware pre-filter | **N/A / pass** |
| Local run | **Not run** |
| Duplicate URL | None. Sibling of OpenViking (tiered *load*) and Scroll (Python kernel). This is *evolution + verify* |

**Named cells (figure, avg@4):** Doubao-2.0-Pro τ²-Retail 58.1→81.4 (+23.3) is their biggest frontier bar. Open-weight: Qwen3.6-27B SkillFlow 42.2→58.7; GPT-OSS-20B τ²-Retail 50.6→60.8. Traffic is retail/airline/SkillFlow/TB 2.1 — **not desk/kanban**.

Ceiling arm exists (agent-alone column). Good.

## 3. Takeaways (max 5)

- **Author drop, tiny repo.** Cite the paper, not the follower count.
- **Different lever than OpenViking / Scroll.** OV = how much of a file you load. Scroll = log + prints. Recuris = **mutate skills behind a gate**. Do not merge the cards.
- **“No model votes on its own patch” is the sentence.** Same family as Pass@1/picker/Oracle (SIG-20260824-01). Warp (SIG-28-08) is the *shape*: scheduled other-agent, small skill PR, human merge. One steal, not two.
- **Cross-model transfer** is the cheap experiment if we ever evolve a skill note on Flash and load it on 120b/Grok. Not a reason to install their harness.
- **87.9 is Opus 5 + Recuris on τ²-Retail.** Do not quote as a Hermes number.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Verified WM + held-out gate on skill mutation** — env must confirm progress before WM writes; a patch to a skill/checker needs evidence the writer did not grade. Warp shape: other agent, schedule, small PR, human merge | When `t_6c3fd131` / memory-hygiene is touched: (1) don’t persist a “lesson” from a failed card (2) a skill patch needs a second context or a test, not the same session that wrote it (3) if an improver ever drafts, it **stops** at a diff — Ryan merges | **P1** | fold — no new card |
| S2 | Localize failure to a *component* (skill vs invocation vs checker) instead of rewriting the whole SKILL.md | Citation-only until S1 exists | P2 | log only |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not `git clone` Recuris into T1000 / Hermes.** ★22, eval harness, not a drop-in memory provider.
- **Do not install Warp** (SIG-28-08). Same steal, different blog.
- **Do not auto-evolve USER.md / skills from traces.** Standing memory-hygiene: Ryan-owned, not a meta-agent loop.
- **Do not quote +32.2 / 87.9 as fleet.**
- **Do not conflate with OpenViking `hermes memory setup`.** Different license, different lever, still don’t install.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md row
- [ ] no card
- [ ] no clone

## 7. Chat blurb

`SIG-20260826-04` · `harness` · **steal P1** · Recuris: freeze the model, evolve Skill Memory behind a **held-out gate**. 35/37 pairs up. Primary steal **S1 — don’t let the writer vote its own memory patch**. Not an install.
