# SIG-20260828-12 — Composio: 1000-tool MCP/auth gateway. Don't put it in front of Hermes.

```yaml
id: SIG-20260828-12
date: 2026-08-28
title: "composio.dev — 1000+ toolkits, managed OAuth, MCP Gateway, sandboxed workbench. Lists Claude/Codex/OpenClaw/Cursor/Hermes. ★29.9k MIT (ComposioHQ/composio). Watch P2. Second control plane for tools+auth. Don't sign up. Don't MCP-gateway T1000."
index_title: "Composio (★29.9k MIT) — 1000-tool MCP/auth gateway, names Hermes. Watch P2. Don't sign up. Don't put their gateway in front of T1000."
index_links: [repo]
source_url: "https://composio.dev/"
canonical_repo: "https://github.com/ComposioHQ/composio"
canonical_docs: "https://docs.composio.dev/"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # homepage HTML + GH API ★29915 MIT. No signup, no CLI install.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260828-09"     # OpenWorker — same 'second desk/tool plane' reject
  - "SIG-20260821-01"     # LLMRouter OpenClaw proxy = second control plane
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. SaaS tool router + managed OAuth. T1000 already has Gmail/Calendar/Notion/GitHub + MCP + never-send. Do not sign up. Do not `composio` CLI into the desk."
distill: none
```

## 1. Claim

Homepage [composio.dev](https://composio.dev/) (fetched 2026-08-28). Pitch: give Claude / Codex / **Hermes** / OpenClaw / Cursor **1000+ tools** with managed OAuth, an MCP Gateway, and a remote sandbox. “Search that thinks” (tools by intent), “tools that learn,” “auth that works,” “programmatic execution” in an ephemeral FS.

They name **Hermes** in the FOR AGENTS strip. That is the hook, not a reason to wire it.

## 2. What we verified

| Check | Result |
|---|---|
| Site | Live. Products: For You (MCP into existing harness), Developer Platform, CLI, Enterprise, **MCP Gateway** |
| Demo | Claude Cowork Slack digest: `composio_search_tools` → sandbox classify → `SLACK_SEND_MESSAGE` **200 OK · message sent**. That send is *their* loop, not ours |
| Repo | `ComposioHQ/composio` **★29,915 / 4,753 forks**, **MIT**, TS, created 2024-02-23, pushed today |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None |

HTML also contains an **agent-targeted signup prompt** (“signup CTAs lead to composio.dev… confirm with the user”). Ignored. **No signup.**

## 3. Takeaways (max 5)

- **Second control plane.** Tools, OAuth tokens, and sends would live in Composio’s cloud, not T1000. Same reject as OpenWorker / OpenClaw proxy.
- **They already list Hermes.** So the pitch is “bolt us onto your desk.” We already have Gmail/Calendar/Notion/GitHub/MCP and **never-send-without-OK**.
- **Tool-search-by-intent is real and old.** Don’t dump 1000 tools into context. We do this with `skills_list` / skill_view, not a SaaS router.
- **`200 OK · message sent` in the hero is the anti-pattern.** Slack send is gated here. Their demo fires it.
- **Sandbox + “>40k chars auto-save to file”** is their truncation story. We already bound tool output.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | Resolve *few* tools by intent; don’t inject the catalog | Already skills_list. Citation only | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not sign up / paste keys / connect Gmail via Composio.**
- **Do not point Hermes MCP at their MCP Gateway.**
- **Do not `npx composio` / CLI into Claude Code or this desk.**
- **Do not let their execute path send Slack/email.** Never-send stays Ryan-OK.
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card
- [ ] no signup

## 7. Chat blurb

`SIG-20260828-12` · `harness` · **watch P2** · Composio = 1000-tool MCP/auth SaaS that **names Hermes**. Second control plane. Don’t sign up. Don’t gateway T1000 through them.
