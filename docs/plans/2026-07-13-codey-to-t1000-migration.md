# Code-y to T1000 native work-lane migration

Status: Proposed
Date: 2026-07-13
Decider: Ryan Neely

## Context

Tom Thump is archived and must not be restored. The Code-y wrapper and its K2
dispatcher are disconnected, their launchd jobs are removed, and K2 keeps a
checked-in kill switch. Ryan has also ruled that there are no scheduled Code-y
runs at this point.

The useful part of the old system was not its name or runtime. It was a bounded
control plane around attended code work: structured intake, one-task claims,
isolated worktrees, cost and write guards, stale-claim recovery, independent
review, and completion receipts.

T1000 already has most of the generic substrate:

- native Codex OAuth/Responses support;
- SQLite-backed Kanban tasks, claims, workspaces, retries, heartbeats, and
  review-required handoffs;
- isolated CLI worktrees;
- approval and plugin hooks;
- plugin CLI and slash-command registration;
- skills and structured completion events.

The migration should extend those primitives at the edge. It should not copy
Tom Thump or grow a second agent core.

## Decision

Build a private T1000 plugin named `k2-work` plus a companion skill. The visible
entry point belongs to Juice, while T1000 remains the execution engine.

The plugin will adapt K2's repo inbox contract to a dedicated T1000 Kanban
board. It will use the native `openai-codex` / `codex_responses` agent path,
T1000-managed task state, and an isolated worktree. It will not shell out to
`hermes codey`, import Tom Thump, or reuse Tom Thump state.

The first release is manually triggered only:

1. `plan` reads and validates one K2 brief without claiming it.
2. `import` creates or reconciles one idempotent Kanban task.
3. `run` claims and executes exactly one explicitly named task.
4. `status` reports task, branch, budget, tests, and review state.
5. `receipt` writes the K2 outbox handoff after validation.

Behavioral controls belong in `~/.t1000/config.yaml`, not `.env`. The plugin's
own `k2_work.enabled` setting defaults to `false`; a file at
`~/.t1000/k2-work.disabled` is its independent emergency stop.

`/k2-work` may surface those actions in the Juice desktop slash palette. It
must remain separate from the existing `/juice` R0-R5 communication-
comprehension ladder, whose classify-only and no-send boundaries are unrelated
to code execution.

## Scheduling boundary

Scheduling is deliberately unauthorized, not an implementation gap.

Before the K2 adapter is enabled:

- keep `k2_work.enabled: false` until the attended pilot is explicitly started;
- do not create T1000 cron jobs, launchd jobs, systemd units, or a Kanban
  daemon for this lane;
- import K2 tasks unassigned and parked in a non-runnable state;
- require an explicit task id on every `run` command;
- make `run <task-id>` claim that exact task directly, without a general
  dispatcher pass;
- keep `.codey-dispatcher.disabled` in the K2 repo;
- verify a Juice/T1000 restart does not import, claim, or execute K2 work.

This boundary applies to the K2 work lane. It does not silently modify or
disable unrelated T1000 jobs or global Kanban dispatch that Ryan has separately
authorized. The K2 lane is manual-only because its cards are parked and its
own gate is default-off, not because global dispatcher behavior is changed.

## Capability mapping

