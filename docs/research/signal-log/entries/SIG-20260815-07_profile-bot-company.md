# SIG-20260815-07 — T1000 Profile-Bot Company: Bot Mode as named faces on existing lanes (not a second OS)

```yaml
id: SIG-20260815-07
date: 2026-08-15
title: "Ryan: optimize newly installed Hermes-Bot-Mode + integrate into K2 / Sov / Proofmark. Public foil: OpenClaw named multi-agent teams vs Claude Cowork one-coworker; Hermes community uses profiles+cron+@handoff. Invention: Company of Faces — 3 business bots (sov/k2/proof) over existing boards+write-gates; lane profiles (flash/worker/orchestrator) stay engines not people."
index_title: "Profile-Bot Company (Bot Mode faces ≠ second OS). Steal P1: 3 business bots + Four Objects Law. Do not spawn lane-profile coworkers or new send crons."
source_url: "https://www.eigent.ai/blog/openclaw-vs-claude-cowork"
source_url_2: "https://x.com/Teknium/status/2088003994904113614"
canonical_repo: "https://github.com/NousResearch/Hermes-Bot-Mode"
canonical_docs: "https://www.tonyreviewsthings.com/hermes-bot-mode-review/"
index_links: [repo, docs]
bucket: product
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [mbp]
stacks_touched: [t1000, k2, sovereign]
related_plans:
  - "SIG-20260813-04"
  - "SIG-20260815-06"
  - "agent-harness-compare"
  - "t1000-model-desk"
  - "AUTOMATION-ROADMAP B25"
status: wired
status_note: "**WIRED 2026-08-15 — faces created, no cards, no send crons, gateways STOPPED.** Profiles `sov` `k2` `proof` at ~/.t1000/profiles/*/ with write-gate SOULs + cloned desk skills/config. Kickoff `create the three faces` done. Bot Chat seeds when Ryan opens each row in Bot Mode. **2026-08-17 public foil:** tonbistudio group-chat (Qwen/GLM/Kimi) ends on human approval — same write-gate. Do not add a fourth face from the video."
distill: mesh_doctrine
```

## 1. Claim

Ryan asked for a deep optimize + integrate pass on the Bot Mode plugin we just installed, plus how the rest of the world uses coworker-roster tech. Public thesis (fetched): OpenClaw-class products win by **named agents with isolated memory**; Claude Cowork wins by **one capable coworker + a task queue**. Hermes Bot Mode is a desktop roster over **profiles we already have**. The T1000-shaped invention is to take the OpenClaw *mental model* and refuse the OpenClaw *runtime*: no second OS, no extra daemons, no send swarm.

## 2. What we verified

### Public usage (fetched this turn)

| Source | Pattern people actually run |
|---|---|
| Teknium Bot Mode launch | One chat per profile; jobs, pics, bot-to-bot; public beta then main Desktop |
| Plugin README / `plugin.js` on this desk | Bot ≡ profile; canonical **"Bot Chat"**; `@mention` → `hermes -p <bot> chat --in ~ -c "Bot Chat"` async; routines = cron `[bot:name]`; hide Bot Chats from Sessions default ON |
| YouTube Bot Mode walkthrough | Handoff discovered as `hermes -p` + Bot Chat; people then cron the handoff |
| r/hermesagent cron thread | Captain's morning brief + contact nudge via Signal — **judgment crons**, not script crons |
| userorbit profile tutorial | Separate profiles for developer / product / researcher / design / support; **do not give every agent the same authority** |
| OpenClaw vs Cowork (Eigent) | OpenClaw = multi-agent teams, isolated memory; Cowork = one coworker + task queue/schedules |
| Tony hub-spoke (already SIG-15-06) | Bot Mode review as a **content hub**, not a product to fork |

### This desk (measured)

