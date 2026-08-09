# PM deep-dive: Juice, Herald 0.20, Teammate EA (Lori)

Read-only investigation, 2026-08-09. All evidence below is live-pulled (juice-doctor run, ssh k2vps journalctl/systemctl, hermes kanban mesh board, gh pr view, git log/status) — not from memory files, which were only used as a starting pointer and cross-checked against live state.

---

## Juice
**Mission:** Sovereign Consulting's private local-only comm-comprehension agent (R0–R2 synthetic classify ladder, `sovereign_juice` package) plus its operationalized VPS legs (inbox triage, ops/stats/funnel digests, reply-nudge, advisory pull) that post to Telegram/Buzz. Runs across three surfaces sharing the "juice" name (the launcher script's own header comment warns not to conflate them): (1) T1000 Electron cockpit at `~/Documents/T1000/apps/desktop`, Mac launchd job `application.ai.sovereign.juice.*` (PID 79877, running); (2) `sovereign_juice` CLI source at `~/Documents/sovereign-consulting/tools/juice`; (3) production crons on k2vps (`srv1623493`) under `/opt/juice`, driven by 11 systemd timers plus a `buzz-agent-juice.service` (active/running).

**Status: LIVE, with one fresh red flag.**
- `juice-doctor` (run live): Ollama UP, Spark classify lane UP (127.0.0.1:11435), T1000 venv OK, **R0: OPERATIONAL — 30/30 semantic (threshold ≥24), review signed, baseline locked, verification current**; reconciler `OK fixed=0 drifted=0 refused=0`.
- VPS timers (`systemctl list-timers`): all 11 juice-* + `k2-juice-auth-readiness` timers are `active waiting` with recent last-fires (5-min doctor-reconcile through daily/weekly digests) — genuinely running, not stale.
- **`juice-triage-digest.service` FAILED today** (2026-08-09 12:29:36 UTC): `Command '[...triage_projection.py, --real, --profile, sovereign_advisory, ...]' timed out after 1500 seconds`, exit status 1/FAILURE, `Triggering OnFailure=` dependencies. The four preceding days (Aug 5–8) all completed cleanly in ~6–10 min with the same non-`--profile` invocation — this is a first-time failure right after a `--profile sovereign_advisory` flag was added, worth a look before tomorrow's run.
- Live-auth (real-comm classification) watchdog `k2-juice-auth-readiness.service`, run live: `"state": "authorized", "days_left": 17.55, "expires_at": "2026-08-27T02:29:56Z", "status": "ok"`. Matches memory's "~2026-08-27" note — not stale, but the clock is real and getting short.

**Shipped last ~2 weeks:** R0 lock/verification current per doctor; VPS digest fleet (advisory-pull, funnel-digest, stats-digest daily/weekly, firehose-digest, reply-nudge, cadens-warm, golden-replay) all confirmed live-firing. Mesh cards: `t_1c966036` (done) "Watch juice-doctor-reconcile: zero silent-drift through 2026-08-20"; `t_767ce9dd` (done) "Run juice-doctor reconcile-only; green or blocked card".

**In flight / carded (mesh board):**
- `t_2e031c06` scheduled — "Final juice-doctor-reconcile zero-silent-drift closeout (through 2026-08-20)"
- `t_161da56b` scheduled — "Week-1 juice-doctor-reconcile journal check (~2026-08-13)"
- `t_9bfcbb2f` todo — "Pulp residuals: proactive cal + invest freshness + arctic gap + auth~08-28"
- `t_f18d325e` blocked — "HUMAN: Renew Pulp auth via TTY ceremony (before 2026-08-28)"

**Top 3 gaps/risks:**
1. `juice-triage-digest` just failed for the first time in its visible history (Aug 9, 1500s timeout on a newly-added `--profile sovereign_advisory` arg) — unconfirmed whether it self-heals on tomorrow's run.
2. Live-auth (real-comm classify) expires 2026-08-27 (17.55 days out per live watchdog) — renewal is a manual TTY ceremony with no automatic path; card `t_f18d325e` is open but has no committed date, just "before 08-28."
3. Three surfaces answer to "juice" (Electron cockpit, CLI package, VPS cron fleet) with an explicit prior incident of claims about one being wrongly applied to another (`t1000_juice_spark_delineation_2026_07_27`) — ongoing mis-attribution risk when reasoning about "is juice live."

**Next 3 moves:**
1. Investigate the Aug 9 `sovereign_advisory` profile timeout before the next 12:00 UTC fire; confirm green or roll back the new flag.
2. Put a concrete calendar date (not "before 08-28") on the live-auth TTY renewal ceremony now, 17 days out.
3. Watch the two scheduled juice-doctor closeout cards (`t_161da56b` ~08-13, `t_2e031c06` through 08-20) for the zero-silent-drift commitment.

**Verdict: MAINTAIN.** Broad, genuinely-live operational footprint (11 active timers + live R0 ladder + running Mac cockpit), but it just produced its first pipeline failure in days and carries a hard, human-gated 18-day auth cliff. This is a watch-and-fix window, not a build-more window.

---

