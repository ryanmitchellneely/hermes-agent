---
title: T1000 agent mesh — Ryan fleet + Kevin lane
date: 2026-08-03
status: active
source: Ryan Telegram (priority: agents talking to each other — Kevin lane + Spark/Juice/Pulp/Popper)
---

# T1000 agent mesh

**North star (Ryan, 2026-08-03):** T1000 should reach **Kevin / Kevin's agents** *and* the Ryan-side fleet — **Spark, Juice, Pulp, Popper** — with clear verbs, receipts, and no identity fusion.

This is not one protocol. It is a **router with per-peer doors**.

## Current reality (honest)

| Path | Status | What it is |
|------|--------|------------|
| **Carlton ↔ Chamberlain** | **Live, proven** | Kevin-side only. Carlton holds the sole `kermes:write` bearer; 56-tool MCP read server is **tenant-locked (403 to non-Kevin)**. |
| **Repo inbox** (`inbox-for-kevin-claude` / `inbox-for-ryan-claude`) | **Live, slow** | File-based agent↔agent handoff. Works. Not real-time. |
| **Chamberlain Telegram notify** | **Live (push)** | Kevin-lab / VPS rail: `chamberlain_notify` + bot → Kevin chat. Used 2026-08-03 for competitive-intel PDF (msg 24326). **Human-facing**, not agent round-trip. |
| **T1000 ↔ Chamberlain / Buzz / K2** | **Zero in code** | Fleet grounding (2026-08-02): full-tree grep = no real wiring. By design / incomplete, not accidental. |
| **Ryan "systems" on Chamberlain** | **Telegram-shaped, Buzz unresolved** | ADR-042: Ryan = `CAP_CHAT` only on Telegram role model. Buzz is now sole live conversational body; pubkey auth may not carry systems role. |
| **Identity rule (inbox-124)** | **Hard** | Do **not** fuse Carelton / Chamberlain / Spark-companion / T1000 identities or credentials. |

**Punchline:** You already have **one-way human delivery** (Chamberlain PDF today) and **async agent mail** (repo inbox). You do **not** yet have a first-class **T1000 ↔ Carlton/Chamberlain dialogue loop**.

## What "good" looks like (product shape)

Ordered by value × safety:

### Tier 1 — Reliable handoff (ship without 0.20)

1. **Named delivery skill: `reach-kevin`**  
   One skill T1000 always loads when Ryan says "tell Kevin / send to Chamberlain / ping Carlton":  
   - prefer Chamberlain Telegram (human) when message is for **Kevin-the-person**  
   - prefer `inbox-for-kevin-claude/NNN-*.md` when message is for **kevin-claude / Carlton**  
   - always log path + receipt (message_id or inbox file)  
   - never invent a second bot; never dual-gateway  

2. **Receipts both ways**  
   - Outbound: message_id / inbox path (we did this today)  
   - Inbound: morning inbound already scans; add explicit "from Kevin/Chamberlain/Carlton" bucket in digest  

3. **Shared drop folder convention** (optional fast lane)  
   e.g. `docs/agent-coordination/drops/ryan-to-kevin/` + `kevin-to-ryan/` with YAML frontmatter  
   `{from, to, priority, needs_ack, artifact_paths}` — still git, still auditable  

### Tier 2 — Live operator chat (needs Kevin OK)

4. **Resolve Ryan access on the surface that actually lives**  
   - If Buzz is Chamberlain's body: confirm Ryan pubkey in `BUZZ_OPERATOR_PUBKEYS` **and** whether systems CAP applies  
   - If Telegram still works for systems: document the exact chat + commands Ryan/T1000 may use  
   - **Kevin must ratify** — this is his privilege boundary  

5. **T1000 → Chamberlain notify as a first-class tool**  
   Thin wrapper (not MCP tenant token):  
   - runs on Mac or via SSH to VPS (where `TELEGRAM_KEVIN_CHAT_ID` lives)  
   - text + optional document  
   - framed 🏛️ Chamberlain / "from Ryan · T1000"  
   - fail-closed if both gateways might be live  