| Fact | Implication |
|---|---|
| Plugin at `~/.t1000/desktop-plugins/hermes-bots` | Door works; first load died on `McpTab` — local stub |
| Live profiles = `flash grok worker orchestrator nemo q38 sonnet mac-nail local-experimental` | These are **kanban engines / caps**, not business faces |
| Boards = desk / k2 / arctic / proofmark / joinsov / mesh / career / investing / steals | Already the Company. Bots should *front* boards, not replace them |
| Dual claimer + default_assignee=worker | Bot Mode must not become a third claimer |
| Proofmark: 640 tests, nothing sends; next = **work the call list** + SendGrid warm-up | `proof` bot = call-prep + scoreboard, never outreach |
| ADV freeze until invoice SENT | `sov` bot = file-only inbound / SEND staging, never mail |
| Pulp = VPS-only | Not a Bot Mode bot. Do not Mac-runtime it |

Hardware pre-filter: N/A (UX/ops).

## 3. Takeaways (max 5)

- **Bot Mode is a face layer.** OpenClaw people want named teammates; Cowork people want one partner + a queue. T1000 already has both (this desk chat + kanban). The plugin is how Ryan *sees* the teammates. It is not a new factory.
- **Lane profiles must not become people.** Chatting `flash` or `worker` as a coworker collides with kanban caps and dual-claimer. Business bots are **new named profiles** (`sov`, `k2`, `proof`) or we just use this desk chat + `@` later. Do not SOUL-up the engine profiles.
- **@mention is a human router, not a swarm.** Async Bot Chat mail is honest and weak (no live interrupt). Good for "ask proof to draft the call brief"; bad for mid-turn coding choreography (`delegate_task` / kanban still own that).
- **Routines inherit write-gates.** Community crons (morning brief, contact nudge) are judgment jobs. Ours stay file-first / draft-only / never-send. Prefix `[bot:sov]` on any face-scoped cron so `hermes cron list` is greppable. Do not mint new send crons to "activate" Bot Mode.
- **Three faces beat eight.** `sov` (ADV) · `k2` (Kevin delivery) · `proof` (placement #1). joinsov/career/investing stay parked or talk to this desk until freeze lifts. Mesh/Pulp stay ops, not mascots.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Company of Faces** — 3 durable business profiles with SOUL write-gates + one Bot Chat each; boards stay SoT; @mention from this desk | On Ryan OK only: `hermes profile create sov|k2|proof` with composed SOUL (never-send, two-lane, client RO, no self-GREEN) + skills pin. No ready kanban cards. Hide Bot Chats ON. Do **not** create faces for flash/worker/orchestrator | **P1** | **wired** |
| S2 | Four Objects Law (operational vocab) | Document in `t1000-model-desk`: `desk` (this chat) · `profile-bot` (named face) · `worker` (kanban claimer) · `subagent` (ephemeral) · Path B coworker (Claude CLI) ≠ Bot Mode | P2 | fold into skill |
| S3 | Community cron shape = judgment + Signal/TG notice, files SoR | Map existing ADV/K2 crons onto faces by `[bot:]` rename only — no new jobs until invoice SENT | P2 | park |

**Primary steal (one only):** S1

## 5. Do not

- Do **not** treat Bot Mode as OpenClaw (24/7 send swarm) or as Cowork (replace kanban with one queue).
- Do **not** `@flash` / `@worker` / `@orchestrator` as teammates.
- Do **not** create joinsov/career/investing bots under the freeze.
- Do **not** Mac-runtime Pulp or give a bot calendar-guest / invoice / iMessage send tools.
- Do **not** cron self-delegate from a bot that *is* the runner (upstream open issue).
- Do **not** free-fire `ready` cards to "staff the company."

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [x] STEALS.md row for S1
- [x] AUTOMATION-ROADMAP **B25** (faces, kickoff phrase only)
- [ ] no kanban card (dispatcher would claim)
- [x] create `sov`/`k2`/`proof` profiles (2026-08-15, Ryan kickoff)
- [ ] Ryan: ⌘K Reload desktop plugins → open each face once to seed Bot Chat

## 7. Chat blurb

**SIG-20260815-07** · product · steal **P1** · high  
Bot Mode = faces, not a second OS. Public foil: OpenClaw teams vs Cowork one-queue.  
**Steal:** 3 business bots (`sov` `k2` `proof`) + write-gate SOULs. Lane profiles stay engines.  
⛔ No new send crons. No `@worker`. No Pulp-as-bot.  
Entry: `docs/research/signal-log/entries/SIG-20260815-07_profile-bot-company.md`
