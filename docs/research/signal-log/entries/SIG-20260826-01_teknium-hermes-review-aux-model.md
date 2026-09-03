# SIG-20260826-01 — Hermes `/review`: pin a different model than the implementer

```yaml
id: SIG-20260826-01
date: 2026-08-26
title: "Teknium: /review + auxiliary.review made his Hermes PRs better. Last 10 messages → full-tool subagent on a separate model → report returns to the session. This desk has no auxiliary.review key. Steal P1: pin a NON-implementer model; do not Grok-review-Grok."
index_title: "Hermes /review aux model (Teknium 08-24/25) — last-10 + subagent, CLI/TUI/Desktop/messaging. Desk has no auxiliary.review pin. Steal P1: different model than the implementer. Do not auto-set (Max spend)."
index_links: []
source_url: "https://x.com/Teknium/status/2092193947036914011"
source_url_2: "https://x.com/Teknium/status/2091686997228478653"
canonical_repo: ""
canonical_docs: ""
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim both posts + card OCR; live ~/.t1000/config.yaml auxiliary block read (no review key). No /review fired.
hardware_fit: [spark, mbp, vps]
stacks_touched: [t1000]
related_plans:
  - "requesting-code-review"  # already says 'no agent verifies its own work' then delegate_task inherits parent
  - "github-code-review"
  - "SIG-20260808-02"         # parent-strong / child-cheap — review wants the inverse child
status: open
status_note: "**OPEN — steal P1, no card.** Hardware pre-filter N/A. First-party Hermes, 08-24. auxiliary.review unset on this desk. Do not hermes config set without Ryan OK (Opus/Max vs 120b vs Fable). requesting-code-review still inherits the parent model."
distill: none
```

## 1. Claim

[@Teknium](https://x.com/Teknium/status/2092193947036914011) (Nous cofounder / Hermes lead; ~122k followers; **478 likes / 25 RTs / 256 bookmarks / 29.6k views** at read; 2026-08-25 10:14 UTC). Quotes his own 08-24 announce (**1,366 likes / 151k views**). Fetched verbatim via `api.fxtwitter.com`:

Parent (08-24):

> New in Hermes: You can now set a new auxiliary model for Review
>
> When you run `/review`, it'll take the last 10 messages and any prompt you put after review, and send a new subagent using that model … then send it's review back to the main agent.

This tweet (08-25):

> My PRs to Hermes Agent have truly gotten a lot better because of this - I'd recommend everyone get a good model set for your review model and get a second opinion on your primary agent's completed work!

Card: `/review — INDEPENDENT REVIEWER SUBAGENT` · last 10 messages → full-tool subagent investigates → review returns to your session · CLI / TUI / Desktop / messaging · `auxiliary.review — pick your reviewer model`.

**Author of the runtime, not a megaphone.**

## 2. What we verified

| Check | Result |
|---|---|
| Both posts | **verbatim** via fxtwitter |
| Live desk `auxiliary:` | vision (grok-4.6) · compression (mtplx 27b) · title_generation (mtplx 27b) · triage/decomposer/estimator (qwen3.8:27b) · **no `review:` key** |
| `kanban.review_profiles: [reviewer]` | Different object — kanban reviewer *profile*, not `/review` aux model |
| `requesting-code-review` v2.0.0 | Doctrine is already *“No agent should verify its own work.”* Step 5 `delegate_task` **inherits the parent model** unless pinned. That is the hole Teknium just shipped a first-party fix for |
| Hardware pre-filter | **N/A / pass** |
| `/review` fired here | **No** |
| Duplicate URL | None |

## 3. Takeaways (max 5)

- **This is in Hermes now.** Not a third-party install. The gap is we have not pinned `auxiliary.review`.
- **Same-model review is the anti-pattern.** Desk default is Grok. A Grok `/review` of Grok work is the thing he is telling people not to do.
- **Review child ≠ implementer child.** B22 is parent-strong / worker-cheap. Review wants a *different* (usually stronger or orthogonal) model as the child.
- **Cost lane matters.** Opus/Fable on every `/review` burns Max. 120b is local and cheap but weaker at “PR taste.” Don’t silently pick Max.
- **Last-10 is a small window.** Long audits will need an explicit prompt after `/review` (diff, card, PR URL) or it reviews the wrong slice.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Pin `auxiliary.review` to a model that is not the implementer** | Ryan picks one: (a) `claude-acp` Opus/Fable for code PRs (b) `spark` 120b for local/yellow (c) leave unset until then. Do not default it to Grok | **P1** | open — needs Ryan OK |
| S2 | Patch `requesting-code-review` Step 5 to pass a model/provider override instead of inheriting parent | After S1 is chosen. Until then the skill still self-reviews | P2 | wait on S1 |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not `hermes config set auxiliary.review …` in this session.** Max vs 120b is a spend/privacy call.
- **Do not use Grok as the review model while Grok is the desk.**
- **Do not confuse this with `kanban.review_profiles`.**
- **Do not treat Teknium’s “PRs got better” as a measured delta.** Anecdote, direction is still right.
- **Do not fire `/review` on a long audit** without a scoped prompt — last 10 messages only.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md row
- [ ] no card — one-word pin from Ryan is enough
- [ ] no config write

## 7. Chat blurb

`SIG-20260826-01` · `harness` · **steal P1** · Hermes `/review` is first-party (08-24). Teknium: PRs got better with a **separate** review model. This desk has **no `auxiliary.review` pin**. Don’t Grok-review-Grok. Need your pick before anyone sets it.
