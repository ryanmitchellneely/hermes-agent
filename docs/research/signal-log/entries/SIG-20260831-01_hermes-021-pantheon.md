# SIG-20260831-01 — Hermes 0.21.0 Pantheon. We're on 0.20.0. Don't update this session.

```yaml
id: SIG-20260831-01
date: 2026-08-31
title: "Axl quotes Nous Hermes Agent v0.21.0 Pantheon (tag v2026.8.31). Bot Mode bundled, hermes peer, cron memory/continuity, live-steer subagents, MCP command center, in-app browser drive. T1000 measured: Hermes 0.20.0 (2026.8.3). Watch P2. Don't hermes update / curl install.sh. Don't quote 5,800 commits."
index_title: "Hermes 0.21.0 Pantheon (v2026.8.31). T1000 is 0.20.0. Watch P2. Don't update this session. Cron continuity + Bot faces are the sentences. Ryan OK before hermes update."
index_links: [repo]
source_url: "https://x.com/andrexibiza/status/2094517055689052233"
source_url_2: "https://x.com/NousResearch/status/2094515104670715940"
canonical_repo: "https://github.com/NousResearch/hermes-agent"
canonical_docs: "https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31"
bucket: ops
posture: watch
steal_rank: P2
confidence: high          # fxtwitter + GH release body + `hermes --version` = 0.20.0 on this host. No update run.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "hermes-agent"
  - "t1000-gateway-ha"
  - "cron-execution-environment"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. First-party. This VPS is 0.20.0 (2026.8.3). Do not `hermes update` without Ryan OK. Cron continuity + Bot Mode faces are the only sentences if we ever plan an upgrade."
distill: none
```

## 1. Claim

[@andrexibiza](https://x.com/andrexibiza/status/2094517055689052233) (Axl; Hermes contributor; ~271 fol; **16 likes**; 2026-08-31 20:05 UTC) quotes [@NousResearch](https://x.com/NousResearch/status/2094515104670715940):

> Hermes Agent v0.21.0: The Pantheon Release

Axl is **pride**, not the changelog. Artifact is the GH tag.

## 2. What we verified

| Check | Result |
|---|---|
| Tag | `v2026.8.31` published 2026-08-31T19:29Z. Since 0.20.0: ~5,800 commits / ~2,475 PRs (vendor size, not a quality number) |
| Highlights | Bot Mode **bundled default-on** (faces, group chats, @-mention). `hermes peer` bot-to-bot DMs. **Cron loads/updates memory**; `continuity=true`; durable notepad; monitor-mode skip-LLM on no-change. **Live-steer** `delegate_task` children. MCP command center. Agent **drives** in-app browser. Six new providers |
| This host | `hermes --version` → **Hermes Agent v0.20.0 (2026.8.3)** · `/opt/t1000/src` |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None |

## 3. Takeaways (max 5)

- **We are behind.** 0.20.0 (Aug 3) vs 0.21.0 (Aug 31). Not a reason to `hermes update` from Telegram.
- **Cron goldfish is the real 0.21 sentence.** Continuity + memory between runs. Our fleet already has crons; they still start fresh unless we take this.
- **Bot Mode faces.** USER already: faces kickoff / empty Bots = hung `profiles.list`. 0.21 makes it default-on in **desktop**. This session is VPS Telegram. Mac is glass, never runtime.
- **Live-steer subagents** is nicer `delegate_task`, not a new SoT.
- **Don’t curl install.sh.** Same hard rule. `hermes update` is the path *after* Ryan OK + HA plan.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Cron that remembers** (`continuity=true`, persist memory, skip LLM on no-change) | Citation until Ryan OKs an upgrade window. Do not `hermes update` here | **P2** | log only |

**Primary steal (one only): S1.** No install this session.

## 5. Do not

- **Do not `hermes update` / `curl …/install.sh` on this VPS.**
- **Do not quote 5,800 commits / 239k stars.**
- **Do not dual-drive a second Hermes next to T1000.**
- **Do not open a card** until Ryan says plan the upgrade.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card
- [ ] no update

## 7. Chat blurb

`SIG-20260831-01` · `ops` · **watch P2** · Hermes **0.21.0 Pantheon** is out. This desk is **0.20.0**. Don’t update from chat. Cron continuity + Bot faces are the sentences if you want an upgrade window.
