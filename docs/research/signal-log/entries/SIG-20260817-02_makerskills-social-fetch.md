# SIG-20260817-02 — Corey Haines /social-fetch + Maker Skills marketplace (18 skills). Don’t install. X “free API” is preview-only.

```yaml
id: SIG-20260817-02
date: 2026-08-17
title: "coreyhainesco: agents can't read social (login walls). Ships /social-fetch — any URL (X, LinkedIn, IG, TikTok, Reddit, HN) → structured author/text/engagement/replies. 'Free APIs first, browser when walls, Wayback for dead posts.' Part of Maker Skills — 18 OSS skills. Install: /plugin marketplace add coreyhaines31/makerskills. Repo MIT ★646. SKILL.md: X free path is preview-only; full thread/replies need ScrapeCreators/Apify keys."
index_title: "Maker Skills /social-fetch. Ladder is real; X free = preview. Don't marketplace-install. Don't add scrape keys. Watch P2."
source_url: "https://x.com/coreyhainesco/status/2089027423774048326"
canonical_repo: "https://github.com/coreyhaines31/makerskills"
canonical_docs: "https://maker-skills.com"
index_links: [repo, docs]
bucket: harness
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "signal-log"
  - "agent-harness-compare"
status: open
status_note: "**OPEN — no install.** Tweet + repo + social-fetch SKILL.md fetched. Hardware N/A. We already have a working X route (fxtwitter). Don't /plugin marketplace add. Don't add SCRAPECREATORS/APIFY keys (desk: no extra API keys)."
distill: none
```

## 1. Claim

[@coreyhainesco](https://x.com/coreyhainesco/status/2089027423774048326) (32.7k fol; 892 likes / 75 RT / 1.8k bookmarks / 76k views):

Agents can’t read social (login walls). `/social-fetch` takes any URL and returns structured author / text / engagement / replies. Free APIs first, browser when walls, Wayback for dead posts. Part of **Maker Skills** — 18 free OSS skills. Claude Code: `/plugin marketplace add coreyhaines31/makerskills`.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `coreyhaines31/makerskills` MIT ★**646** / 53 forks / created 2026-06-03 / pushed 2026-08-12 / site maker-skills.com |
| Count | **20** skill dirs (tweet said 18). Includes `social-fetch`, `decide`, `jab-hook`, `maker-council`, `second-brain`, `loopify` |
| social-fetch | v0.1.1 SKILL.md fetched (7.5 KB). Normalize-to-JSON. Strategy chain per platform |
| X honesty (their own limits) | **Free strategies = tweet preview only.** Full thread + replies need `$SCRAPECREATORS_API_KEY` or `$APIFY_API_TOKEN` |
| Paid fallbacks | ScrapeCreators / Apify — only if env keys present; prompt before paid |
| Hardware pre-filter | **N/A** |

## 3. Takeaways (max 5)

- The tweet is a **Claude Code marketplace install**. Not a T1000 skill pack.
- **Ladder is the only stealable bit** (free → browser → Wayback → paid). We already do free-first for X (`api.fxtwitter.com`) and it returns full note-tweet text + metrics without a key.
- Their X free path is **weaker than ours**. Don’t replace fxtwitter with this.
- `maker-council` is a named-founder board — foil for `llm-council`, not a swap.
- Paid scrape keys violate the desk “no extra provider API keys” rule.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Fallback ladder, not a single fetch** — if fxtwitter/vx die, try browser then Wayback before declaring unfetched | Already implied by signal-log’s 2026-08-09/10 fxtwitter lesson. Optional one-line in that skill later — not this turn | **P2** | watch |

**Primary steal:** S1 (not P1 — no STEALS row, no card)

## 5. Do not

- `/plugin marketplace add coreyhaines31/makerskills` on this desk or into `~/.t1000`.
- Export `SCRAPECREATORS_API_KEY` / `APIFY_API_TOKEN`.
- Replace the signal-log fxtwitter route with their X preview.
- Clone the 20-skill pack “to try decide.”

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260817-02** · harness · **watch P2** · high
Maker Skills `/social-fetch`. Ladder is fine; **X free = preview**. We already beat that with fxtwitter.
**Do not marketplace-install. No scrape keys.**