### Tier 3 — Protocol mesh (after 0.20 + Kevin design pass)

6. **Herald A2A v1.0** — only with a written peer map  
   - Peers: T1000 (Ryan desk) · Carlton (Kevin desk) · Chamberlain (K2 brain) as **separate principals**  
   - T1000 must **not** get Kevin-tenant MCP bearer  
   - Allowed verbs first: `notify`, `ask_status`, `drop_artifact`, `ack` — **not** Sierra writes / GCI / chip.decide  

7. **Buzz as shared channel** (if both humans already live there)  
   - Herald bundles Buzz gateway — interesting **after** auth model is clear  
   - Still not a substitute for repo SoT on code decisions  

8. **Signed outbound webhooks** (Herald)  
   - T1000 turn-complete → optional Kevin-visible status board  
   - Not a chat replacement; good for "T1000 finished X"  

## Herald 0.20 — reordered for *this* priority

| Feature | Priority for mesh | Action |
|---------|-------------------|--------|
| Mid-turn redirects, compression, self-healing tools | High (keeps T1000 enjoyable + reliable) | Take on upgrade |
| Approvals suggest + denial breaker | High (safer long runs that touch shared rails) | Take on upgrade |
| Outbound signed webhooks | Medium-High (status to Kevin surfaces) | Enable after upgrade |
| A2A v1.0 | **Strategic** for mesh | Design peer map **with Kevin** before enable |
| Buzz native platform | Medium (if Buzz is shared ops surface) | Probe auth; don't guess |
| Grounded-citations | Medium (shared intel quality) | Install when useful |
| Voice barge-in, desktop toys | Low for mesh | Park |

## Upgrade posture (keep T1000 feeling good)

You like this instance. Protect that:

1. **Do not** blind `hermes update` on primary mid-day.  
2. Worktree / branch: merge upstream Herald **onto** `ryan/t1000-failover-stacked` carry (HA + juice doctor commits).  
3. Green bar before cutover:  
   - `hermes doctor`  
   - Telegram single-writer (Mac primary, VPS standby inactive, hb age &lt; 60s)  
   - one cron tick  
   - one DM round-trip  
   - one `reach-kevin` dry-run (inbox only) + one live Chamberlain text (only with Ryan OK)  
4. VPS `/opt/t1000` sync **after** Mac primary is green (standby must match).  
5. Rollback: pin previous venv + git SHA; HA skill emergency dual-gateway stop.

### Carry-forward commits to preserve (load-bearing)

From tip `313176bc` (+9 carried narrative):

- Failover authority: Mac declares, watchdog decides (`313176bc`, `6b3ec04d`)  
- Doctor honesty / juice launcher passthrough cluster  
- Desktop/Juice product commits already on branch — rebase carefully; conflict risk is real  

## Proposed build order (when you say go)

| Step | Work | Needs Kevin? | Needs 0.20? |
|------|------|--------------|-------------|
| **A** | Write `reach-kevin` skill (inbox + Chamberlain notify paths, receipts) | No | No |
| **B** | Script: T1000-safe Chamberlain notify via VPS (text; PDF optional) | No for build; Yes for spam norms | No |
| **C** | One-pager to Kevin: "Ryan systems on Buzz?" + allowed verbs | **Yes** | No |
| **D** | Calm Herald upgrade in worktree → doctor → HA green → cutover | No | **Yes** |
| **E** | A2A peer map draft + spike (discover only, no writes) | **Yes** | **Yes** |
| **F** | Optional: shared drops/ + webhook status lane | Soft | Webhooks yes |

## Anti-patterns

- Giving T1000 a Kevin-tenant Chamberlain MCP token "so it can do everything Carlton does"  
- Dual Telegram gateways during mesh tests  
- Treating repo inbox as obsolete the day A2A lands (keep SoT for code/PR handoffs)  
- Fusing souls/personas across Ryan and Kevin agents  
- Building mesh during client send fire without &lt;30 min clear win  

## Open questions for Ryan / Kevin

