# SIG-20260813-03 — Influencer rehash of first-party Hermes↔Buzz docs: three integration paths (Desktop runtime / buzz-acp relay / native gateway); only path ③ keeps full Hermes memory·skills·cron·approvals

```yaml
id: SIG-20260813-03
date: 2026-08-13
title: "AI Edge (@aiedge_) 'FULL GUIDE' to Hermes Agent + Buzz — long-form X article that is mostly a rewrite of hermes-agent.nousresearch.com/docs/integrations/buzz. Useful as a traffic signal that the three-path matrix is now public and being promoted; not a new capability. Official paths: ① Buzz Desktop managed runtime (auto-discovers hermes-acp; auto-approves tools) ② buzz-acp relay bridge (Buzz owns transport, Hermes via ACP stdio) ③ native gateway platform (recommended for full Hermes — memory/skills/approvals/cron; NIP-42 Nostr WS + buzz CLI). Third-party tonbistudio/buzz-skills (hermes-in-buzz) is MIT, not Nous-shipped — treat as untrusted credential surface."
index_title: "Hermes↔Buzz three-path matrix is first-party (Nous docs), not an aiedge scoop. Path ③ = full Hermes as a messaging platform; ① Desktop auto-approves tools (owner-only). We already use Buzz for K2 dual-notify / #codex-build / Pulp ACP — this does not auto-wire T1000 into Kevin's rooms. Watch + P1 posture: if Ryan wants a T1000 identity in Buzz, pick ③ with a dedicated keypair; never install tonbistudio skills into ~/.t1000 without review."
source_url: "https://x.com/aiedge_/status/2087665959557566800"
source_url_2: "https://x.com/aiedge_/status/2087542215673569789"
canonical_repo: "https://github.com/block/buzz"
canonical_docs: "https://hermes-agent.nousresearch.com/docs/integrations/buzz"
index_links: [repo, docs]
bucket: harness
posture: watch
steal_rank: P1
confidence: high          # both posts + full X Article body via fxtwitter; official Nous integration + messaging docs read live; local skill tree already references Buzz extensively
hardware_fit: [mbp, vps, spark, none]
stacks_touched: [t1000, k2, pulp]
related_plans:
  - "T1000-KEVIN-AGENT-MESH-PLAN"   # Buzz as shared channel still open questions
  - "CLAUDE-ACP-LANE"               # Path C = Buzz-analog ACP inside Hermes
  - "kevin-dual-notify"             # existing human notify path — not replaced by this
  - "SIG-20260811-02"               # browser-use / first-party Hermes surface
  - "SIG-20260811-03"               # unsloth start hermes — same class: third-party launcher vs our HERMES_HOME
status: open
status_note: "**UPDATED 2026-08-18 — aiedge Grok Bot + Hermes + Buzz stack.** Same promo machine, new pairing. Their split (Grok Bot = app/CRM orchestrator, Hermes = cheap always-on, Buzz = one workspace) is **inverted vs this desk**: Grok (xai-oauth) is already the chair; Hermes is the OS; Buzz is Kevin-facing notify, not desk GREEN. No install. No T1000 Buzz join. No Grok Bot second OS."
updated: 2026-08-18
distill: none
```

## 0. 2026-08-18 follow-up — Grok Bot + Hermes (still this entry)

