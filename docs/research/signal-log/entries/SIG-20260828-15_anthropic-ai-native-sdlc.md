# SIG-20260828-15 — Anthropic AI-native SDLC playbook. Artifact chain + verifier ≠ fixer.

```yaml
id: SIG-20260828-15
date: 2026-08-28
title: "Anthropic (Claxton, 21 Aug): AI-native SDLC playbook. Each stage commits an artifact the next stage reads (intent.md → spec.md → plan.md → PR). Skill = advisory; hook = deterministic. Verifier subagent reports, does not fix. Human approval hooks belong at Deploy, not Build. Steal P2 fold Recuris + handoff tax. Don't install Claude Code as SoT."
index_title: "Anthropic SDLC playbook (08-21) — committed artifact chain; verifier ≠ fixer; hooks at deploy. Steal P2 fold Recuris. Don't adopt Claude Code."
index_links: [docs]
source_url: "https://claude.com/blog/the-ai-native-sdlc-playbook"
canonical_repo: ""
canonical_docs: "https://claude.com/blog/the-ai-native-sdlc-playbook"
bucket: harness
posture: steal
steal_rank: P2
confidence: high          # full blog extract 21 Aug 2026, Louis Claxton / Applied AI. No Claude Code install.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-04"     # Recuris no-self-vote — verifier subagent is the shape
  - "SIG-20260828-08"     # Warp Improver — skill PR, human merge
  - "SIG-20260826-05"     # Handoff tax — closer gets card+repo, not CoT dump. intent.md is that compact
  - "SIG-20260826-01"     # /review ≠ implementer
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. Enterprise Claude Code playbook. Steal: artifact between stages + verifier doesn't fix. Don't auto-loop Maintain into send. Fold Recuris."
distill: none
```

## 1. Claim

[The AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) — Anthropic, **Louis Claxton**, **21 Aug 2026**, ~46 min. Applied AI team practices across Plan / Design / Build / Test / Deploy / Maintain.

Thesis: code is no longer the bottleneck; plan / review / deploy still run at human speed. Rebuild the SDLC so each stage **commits an artifact the next stage can read**. Humans stay at the gates.

## 2. What we verified

| Check | Result |
|---|---|
| Page | Live. Six-stage table + plays. `intent.md` template, `CLAUDE.md`, `.claude/skills/`, hooks, worktrees, verifier subagent, Maintain → new `intent.md` |
| Named pattern | Skill = advisory. Hook = deterministic. **Human-approval hook during Build puts a person on the critical path of every parallel session — park it at Deploy** |
| Verifier | Fresh context, `tools: Bash, Read`, **report only, do not fix** |
| Test loop | Agent must not weaken the check: hook blocks test-file edits during a fix |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. Overlaps Recuris / Warp / handoff tax / `/review` — different artifact (enterprise playbook, not a paper) |

## 3. Takeaways (max 5)

- **Committed artifact is the handoff.** `intent.md` / `spec.md` / `plan.md` / PR. Same sentence as AWS handoff tax (26-05): closer gets the card + repo, not the CoT dump.
- **Verifier ≠ implementer.** Fresh window, report only. Recuris no-self-vote. Warp’s other-agent. `/review` pin.
- **Skill without a hook is a suggestion.** We already fail this when `skill_manage` patches land with no test.
- **Don’t put Ryan on every Build action.** Approval gates belong where we already put them (never-send, kanban `needs_input`, Deploy/PR).
- **Maintain auto-loop is the anti-pattern here.** “Trigger invokes Claude with no person in the path” still writes `intent.md` for a human to triage. Do not auto-send / auto-merge.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Stage ends in a committed artifact; verifier reports, does not patch** | Fold Recuris S1 + 26-05: kanban/PR is the artifact; `/review` or a leaf verifier does not `skill_manage`. No auto-Maintain | **P2** | fold into SIG-20260826-04 |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not adopt Claude Code / Cowork as Telegram SoT.**
- **Do not auto-commit `intent.md` from crons into a send.**
- **Do not put a human-approval hook on every file edit.**
- **Do not open a card.** Recuris + `t_6c3fd131` already exist.
- **Do not quote “46 min” as a quality number.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-15` · `harness` · **steal P2** · Anthropic SDLC: **commit an artifact per stage; verifier doesn’t fix.** Fold Recuris. Don’t install Claude Code. Don’t auto-loop Maintain.
