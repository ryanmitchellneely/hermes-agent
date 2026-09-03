# SIG-20260828-09 — OpenWorker is a competing desk OS. Don't install.

```yaml
id: SIG-20260828-09
date: 2026-08-28
title: "vicky_grok 'Andrew Ng free AI coworker 16k stars' = andrewyng/openworker (MIT, ★16.7k, Jul 2026, Ng+Prasad). Desktop app, finished work not chat, approval-gated writes/sends/shell, 25+ connectors + MCP, cron. Watch P2. We already run this shape as T1000. Second control plane. Do not download."
index_title: "OpenWorker (andrewyng, ★16.7k MIT) — desktop coworker, local-first, approval-gated. Watch P2. T1000 already is this. Don't install. Don't dual-drive."
index_links: [repo]
source_url: "https://x.com/vicky_grok/status/2092990755396870471"
canonical_repo: "https://github.com/andrewyng/openworker"
canonical_docs: "https://openworker.com"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter + GH API ★16697 MIT + README. No download.
hardware_fit: [none]      # Mac app; this desk's runtime is VPS Hermes, Mac is glass
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "SIG-20260825-05"     # Perplexity Portable Computer — same 'second desk' reject
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. vicky is Typefully megaphone of a Jul-23 launch. ★16.7k is the repo. T1000 already has never-send, cron, connectors, Grok+Ollama. Do not download the Mac app onto the glass."
distill: none
```

## 1. Claim

[@vicky_grok](https://x.com/vicky_grok/status/2092990755396870471) (Vikas Gupta; ~10.6k fol; LinkedIn promo; **399 likes / 54 RTs / 828 bookmarks / 52k views** at read; 2026-08-27 15:00 UTC; Typefully + 30s video). Fetched verbatim via `api.fxtwitter.com`:

> Andrew Ng just open sourced a free AI coworker that delivers FINISHED work, not chat. 16,000+ stars… approval-gated… 25+ tools… schedule… BYOK or Ollama.

Quotes his own beginner “LLMs vs Agents” article. **No repo URL in the tweet.** He is a **megaphone**.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `andrewyng/openworker` **★16,697 / 2,302 forks**, **MIT**, Python, created **2026-07-20**, pushed 08-26. Matches the 16k claim. Ng + Rohit Prasad. Beta Mac+Windows desktop |
| README | Outcome in → steps → desktop/files/apps → **check-in before send/write/shell**. 25+ connectors (GitHub, Slack, Jira, Notion, Gmail, Calendar) + MCP. Cron. BYOK including Grok + Ollama. Local secret store |
| Governance | Hard floors (human-only, even in auto-approve). Ladder of earned autonomy. Audit trail. **Unattended runs never self-approve** — park in an inbox. Security coworkers: “fixer is never the only checker” |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. Cousin of Perplexity Portable Computer (SIG-25-05) |

This desk already: never-send-without-OK, cron briefs, Gmail/Calendar/Notion/GitHub, MCP, Grok default + local Ollama/Flash, kanban sticky `needs_input`.

## 3. Takeaways (max 5)

- **Competing desk OS, not a library.** Same reject as Prime / Perplexity PC / OpenClaw: T1000 stays SoT.
- **vicky didn't link the repo.** Attribution is the GH search, not the tweet.
- **“Fixer is never the only checker”** = Recuris / `/review`. Citation only.
- **Unattended never self-approves** = our never-send + sticky block. We already have this.
- **Mac download is the glass.** Runtime SoT is VPS Hermes. Don't put a second coworker on the laptop.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | Unattended never self-approves; fixer ≠ checker | Already never-send + Recuris. Citation only | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not download OpenWorker onto the Mac glass or `~/.t1000`.**
- **Do not dual-drive it with Hermes as Telegram primary.**
- **Do not run their security-coworker scanners against a target.** (Defensive product; still not ours.)
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-09` · `harness` · **watch P2** · OpenWorker (`andrewyng`, ★16.7k MIT) is a **competing desk OS**. We already are this. Don't install.