[@aiedge_](https://x.com/aiedge_/status/2089454218923163770) (75.6k fol; 153 likes / 7 RT / 290 bookmarks / 11.6k views; note tweet). **No SIG-18-02.**

Thesis: “Grok Bot + Hermes is the most powerful agentic setup.” Complementary, not competitors.

Their split:
- **Grok Bot** = cloud computer per agent, sign into Salesforce/Slack/Gmail/Figma/CRM, model flexibility (Opus / Claude / GPT-5.6)
- **Hermes** = sovereignty, self-hosted memory, **$5–10/mo vs $120–300/mo**
- **Bus** = Buzz workspace, *or* Grok Bot CoS delegates to Hermes via webhook / shared task file

Our desk already has the stack, **inverted**:
- Chair = **Grok via xai-oauth** (not “Grok Bot” cloud VMs)
- OS = **T1000 Hermes** (gateway, memory, kanban, never-auto-send)
- Buzz = **Kevin-facing notify** (`kevin-dual-notify`), **not** desk GREEN / merge / personal ack (that’s Telegram DM)

“Grok Bot Chief of Staff delegates to Hermes” would make a third-party cloud agent the orchestrator over our SoT. **No.**

$5–10 vs $120–300 is influencer math. We already pay subscriptions and **do not add provider API keys**.

## 1. Claim

[@aiedge_](https://x.com/aiedge_/status/2087665959557566800) (AI Edge / Miles Deutscher hub; ~75.5k followers; 129 likes / 16 RTs / 269 bookmarks / 21.4k views at read; 2026-08-12 22:22 UTC):

> Nous Research released a FULL GUIDE on how to connect Hermes Agent to Buzz.
> It's a complete cheat code that allows Hermes to be fully integrated into your AI-native workspace.

Quotes an X Article (same author): **[How to Connect Hermes Agent + Buzz (step-by-step guide)](https://x.com/aiedge_/status/2087542215673569789)** (article id `2086875769045913600`, created 2026-08-12 14:10Z). Article TOC: Buzz explained → two "best" connect routes → third-party `buzz-skills` hack. Points readers at official docs for verification.

Sibling promo: [2087588680278102233](https://x.com/aiedge_/status/2087588680278102233) — "three ways… memory, skills, and full context."

## 2. What we verified

### Official matrix (source of truth — not the article)

From `hermes-agent.nousresearch.com/docs/integrations/buzz` (read live):

| | ① Desktop runtime | ② Relay bridge (ACP) | ③ Native gateway platform |
|---|---|---|---|
| What | Buzz Desktop spawns Hermes locally as managed harness | `buzz-acp` bridges channel → `hermes acp` over stdio | Hermes gateway joins Buzz as first-class messaging platform |
| Hermes runs | On desktop, launched by Buzz | On server, launched by buzz-acp | In your gateway, beside TG/Discord/etc. |
| Best for | Zero-config try | Hosted agent identity; Buzz owns transport | **Full Hermes: memory, skills, approvals, cron, sessions** |
| Inbound | ACP stdio | ACP stdio via relay WS | NIP-42-authenticated Nostr WS (poll fallback) |
| Setup | Auto discovery of `hermes-acp` on login-shell PATH | buzz-acp env vars | `hermes gateway setup` → Buzz |

Docs pick guide:
- exploring / Desktop user → ①
- community relay, Buzz-managed identity → ②
- **already run Hermes as the agent, want Buzz as another channel → ③** (deepest)

Also: ①/② and ③ use **different identities/transports**; run ③ with a **dedicated Nostr keypair**. Adapter takes a scoped lock on relay+pubkey — two Hermes profiles cannot drive one Buzz identity.

### Messaging adapter details (path ③)

From `/docs/user-guide/messaging/buzz`:
- Outbound = `buzz` CLI (JSON in/out); inbound = bundled `websockets` NIP-42 sub, CLI poll fallback
- Prereqs: `buzz` binary on PATH (`cargo build --release -p buzz-cli`), community relay URL, member nsec
- Secret: `BUZZ_PRIVATE_KEY` in env only (never argv/logs)
- Recommended channel hygiene: `interim_assistant_messages: false`, `tool_progress: off`, `require_mention: true`, private allowlist by default
- Cron: `deliver=buzz` → home channel
- Notes still mention poll latency on CLI path; WS is the preferred inbound

### Article vs docs (delta)

| Article claim | Docs reality |
|---|---|
| "Two best ways" | **Three** official paths; article under-weights ② |
| Desktop auto-finds Hermes | True — `hermes-acp` on `~/.local/bin` |
| Gateway one command keeps memory/skills | True for **③** |
| `tonbistudio/buzz-skills` / `hermes-in-buzz` | **Third-party MIT**, explicitly "NOT something Nous shipped" — article does flag this |
| "Slack killer" / "AI employee" | Marketing; not measured |

### What we already do with Buzz (local skill tree — not inferred)

- **kevin-dual-notify** — Chamberlain + Buzz `#k2-hq` on Ryan OK (human notify, not Hermes gateway)
- **GEO / measurement** — Buzz `#stats` steward posts
- **Codex lane** — Buzz `#codex-build` managed agent (implementation), not T1000 codey
- **Pulp** — VPS `buzz-acp` / ACP path (path ②-class), T1000 reaches via SSH ask, no Buzz post from Mac
- **Claude Path C** — `claude-agent-acp` binary lives under Buzz `node-tools`; Hermes spawns it (Buzz-analog ACP *inside* desk, not T1000-as-Buzz-member)
- **Mesh plan** still lists open Qs: Ryan systems role on Buzz, shared channel acceptability, native platform later

So this signal is **documentation maturity + distribution**, not a greenfield integration.

### Third-party skill risk

`github.com/tonbistudio/buzz-skills` — article instructs `cp -R … ~/.hermes/skills/`. On this desk the live home is **`~/.t1000`**, and skills go through curator/pin policy. **Do not** copy unknown skills that handle nsec / relay URLs into the profile without a read of every script.

## 3. Takeaways (max 5)

- **First-party three-path matrix is the artifact**; aiedge is a megaphone. Prefer Nous docs over the article for any setup.
- **Only path ③ = "Hermes as we run it" inside Buzz.** ① is a try-path and **auto-approves tool permissions** (docs: keep agents owner-only). ② is closer to how Pulp already rides ACP.
- **T1000 is not automatically a Buzz member.** Dual-notify and #codex-build do not imply gateway Buzz is on. Wiring ③ needs a dedicated keypair, relay URL, allowlist, and Ryan OK to send/appear in Kevin rooms.
- **Identity isolation is designed in** — one relay+pubkey lock per adapter; don't share the Kevin-agent nsec with T1000.
- **Channel hygiene defaults matter** — suppress interim tool spam or K2 channels become a tool log.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Path picker before any Buzz wiring** — Desktop (try) / ACP-relay (Buzz-owned transport) / native gateway (full Hermes). Match to existing surfaces: Pulp≈②, dual-notify=human post, T1000 desk today=neither-as-member | One short decision note in mesh plan or skill ref: "T1000 Buzz identity = ③ only, dedicated nsec, require_mention + allowlist; never ① for prod" | **P1** | open — Ryan word |
| S2 | Official recommended display defaults for shared agent channels (`interim_assistant_messages: false`, `tool_progress: off`, `require_mention: true`) | If/when path ③ is enabled under `HERMES_HOME=~/.t1000`, apply these before first join; mirror onto any other multi-human platform | P2 | gated on S1 |
| S3 | Third-party "setup skill" that writes credentials = supply-chain surface | Default deny `tonbistudio/buzz-skills`; if ever wanted, read-only review + skill_manage, never raw `cp` into profile | P2 | log only |

**Primary steal (one only):** S1

## 5. Do not

- Do **not** run `hermes gateway setup` → Buzz or set `BUZZ_PRIVATE_KEY` from this chat — needs explicit Ryan OK (send/appear surface).
- Do **not** install `tonbistudio/buzz-skills` into `~/.t1000/skills`.
- Do **not** use Buzz Desktop path ① as the production T1000 brain (auto-approve + separate identity/lifecycle).
- Do **not** reuse Pulp/Kevin agent keypairs for a T1000 identity.
- Do **not** treat the aiedge article as more authoritative than `docs/integrations/buzz`.
- Do **not** stand up “Grok Bot” as a second OS or let it CoS-delegate over T1000.
- Do **not** move desk GREEN / personal ack onto Buzz because this tweet says “one workspace.”

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [x] STEALS.md row for S1 (decision, not install)
- [x] 2026-08-18: Grok Bot + Hermes stack noted (no new SIG)
- [ ] no kanban card until Ryan answers: "T1000 native Buzz identity — yes/no/later?"
- [ ] if yes → path ③ checklist only (dedicated nsec, relay, allowlist, display defaults); draft config, don't enable

## 7. Chat blurb (paste-ready, ≤6 lines)

**SIG-20260813-03** · harness · watch · steal **P1**
aiedge 08-18: Grok Bot + Hermes via Buzz. Their split is **inverted** — Grok is already the chair, Hermes the OS, Buzz is Kevin-notify not desk GREEN.
**Steal unchanged:** path ③ only on Ryan OK. No Grok Bot install. No webhook CoS.
