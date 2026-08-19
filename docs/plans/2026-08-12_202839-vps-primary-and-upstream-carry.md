# VPS-primary desk + upstream carry (A+2+3) Implementation Plan

> **For Hermes:** Implement only after Ryan kickoff phrases on the epic or phase cards.
> Board: **mesh**. Plan file is SoT; kanban cards are the work queue.
> **Do not** free-fire topology flip or blind `hermes update`.

**Goal:** Move **the entire T1000 Hermes desk** to k2vps so the Mac can be off/asleep indefinitely. Mac becomes **glass only** (Cursor / T1000.app / SSH) — not the control plane. Also absorb current Nous `origin/main` into the carry branch so fleet SHA is current before cutover.

**Ryan lock (2026-08-12 follow-up):** “I would rather my entire hermes is on the VPS.”  
→ **Not** Mac-primary HA with occasional promote.  
→ **Not** sticky VPS chat with crons still Mac-local.  
→ **Yes:** VPS owns gateway + cron + `HERMES_HOME` SoT + skills + memory + kanban boards + sessions. Mac does not run `ai.hermes.gateway` in steady state.

**Architecture:** Two parallel tracks with a hard join gate.
1. **Track U (upstream carry #3)** — get `~/Documents/T1000` onto a proven tip that includes latest Nous main **plus** T1000 carry (HA, reconciler, kanban locks, wrap_untrusted, MESH-TEL, etc.).
2. **Track V (full VPS residency)** — upgrade VPS engine+home to fleet SHA, **full home migration** (not lean standby slice), invert topology to VPS-only writer, port **all** portable crons + workspace mirrors, disable Mac gateway, prove laptop-off for days.

**Tech stack / hosts:** Hermes 0.20+ git tree · **SoT `HERMES_HOME` = VPS `/opt/t1000/home`** (Mac `~/.t1000` becomes cold mirror / emergency only) · systemd `t1000-gateway` always on · Mac launchd gateway **bootout** in steady state · juice-doctor desired-state `primary=vps` · xAI OAuth refresh on VPS (hybrid Mac-refresh only as temporary bridge).

**Decision date:** 2026-08-12 (Desktop session). Scope = **A + 2 + 3** with end-state upgraded to **full VPS residency**. Mini (path B) is **not** required if VPS acceptance passes.

---

## 0. Non-negotiable laws

1. **One Telegram writer only.** Never dual `getUpdates` on the T1000 bot token.
2. **No blind `hermes update` on primary.** Fork is diverged (carry slice + main tip).
3. **No Mac gateway hand-start while VPS is serving** (reconciler refuse).
4. **No outbound send/post/invite** without Ryan OK (USER law).
5. **GREEN/merge = Ryan OK only.**
6. **Secrets in `.env` / `auth.json` only** — never commit.
7. **Kanban:** `--board mesh` on every mutate; force real block records on PARK/HUMAN; **no `--parent` on blocked epic** (cousin comments only).
8. **Desktop chat ≠ gateway alive.** Always probe launchd/systemd + HB age.
9. **Pulp stays VPS-only** and on its own bot — do not conflate with T1000 writer.
10. **Mac is glass, not brain.** Steady-state Mac must **not** run the T1000 Telegram gateway or the desk cron scheduler. Optional Mac surfaces only: T1000.app/Cursor UI (remote or local offline toys), macOS computer-use when Ryan is at the laptop, MBP Ollama as a *peer* endpoint, one-shot OAuth browser ceremonies that then **sync tokens to VPS**.
11. **Entire desk = full home.** Skills, memory, kanban DBs, cron jobs.json, scripts, auth, config, session DB (compacted if needed) live on VPS. Partial “chat-only failover” is a milestone, not the destination.

---

## 1. Current baseline (measured 2026-08-12 ~20:20 CT)

| Item | Value |
|------|--------|
| Mac engine | Hermes **v0.20.0 (2026.8.3)** · local `f92691f86b` · branch `ryan/herald-0.20-cutover` |
| Carry vs Nous | **+56** local-only · **169** missing from `origin/main` · merge-base `9b1a2a14ca` |
| Mac doctor | green after config migrate |
| Mac gateway | launchd OK, TG connected (refreshed plist same night) |
| HA | Mac primary · VPS `t1000-gateway` **inactive** · HB age &lt;60s · auth_sync throttled |
| VPS engine | **v0.17.0 (2026.6.19)** · `/opt/t1000/{src,venv,home}` |
| Mac crons | **30** in `~/.t1000/cron/jobs.json` |
| VPS cron snapshot | **11** stale (updated ~2026-08-12 17:30Z) |
| Cron workdirs | many `/Users/ryan/Documents/{sovereign-advisory,career,investing,student-lab}` |
| Cousin cards | `t_e0419aa3` three-weeks-dark · `t_2f43f830` Herald park (historical) · `t_566bf5c1` cron model PM |

### What fails over today vs what does not

| Fails over (chat) | Does **not** auto-run on VPS |
|-------------------|------------------------------|
| T1000 Telegram poller after HB stale ~180s | Hermes desk crons (`jobs.json` tick is Mac-gateway-local) |
| Standby replies if auth fresh | Google UI / Chrome profiles |
| | macOS computer-use |
| | Full `~/Documents/*` workdirs |

---

## 2. Target end-state (entire Hermes on VPS)

```text
 Ryan MBP (GLASS ONLY)
   Cursor / T1000.app / SSH
   ai.hermes.gateway = OFF (bootout)
   ~/.t1000 = cold mirror or remote-client stub (NOT SoT)
              │
              │  human UI only — no TG getUpdates
              ▼
 ┌─────────────────────────────────────────────┐
 │  k2vps  = ENTIRE HERMES DESK (SoT)            │
 │  /opt/t1000/src + venv     engine             │
 │  /opt/t1000/home           HERMES_HOME SoT    │
 │    auth, config, skills, memory, kanban,      │
 │    cron/jobs.json, scripts, sessions, SOUL    │
 │  t1000-gateway.service     ALWAYS active      │
 │  desk crons                ALL portable jobs  │
 │  juice-doctor-reconcile    desired primary=vps│
 │  workspaces                /opt/t1000/workspaces/* │
 └───────────────┬─────────────────────────────┘
                 ├─ Spark / Kevin tunnels (from VPS)
                 └─ Pulp separate bot (already VPS)
```

### What “entire Hermes” includes (must move)

| Surface | VPS path / note |
|---------|-----------------|
| Engine | `/opt/t1000/src` + `/opt/t1000/venv` @ fleet SHA |
| Home SoT | `/opt/t1000/home` ← full `~/.t1000` migration |
| Telegram gateway | `t1000-gateway` sole writer |
| Cron scheduler | same gateway process; **all** T0–T2 jobs |
| Skills + memory | under home |
| Kanban boards | `home/kanban/boards/*` (full DBs) |
| Sessions | `state.db` + sessions (compact/optimize before ship if huge) |
| Scripts/bin | `home/scripts`, `home/bin` |
| Auth/config | home; overlay disables Mac-only providers as defaults |
| Workdirs | mirror `career`, `investing`, `sovereign-advisory`, `student-lab` (+ T1000 src) |

### What stays Mac-only by physics (not “Hermes desk”)

| Surface | Why |
|---------|-----|
| T1000.app / Cursor pixels | GUI on laptop |
| macOS computer-use / Accessibility | needs Mac |
| MBP Ollama GPUs | local silicon — call as remote peer if ever needed |
| Interactive browser OAuth click | ceremony on Mac → **copy tokens to VPS home** |

These do **not** keep the desk brain on the Mac.

### Steady-state Mac policy

1. `launchctl bootout` `ai.hermes.gateway` (+ do not KeepAlive).
2. Stop Mac failover heartbeat **or** switch it to “mirror-only / no claim” so it cannot steal primary.
3. Optional: periodic **pull** mirror VPS home → Mac for offline browse (never reverse without explicit reclaim).
4. Emergency only: `reclaim-mac-primary.sh` (documented break-glass).

**Success criteria (all required):**

1. Mac lid closed / powered off **≥24h** (not just 30m) → T1000 TG still answers; desk crons still fire on CT wall clock.
2. **Every** non-T3 cron from Mac `jobs.json` is classified and either running on VPS or explicitly retired with Ryan OK.
3. `HERMES_HOME` SoT is `/opt/t1000/home` (doctor/gateway/cron on VPS read that tree).
4. Kanban CLI on VPS sees same boards/cards as pre-cutover Mac (or documented one-time cutover stamp).
5. `juice-doctor --reconcile-only` OK with **desired primary=vps**; Mac gateway inactive.
6. No dual-writer events for 48h; Mac gateway process **absent** in steady state.
7. Upstream carry: fleet SHA on VPS matches proven Mac build; carry proofs green.
8. Break-glass reclaim script tested once in drill, then Mac returned to glass.
9. **Web app view:** authenticated Hermes dashboard reachable when Mac is off — at minimum `/kanban`, sessions, config, embedded chat — via Tailscale and/or HTTPS with dashboard auth (never open unauthenticated public bind).

---

## 2b. Track W — Web app view (required for full residency)

When the brain is on VPS, Ryan still needs a **browser pane** into the desk without the laptop gateway.

### Product surface (stock Hermes — do not rebuild Juice)

| URL path | Purpose |
|----------|---------|
| `/` | Hermes Agent Dashboard shell |
| `/kanban` | Board switcher + cards (mesh/k2/desk/…) |
| sessions / chat embed | Talk to same home SoT |
| config / skills / cron (as exposed) | Ops without SSH |

Engine: `hermes dashboard` → SPA in `hermes_cli/web_dist` (build from `web/` on deploy).  
**Not** packaged T1000.app `HERMES_WEB_DIST=app.asar` (Juice IPC trap).

### Access architecture (pick one primary; can offer both)

| Option | How | Pros | Cons |
|--------|-----|------|------|
| **W-A Tailscale only (default recommend)** | Dashboard binds `127.0.0.1:9119`; expose with `tailscale serve` or MagicDNS + SSH tunnel | No public attack surface; fits Ryan mesh | Needs Tailscale on phone/travel laptop |
| **W-B HTTPS public + dashboard auth** | Caddy/nginx TLS → loopback 9119; password or OAuth (`hermes dashboard register` / portal) | Works from any browser | Must lock auth; rate-limit; no `--insecure` noop reliance |
| **W-C SSH tunnel ad-hoc** | `ssh -L 9119:127.0.0.1:9119 k2vps` | Zero extra deps | Not “open the app” UX |

**Default for plan:** **W-A first**, optional **W-B** later if Ryan wants shareable URL. Never bind `0.0.0.0` without auth provider configured.

### Deploy pieces

```text
deploy/vps-primary/
  t1000-dashboard.service    # User=t1000, HERMES_HOME=/opt/t1000/home
                             # Exec: venv python -m hermes_cli.main dashboard
                             #   --host 127.0.0.1 --port 9119 --no-open --skip-build
  install-dashboard.sh
  # optional: Caddyfile fragment, tailscale serve unit notes
```

Pre-req on VPS after engine upgrade:
```bash
cd /opt/t1000/src/web && npm ci && npm run build   # → hermes_cli/web_dist
```

Auth:
- Loopback + Tailscale: session token still exists; treat TS identity as perimeter
- Public: configure dashboard password/OAuth per Hermes dashboard_auth; set `HERMES_DASHBOARD_PUBLIC_URL`

### Acceptance (Track W)

- [ ] From Mac on Tailscale (Mac gateway **off**): open dashboard, title **Hermes Agent - Dashboard**, `/kanban` shows mesh epic
- [ ] From phone Tailscale (or W-B HTTPS): same
- [ ] Unauthenticated public internet probe gets no desk API (connection refused or auth wall)
- [ ] Dashboard survives VPS reboot (systemd enabled)
- [ ] Does not second-open Telegram getUpdates (dashboard ≠ gateway writer)

### Sequencing note

W1 can land **after V1 engine 0.20** and **alongside V2 home migration** (dashboard needs real home SoT). Prove W before or at V5 so “laptop off” includes “I can still see the board in a browser.”

## 3. Track U — Upstream carry (#3)

### U0. Honest recon (no merge yet)

**Objective:** Inventory what must survive and what main brings.

```bash
export HERMES_HOME=~/.t1000
cd ~/Documents/T1000
git fetch origin
git rev-list --left-right --count HEAD...origin/main
git log --oneline origin/main..HEAD > /tmp/t1000-carry-only.txt
git log --oneline HEAD..origin/main > /tmp/t1000-main-only.txt
# classify carry: HA/failover, reconciler, kanban, wrap_untrusted, MESH-TEL, doctor, scripts
rg -n "failover|reconciler|wrap_untrusted|kanban|MESH-TEL|juice-doctor" /tmp/t1000-carry-only.txt | head
```

**Deliverable:** `docs/plans/carry-inventory-YYYYMMDD.md` listing:
- Must-keep paths (deploy/failover, hermes_cli/reconciler, startup_secrets, model_failover, wrap_untrusted mint-set, kanban claim locks, scripts/*)
- Nice-to-have local commits
- Main commits that touch same files (conflict forecast)

### U1. Strategy choice (document, then execute one)

| Strategy | When |
|----------|------|
| **U1-A Merge** `origin/main` into carry branch | Histories share base (they do: merge-base exists) and conflicts are manageable |
| **U1-B Rebase** carry onto `origin/main` | Cleaner history; riskier on published branch — use throwaway branch |
| **U1-C Path A style** sibling clone at tip + port carry modules | Only if merge explodes (Herald lesson) |

**Default preference:** **U1-A on branch** `ryan/carry-main-$(date +%Y%m%d)` from current tip:
```bash
git checkout -B ryan/carry-main-20260812
git merge origin/main -m "merge(origin/main): absorb Nous tip into T1000 carry"
# fix conflicts favoring carry for HA/secrets/kanban locks; take main for pure upstream plugins
```

### U2. Conflict resolution rules

| Area | Keep |
|------|------|
| `deploy/failover/**`, `~/.t1000/failover` dual-write docs | **Carry** |
| `hermes_cli/reconciler.py`, `deploy/reconciler/**` | **Carry** unless main has strict superset — then port tests |
| `wrap_untrusted` mint-set / LAB-0023 | **Carry** |
| `startup_secrets` fail-closed | **Carry** |
| Plugin platform / gateway reaction observers | **Main** |
| Kanban dispatcher claim / self-review lock | **Carry** (MESH-TEL / governance) |
| Version banners | regenerate after merge |

### U3. Prove on Mac **before** VPS copy

```bash
cd ~/Documents/T1000
./venv/bin/python -m pip install -e . --force-reinstall --no-deps
./venv/bin/python -m hermes_cli.main doctor
./venv/bin/python -m pytest \
  tests/hermes_cli/test_reconciler.py \
  tests/hermes_cli/test_startup_secrets.py \
  tests/agent/test_model_failover_policy.py \
  tests/agent/test_model_failover_attach.py \
  tests/agent/test_wrap_untrusted.py \
  tests/agent/test_tool_dispatch_helpers.py \
  tests/cron/test_cron_prompt_injection_skill.py \
  tests/hermes_cli/test_kanban_claim_on_bind.py \
  -q --tb=line
# add any new main-touched critical suites that fail-closed security
```

**Gateway cutover on Mac (only in approved window):**
```bash
HERMES_HOME=~/.t1000 ./venv/bin/python -m hermes_cli.main gateway install --force
# OUTSIDE agent session:
~/.t1000/bin/reload-gateway-outside.sh
# prove:
./venv/bin/python -m hermes_cli.main gateway status
~/Documents/T1000/deploy/failover/status.sh
~/Documents/T1000/scripts/juice-doctor --reconcile-only
# one owner TG ping
```

**Do not** leave heartbeat disarmed. Re-kickstart `com.ryan.t1000-failover-heartbeat` if install touched it.

### U4. Freeze SHA for fleet

Tag both git and note in plan:
```bash
git tag -a t1000-fleet-$(date +%Y%m%d) -m "Mac+VPS target SHA after carry merge"
git rev-parse HEAD > ~/.t1000/cache/fleet-target-sha.txt
```
VPS must install **this** SHA (or descendant), not random 0.17.

### U5. HUMAN gate — Mac primary reload window

Ryan OK required before outside reload if mid-client-day or SBS fire. Quiet evening preferred.

---

## 4. Track V — Full VPS residency (entire Hermes)

### V0. Inventory + tiering (no topology change)

**Cron tiers (classify every job in `jobs.json`):**

| Tier | Meaning | Full-residency target |
|------|---------|----------------------|
| **T0** | Ops health, alerts, no Mac path, no_agent preferred | **Must run on VPS** |
| **T1** | Agent Grok jobs with portable tools (web, gws if tokens on VPS) | **Must run on VPS** |
| **T2** | Needs Documents workdirs | **Must run on VPS after workspace mirror** (all four trees) |
| **T3** | Mac-only (computer-use, local UI, MBP ollama) | Retire, convert, or document as **non-desk** Mac toys — **not** left as silent Mac dependency |

**Path map deliverable:** `deploy/vps-primary/path-map.yaml`

```yaml
# example shape
workdir_map:
  "/Users/ryan/Documents/sovereign-advisory": "/opt/t1000/workspaces/sovereign-advisory"
  "/Users/ryan/Documents/career": "/opt/t1000/workspaces/career"
  "/Users/ryan/Documents/investing": "/opt/t1000/workspaces/investing"
  "/Users/ryan/Documents/student-lab": "/opt/t1000/workspaces/student-lab"
  "/Users/ryan/Documents/T1000": "/opt/t1000/src"
hermes_home:
  sot: "/opt/t1000/home"
  mac_cold_mirror: "/Users/ryan/.t1000"
```

**Workspace sync (full residency default):** rsync **all four** Documents workdirs + git-aware where repos exist. “Drop T2” is **not** acceptable for end-state — only a temporary bridge while mirrors bootstrap.

### V1. Phase 1 — VPS engine upgrade to fleet SHA (Mac still primary)

**Goal:** VPS engine leaves 0.17 museum. Writer still inactive until flip.

Steps:
1. Snapshot VPS: `cp -a /opt/t1000 /opt/t1000-bak-$(date +%Y%m%d)`
2. Rsync Mac tree (or git fetch) → `/opt/t1000/src` as user `t1000`
3. Recreate/update venv with **python3.12**, `pip install -e .`
4. Prove version matches Mac family
5. Subset pytest on VPS if deps allow
6. **Do not** enable writer yet if Mac still primary mid-phase
7. Force auth_sync; confirm VPS `auth.json` fresh
8. Optional hold drill: promote → one TG DM → restore (pre-flip proof)

Files: `deploy/vps-primary/upgrade-vps-engine.sh` (**create**), failover install scripts as needed.

### V2. Full home migration (not lean standby)

**Goal:** `/opt/t1000/home` becomes a **complete** copy of the live desk, then becomes **SoT**.

**Include (entire desk):**
- `.env`, `auth.json`, `config.yaml` (+ VPS overlay)
- `cron/` (jobs + output dirs as needed)
- `scripts/`, `bin/`
- `skills/` (full estate)
- `memories/` / memory backend files
- `kanban/` **all boards**
- `state.db` + `sessions/` after `hermes sessions optimize` / hygiene if multi‑GB
- `SOUL.md`, channel directory, google tokens, hooks, comm_comprehension, etc.

**Exclude only:**
- Mac LaunchAgent plists / desktop Electron caches / computer-use sockets / huge replaceable media caches if rehydratable
- Stale `*.bak-*` optional to save space (keep last 2 config baks)

**Cutover shape:**
1. Final rsync Mac→VPS while Mac gateway still primary (brief)
2. Stop Mac gateway + HB claim
3. Start VPS gateway on migrated home
4. Mark Mac `~/.t1000` **cold** (README + optional chflags / rename stamp)
5. Ongoing: VPS→Mac **pull mirror** optional; never Mac→VPS as SoT after cut

Script: `deploy/vps-primary/sync-home.sh` (full mode default; `--lean` only for emergency).

**Config overlay:** default model **grok-4.5 / xai-oauth**; no `mbp-ollama` default; Spark only if VPS tunnel works; Claude ACP not required for desk vitality.

### V2b. Workspace mirrors

Bootstrap `/opt/t1000/workspaces/{sovereign-advisory,career,investing,student-lab}` via rsync or git clone. Cron workdirs rewritten by path-map. Nightly VPS pull from Mac **or** treat VPS as git remote worker with push-back rules (document — default rsync Mac→VPS until Ryan says VPS is also git writer).

### V3. Topology flip — VPS is the only brain

Update `deploy/reconciler/desired-state.yaml`: **primary=vps** always.

| Mode | Steady state |
|------|----------------|
| **vps_residency (CHOSEN)** | VPS gateway always active; Mac gateway **bootout**; Mac HB does **not** steal claim; reclaim script = break-glass only |
| ~~mac_primary_ha~~ | **Retired** as target (may remain code path for emergency) |

Scripts:
- `deploy/vps-primary/promote-vps-residency.sh` (final flip)
- `deploy/vps-primary/reclaim-mac-primary.sh` (break-glass)
- Watchdog `PRIMARY_MODE=vps_residency`

### V4. Cron port (all portable jobs)

1. Classify T0–T3  
2. Rewrite **all** T0–T2 workdirs  
3. Pin agent crons grok/xai-oauth  
4. Live only on VPS gateway  
5. Mac gateway off ⇒ no double fire  
6. Smoke T0 then T1 then T2 samples  
7. T3 list: Ryan OK to drop or keep as manual Mac-only

### V5. Laptop-off acceptance (raised bar)

- [ ] Mac **powered off or asleep ≥24h** (not 30m only)
- [ ] VPS gateway active; claim=vps; **no** Mac gateway process
- [ ] Owner T1000 TG DM answered
- [ ] Sample T0 + T1 + one T2 cron OK
- [ ] Kanban show on VPS matches epic card
- [ ] Pulp unaffected
- [ ] Wake Mac glass-only: no dual poll
- [ ] juice-doctor OK primary=vps
- [ ] 48h soak after flip

### V6. Docs / skills patch

- `t1000-gateway-ha`: topology = VPS residency; Mac glass
- `t1000-hermes-ops`: “crons if computer off” → **yes, they run on VPS**
- failover README + `deploy/vps-primary/README.md`
- Close/retarget `t_e0419aa3` zero-Mac

### V7. Out of scope / non-goals

- Killing T1000.app (UI stays on Mac)
- Multi-master live session write from Mac+VPS (Mac is not SoT)
- Claude Max as VPS default brain (optional later)
- Buying Mini (unnecessary if this lands)
- Keeping Mac HA primary “just in case” as steady state — **rejected by Ryan 2026-08-12**
---

## 5. Sequencing (critical path)

```text
U0 recon ─┐
          ├─► U1 merge ─► U3 Mac pytest ─► U5 Ryan OK reload ─► U4 fleet SHA
V0 inventory ─┘                              │
                                             ▼
                                  V1 VPS engine@SHA
                                             │
                                  V2 full home migration (+ optimize state.db)
                                  V2b workspace mirrors (all four trees)
                                             │
                                  V4 rewrite ALL T0–T2 crons on VPS home
                                             │
                                  V3 residency flip  ◄── HUMAN `flip vps primary`
                                   (Mac gateway bootout; VPS sole SoT)
                                             │
                                  V5 laptop-off ≥24h + 48h soak
                                             │
                                  V6 skills/docs + cousin closeout
```

**Parallelism:** U0 and V0 after kickoff. **No V3 flip** until fleet SHA + full home rsync dry-run + cron rewrite ready + Mac bootout script ready.

**Estimated effort:** U 0.5–1.5d · V0–V2b 1–2d · V3–V5 0.5d + soak · V6 hours.
---

## 6. Rollback

| Stage | Rollback |
|-------|----------|
| U merge broken | `git reset --hard` pre-merge tag; reinstall prior venv editable; gateway install --force + outside reload |
| V1 VPS engine bad | restore `/opt/t1000-bak-*`; keep Mac primary |
| V3 flip bad | `reclaim-mac-primary.sh`: start Mac gw+HB, stop VPS gw, claim mac, auth_sync |
| Dual writer | emergency: `ssh k2vps 'systemctl stop t1000-gateway; reset-failed'` + Mac HB |

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Dual TG replies | sticky mode + Mac gw bootout; reconciler refuse |
| Stale xAI tokens on VPS | auth_sync direction from **primary**; after flip primary=VPS must refresh OAuth (PKCE may need one interactive if refresh fails) |
| Cron double-send | Mac gateway must not run jobs.json while VPS does |
| Path rewrite misses | T2 stay off until mirror; start T0 only |
| Merge destroys HA | U2 rules + pytest list mandatory |
| Session DB split brain | VPS starts lean sessions; Desktop points carefully; no multi-master |
| Client week / SBS | no flip mid fire; U5/V3 HUMAN gates |
| kanban free-fire on restore | force-block PARK cards; width park ready@worker |

---

## 8. Open questions (Ryan) — mostly locked

| # | Question | Status |
|---|----------|--------|
| 1 | Sticky VPS forever vs Mac reclaim when at desk? | **LOCKED: entire Hermes on VPS; Mac glass; reclaim = break-glass only** |
| 2 | Which workspace mirrors? | **Default ALL four** Documents trees used by crons |
| 3 | Kanban workers on VPS? | **Yes target** — after Spark reach-from-VPS; else workers pause not fall back to Mac gateway |
| 4 | Upstream merge window? | Quiet evening (still open for calendar pick) |
| 5 | OAuth headless on VPS? | Hybrid Mac-refresh→sync OK temporarily |

Remaining asks only if blocking: (4) which evening for U5/V3, and confirm session DB full copy vs optimize-first if `state.db` is multi‑GB.
---

## 9. Kickoff phrases (cards)

| Phrase | Effect |
|--------|--------|
| `start vps-primary epic` | Unblock epic; allow U0+V0 agent work |
| `start upstream carry` | Unblock Track U |
| `start vps phase1 engine` | Unblock V1 only |
| `start vps web` | Unblock Track W (dashboard) |
| `flip vps primary` | HUMAN — V3 residency flip |
| `abort vps-primary` | Stop; reclaim Mac; leave plan |

---

## 10. Kanban map

**Canonical board: `dust`** — *Pardon our dust — Hermes → VPS* (🚧).  
Mesh holds **pointer** copies only (same idempotency keys) — do not dispatch mesh.

Access locked **2026-08-12: A+B, A first** (Tailscale, then public HTTPS+auth).

See seed bodies under `~/.t1000/kanban/seed-bodies/20260812-vps-primary-*.md`.

| Key | Dust title (blocked) |
|-----|----------------------|
| `dust-status-banner-20260812-v2` | 🚧 STATUS banner |
| `vps-primary-epic-20260812` | REF epic: Entire Hermes on VPS + web (A+B) |
| `vps-u0` … `vps-w2` | Full U/V/W phase set (16 work cards + banner) |

Dashboard: board switcher → **dust**.

---

## 11. Files likely to change (implementation)

**Create:**
- `deploy/vps-primary/README.md`
- `deploy/vps-primary/path-map.yaml`
- `deploy/vps-primary/upgrade-vps-engine.sh`
- `deploy/vps-primary/sync-home.sh` (full home; size filters)
- `deploy/vps-primary/config.vps-overlay.yaml`
- `deploy/vps-primary/promote-vps-residency.sh`
- `deploy/vps-primary/reclaim-mac-primary.sh`
- `deploy/vps-primary/t1000-dashboard.service`
- `deploy/vps-primary/install-dashboard.sh`
- `deploy/vps-primary/Caddyfile.fragment` (optional W-B)
- `docs/plans/carry-inventory-YYYYMMDD.md`

**Modify:**
- `deploy/reconciler/desired-state.yaml`
- `deploy/failover/vps/watchdog.sh` (+ runtime `~/.t1000` N/A on VPS — VPS paths under `/opt` / `/var/lib`)
- `deploy/failover/README.md`
- `~/.t1000/skills/.../t1000-gateway-ha/SKILL.md`
- `~/.t1000/skills/.../t1000-hermes-ops/SKILL.md` (cron-off pitfall)

**Tests:** existing reconciler/failover/secrets/wrap_untrusted/kanban lists above; add `tests/deploy/test_path_map.py` if rewrite helper is Python.

---

## 12. Verification commands (copy/paste green bar)

```bash
# Mac
export HERMES_HOME=~/.t1000
cd ~/Documents/T1000
./venv/bin/python -m hermes_cli.main --version
./venv/bin/python -m hermes_cli.main doctor
./venv/bin/python -m hermes_cli.main gateway status
./deploy/failover/status.sh
./scripts/juice-doctor --reconcile-only

# VPS
ssh k2vps 'systemctl is-active t1000-gateway.service t1000-failover-watchdog.timer
/opt/t1000/venv/bin/python -m hermes_cli.main --version
cat /var/lib/t1000-failover/claimed_by
echo age:$(( $(date +%s) - $(awk "{print \$1}" /var/lib/t1000-failover/heartbeat) ))'
```

Post-flip expect: VPS gateway **active**, claim **vps**, Mac gateway **inactive/bootout**, doctor OK, TG DM OK, dashboard on Tailscale (or HTTPS auth) shows `/kanban`.

---

*Plan authored 2026-08-12 for Ryan A+2+3; locked to **entire Hermes on VPS** + **web app view** same day. Execution gated on kickoff phrases.*
---

## 2026-08-19 reconciliation (ryan-claude, card t_726914e9 — append-only; nothing above edited)

Ryan re-affirmed the goal in session 2026-08-19 ("getting my hermes full in the
cloud"). This plan remains the SoT; the week between 08-12 and 08-19 changed
the ground it stands on. Delta, measured live:

### What changed since the baseline

1. **Upstream carry (Track U) largely happened.** The cutover branch now sits
   at `382db0d850`, is PUSHED to the product remote (was Mac-only), and the
   08-17 checkout-flip incident produced hard guards this plan should adopt:
   PB-003/PB-009 (docs/playbook/), a 30-min pulse checkout guard, and the
   `git fetch origin main:main` no-flip ritual. Track U's residual is a
   re-measure of carry-vs-Nous, not the full absorb it describes.
2. **The dsh foreign-runtime lane exists** (kanban.worker_command seam,
   wrapper at ~/.t1000/bin/dsh_kanban_worker.py, sha-pinned against the
   read-only K2 clone, node>=22.13 dependency, DS4 Flash at 127.0.0.1:8889).
   NEW MIGRATION ITEM: the lane needs its runtime (node22 tree, dsh npm
   install, clone, wrapper) provisioned on the VPS, and the 8889 route must
   terminate there (today's Spark tunnel lands :11435 on the VPS — 8889 is a
   Mac-side landing). Until then the dsh lane stays a Mac-satellite lane.
3. **Pulse riders are new Mac-path-dependent organs**: playbook_sweep,
   k2_intake_sync, checkout guard (all in ~/.t1000/scripts/, state in
   ~/.t1000/cache/, reading ~/.t1000/src/kevin-real-estate-tools and
   ~/Documents/T1000/docs/playbook). They migrate WITH the home (law 11
   already covers the home) but need: a K2 read-only clone on the VPS, the
   playbook dir resolvable (T1000 checkout on VPS exists at /opt/t1000/src),
   and PLAYBOOK_* / K2_INTAKE_* env defaults re-pointed.
4. **Fleet GitHub auth is now keychain-FREE by design** (GitHub App mint:
   k2app-token + HERMES_KANBAN_GH_TOKEN_CMD + GIT_CONFIG_GLOBAL fleet
   gitconfig) — this REMOVES the old blocker class where launchd/systemd
   workers had no credentials. It ports to systemd cleanly. ⚠️ Secrets
   residency: the App private key (.pem) would land on a VPS disk that is
   NOT encrypted (standing memory) — decide: accept, encrypt the secrets
   dir, or keep minting Mac-side until addressed.
5. **Park/unpark attribution landed** (`by` on unblocked/scheduled events,
   382db0d850) — prerequisite quality for the shared Ryan+Kevin board card
   (t_7ea3f49b), which is sequenced AFTER this migration by design.
6. **VPS measured 2026-08-19**: engine still v0.17.0 (2 majors behind fleet),
   109G free disk, 15G RAM (10G available), watchdog timer active, gateway
   standby inactive — consistent with the 08-12 baseline; Track V's engine
   upgrade is still the first mile.

### Stage order (unchanged in spirit, updated in content)

- **V0 — engine + home groundwork** (VPS engine to fleet SHA from the product
  remote; full home rsync rehearsal WITHOUT switching writers; kanban DBs
  copied cold and verified readable). No-regression gate: VPS `hermes doctor`
  green + boards enumerate identically on both sides.
- **V1 — organ migration dark**: pulse + riders installed on VPS against VPS
  paths (K2 clone, checkers, playbook), running in DRY-RUN/log-only beside
  the live Mac pulse. Gate: 48h of VPS rider logs matching Mac rider actions.
- **V2 — writer flip**: Telegram writer + cron scheduler + kanban dispatch to
  VPS (one-writer law), Mac gateway bootout, watchdog semantics inverted
  (Mac becomes the failover, per the plan's original design). Gate: laptop
  closed 48h, zero missed pulses, dsh-lane cards either parked or proven on
  the satellite path.
- **V3 — satellite lanes**: dsh runtime on VPS or formalized Mac-satellite
  dispatch; MBP-ollama as peer endpoint only; Bot Mode/desktop app pointed
  at the cloud gateway.

Kickoff remains Ryan's, per the plan's own header law.

## ✅ V2 LANDED — 2026-08-19 20:24:42Z (append-only close-out)

The flip is done: `t1000-gateway` (systemd, k2vps) is the sole Telegram writer,
dispatcher holds the lock over the migrated boards, riders run with VPS paths
(unit drop-in `vps-paths.conf`), timezone fixed America/Chicago, secrets landed
(Ryan, option a) with the git/gh mint chain proven on-box. Mac is glass: gateway
plist retired `.mac-glass`; `com.ryan.launchd_watchdog` was the resurrection
daemon (and the probable 08-17 16:16 restart actor — PB-009's last thread).
Rollback: `/opt/t1000/home-standby-v017` + Mac plists preserved. Residuals:
VPS mesh card `t_cb5b0bd5` (12 paused Mac-workdir crons, dsh-lane provisioning,
desktop remote attach, sqlite runtime). Full receipts: mesh `t_18ba6dbd` (V0)
and `t_72b85b29` (V1+V2) on the now-authoritative VPS boards.