| Retired behavior worth keeping | T1000-native home | Required delta |
|---|---|---|
| Human-open numeric inbox, lowest-first ordering | Kanban task metadata and priority | K2 front-matter importer with source path, source hash, numeric id, and `Status: open` gate |
| Durable claim lifecycle | Kanban claims, runs, heartbeats, retries | Add a supported exact-task primitive that atomically moves one K2 card from `blocked` to `running`, assigns its attended worker, and creates its run row |
| Parallel isolation | Kanban workspace/branch fields and CLI worktrees | Fail closed if an isolated worktree cannot be created |
| Stale claim and crash recovery | Kanban reclaim, timeout, and failure circuit breaker | K2-facing recovery status and receipt text |
| Codex execution | Native `openai-codex` / `codex_responses` | Pin the attended K2 profile; do not use Codex app-server until policy parity is proven |
| Kill switch before any I/O | Plugin command preflight and hooks | Check the separate T1000 lane gate while requiring K2 `.codey-dispatcher.disabled` as proof the legacy lane stays dead |
| Sierra, send, and path rails | T1000 approvals and plugin hooks | Unconditionally deny Sierra mutation and outbound send; separately encode protected paths, lane ownership, and no self-merge rules |
| Budget and escalation backpressure | Kanban run/concurrency limits | Dollar/run ledger, per-task ceiling, daily ceiling, and K2 escalation-queue gate |
| Completion audit | Kanban events, comments, run metadata | K2 outbox exporter with diff, tests, branch, PR, spend, and deferred work |
| Independent approval | Kanban `review-required` handoff | Separate reviewer/human approval; execution context cannot approve itself |
| Standing reports | Preserved brief templates | Manual-only buttons/commands; no cadence in the initial migration |

## K2 policy contract

The plugin uses two ordered gates. A local static gate runs before any network
operation:

1. The legacy K2 `.codey-dispatcher.disabled` file exists, proving the old lane
   is still dead; this is an invariant, not the new lane's enable switch.
2. `k2_work.enabled` is true and `~/.t1000/k2-work.disabled` is absent.
3. The brief is numeric, canonical, and explicitly `Status: open`.
4. Its cost ceiling is present and valid.
5. No locally known active task or branch already owns the brief's
   deterministic mapping key.
6. The brief cannot authorize a Sierra mutation or outbound send under any
   field, approval, override, or instruction. Either condition is an absolute
   deny.
7. Automatic approval and self-merge are off.

After that gate passes, the only permitted network operation is a read-only
`git fetch origin main`. A second gate validates the fetched brief's status and
hash, the escalation queue, budgets, branch availability, and current upstream
state. Only then may the plugin create a worktree or invoke the model provider.
Push, PR creation, API mutation, and every other network operation remain
blocked until their explicit later policy stage.

Immediately before a direct claim, `run <task-id>` must reread the same brief
from current `origin/main` and match its open status, source commit, and stored
source hash. Drift blocks execution until an attended re-import or reconcile.
The command must lock and promote only the named card; it must never invoke the
general Kanban dispatcher.

All enable, emergency-stop, declared-cost, Sierra, and send preflights run
before the read-only fetch. Source-drift, current budget, escalation, and branch
preflights run immediately after it and before model-provider invocation. A
protected-path change may be review-gated, but Sierra mutation and outbound
send cannot be enabled by review.

Post-execution validation must inspect the actual diff rather than trusting the
agent's narrative. It must block a ready receipt when the diff contains
secrets, forbidden paths, unclassified files, failed required tests, a Sierra
mutation, an outbound-send change, or an invalid branch. A validated push or
draft PR may be an explicit attended action, but independent approval is
required before merge. Amend, force-push, and self-merge remain prohibited.

Codex app-server is deferred because its file edits can occur inside the Codex
subprocess instead of T1000's normal `pre_tool_call` hook path. It can become an
option only after an equivalent post-diff enforcement test proves the same
rails.

## Mapping and reconciliation

The Git brief is the intake source of truth. Its logical idempotency key is the
normalized repository identity plus canonical brief path (including the
numeric brief id). `import` creates or reconciles one unassigned Kanban card in
the parked `blocked` state and stores the source hash and the last commit that
modified that brief. An unrelated advance of `origin/main` therefore does not
invalidate the import. It does not create a branch or worktree.

`run <task-id>` first fetches under the two-gate policy, then rereads and
validates the same brief from current `origin/main`. A changed hash, modifying
commit, or status leaves the card blocked and requires attended reconciliation.
After a successful preflight, the command creates a fresh isolated worktree
from verified current `origin/main`, creates the `codex/*` branch, and records
the repo claim as a new commit without amending existing history.