1. Primary human surface for Kevin: **Buzz, Telegram, or both?**  
2. Should T1000 ever message **Carlton** directly, or only Kevin-human + kevin-claude inbox?  
3. Is a **shared Slack/Buzz channel** acceptable for agent status, or keep DMs + repo only?  
4. When do you want Step A (`reach-kevin` skill) — **now** (pre-upgrade) or after Herald?

---

## Ryan-side fleet (Spark / Juice / Pulp / Popper)

These are **separate code trees**, not T1000 personas. Scoreboard already tracks four boards: juice, pulp, popper, proofy — T1000 is the desk operator that should be able to **call** them.

| Peer | What it actually is | Where it lives | How T1000 reaches it *today* | Target reach (verbs) |
|------|---------------------|----------------|------------------------------|----------------------|
| **Spark** | Inference substrate (Ollama on DGX) — not a chat buddy | Host `spark`; tunnel `127.0.0.1:11435` → remote 11434 | `spark_tunnel.sh`; `SPARK_ENABLED` tools (e.g. `comm_comprehension` on feature branch) | `status`, `up`/`down` tunnel, `complete` (reason/format models), health |
| **Juice** | Two things glued by one launcher: (1) Electron/T1000 cockpit brand (2) **`sovereign_juice` CLI** classifier engine | `sovereign-consulting/tools/juice` · `python -m sovereign_juice` · Buzz digests on VPS | `juice status/classify/triage/doctor` via launcher passthrough (local commits already teach honest v2 status) | `status`, `classify`, `triage`, `r0` eval, `threshold` — **read/classify only** unless rungs authorize more |
| **Pulp** | Tooled, memory-holding operator agent; straddles ADV + K2 *topics*; **cannot send** by charter | Juice bridges (`pulp_core`, ACP `buzz_acp_pulp`) · VPS `buzz-agent-pulp.service` | Mostly **indirect** (Buzz ACP on VPS). T1000 has no first-class `ask_pulp` | `ask` / `plan` (authorized), `status`, `commitments_list` — never send/Sierra |
| **Popper** | Labs / autonomous scientist boundary — **not imported into Juice** | `/opt/t1000-lab/labs` · user `t1000lab` (CadensPC / lab box) | Boundary only from T1000; labs tree separate | `list_labs`, `lab_status`, `enqueue_lab` (human-gated), read findings |

### Identity rules (do not collapse)

| Name | Is |
|------|-----|
| T1000 | Personal desk agent (this gateway) · Grok/xAI-oauth default |
| Juice (CLI) | Classifier + digests package — **not** the same process as T1000 gateway |
| Juice (desktop) | Often T1000 Electron under a brand — launcher illusion |
| Pulp | Operator agent on Buzz ACP + pulp_core — fail-closed auth |
| Popper | Labs resident — separate user/tree |
| Spark | GPUs + models — **substrate**, address via URL not soul |
| Carlton / Chamberlain | Kevin lane — separate mesh branch |

**Forbidden:** one bearer/token that is “T1000 but also Pulp and Chamberlain.”  
**Required:** per-peer adapter + receipt.

### Spark detail

- Models expected on tunnel: `gpt-oss:120b` (reason), `hermes3:8b-16k` (format/JSON)
- CadensPC is a **separate** tunnel (`11436`) — not critical path; Popper/lab warm only
- Juice classify was recently **DOWN** when `11435` unreachable — T1000 mesh health must surface tunnel age
- Skill already exists: `t1000-spark-tools` (tunnel + SPARK-gated tools)

### Juice detail

- Live surfaces largely `sovereign_advisory` profile; `k2_real_estate` mostly unexercised
- Input scope can be “live-authorized (real comms, read-only)” while classify model is down — status must split **auth** vs **model**
- T1000 launcher already growing juice subcommand passthrough (local commits) — extend into mesh router

### Pulp detail

- Charter: no send, no outreach draft, no mail, no Sierra — gates in code + tests
- Reach path is primarily **Buzz ACP** on VPS, not a local Hermes tool loop
- T1000 should SSH/CLI into a **narrow ask interface** (or Buzz message to Pulp channel) rather than importing pulp_core into the gateway process

### Popper detail

