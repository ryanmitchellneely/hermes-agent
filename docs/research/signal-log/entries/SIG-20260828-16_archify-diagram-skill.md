# SIG-20260828-16 — archify: trending diagram skill. We already have that lane.

```yaml
id: SIG-20260828-16
date: 2026-08-28
title: "trending_repos: archify (tt-a1i) — agent skill, typed JSON IR → deterministic HTML/SVG. Tweet 25.4k★ / +4.5k in 24h; GH now ~33k MIT. Watch P2. We already have architecture-diagram + excalidraw. Don't npx skills add -g. Don't let the model emit HTML by hand — that's the only sentence."
index_title: "archify (tt-a1i, ~33k MIT) — JSON IR → HTML diagrams. Watch P2. Don't npx -g. We already have architecture-diagram. IR-then-compile is the citation."
index_links: [repo]
source_url: "https://x.com/trending_repos/status/2093309791120543846"
canonical_repo: "https://github.com/tt-a1i/archify"
canonical_docs: "https://tt-a1i.github.io/archify/"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter + GH API ★32914 MIT + README. No npx, no clone.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "architecture-diagram"
  - "excalidraw"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. Viral skill. T1000 already has architecture-diagram. Do not `npx skills add tt-a1i/archify -g`. IR-then-compile is the only sentence."
distill: none
```

## 1. Claim

[@trending_repos](https://x.com/trending_repos/status/2093309791120543846) (bot; ~30k fol; **171 likes / 19 RTs / 332 bookmarks / 18k views** at read; 2026-08-28 12:08 UTC). Fetched verbatim via `api.fxtwitter.com`:

> archify — Agent skill for beautiful, verifiable architecture, workflow, sequence, data-flow, and lifecycle diagrams—self-contained HTML with motion and crisp export.
> Last 24h: 4,561 ★  Total: 25,424 ★
> https://github.com/tt-a1i/archify

Megaphone bot. Artifact is the repo.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `tt-a1i/archify` **★32,914 / 2,072 forks**, **MIT**, JS, created **2026-04-15**, pushed today. v2.16.0 |
| Mechanism | Agent emits **typed JSON IR**; Archify **compiles** to self-contained HTML/SVG. Before/Delta/After on two snapshots. PNG/SVG/WebM export |
| Install | README: `npx skills add tt-a1i/archify -g` |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None |

This desk already: `architecture-diagram` (dark SVG HTML), `excalidraw`, `claude-design`, `sketch`. joinsov mockups stay draft-only until OK.

## 3. Takeaways (max 5)

- **Viral ≠ install.** +4.5k in a day is Trendshift bait. MIT helps; `npx -g` still writes into the agent skill path.
- **IR then compile is the sentence.** Don’t let the model freehand the HTML. We already fail this when architecture-diagram is skipped for a one-off SVG.
- **We already have the lane.** Don’t add a second diagram compiler.
- **Before/Delta/After** is a review shape, not a reason to vendor-lock diagrams.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Agent emits IR; a compiler validates and renders** | Citation only. Keep using `architecture-diagram`. Don’t `npx -g` | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `npx skills add tt-a1i/archify -g` onto `~/.t1000`.**
- **Do not clone into the desk.**
- **Do not open a card.**
- **Do not quote 25k/33k as quality.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-16` · `harness` · **watch P2** · archify = JSON IR → HTML diagrams, ~33k MIT. We already have `architecture-diagram`. Don’t `npx -g`.
