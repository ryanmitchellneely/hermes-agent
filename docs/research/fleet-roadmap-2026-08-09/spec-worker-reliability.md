# SPEC: Worker Reliability Layer (mesh)

## Problem + evidence
Measured over the last 48h on the mesh board (pm-factory recon, 2026-08-09): **174 runs,
27 (15.5%) never reached a clean terminal state unassisted.** The 24 crashes split into
exactly two known causes:
- **58% — ACP kanban-tool binding gap**: `kanban_*` tools advertised but not natively bound
  on the claude-acp backend; workers finish their work and exit rc=0 without ever telling
  the board → protocol_violation. Diagnosed AND FIXED on `t_3323c114` (6 files, +291/-8,
  140 tests green in its workspace) — **unreviewed, unmerged**.
- **42% — dispatcher lock race**: CLI `hermes kanban dispatch` does not flock the gateway's
  `.dispatcher.lock` → same-second double-spawns blow past max_in_progress_per_profile
  → dead-pid crashes. Documented in AUDIT-2026-08-08-worker-cap-and-lab.md, unstarted.
Also: the mesh's own health cron ("Kanban status health", 50cc2d3bbf9a-class id) fails every
run — script path and its `--apply-safe` flag were concatenated into one field at
registration. And the goal-judge gate fix (`t_8b9f196f`) is stuck because the worker
fixing the 90-iteration timeout itself times out at 90 iterations.
Related upstream: 5/9 subagents in today's PM/spec fan-out returned filler finals
(the "final-message-only" harness gotcha) — mitigated session-side by file-deliverables;
a durable fix belongs in the dispatch prompt path.

## V1 scope
1. Review + merge `t_3323c114`'s existing patch (T1000 repo; no branch protection; run its
   140-test suite + the 3 regression suites on a clean tree first).
2. Flock the CLI dispatch path to `.dispatcher.lock` (one function; AUDIT doc names it).
3. Re-register the kanban-status-health cron with script and args in separate fields.
4. Re-scope `t_8b9f196f` to a 30-iteration human-paired fix instead of 90-iteration autonomy.
5. Add a `reliability` section to the twice-daily digest: runs/terminal-clean %, crash
   split by class, gave_up count (data already in kanban.db — 3 SQL queries).

## Non-goals
No dispatcher rewrite; no new agent framework; no retry-policy tuning beyond the two
named fixes; no changes to K2-side workers.

## Gates & risks
All T1000-repo/Mac-local; no restarts of serving lanes; the t_3323c114 merge touches the
live prompt path — merge during a quiet dispatch window and watch the next 5 runs.
Success = crash class share drops from 15.5% toward <5% over the following 48h (digest
reliability section proves it either way).

## Card decomposition
- WR-1 (ready): Review + merge t_3323c114 patch on clean main; verify next 5 dispatches clean.
- WR-2 (ready): Flock CLI dispatch to .dispatcher.lock per AUDIT-2026-08-08 follow-up #1.
- WR-3 (ready): Fix kanban-status-health cron registration (script vs args fields).
- WR-4 (ready): Add reliability section to kevin_digest.py (3 SQL queries over task_runs).
- WR-5 (todo, parents WR-1..4): 48h after-measurement — rerun the 48h failure-rate query,
  paste before/after into card, comment the digest card.

## Open questions
1. Should protocol_violation retries be capped at 1 (not 3) now that the root cause is fixed —
   saving ~2 wasted runs per residual failure?