- Treat as **lab control plane**: list experiments, read LAB findings, optionally queue work with human OK
- Do not claim LAB completion from scoreboard alone (known stale contradictions in fleet pack)

---

## Unified router: `reach` (expands `reach-kevin`)

One skill / CLI surface:

```text
reach <peer> <verb> [--payload ...]
```

| Peer aliases | Verbs (v1) |
|--------------|------------|
| `kevin` / `chamberlain` | `notify`, `inbox`, `ack_status` |
| `carlton` | `inbox` only until Kevin OK |
| `spark` | `status`, `tunnel_up`, `tunnel_down`, `models` |
| `juice` | `status`, `classify`, `triage`, `doctor` |
| `pulp` | `status`, `ask` (auth-gated) |
| `popper` | `status`, `labs`, `findings` |

Every call returns:

```yaml
peer: juice
verb: status
ok: true|false
receipt: <path|message_id|http>
as_of: ISO-8601
grade: live|stale|error
```

### Implementation layers (don’t wait for A2A)

| Layer | Mechanism | Peers |
|-------|-----------|-------|
| **L0 local CLI** | subprocess to known bins (`juice`, tunnel scripts, lab SSH) | spark, juice, popper |
| **L1 VPS exec** | `ssh k2vps` systemctl/status + pulp ask helper | pulp, juice digests, scoreboard |
| **L2 human notify** | Chamberlain Telegram / Buzz post | kevin |
| **L3 async mail** | repo inbox / drops/ | kevin-claude, optional pulp/popper work orders |
| **L4 protocol** | Herald A2A / Buzz native (later) | any peer that speaks it |

L0–L3 make the mesh **real on 0.17**. L4 is polish after upgrade + Kevin design.

---

## Revised build order

| Step | Work | Depends | Status |
|------|------|---------|--------|
| **A0** | `reach` skill skeleton + receipt schema | none | **done 2026-08-03** (`t1000-reach`) |
| **A1** | `reach spark status|tunnel_*` | spark tunnel scripts | **done 2026-08-03** — live smoke: tunnel-up → grade=live |
| **A2** | `reach juice status|classify|doctor` | juice launcher | **done 2026-08-03** |
| **A3** | `reach kevin notify|inbox` (Chamberlain + inbox-168 pattern) | VPS telegram env | **done 2026-08-03/04** |
| **A4** | `reach pulp status|ask` (VPS, auth-gated, no send) | pulp/buzz on VPS | **done 2026-08-04** |
| **A5** | `reach popper status|labs|findings` | SSH k2vps `/opt/t1000-lab` | **done 2026-08-04** |
| **B** | Health strip: one `reach all status` for morning digest | A1–A5 | **done 2026-08-04** |
| **C** | Kevin one-pager (Buzz + allowed verbs) | human | pending |
| **D** | Herald 0.20 upgrade (compression, webhooks, A2A later) | calm window | pending |
| **E** | A2A peer map only for peers that benefit (likely Carlton/Pulp, not Spark-the-GPU) | D + design | pending |

**Install path:** `~/.t1000/skills/software-development/t1000-reach/` · launcher `~/.t1000/bin/reach`  
**SPEC:** `~/Documents/T1000/docs/reach/SPEC.md`

---

## Anti-patterns (fleet-specific)

- Calling Spark “an agent” in user copy — it’s **compute**
- Assuming `juice` CLI == T1000 gateway process
- Importing Pulp into T1000 to “make it faster” (privilege + send-lint boundary)
- Giving T1000 write paths into Popper labs without ceremony
- One mega-prompt that routes all four peers through Grok without receipts

---

## Related

- Fleet grounding: `sovereign-consulting/docs/research/2026-08-02-agent-fleet-architecture/` (apply VERIFY corrections in header)
- HA: skill `t1000-gateway-ha`
- Spark tools: skill `t1000-spark-tools`
- Juice package: `sovereign-consulting/tools/juice`
- Today’s Kevin human rail proof: Chamberlain PDF msg 24326
- Herald: v0.20 A2A/webhooks as **later** transport, not the definition of mesh
