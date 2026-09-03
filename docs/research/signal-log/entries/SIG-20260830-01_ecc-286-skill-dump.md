# SIG-20260830-01 — ECC: 286-skill Claude Code dump. Don't install the catalog.

```yaml
id: SIG-20260830-01
date: 2026-08-30
title: "undefinedKi remix: affaan-m/ECC — 68 subagents, 286 skills, 94 commands, MIT. Plan→TDD→fresh-context review. GH ★244k. Watch P2. Tweet itself: installing all 286 at once makes it worse. Fold Recuris + TDD. Don't npx ecc-universal. Don't adopt Claude Code as SoT."
index_title: "ECC (affaan-m, ★244k MIT) — 286-skill Claude Code catalog. Watch P2. Don't install the dump. One plan + one rules pack. Fold Recuris."
index_links: [repo]
source_url: "https://x.com/undefinedKi/status/2094088284443992514"
canonical_repo: "https://github.com/affaan-m/ECC"
canonical_docs: "https://ecc.tools"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter + card OCR github.com/affaan-m/ECC + GH API ★244709 MIT. No clone, no npx.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-04"     # Recuris — fresh-context review / no self-vote
  - "SIG-20260828-15"     # Anthropic SDLC — plan artifact, verifier ≠ fixer
  - "test-driven-development"
  - "requesting-code-review"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. Megaphone of a 244k-star catalog. Don't npx. Don't clone into ~/.t1000. One plan + one rules pack is the only sentence."
distill: none
```

## 1. Claim

[@undefinedKi](https://x.com/undefinedKi/status/2094088284443992514) (Yarchi; ~14k fol; **904 likes / 84 RTs / 1.9k bookmarks / 109k views** at read; 2026-08-30 15:42 UTC). Fetched verbatim via `api.fxtwitter.com`:

> The winner of an Anthropic hackathon open sourced his entire Claude Code setup. 68 subagents, 286 skills, 94 commands, MIT.
> ECC … plans before it builds, writes the failing test first, then reviews its own work from a fresh context.
> **Start with one plan and one rules pack. Installing all 286 skills at once is the fastest way to make it worse.**

Megaphone. Quotes his own Claude-setup article. Card tree: `github.com/affaan-m/ECC`.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `affaan-m/ECC` **★244,709 / 36,986 forks**, **MIT**, created 2026-01-18, pushed today. README: “agent harness OS” for Claude Code / Codex / OpenCode / Cursor. `ecc.tools` + GitHub App + `ecc-universal` npm |
| Card | Annotated catalog: agents (planner, tdd-guide, *-reviewer, *-build-resolver, security-reviewer), skills (tdd-workflow, language packs, iterative-retrieval), hooks, commands. Footer: counts differ from README header |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. Pattern-class = Recuris / Warp / Anthropic SDLC / our TDD + `/review` skills |

★244k is a **trend farm**, not a quality number. MIT is real; the dump is still a second harness.

## 3. Takeaways (max 5)

- **The tweet already wrote the steal.** Don’t install 286. One plan + one rules pack.
- **Plan → red test → fresh-context review** is Recuris + TDD + `/review`. We already have those skills.
- **Don’t adopt Claude Code as SoT.** Same reject as 28-15.
- **Don’t `npx ecc-universal` / GitHub App.** Catalog into `~/.t1000` is the anti-pattern (skill_view first, few skills).
- **iterative-retrieval / search-first** = don’t drag the whole repo into the window. We already fail this. Citation only.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Don’t dump the catalog.** One plan skill + one rules pack; verifier in a fresh context | Already Recuris S1 + `plan` + TDD. Do not clone ECC | **P2** | fold into SIG-20260826-04 |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `npx ecc-universal` / clone ECC into Hermes.**
- **Do not enable 68 subagents.**
- **Do not quote ★244k.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260830-01` · `harness` · **watch P2** · ECC = 286-skill Claude Code dump (★244k MIT). **Installing all 286 makes it worse.** Fold Recuris. Don’t npx. Don’t adopt Claude Code.
