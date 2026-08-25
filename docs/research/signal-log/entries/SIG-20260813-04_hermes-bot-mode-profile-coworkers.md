# SIG-20260813-04 — Nous ships Hermes-Bot-Mode the same day: desktop plugin that reframes multi-agent as a **roster of named profiles ("coworkers")** with per-bot chat, cron routines, and Agent-Inbox handoffs — not nested subagents

```yaml
id: SIG-20260813-04
date: 2026-08-13
title: "Mreatived points at github.com/NousResearch/Hermes-Bot-Mode (@Teknium) — 'not subagents instead co-workers.' Verified first-party: brand-new Nous org repo (created 2026-08-13 16:40Z, MIT, ★57, JS desktop plugin), single plugin.js (~92 KB / 2765 lines) on @hermes/plugin-sdk. A bot IS a Hermes profile under profiles/<name>/; UI over existing primitives (profiles.* RPCs, cron, cross-profile hermes -p chat). Features: Bots roster pane, New Agent + SOUL.md/skills/model pin, avatars/pets, Routines pane = namespaced cron, bot-to-bot via persistent 'Agent Inbox' + @mention handoffs. Explicitly no core patches / no extra daemons. Install path ~/.hermes/desktop-plugins/ — does NOT land on T1000 HERMES_HOME=~/.t1000 without a deliberate map."
index_title: "Hermes-Bot-Mode (Nous, same-day ★57 MIT): multi-agent = named profile roster + Agent Inbox + @handoffs, not nested subagents. Bot≡profile; cron namespaced [bot:name]; delivery is hermes -p <bot> chat -c 'Agent Inbox'. Pattern steal for T1000; plugin install is stock-desktop-only unless T1000 Desktop grows the same plugin SDK path. Do not clone into ~/.hermes while desk is ~/.t1000."
source_url: "https://x.com/Mreatived/status/2087948651448414555"
source_url_2: "https://x.com/Teknium/status/2088003994904113614"
canonical_repo: "https://github.com/NousResearch/Hermes-Bot-Mode"
canonical_docs: "https://github.com/NousResearch/Hermes-Bot-Mode/blob/main/README.md"
index_links: [repo]
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # post via fxtwitter; repo meta/README/plugin.js/issues via GitHub API+raw — no install, no desktop run
hardware_fit: [mbp]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "t1000-model-desk"          # Path B 'coworker' naming collision — different thing
  - "SIG-20260813-03"           # Buzz path matrix — another multi-surface identity question
  - "SIG-20260811-02"           # first-party Hermes surface expansion
  - "kanban workers / profiles" # existing multi-agent SoT on this desk
status: open
status_note: "**UPDATED 2026-08-17 — Nous community (witcheer) + tonbistudio group-chat video.** Weekend Bot Mode upgrade; 'fully integrated into Hermes Desktop this week.' Public demo = Qwen/GLM/Kimi specialist bots in a group chat, last step = human approval. Plugin still at ~/.t1000/desktop-plugins/hermes-bots (clone 08-15, not pulled). Operating model stays SIG-20260815-07. No card. Do not git-pull weekend upgrade without Ryan OK."
updated: 2026-08-17
distill: none
```

## 0. Same-day promo wave (no new fork)