T1000 must expose a supported `claim_and_start_exact`-style operation. In one
SQLite transaction it conditionally moves the named card directly from
`blocked` to `running`, assigns the attended worker identity, creates the run
row, and records its branch/worktree mapping. It never exposes a `ready` state,
so the gateway dispatcher cannot observe or assign the card. The operation
returns a lease for the adapter to start the exact worker; spawn failure marks
that run failed and recovery returns the card to `blocked`. The adapter must
not call the private `_default_spawn` helper.

The mapping spans Git and SQLite, so recovery is deterministic rather than
claimed to be atomic:

- if the run lease exists but worker spawn did not complete, recovery marks the
  run failed and returns the card to `blocked`;
- if a branch exists but no claim/run transaction completed, recovery reuses
  or cleans that isolated branch under the attended policy instead of creating
  another card;
- if a claim commit and branch exist but the Kanban link is missing, recovery
  attaches that existing branch instead of creating another task or branch;
- repeated import, run, recovery, and receipt commands converge on one Kanban
  task, one active branch, and one eventual completion receipt.

## Options considered

### Copy the old Code-y dispatcher into T1000

Rejected. It preserves the wrong abstractions, hard-coded personal paths,
Tom Thump command shape, detached shell wrappers, and amend/force-push
behavior. It would make the archive live again under a new directory.

### Use T1000 cron or the gateway Kanban dispatcher immediately

Rejected for the initial migration. Those mechanisms are capable, but Ryan has
not authorized unattended K2 execution. Starting with them would violate the
operating decision before the policy adapter has been proven.

### Use only `delegate_task`

Rejected as the durable control plane. `delegate_task` is appropriate for
attended fan-out and can return durable background handles and results. It does
not provide the Kanban claim, cross-restart Git-to-task reconciliation, policy
preflight, or completion-receipt lifecycle required for this lane.

### T1000 plugin plus Kanban

Selected. It reuses the durable primitives, keeps K2-specific behavior outside
the core tool schema, and leaves a small, testable adapter as the only new
surface.

## Delivery sequence

### Phase 0 - freeze and contract tests

- Preserve the legacy K2 kill switch as proof that Code-y remains disconnected.
- Prove the separate T1000 lane gate and emergency stop are checked before any
  repo/network action.
- Keep the K2 lane manual-only with parked, unassigned cards and an exact-task
  run path; do not alter global Kanban dispatch.
- Port behavior tests, not implementation: draft ignored, numeric ordering,
  duplicate mapping, atomic exact-task start, branch collision, stale claim,
  budget/backpressure, Sierra wording, protected paths, and structured audit
  records.
- Prove the exact-start primitive preserves dependency checks, lease/TTL,
  `current_run_id`, run/event creation, board pinning, profile validation, and
  failure counters.

### Phase 1 - read-only plan and import

- Add `k2-work plan`, `import`, and `status`.
- Use a dedicated board so K2 tasks cannot leak into other T1000 work.
- Store the brief path, SHA-256 source hash, numeric id, source commit, cost
  ceiling, and policy result as task metadata.
- Define `source commit` as the last commit that modified the brief.
- Leave imports unassigned and parked in `blocked`.
- Do not spawn an agent or create a branch or worktree in `plan` or `import`.

### Phase 2 - attended execution

- Add `run <task-id>` for one bounded task.
- Atomically move exactly that task from `blocked` to `running`, assign the
  attended worker, and create its run row without a `ready` state or general
  dispatch pass.
- Reread its brief from current `origin/main` and fail closed on source or
  status drift.
- Require an isolated worktree and native Codex Responses profile.
- Stop if upstream fetch fails, the newly created isolated worktree is dirty,
  or branch creation would conflict with an existing or merged branch. An
  unrelated dirty canonical checkout is not used by this lane.