## Herald (0.20 gateway)
**Mission:** T1000's production messaging/agent gateway (Telegram, Buzz, kanban dispatch) — the Hermes engine itself, now at version 0.20.0. Runs on Mac launchd: `ai.hermes.gateway` (the gateway process), `com.ryan.t1000-failover-heartbeat`, `com.ryan.t1000-failover-drill`. Tree: `~/Documents/T1000`, currently checked out on branch `ryan/herald-0.20-cutover`.

**Status: LIVE (engine) / PARKED (program) — a split claim, evidenced both ways.**
- `launchctl list`: `ai.hermes.gateway` has a live PID (39332) — running.
- `~/.t1000/gateway_state.json` (read live): `"gateway_state":"running"`, `"updated_at":"2026-08-09T12:16:34Z"` (today), Telegram platform `"state":"connected"` as of 2026-08-08T15:02:21Z.
- T1000 repo HEAD is literally on `ryan/herald-0.20-cutover`; last commit 2026-08-09 08:03 CT (today) — this branch is the live production branch, not a side experiment.
- **But** mesh card `t_2f43f830` "PARK Herald 0.20 until SBS green bar + Ryan unpark" is still `status: blocked`, most recently re-scored 2026-08-08 17:56 CT: "GB1 FAIL (invoice STAGED; tripwire RED +17 biz d), GB2 FAIL (Gate 1 Mon 08-10 not past), GB3 FAIL (inside 48h) → **stay PARKED**." The card's own comment thread is explicit: "Engine already on 0.20 (Path A exception) — park is SBS doctrine not engine rollback." So the engine cutover is done and running production traffic; further Herald *feature* work (voice/A2A/fleet) is doctrine-paused, unrelated to any outage.

**Shipped last ~2 weeks:**
- Full Path A cutover to Hermes 0.20.0 (2026.8.3) + HA/Distillery carry, landed 2026-08-06 (`t_ca20a700` P0, done — venv/shebang fixed, clean plist reinstall, gateway PID alive w/ LastExitStatus=0, TG reconnected, failover heartbeat restored, juice-doctor reconciler drifted=0).
- Claude ACP Max lane shipped on this branch 2026-08-07 (`t_e863f674`, done): 4 commits `70b9a0b83`→`721700951` — Max-sub OAuth ACP lane (no extra Anthropic HTTP usage), live thinking-stream + tool activity in Desktop UI, session pooling across reuse_evict, cache-scope/client-reuse fix. Aliases `adv/opus/sonnet/haiku/fable/grok`; default brain stays Grok.
- Desktop rebuild to match 0.20 (`t_33b54172`, done); Tier A feature-proof pass (`t_4eb0d6e8`, done); full verification sweep (compression, stall watchdog, mid-turn redirect, tool self-recovery, smart approvals 2.0, sessions optimize/FTS, kanban model/wake-DM + grounded citations) — all done 2026-08-06/07.

**In flight / carded:** `t_2f43f830` (blocked/PARK — re-scored almost daily, next score due ~2026-08-11 or immediately on invoice SEND). No other open Herald-specific mesh cards found.

**Top 3 gaps/risks:**
1. Live, unresolved reliability bug: `t_30222451` (blocked) — a `nemo_relay` scope-stack corruption reproduced live 2026-08-08 that permanently wedges a Telegram session after an interrupted context-compaction, silently dropping ~6 inbound messages until a hard `gateway restart` (which itself hit its 180s drain timeout and had to force-kill). Fix is an upstream PR, `NousResearch/hermes-agent#81858`, **still review-required, not merged** as of the last comment (2026-08-08 17:56).
2. Working tree is dirty: 19 modified, uncommitted files on `ryan/herald-0.20-cutover` (`agent/agent_init.py`, `agent/claude_acp_client.py`, `agent/prompt_builder.py`, `agent/system_prompt.py`, desktop kanban plugin files, etc.) sitting on the same branch that's simultaneously serving production.
3. "Herald is live" easily overstates scope if read as "unparked" — the engine/gateway is live and serving traffic, but the Herald 0.20 *program* (voice/A2A/fleet) remains explicitly doctrine-blocked (invoice tripwire RED +17 business days; Gate 1 client meeting not yet past as of the last score).

