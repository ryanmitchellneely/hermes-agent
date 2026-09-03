# SIG-20260829-01 — Sodium: website → WebMCP tools. Don't script-tag joinsov.

```yaml
id: SIG-20260829-01
date: 2026-08-29
title: "Savio/Result Sodium — turn site features into WebMCP tools. 2 min setup, claims 2.82x faster / 91x token efficient. $49/repo, one script tag, GitHub analyze (no execute/push). Names Hermes. Watch P2. Don't quote 91x. Don't put sodium.result.dev/agent/v1.js on joinsov."
index_title: "Sodium (Result) — site→WebMCP, $49/repo, names Hermes. Watch P2. Don't quote 91x. Don't script-tag joinsov. Don't GitHub-OAuth their analyzer."
index_links: [docs]
source_url: "https://x.com/saviomartin/status/2093780571638149523"
canonical_repo: ""
canonical_docs: "https://sodium.result.dev"
bucket: product
posture: watch
steal_rank: P2
confidence: high          # fxtwitter verbatim + homepage HTML. No signup, no script tag.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260828-12"     # Composio — other side of the same MCP-for-agents pitch
  - "sovereign-public-surface"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. SaaS script tag + GitHub analyzer. 91x has no named bench. Don't add to joinsov. Don't sign in."
distill: none
```

## 1. Claim

[@saviomartin](https://x.com/saviomartin/status/2093780571638149523) (Savio, CTO Result; ~59k fol; **994 likes / 61 RTs / 1.2k bookmarks / 62k views** at read; 2026-08-29 19:19 UTC). Fetched verbatim via `api.fxtwitter.com`:

> Introducing Sodium. Turns all your website’s existing features into WebMCP tools so AI agents can discover and use your site directly. 2 minute setup · 2.82x faster · 91x token efficient.
> https://sodium.result.dev

Author, not a clip. SaaS launch.

## 2. What we verified

| Check | Result |
|---|---|
| Site | Live. “Make your website usable by ChatGPT, Claude, … **Hermes**.” One `<script src="https://sodium.result.dev/agent/v1.js" data-site="…">`. GitHub connect: **analyzes repo, never runs code or pushes**. Tools you approve go live. Versions + rollback. $49/repo/mo |
| WebMCP | FAQ: any WebMCP **browser** agent **while the website is open**. W3C standardization claim. Not a Hermes MCP server on our VPS |
| 91x / 2.82x | Homepage slogans. **No bench, no baseline, no N.** |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. Cousin of Composio (28-12): they make *your tools* callable; this makes *your site* callable |

## 3. Takeaways (max 5)

- **Browser WebMCP ≠ T1000 MCP.** Tools exist only while the page is open in a WebMCP browser. Telegram desk does not load joinsov.com.
- **91x is unreadable.** No ceiling arm. Don’t quote.
- **joinsov is draft-mockup-only.** Script tag is a public-surface change. Not without Ryan OK.
- **GitHub-OAuth analyzer is a third-party read of the repo.** They say no execute/push. Still a vendor in the git graph. Don’t connect.
- **“You choose which actions require confirmation”** is their send-gate. Ours is never-send. Don’t outsource it.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Expose site actions as tools instead of scraping HTML** (token win is the pitch) | Citation only. If joinsov ever grows an agent surface, it’s first-party MCP/tools, not a $49 script | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not add `sodium.result.dev/agent/v1.js` to joinsov.**
- **Do not Sign in / GitHub-connect their analyzer.**
- **Do not quote 91x / 2.82x.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260829-01` · `product` · **watch P2** · Sodium = site→WebMCP script tag, $49/repo, names Hermes. 91x has no bench. Don’t put it on joinsov. Don’t GitHub-OAuth them.