- Fail closed when pricing is unknown; every task also requires an explicit
  maximum model-token/run ceiling independent of dollar pricing.
- Keep auto-approval, auto-commit, auto-push, and self-merge off by default.
- Allow short-lived `delegate_task` children only inside the attended run and
  within configured concurrency/depth limits.

### Phase 3 - verify and export

- Validate the diff, secret scan, expected tests, branch, and policy rails.
- Record cost/run status in Kanban.
- Write a K2 outbox receipt and mark code work `review-required`.
- Permit a validated push or draft PR only as an explicit attended action.
- Require an independent reviewer or Ryan before merge; never amend,
  force-push, or self-merge.

### Phase 4 - pilot

- Run a synthetic read-only brief.
- Run a docs-only brief.
- Run one low-risk code brief with no Sierra/send/shared-path contact.
- Kill and restart T1000 during a run to prove recovery and no automatic
  redispatch.
- Prove duplicate import, forbidden path, Sierra wording, failed test, and
  kill-switch cases all fail closed.

### Later decision - unattended operation

Scheduling, gateway dispatch, and manual standing-report buttons are separate
decisions after the pilot. They are not implied by completing this migration.

## Acceptance criteria

- No Tom Thump import, process, state path, or command is used.
- No `hermes codey` invocation exists in the new lane.
- No scheduled K2/Code-y run exists.
- The legacy Code-y kill switch remains present while the new lane uses its own
  default-off enable control and emergency stop.
- Import leaves a K2 task unassigned and parked; restarting Juice/T1000 cannot
  transition, claim, or run it.
- A human can plan and run exactly one named task through Juice/T1000. The
  adapter mutates no other task record or event on the dedicated K2 board;
  unrelated authorized boards may continue independently.
- The task executes in an isolated `codex/*` worktree through native Codex
  Responses support.
- The worktree starts from verified current `origin/main`; fetch failure,
  dirty state, source/status drift, or branch conflict stops execution.
- Kill-switch, duplicate, declared-cost, Sierra, and send cases stop before any
  network operation. After the sole read-only fetch, current per-task and daily
  budgets, unknown pricing, escalation, source drift, and branch conflicts stop
  before model-provider or any other network invocation.
- Sierra mutation and outbound send are unconditional denies with no approval,
  brief field, or override path.
- Protected-path and failed-test cases stop before a ready receipt.
- A crash at each Git/SQLite mapping boundary reconciles to exactly one task,
  one active branch, and one eventual receipt.
- The exact-start concurrency test proves a globally enabled dispatcher cannot
  observe or assign the K2 card between its parked state and attended run.
- Completion produces structured Kanban state and a source-honest K2 outbox
  receipt.
- Independent approval remains required before merge; amend, force-push, and
  self-merge are prohibited.
- Retirement verification proves launchd labels
  `com.k2hub.codey-dispatcher`, `com.k2.codex-weekly-matrix-audit`,
  `com.k2.codex-weekly-pr-digest`, and `com.k2.codex-daily-readiness` are absent;
  no Code-y cron or systemd job exists; `start-codex-matrix-audit.sh`,
  `start-codex-digest.sh`, and `start-codex-readiness.sh` each exit 78; and a
  restart plus two dispatcher intervals produces no K2 import, claim, run, or
  receipt event in instrumented counters relative to the pre-restart event
  baseline.
- Effective configuration proves the separate K2 gate is default-off and the
  lane is manual-only without changing unrelated global dispatch.

## Consequences

The first useful replacement will be attended and intentionally less automatic
than Code-y. That is the safety feature: it lets the durable state and policy
rails prove themselves before any cadence is considered.

T1000 gains one private edge plugin rather than another orchestration core.
K2 keeps ownership of its repo policy and output contract, while Juice/T1000
owns execution state, model routing, worktree isolation, and the operator
surface.