Also promoted 2026-08-13 by [@Teknium](https://x.com/Teknium/status/2088003994904113614) (official: one-day public beta of Desktop plugin, feedback→main Desktop) and long-form by [@IBuzovskyi](https://x.com/IBuzovskyi/status/2088026524255453305) (same README facts). **Duplicate URL rule:** update this entry, do not open a new SIG for Bot Mode again.

2026-08-14/15: [@tonysimons_](https://x.com/tonysimons_/status/2088135760880730502) published a long-form review ([tonyreviewsthings.com/hermes-bot-mode-review](https://www.tonyreviewsthings.com/hermes-bot-mode-review/), 4.5/5) that restates README facts we already verified. His 08-15 follow-up is a **content half-life / hub-spoke** thesis with this review as the hub — filed separately as **SIG-20260815-06** (product P2), not a Bot Mode fork.

2026-08-17: [@witcheer](https://x.com/witcheer/status/2089229258312814979) (Nous community, 15.5k fol; 151 likes / 164 bookmarks / 13k views) quote-tweeted [@tonbistudio](https://x.com/tonbistudio/status/2089226021749030999) (16.6k fol; 310 likes / 216 bookmarks / 22k views; 5:16 video). **Still this entry — no SIG-17-01.**

Witcheer: weekend Bot Mode upgrade; ask for feedback; **“should be fully integrated into your Hermes Desktop app this week.”**

tonbistudio demo (group chat, not 1:1 Agent Inbox):
- Qwen Bot is on a 2D puzzle-platformer
- GLM Bot offers help (last project done)
- Qwen judges GLM a fit for frontend-heavy next phase
- Kimi Bot names the ticket + current workflow
- GLM reads docs, **asks the human for approval** before picking it up

That last beat is our write-gate, not a new OS. Specialists-by-skill matches SIG-20260815-07 faces ≠ lane profiles. Local plugin mtime is **2026-08-15** — weekend upstream is **not** pulled.

## 1. Claim

[@Mreatived](https://x.com/Mreatived/status/2087948651448414555) (11 followers; 40 likes / 3 RTs / 46 bookmarks / 4,208 views at read; 2026-08-13 17:05 UTC), fetched via fxtwitter:

> https://github.com/NousResearch/Hermes-Bot-Mode
> @Teknium is this the new "big thing", not subagents instead co-workers.
> I was literally gonna look for a pi extension for this and then you suddenly created a new repo. What a coincidence.
> It is similar to the cloudflare/openai hack incident. I dunno

The tweet is a low-follower pointer. **The signal is the repo**, first-party Nous, authored/merged by Teknium the same calendar day.

## 2. What we verified

### Repo (GitHub API, read live)

| Field | Value |
|---|---|
| full_name | `NousResearch/Hermes-Bot-Mode` |
| created_at | **2026-08-13T16:40:20Z** (hours before the tweet) |
| pushed_at | 2026-08-13T21:26:37Z |
| license | **MIT** |
| stars / forks | **57** / 9 |
| language / size | JavaScript / 1219 KB git |
| tree | `LICENSE`, `README.md`, `plugin.js` (**92,200 B / 2,765 lines**), `docs/*.png` screenshots |
| default branch | `main` |
| top contributor | `teknium1` (13 commits at read) |
| issues | 5 open (cron self-delegation bug, provider dropdown, Profile tab, group agents, persistent messaging protocol) |
| PRs merged | #6 "Add real multi-profile Teams", #7 "@agent handle in roster" |

Description (verbatim): *“Bot Mode for the Hermes desktop: a roster of named agents with their own chats, avatars, routines, and bot-to-bot messaging. Desktop plugin, no core patches.”*

### Architecture (README + `plugin.js` header / RPC greps)

**A bot IS a Hermes profile** — isolated config, memory, skills, credentials, chat history under `~/.hermes/profiles/<name>/`. The plugin is a UI over that primitive:

| Feature | Mechanism |
|---|---|
| Bots pane | One row per profile; click → that bot's chat (cross-profile session nav) |
| New Agent / Edit | `profiles.list/create/describe/configure` gateway RPCs; Advanced → clone profile, pin provider/model, custom `SOUL.md`, skip bundled skills, per-skill/toolset enablement |
| Duplicate | Full clone: config, skills, SOUL.md, memory, look |
| Avatars | Geometric faces / upload / `image.generate` RPC / pixel **pet**; meta in plugin storage + `ui_meta['hermes-bots']`; assets via `profiles.set_asset` |
| Routines pane | Hermes **cron** namespaced `[bot:<name>] <routine>`; also visible in `hermes cron list` + core Cron page |
| Bot-to-bot | Persistent **Agent Inbox** conversation per bot; delivery = `hermes -p <bot> chat -c "Agent Inbox" -q "..."` with attribution `[Message from agent 'researcher']`; SOUL.md teaches protocol |
| @mentions | Composer middleware: `@researcher have a look` → active bot hands off, waits, reports back |

**Explicit non-goals / limits (README):**
- No core patches, no background daemons, no extra storage beyond standard Hermes surface
- Profile **delete** not in UI → `hermes profile delete <name>`
- Bot-to-bot is **per-invocation** (receiver sees mail when it next runs); live interrupt of a mid-turn bot = upstream future work
- Requires Hermes desktop with plugin SDK; `profiles.*` / `image.generate` need hermes-agent ≥ mid-2026 (`hermes update`); older gateways degrade (roster still works)

Install (official):
```bash
git clone https://github.com/NousResearch/Hermes-Bot-Mode ~/.hermes/desktop-plugins/hermes-bots
# Ctrl+K → "Reload desktop plugins"
```

`plugin.js` imports from **`@hermes/plugin-sdk`** (`host`, `atom`, UI kit, `COMPOSER_AREAS`, `PALETTE_AREA`, …). ID = `hermes-bots`. RPCs referenced: `profiles.configure|create|describe|get_asset|list|set_asset`, `image.generate`.

### Fit to this desk (measured paths, not vibes)

| Desk fact | Implication |
|---|---|
| Live control plane `HERMES_HOME=~/.t1000` (wrapper + memory) | Stock install path `~/.hermes/desktop-plugins/…` **misses** the running home |
| Profiles already exist as a Hermes primitive; T1000 has `profiles/` under home | The *model* (bot≡profile) is already ours; the *roster UX + Agent Inbox protocol* is the new productization |
| Multi-agent today = kanban workers, `delegate_task`, Path B "coworker" (= Claude CLI subprocess), optional extra profiles | Bot Mode is a **durable named roster with mail**, not a nested subagent fan-out and not Path B |
| T1000 Desktop / Hermes desktop plugin SDK parity | **Not verified this turn** — do not assume the plugin loads in T1000.app without a spike |
| Naming collision | Desk skill `t1000-model-desk` Path B **"coworker"** = Claude subprocess. Bot Mode "co-workers" = **peer profiles**. Different objects — keep the words straight in chat |

### Hardware pre-filter

N/A (harness/UI). No PCIe/KV claim.

## 3. Takeaways (max 5)

- **Product thesis:** multi-agent UX should look like **named coworkers with inboxes**, not an invisible subagent tree. Matches the tweet's framing; repo implements it on top of profiles.
- **Zero new runtime** — if you already trust profiles + cron + `hermes -p`, you already have the backend. The plugin is discovery + ritual (SOUL teaches inbox protocol, @mention handoff, avatar chrome).
- **Delivery semantics are honest and weak:** bot-to-bot is async mail into Agent Inbox on next run, not a live interrupt bus. Don't plan synchronous multi-agent choreography on it.
- **Install path is stock-Hermes-desktop-shaped.** On a `HERMES_HOME=~/.t1000` desk, blind `git clone … ~/.hermes/desktop-plugins` is the wrong home (same class of footgun as `unsloth start hermes` writing the wrong control plane).
- **Open issues already show the hard parts** people want next: Teams/grouping, persistent messaging protocol, cron self-delegation bugs when the bot *is* the runner — i.e. the roster UX is the easy half.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Coworker = durable profile + named inbox channel + attribution line + SOUL protocol** — not `delegate_task` children and not Path-B Claude subprocess | Document a T1000 multi-agent vocabulary strip: `subagent` (ephemeral child) · `worker` (kanban claimer) · `profile-bot` (durable peer w/ Agent Inbox). Optionally stand up one non-default profile with an `Agent Inbox` session and a SOUL blurb that knows `[Message from agent '…']` — **no desktop plugin required** | **P1** | open |
| S2 | Routines UX = cron **namespaced to the bot you have focused** (`[bot:<name>] …`) so schedule lives next to identity | When adding profile-scoped crons under `~/.t1000`, adopt the `[bot:name]` name prefix so `hermes cronjob list` is greppable by identity | P2 | fold into cron hygiene |
| S3 | Desktop plugin as thin UI over gateway RPCs (`profiles.*`) with feature-detect degrade | Proved 2026-08-15: T1000.app loads `~/.t1000/desktop-plugins/`. Stock plugin named-imports `McpTab`/`ToolsetConfigPanel` missing from this SDK — stub null. Operating model → SIG-20260815-07 | P2 | **done** |

**Primary steal (one only):** S1

## 5. Do not

- Do **not** `git clone` into `~/.hermes/desktop-plugins` on this machine as a "setup" step — wrong home, and desktop plugin load path for T1000.app is unproven.
- Do **not** replace kanban workers or `delegate_task` with Bot Mode; different job (board claim vs chat coworker).
- Do **not** call Path B "coworker" and Bot Mode "co-worker" interchangeably in plans — rename in prose when both appear.
- Do **not** assume bot-to-bot is synchronous or that mid-turn interrupt works (README says it doesn't).
- Do **not** expose profile delete in any UI we build without the same intentional omission (or a confirm gate) — they left it CLI-only on purpose.

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [x] STEALS.md row for S1
- [x] 2026-08-17: witcheer + tonbistudio group-chat demo noted (no new SIG)
- [ ] no git-pull of weekend Bot Mode into `~/.t1000/desktop-plugins/hermes-bots` until Ryan OK
- [x] optional spike: T1000 Desktop **does** load `~/.t1000/desktop-plugins/` (2026-08-15). Operating model → SIG-20260815-07

## 7. Chat blurb (paste-ready, ≤6 lines)

**SIG-20260813-04** · harness · steal **P1** · high
Nous Bot Mode. 08-17: weekend upgrade + Desktop integration “this week.” Public demo = group-chat specialists (Qwen/GLM/Kimi) + **human approval**.
**Steal unchanged:** profile-bot + named inbox. Operating model = 15-07.
⛔ Don’t pull weekend plugin without OK. Local clone is 08-15.
