# WORK-FACTORY consolidation — DevBot, T1000 kanban mesh, Distillery intake

PM read-only deep-dive, 2026-08-09 morning. Sources: `hermes kanban --board mesh {stats,diagnostics,show}`, mesh `kanban.db` (sqlite, task_events/task_runs), DevBot `SPRINT.md`/`QUEUE.md` (origin/main), Distillery intake dir + design doc, `~/.t1000/kanban/ROADMAP-DUAL-BOX-2026-08-09.md`, `AUDIT-2026-08-08-worker-cap-and-lab.md`, `hermes cron list --all`. Nothing restarted, nothing written except this file.

**Headline:** all three builds crossed from "designed" to "proven live" in the last 24h. The shared risk across all three is the same shape: **the production step is proven, the review/consumption step is not.** DevBot can run a job cleanly but has no new jobs queued. Distillery can draft a row but nothing has been filed. The mesh can dispatch a worker but ~1 in 6 runs still dies without a clean handoff.

---

## T1000 kanban mesh (the dispatcher/orchestrator/worker system itself)

- **Mission**: the fleet-wide task board + dispatcher that runs every other build in this report (and K2/arctic/desk work). Runs on Ryan's Mac (`~/.t1000/kanban`, `hermes kanban`, `hermes serve`/gateway).
- **Status: LIVE**, high-throughput, but with a real and quantifiable reliability tax (see below). `hermes kanban --board mesh stats`: 120 done, 3 running, 3 ready, 7 scheduled, 10 todo, **42 blocked**. Oldest ready-queue wait: 3219s (~54 min) — dispatch itself is not the bottleneck.
- **Shipped last ~2 weeks (today's items included)**:
  - ctx-floor collision root-caused and fixed (`t_59505920`, archived) — this was the actual cause of the "dead PID" DevBot-lane crashes that had triggered a worker-cap park; verified via `t_c582db54` run #192 completing cleanly on `spark/gpt-oss:120b`.
  - Orchestrator default repointed to `spark/gpt-oss:120b`.
  - Twice-daily digest cron **live** (job `8998d97fe07a`, `0 8,17 * * *`) → Telegram + Buzz `#stats`. Verified healthy: last run 08:00:16, `ok`.
  - **`t_3323c114` (MESH-INFRA, today, biggest worker-reliability find)** — full body read. Two defects on the `claude-acp` backend: (1) `kanban_*` tools are *advertised but not natively bound* to Claude Code's native tool set when Hermes runs a worker over ACP — a worker following its own injected instructions ("use the `kanban_*` tools") gets `Error: No such tool available: kanban_create` and either has to discover the undocumented `<tool_call>` text-block escape hatch or die without closing the task. Proven fixable: a `kanban_heartbeat` issued as a raw `<tool_call>` text block round-tripped live (task_events row 2949). (2) A separate "task is still running / protocol violation" nag (`agent/kanban_stop.py:92`) fires off stale in-session state, not live DB state, so it nags already-`done` tasks — confirmed by DB query it has **not** poisoned the real `protocol_violation` streak counter (25 events across all boards in the full history checked, 0 fired after completion). Fix for both landed **in the task's workspace only** (6 files, +291/-8, 72+45+23 tests green, zero regressions vs. a clean baseline) and the card is sitting `blocked` with `review-required` — **not yet reviewed, not merged, not deployed to the live prompt path.**
- **In flight / carded**:
  - `t_8b9f196f` — goal-judge completion-gate fix (the transport_failed / shadowed-30s-timeout bug: a transient judge timeout hard-*rejects* a legitimate completion at two call sites, `kanban.py:2196` and `kanban_tools.py:727`). This is diagnosed in detail and scoped, but the *worker trying to implement the fix* has itself **timed out twice** (run #181 timed_out, run #195 `gave_up` at iteration budget 90/90) — the fix for "the judge times out and blocks completions" is stuck because the fixing agent also runs out of budget. Still blocked, unimplemented.
  - MESH-TEL telemetry series: `t_ca387cf4`/`t_e1a86e85`/`t_08184cd2`/`t_d19efc08` done; `t_02aca524` (usage+success daily digest) todo; `t_3a1b8b6b` (call-record sink schema) **blocked**; `t_b3a90086` (emit at chokepoints) todo; `t_d7f24672` (claude-acp hardcoded-zero-tokens) todo; `t_2545126f` (verify ≥95% model-attribution) scheduled. Roughly half-built — census and instrumentation-design done, the actual emit-and-verify half is not.
  - `AUDIT-2026-08-08-worker-cap-and-lab.md` follow-ups explicitly **not done**: (1) CLI `hermes kanban dispatch` should flock the same `.dispatcher.lock` the gateway uses — it currently doesn't, which is the root cause of the same-second double-spawn that blew through `max_in_progress_per_profile=2` up to 4 running workers; (2) optional cross-board per-profile cap; (3) avoid ad hoc `kanban dispatch` while the gateway owns the board.
  - Minor: a fourth cron, "Kanban status health (safe auto)" (`50cc3d2bbf9a`, every 4h), is currently **failing** every run — `Script not found: /Users/ryan/.t1000/scripts/kanban_status_health.py --apply-safe` (looks like the script path and its own CLI flag got concatenated into one field at registration). Self-observability of the mesh's own health is silently broken.
- **Top 3 gaps/risks**:
  1. **Worker reliability tax is real and measured** (full breakdown below): ~15.5% of dispatched runs in the last 48h did not reach a clean terminal state on their own.
  2. **42 blocked cards**, several stuck on pure human-decision backlog for a long time: `t_aab9f0d6` 83h, `t_fb05b715` 67h, three cards 34-35h. The mesh generates decisions faster than Ryan clears them.
  3. The one card that would most reduce failure rate (`t_3323c114`) is finished but unreviewed/unmerged — it is sitting exactly where the review bottleneck pattern (see headline) shows up again.
- **Next 3 moves**:
  1. Review and land `t_3323c114`'s patch (kills the dominant crash class — see below) — it's done, tested, and waiting on a human look.
  2. Fix the CLI-vs-gateway dispatcher lock race (AUDIT doc follow-up #1) — kills the second-largest crash class.
  3. Fix the broken `kanban_status_health.py --apply-safe` cron registration and re-scope `t_8b9f196f` with a smaller iteration budget or human-assisted pairing rather than full 90-iteration autonomy.
- **Verdict: INVEST.** This is the substrate everything else runs on; the failure modes are well-diagnosed (not mysterious) and cheap to close.

### Worker-reliability failure-rate story (evidence, last 48h, mesh board)

`task_runs` started in the last 48h: **174 total.**

| outcome | count | share |
|---|---|---|
| completed | 72 | 41% |
| blocked | 54 | 31% (mostly legitimate review-required holds) |
| **crashed** | **24** | **14%** |
| reclaimed (zombie/manual recovery) | 10 | 6% |
| scheduled | 10 | 6% |
| gave_up | 2 | 1% |
| timed_out | 1 | 1% |
| (empty) | 3 | 2% |

Runs that **never reached a clean terminal state unassisted** (crashed + gave_up + timed_out) = **27/174 ≈ 15.5%.**

Breaking down the 24 `crashed` runs by root cause (classified from the stored error string):

- **14/24 (58%)** — *"worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation."* This is the dominant class, and it is exactly the failure mode `t_3323c114` diagnosed and fixed: on the `claude-acp` backend, `kanban_*` tools are not natively bound, so a worker that doesn't discover the `<tool_call>` text-block escape hatch (or the sanctioned CLI fallback) simply finishes its work and exits without ever telling the board it's done.
- **10/24 (42%)** — *"pid NNNNN not alive"* (dead-pid crashes). This matches the AUDIT doc's diagnosis: same-second double-spawns past the per-profile cap, caused by the CLI dispatch path not sharing the gateway's `.dispatcher.lock`.

**Top 2 mechanical fixes, in priority order:**

1. **Land `t_3323c114`** — ACP kanban-tool-call guidance + live-DB-backed stop-nudge, already implemented and tested (6 files, zero regressions), currently sitting `blocked: review-required`. This alone targets the 58% majority of crashes.
2. **Flock the CLI dispatch path to `.dispatcher.lock`** (documented, not started) — closes the same-second double-spawn / dead-pid class, the remaining 42% of crashes.

Together these two (both diagnosed, one already coded) would address essentially all of the 24 crashed runs — i.e. most of the 15.5% non-terminal-run rate.

---

## DevBot (eng-job runner)

- **Mission**: takes `status: approved` job cards from `docs/agent-coordination/devbot/QUEUE.md`, runs a propose (draft plan, 120B) + code (implementation, cheap/local model) phase, and produces a diff/PR for Ryan. Runs Mac-free on Kevin's Spark box (`kevin-spark`, DS4 DeepSeek-Flash on `:8889`).
- **Status: LIVE (supervised), but the job queue is functionally EMPTY.** `QUEUE.md` (origin/main, updated 2026-08-08 PM) lists 12 job cards total: db-0001…0007 are "approved (legacy dogfood, optional re-run)"; db-0008…0012 are "done". db-0013 (referenced heavily today) is a **re-run of an existing slot** used to prove wall-clock/token instrumentation, not a new job. There is no `db-0014` or later. DevBot works — it just has nothing new to build.
- **Shipped last ~2 weeks (today's items included)**:
  - **Supervised sign-off landed** (`t_d11fa676`, done, completed 2026-08-09 07:59): Ryan signed GREEN in-session on db-0013 evidence — Mac-free run on kevin-spark, code phase `deepseek-v4-flash@8889` ctx 65536, `ok=2 fail=0`, first-ever real `wall_s=41.422` captured. Runner synced to origin/main (#4414 fail-closed preflight + #4417 wall_s). Supervised DevBot runs are now declared "a normal repeatable lane."
  - **Night dequeue armed** (`t_72ea765f`, done, completed 08:04): `/home/ryan-lab/devbot/night_dequeue.sh` on kevin-spark, crontab `30 2 * * *` (02:30 ET), picks the first `status: approved` job lacking a log, runs `devbot_run.py --job <id> --skip-propose` (propose forced OFF, 40-min timeout, pgrep concurrency guard, silent no-op on empty queue). **Proven live at install**: dequeued db-0001 and ran it unattended, rc=0.
  - M2 scoreboard usage-threading — PR **#4452 open, review-required, not merged** (Part 2: real `prompt_tokens`/`completion_tokens` instead of char-count estimates; 44 tests green; synthetic harvest verified `tokens_est=false`). Part 1 (`wall_s`) already verified live on db-0013.
  - Reverse-tunnel decision made and build in progress: `t_20339311` — Ryan decided **keep port 11435**, build the tunnel to match `config.env` as-is (no more edits), mirror the `ds4-reverse-tunnel.service` pattern. Card status is **`running`** right now (run #225 active) — not yet complete as of this read.
  - `t_700d9953` (harvest kevin-box scoreboard rows home to Mac SoT) — created this morning, **`ready`, unclaimed**. Kevin-box Mac-free runs append to a scoreboard file on kevin-spark that the Mac-side digest never reads, so today's real wall_s row is invisible to the twice-daily digest until this lands.
- **In flight / carded**: `t_20339311` (M2 tunnel, running), `t_700d9953` (harvest, ready/unclaimed), PR #4452 (open, unmerged).
- **Top 3 gaps/risks**:
  1. **Job-generation is the strategic gap, exactly as flagged.** 12 cards have ever existed; 5 are legacy dogfood, 5 are done, one is a re-run. Nothing generates new `approved` job cards. Night dequeue is armed and *will* run — against an empty queue, it is a no-op every night.
  2. Propose lane is still RED (`models.propose: skip` forced) pending `t_20339311`; DevBot has only proven its **code** phase end-to-end, not the **propose/plan** phase on 120B.
  3. Kevin-box scoreboard rows are stranded (`t_700d9953` unclaimed) — the twice-daily digest currently undercounts real DevBot activity, which is an observability gap on a system the CLAUDE.md observability principle specifically calls out.
- **Next 3 moves**:
  1. Land `t_20339311` (in progress) and do one propose-ON supervised run to prove the full pipeline, not just the code half.
  2. Pick up `t_700d9953` — small, ready, unclaimed, fixes the digest undercount.
  3. **Build a job-generation source** (SPRINT.md "Next" item G: "widened-fence eng jobs (hub/tests)") — without this, DevBot stays a proven-but-idle factory floor; the mechanical risk (fail-closed preflight, dual-load mutex, wall-clock/token instrumentation) is solved, the input-pipe is not.
- **Verdict: INVEST.** Mechanically de-risked (rc=0 proven, real timing/tokens now captured, night cron fail-safe and armed) — the remaining work is almost entirely "give it something to do," which is a cheap, high-leverage next step.

---

## Distillery intake (pattern-harvesting pull sweep)

- **Mission**: read-only pull sweep over systems of record (`~/.hermes/plans/`, `docs/research/signal-log/entries/`, mesh `done` cards, skill `references/` trees) that fingerprints each durable artifact and drafts a review row, so nothing shipped is silently unconnected to the pattern ledger. **Never writes into K2 Distillery / PATTERN-LEDGER / Buzz — filing is always a human action.** Runs from `~/Documents/T1000` + `~/.t1000/scripts` (dual-written) on Ryan's Mac.
- **Status: LIVE (sweep + cron), but 100% DARK on review.** `index.json` right now: **161 rows, all status=`draft`** (119 mesh_done_card, 23 skill_reference, 11 signal_log_entry, 8 plan). Zero `filed`, zero `skipped`. Cron `534f64030bae` is `[active]`, every 360m, next run 14:11 CT, silent-when-clean, delivers to Telegram — confirmed armed and healthy in `hermes cron list --all`.
- **Shipped last ~2 weeks (today's items included)**:
  - Full design→implement→wire pipeline built same-day: design `t_216ac84b`, implement `t_9c64c42a` (done, 08:03), wire `t_a7553997` (running now — see below).
  - **156 drafts committed** to the T1000 repo across two commits — `e5834a8e7` (backfill, 141 rows: 8 plans / 11 signal entries / 99 mesh done cards / 23 skill refs) and `4a6428a6e` ("distillery sweep pass — 15 new drafts from 2026-08-09 morning cards"). Live index.json has since grown to 161 (5 more rows + a modified `index.json` are **currently uncommitted** in the working tree).
  - **6h sweep cron armed** (`t_a7553997`/`t_e6fd0cb3`, job `534f64030bae`) — Ryan explicitly signed GREEN and armed it in-session 2026-08-09 ("please arm the distillery cron"). `t_e6fd0cb3` (the HUMAN gate card) is `done`.
  - Staleness policy decided deliberately: `captured_at` stays at true capture time (not backdated to source mtime), meaning the 5-day staleness clock is honest but also means **all ~141 backfill rows will flip to `stale` in one batch on 2026-08-14** unless bulk-triaged first — this was called out and accepted as a known risk, not fixed.
- **In flight / carded**:
  - `t_a7553997` — **running now** (run #224 active). Remaining scope per its own comment: only the `kanban-checkin` skill wrap-up patch (point future sessions at the sweep + draft queue, document the manual-draft escape hatch). Cron half is already done.
  - `t_048f0c5c` — the actual first manual filing tranche (5 concrete candidate rows Ryan/agents already identified: send-path lint reachability gap, LAB-0010/0012 reason-first panel, LAB-0011 WAN-leg pattern, LAB-0023 hardening-creates-bypass, Proofmark fee-agreement trigger shape). **Blocked since 2026-08-07**, block reason still reads "recon-first, no free-fire rebuild... re-block until Ryan promote" — i.e. the one card that would prove the review/filing step actually works has been sitting untouched through the entire build-and-arm cycle above.
- **Top 3 gaps/risks**:
  1. **No review has happened.** The sweep is a perfect faucet with no drain: 161 drafts, 0 filed, 0 skipped, and no review *agent* — filing is human-only by design, and no human filing has occurred yet.
  2. **Committed the batch will go stale as one loud event on 2026-08-14** — a known, accepted, unmitigated risk. If nobody triages before then, the first signal from this system will be "141+ items are stale," which risks reading as noise rather than the intended review nudge.
  3. **Working-tree drift already**: 5 new draft files + a modified `index.json` are uncommitted right now, hours after the pipeline was declared "fully live" — the design's stated audit-trail rationale ("git history is a free audit trail") only holds if commits keep pace with sweep runs.
- **Next 3 moves**:
  1. Commit the 5 new draft files + updated `index.json` now, before the next 6h tick compounds the diff further.
  2. Use `t_048f0c5c`'s already-identified 5 rows as the first real filing pass — it both produces value and proves the review step is not vaporware, and it unblocks the oldest stale card in this whole area (open since 08-07).
  3. Finish `t_a7553997`'s remaining scope (kanban-checkin skill wrap-up patch) so the next session's session-start ritual actually surfaces the queue instead of relying on someone remembering it exists.
- **Verdict: MAINTAIN, leaning INVEST.** The mechanism is sound, cheap, and correctly scoped (mesh-only, pull, never auto-files) — but right now 100% of its output is unconsumed. Its value is entirely in the filing step, and that step hasn't started.

---

## Cross-cutting note (ties to `ROADMAP-DUAL-BOX-2026-08-09.md`)

This report does not contradict the roadmap doc — it's consistent with and extends it: the roadmap's own "Human queue" section already names the same Ryan-owed items surfaced above (`t_700d9953` harvest, `t_6fb2c9c3` digest cron command, `t_b82de3da` Distillery decisions — already executed since the roadmap was written this morning). The one addition this report makes beyond the roadmap is the **quantified worker-reliability failure-rate** (15.5% non-terminal, split 58/42 between the two named mechanical causes) and the explicit call that **`t_3323c114`'s finished patch is unreviewed** — the roadmap doc doesn't mention that card at all, and it's the single highest-leverage unmerged fix in the whole system right now.