**Next 3 moves:**
1. Get the `nemo_relay` scope-stack heal PR (#81858) reviewed and merged — it's the only fix for a bug that already caused a live message-loss incident.
2. Commit or stash the 19 dirty files on `ryan/herald-0.20-cutover` so the production branch has a clean, reviewable state.
3. Track the next Herald green-bar re-score (card's own cadence says ~2026-08-11, or immediately on invoice SEND) — don't let engine-live get read as program-unparked in the meantime.

**Verdict: MAINTAIN (engine) / PARK (program).** The gateway itself is working infrastructure worth keeping running and patching (especially the relay bug), but new Herald feature investment is explicitly and repeatedly doctrine-blocked by Ryan's own SBS-first ruling. Don't invest further until the park lifts.

---

## Teammate EA (Lori / jarvis design)
**Mission:** K2's first non-Kevin, non-Ryan agent principal — a scoped executive-assistant shell ("Lori") reading existing K2 business surfaces (call cockpit, morning brief, daily agenda, PreCall brief) and queuing every proposed action as a review-only chip. Hard floor: no send / CRM-write / publish. Lives in this repo: `k2-hub/src/k2_hub/teammate_ea/`, `k2-hub/teammate_ea/scopes/teammate-lori/` (README read directly — load contract for `USER.md`/`MEMORY.md`/`PROVENANCE.md`/`VOICE.md`, fail-closed no-Kevin-fallback). Intended VPS leg: `k2-teammate-ea-tick.timer`/`.service` under `k2-hub/deploy/systemd/` — defined in-repo but confirmed **not installed anywhere**.

**Status: DARK at runtime / mostly-landed in code.**
- `ssh k2vps 'systemctl list-units --all | grep -i teammate'` and `list-unit-files | grep -i teammate` both return **nothing** — the tick timer has never been deployed to the VPS (nor found on Mac). The heartbeat/tick code merged with the timer deliberately shipped **unarmed** ("not in ENABLED_TIMERS until ops enable") — that arming step has not happened since.
- Ratification: Kevin ratified Teammate EA via inbox 2058 (2026-08-07) — Lori named first user, K4 RBAC-lite in scope, explicitly **no send/CRM/publish**.
- Phase 0 (assignee-scoping spine) fully merged 2026-08-07: PR #4339 (call_cockpit + morning_brief actor scope), #4340 (daily_agenda + PreCallBrief actor scope), #4341 (principal bind) — all confirmed done on main same day.
- Phase 1, same day (2026-08-07): Lori USER/MEMORY/PROVENANCE/VOICE corpus merged (#4346 — self-review checklist passed, no Kevin-voice leak); qm-scope identity loader merged (#4351, 10/10 tests, fail-closed no-Kevin-fallback verified in code path `k2_hub.teammate_ea_scope_memory.load_scope_memory`); heartbeat + silent-tick substrate merged (#4349, 12/12 tests) — but its own timer, per the PR's own decision notes, "shipped unarmed... until ops enable."
- **Remaining piece is stuck.** `PR #4348` (one-queue chip ingress + interrupt budget, ≤3/day, never-execute) is checked live via `gh pr view`: **`state: OPEN`, `mergeStateStatus: DIRTY`, `mergedAt: null`**, `root-tests` check shows `CONCLUSION: CANCELLED` on its last run, `updatedAt: 2026-08-08T01:04:08Z` — no movement since the 2026-08-07 21:37 CT card comment "CI 2026-08-07 night: pytest PASS · root-tests FAIL ... Not mergeable until root-tests green." That's >36h stale as of this investigation, and `DIRTY` means it now needs a rebase (main has moved since).
- Parent card `t_4e9cc69a` (Phase 1 shell) is still `status: todo` — last substantive comment 2026-08-08 14:59 just points at the Kevin ratification, no fresh status pass since.

**Shipped last ~2 weeks:** All of the above — Phase 0 (3 PRs) + Phase 1 Delta-gate/corpus/identity/heartbeat (4 PRs, #4346/#4347/#4349/#4351) — landed in a single day, 2026-08-07.

**In flight / carded:**
- `t_ced7480f` blocked — one-queue ingress, PR #4348 review-required, CI red/stale
- `t_a02c40c1` todo — nudges (blocked behind one-queue)
- `t_4e9cc69a` todo — Phase 1 shell parent (waits on both; needs a fresh status pass)

**Top 3 gaps/risks:**
1. PR #4348 — the last load-bearing piece of Phase 1 — has been stuck >36h: `DIRTY` merge state (needs rebase) plus a cancelled/red `root-tests` check. It will not self-resolve.
2. Even the already-merged heartbeat/tick code (#4349) has zero runtime presence anywhere — deliberately shipped disabled, and nobody has since installed the systemd unit on k2vps or elsewhere. "EA shell" today is library code with no scheduled execution.
3. Review depth on the merged pieces is self-review only: each PR's kanban comment is the *authoring* agent's own checklist (no-Kevin-voice-leak, fail-closed identity, never-execute invariant) — worth confirming a second set of human eyes actually looked at those before the shell is armed and starts producing chips a human will act on.

**Next 3 moves:**
1. Rebase PR #4348 onto current main, get `root-tests` green, merge it — this unblocks both remaining Phase 1 children (`t_a02c40c1`, `t_4e9cc69a`).
2. Once merged, install and arm `k2-teammate-ea-tick.timer`/`.service` on k2vps (currently absent from both `list-units` and `list-unit-files`) so the shell actually ticks.
3. Do a fresh status pass on `t_4e9cc69a` now that 3 of 4 children are merged — it hasn't been touched since 2026-08-08 14:59.

**Verdict: INVEST.** Kevin-ratified, correctly scoped (no send, fail-closed identity, chip-only actions, Lori-only corpus with provenance), and ~80% landed in a single focused day. The remaining blocker is one stuck PR needing a rebase and a CI fix, not an open design question. Small, concrete push finishes it.
