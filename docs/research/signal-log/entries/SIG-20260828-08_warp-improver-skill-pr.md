# SIG-20260828-08 — Warp Improver: scheduled other-agent, skill PR, human merge

```yaml
id: SIG-20260828-08
date: 2026-08-28
title: "Xudong Han remix of Anthropic/Warp (26 Aug): inner skill does the job; a scheduled Improver Agent mines 'why it was wrong', opens a small Git PR, human reviews/merges. FOLDED into Recuris SIG-20260826-04 — Warp is the merge-shape of no-self-vote, not a second steal. No Warp install."
index_title: "Warp Improver FOLDED into Recuris (26-04). Scheduled other-agent → skill PR → human merge is the shape of no-self-vote. Steal P2 citation. Don't install."
index_links: [docs]
source_url: "https://x.com/Xudong07452910/status/2093145288672158204"
canonical_repo: ""
canonical_docs: "https://claude.com/blog/how-warp-builds-self-improving-agents-on-claude"
bucket: harness
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + Anthropic blog body. No Warp binary fetched.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-04"     # Recuris held-out gate
  - "SIG-20260807-02"     # Prime /refine — same agent, mid-task
  - "SIG-20260826-01"     # /review pin ≠ implementer
  - "t_b6d1a13d"
status: open
status_note: "**FOLDED into SIG-20260826-04 Recuris.** Steal P2 citation, no own STEALS row. Hardware pre-filter N/A. Warp = scheduled other-agent + human merge — the *shape* of Recuris no-self-vote. Do not install Warp. Do not open a card."
distill: none
```

## 1. Claim

[@Xudong07452910](https://x.com/Xudong07452910/status/2093145288672158204) (Xudong Han; ~11k fol; **492 likes / 72 RTs / 877 bookmarks / 46k views** at read; 2026-08-28 01:15 UTC; zh note-tweet). Fetched verbatim via `api.fxtwitter.com`. Points at Anthropic:

> How Warp builds self-improving agents on Claude (26 Aug 2026)

Loop: agent works → human feedback in the PR/issue → **scheduled Improver Agent** mines recurring mistakes → **small skill PR** → human review/merge → next run inherits.

He is a **megaphone**. Artifact is Warp + Claude Platform.

## 2. What we verified

| Check | Result |
|---|---|
| Blog | Anthropic, Michael Segner, 2026-08-26. Warp: Rust/Go, Oz orchestrator, 800k monthly devs. Code-review / spec-writing / issue-triage each get their own loop |
| Inner vs outer | **Base skill** = domain. **Improver skill** = observer on a schedule, not per-task. Updates are files → normal PR |
| Feedback | Capture where work already happens (PR/issue comment). “Why it was wrong” > thumbs. Low friction or the loop dies |
| Skills ≠ memory | Skills = procedural, stable, changed deliberately. Memory = auto-written, never stops |
| Wrong feedback | Assume it happens. Filter whose input counts; human at filter **or** merge |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None |

**Vs what we already own**

| System | Who mutates | When | Gate |
|---|---|---|---|
| Prime `/refine` (`t_b6d1a13d`) | **Same agent**, mid-task | During the job | Snapshot/rollback |
| Recuris (26-04) | Meta-agent | Across tasks | **Held-out**; no self-vote |
| Warp | **Other agent, scheduled** | After humans commented | **Human merge** |
| This desk today | `skill_manage` in-session | Whenever | Ryan-owned memory-hygiene, no improver cron |

## 3. Takeaways (max 5)

- **Improver ≠ implementer** is the sentence. Complements `/review` pin (26-01) and Recuris no-self-vote.
- **Don't stuff the prompt.** Small skills, principles + why, progressive disclosure. We already fail this when USER/MEMORY eat the turn.
- **Feedback in the workflow**, not a new form. Kanban comment / PR review is the capture surface we have.
- **Unattended never self-merges.** Warp still has a human on the PR. Matches never-send-without-OK.
- **Not a Warp install.** Desktop terminal coworker would be a second SoT.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Scheduled improver ≠ implementer** — mine “why it was wrong,” propose a *small* skill diff, human merges | **Citation of Recuris S1**, not a second steal. Shape only: other agent, on a schedule, PR, human merge | **P2** | folded into SIG-20260826-04 |

**Primary steal (one only): none here.** Lives on Recuris S1.

## 5. Do not

- **Do not install Warp / Oz as Telegram primary.**
- **Do not auto-evolve USER.md or skills from traces.**
- **Do not open a fifth card.** `t_b6d1a13d` already exists.
- **Do not quote 800k monthly developers as a quality number.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] demoted P1 → P2; STEALS row removed (lives on Recuris)
- [ ] no card
- [ ] no Warp install

## 7. Chat blurb

`SIG-20260828-08` · `harness` · **steal P2, FOLDED** · Warp Improver is the **merge-shape of Recuris** (26-04): other agent, schedule, skill PR, human merge. Not a second steal. Don't install Warp.
