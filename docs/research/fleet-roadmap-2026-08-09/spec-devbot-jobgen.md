# SPEC

## Problem + evidence

DevBot's night dequeue is now armed. `t_72ea765f` on the mesh board shows: **"ARMED BY RYAN 2026-08-09 (in-session sign-off)"** — `/home/ryan-lab/devbot/night_dequeue.sh` is built on kevin-spark, picks the first `status: approved` job lacking an `<id>-code.json` log, runs `devbot_run.py --job <id> --skip-propose` (40 min timeout), one job per night, cron `30 2 * * *` (02:30 ET), pgrep-guarded against concurrent runs, silent no-op on empty queue. It was proven live at install by dequeuing `db-0001` unattended (rc=0).

**The queue has nothing new to dequeue.** All twelve job files under `docs/agent-coordination/devbot/jobs/` (`db-0001` … `db-0013`, minus `db-0009`) are either `status: done` or `status: approved` smoke/dogfood cards written to prove the DS4 Flash pipeline itself (grounding smokes, codebooks, ops-log notes) — not a backlog of real engineering work. `db-0001` was already consumed by the arming run. The mesh board carries `t_02ca723e` ("Next fenced eng job on Kevin Mac-free") explicitly `blocked` with the note **"HUMAN picks eng scope — do not free-fire"** — the queue-filling step is a named, acknowledged, unstaffed bottleneck.

**⚠️ Stale-doc conflict found during this spec's own research (flag per CLAUDE.md's reconcile-before-you-present rule):** `docs/agent-coordination/devbot/SPRINT.md`, `STATUS.md`, and `QUEUE.md` (last touched 2026-08-08, commit `2806b5cf4`) all still assert **"night dequeue OFF"** as locked truth. The arming happened 2026-08-09 via kanban card, not yet reflected in those docs. Whoever builds this pipeline should land a one-line doc fix (`night cron: ARMED 2026-08-09, see t_72ea765f`) alongside it — captured here as Wave-0 hygiene, not scope creep, because a generator that writes toward a queue nobody believes is live will get ignored.

**Safety spine already in place, do not re-litigate:** `scripts/devbot_run.py` L1505 refuses any job whose `status` is not `approved` or `in_progress` (`refusing job status={status!r} (need approved)`, exit 2) unless `--dry-run`. This means **generation cannot imply approval by construction** — a generator can only ever produce `draft`/`proposed` status, and the runner is structurally incapable of picking those up. That invariant is the whole safety argument for this spec; the design sketch below never tries to route around it.

## V1 scope

A weekly (not continuous, not per-commit) generation pass that:

1. Reads the mesh board (`hermes kanban --board mesh list` / `show`) for `ready`/`todo` cards.
2. Applies a mechanical **admission filter** (below) to find cards that are job-able.
3. For each admitted card, writes ONE new file under `docs/agent-coordination/devbot/jobs/db-NNNN-<slug>.md` in the existing frontmatter+body format (id/status/title/repos/paths/fence/autonomy/approved_by/source/risk/models/acceptance), with **`status: draft`**.
4. Caps output at 3-5 draft jobs per run.
5. Surfaces the batch to Ryan through exactly one channel (see Design sketch) — no silent landing.
6. Stops. Does not touch `SPRINT.md`, does not flip any status, does not run `devbot_run.py`.

Ryan (or Kevin, for `kevin-lab/**`-scoped cards under his lane) reviews each draft and manually edits `status: draft` → `status: approved` (plus fills `approved_by`) when satisfied. That flip is the only thing that makes a job eligible for the night dequeue. This spec does not build or propose the review UI beyond "how the batch gets in front of a human" — that's Non-goals below.

## Non-goals

- **No auto-approval, ever.** No code path in this pipeline sets `status: approved`. That is a hand-edit only Ryan (or Kevin in his lane) performs.
- **No night-queue writes.** The generator never touches `night_dequeue.sh`, its crontab, or `logs/night-last.json`.
- **No Sierra-adjacent, restart-triggering, or cross-lane cards get admitted** — the filter rejects them outright (see below), it doesn't downgrade or flag them for special handling.
- **No multi-file (3+) jobs in v1** — `QUEUE-TIP.md` on `origin/main` is explicit: "Multi-file writes (2+ files) can hit 500 / truncate on Flash unless the runner is lean" and "Never batch 5+ files in one Flash call." V1 caps at 2 files per generated job, matching db-0013's shape.
- **Not a real-time trigger.** No hook fires generation the moment a mesh card turns `ready`. It's a scheduled sweep, matching the existing weekly-triage rhythm already defined by `t_ca406f9d` ("Define mesh board weekly triage rhythm (human promote)") — reuse that cadence rather than inventing a second one.
- **Not a replacement for `t_02ca723e`.** That card stays exactly as blocked/human-scoped as it is today; this pipeline is a *parallel*, narrower lane for the subset of backlog that's mechanical enough to not need Ryan to hand-scope it. Anything ambiguous still routes through `t_02ca723e`.
- **No new merge path.** Whether drafts land via PR or direct commit is an open question (below), but under no interpretation does this spec add a new self-merge exception.

## Design sketch

```
weekly trigger (piggybacks t_ca406f9d's triage rhythm)
        │
        ▼
┌─────────────────────────┐
│ 1. Pull mesh board       │  hermes kanban --board mesh list
│    ready + todo cards    │  (skip blocked/done/running/scheduled)
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ 2. Admission filter      │  mechanical, all-must-pass (see below)
│    (READ-ONLY judgment)  │
└──────────┬────────────────┘
           ▼  (0-5 cards survive; if 0, no-op — no empty PR)
┌─────────────────────────┐
│ 3. Render job file(s)    │  frontmatter: status: draft
│    per admitted card     │  paths: derived from card body / filter step
│    (reuse db-00XX shape) │  acceptance: mechanically checkable only
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ 4. Land drafts           │  see "Where generated drafts land" open Q —
│    (PR on claude/* OR    │  default to normal PR unless ruled otherwise
│     direct if ruled       │
│     coordination-only)   │
└──────────┬────────────────┘
           ▼
┌─────────────────────────┐
│ 5. Human review surface  │  ONE mesh HUMAN card per batch, born blocked:
│                          │  "HUMAN gate: review N draft DevBot jobs
│                          │   (db-NNNN..db-NNNN)" — links the PR/commit,
│                          │  lists each draft's one-line acceptance.
│                          │  Ryan un-blocks it once he's actioned the batch
│                          │  (approved some, rejected/deleted others).
└──────────────────────────┘
```

**Admission filter** — the generator's entire judgment surface, and it must be mechanical/checkable, not vibes:

| Check | Rule |
|---|---|
| Repo scope | Card names or clearly implies exactly one repo (`kevin-real-estate-tools`) |
| Path scope | Card's target files are nameable up front and expressible as a `fence:` (no "somewhere in the codebase" cards) |
| File count | ≤ 2 files touched, matching `QUEUE-TIP.md`'s lean-Flash cap |
| Acceptance | Card's done-condition reduces to a grep/exists/diff check — no "looks right," no visual judgment, no live-service verification |
| Sierra | Zero Sierra read or write paths (`k2_hub/sierra_client.py`, `sierra_sandbox.py`, anything tagged send-path) |
| Restarts / services | No launchd/systemd/cron install-or-restart step required to verify done |
| Lane | Not in the other agent's owned directories/branches; not a doc in the CLAUDE.md shared-doc list |
| Risk | Card or generator's own read of it maps to `risk: low` — anything ambiguous is rejected, not downgraded |

A card failing any row is **skipped silently** for that run (not rejected-with-comment on the mesh card — this pipeline does not write to mesh cards it doesn't admit, to avoid spamming board history with a bot's opinion). It remains eligible next week if its shape changes.

**Card decomposition** field mapping (job frontmatter ← mesh card):
- `title` ← card title, trimmed
- `repos: [kevin-real-estate-tools]` (v1 hardcoded, matches every existing job file)
- `paths:` ← the ≤2 files the filter identified
- `fence: ryan` (or `kevin` if under `kevin-lab/**` — matches ownership table)
- `autonomy: propose` (matches every existing job; code auto, propose skip per `models:` block — v1 always skips propose to save the 120B round-trip, matching db-0008/db-0012's convention)
- `status: draft` (never `approved` — the load-bearing line of this whole spec)
- `approved_by: []` (empty; filled by hand on approval)
- `source: mesh:<card_id>` (new convention — traceability back to the origin card; none of the existing job files need this since they were hand-authored, but a generated job must carry provenance)
- `risk: low`
- `acceptance:` ← mechanical checks lifted from the card body, rewritten as file-exists/grep/diff assertions

## Gates & risks

- **Runner-refusal gate (existing, verified):** `devbot_run.py` L1505 hard-refuses non-approved/in_progress status. This is the only gate that actually matters for safety and it already exists — this spec adds nothing here, just depends on it.
- **Single human-review chokepoint:** if the weekly HUMAN card gets ignored, drafts pile up unreviewed but **cannot** leak into the night queue (same gate). Worst case is clutter, not an unauthorized run. Still: cap at 3-5/week specifically so the review batch stays skimmable in one sitting.
- **Admission filter false positives:** a card that looks file-scoped but actually needs judgment calls (e.g., "fix the bug in X" without a clear acceptance check) could get admitted and produce a job whose acceptance criteria are technically mechanical but substantively wrong. Mitigation: acceptance criteria must be lifted verbatim-ish from the card, not invented by the generator — if the card doesn't state a checkable done-condition, the card fails admission.
- **Landing-path risk (see Open Questions):** if drafts land via direct commit to `main` under a "coordination-only" reading of the pr-efficiency-loop rule, and that reading turns out wrong, it's an accidental direct-to-main write of code-adjacent files. This is exactly why it's called out as an open question rather than assumed.
- **Doc drift compounding:** SPRINT.md/STATUS.md/QUEUE.md are already stale on the arming fact (see Problem). If this pipeline ships without the one-line fix, the generator is producing jobs against a queue its own source docs still claim doesn't run — confusing for the next agent who reads SPRINT.md instead of the kanban board.
- **DS4 quality ceiling isn't this spec's problem to solve** — `QUEUE-TIP.md` and `JOB-LOG-0012` already document the multi-file 500 failure mode and its lean-runner workaround. V1 sidesteps it entirely via the 2-file cap rather than trying to out-engineer Flash's context handling.

## Acceptance criteria

- [ ] A single script/job (name TBD by implementer) runs on demand and, given the current mesh board state, produces 0-5 files under `docs/agent-coordination/devbot/jobs/db-NNNN-*.md`, each with `status: draft` and a valid `source: mesh:<card_id>` field.
- [ ] No admitted job exceeds 2 files in its `paths:` list.
- [ ] No generated job's frontmatter ever contains `status: approved` — verified by a test that greps every file the generator writes for that exact string and fails the run if found.
- [ ] Running `devbot_run.py --job db-<generated-id>` (without hand-editing status first) exits 2 with "refusing job status='draft'" — i.e., the existing runner gate is exercised, not just assumed, as a smoke test of this pipeline's output.
- [ ] Exactly one mesh HUMAN card is created per generation run that produced ≥1 draft (zero cards if zero drafts — no empty-batch noise), born `blocked`, listing every draft job id in that batch.
- [ ] A card that fails any admission-filter row is not present in that run's job output (spot-checkable against the filter table above).
- [ ] SPRINT.md/STATUS.md/QUEUE.md night-dequeue status corrected to reflect `t_72ea765f`'s ARMED result before or alongside this ships (Wave-0 hygiene card below).

## Card decomposition

**Card 1 — HUMAN: rule on generated-draft landing path (born blocked)**
```
Title: HUMAN: rule on where DevBot-generated draft jobs land (PR vs direct commit)
Body: Generated draft job files under docs/agent-coordination/devbot/jobs/ are
new files with status: draft, never approved. CLAUDE.md's coordination-only
direct-to-main exception is scoped to inbox-*/outbox-*/digests/ledger files —
jobs/ isn't listed and may count as code-adjacent. Need Ryan's ruling: (a)
route via normal PR on a claude/* branch (safe default, matches
scripts_pr_efficiency.py classify == mixed), or (b) extend the coordination
exception to cover jobs/*.md specifically since draft status carries zero
execution risk. Blocks Card 3 until answered.
Parents: none
Born status: blocked
```

**Card 2 — HUMAN: fix stale night-dequeue status in SPRINT/STATUS/QUEUE (born blocked)**
```
Title: HUMAN or agent: correct SPRINT.md/STATUS.md/QUEUE.md — night dequeue is ARMED not OFF
Body: t_72ea765f shows "ARMED BY RYAN 2026-08-09" with night_dequeue.sh live
on kevin-spark (crontab 30 2 * * *, proven dequeuing db-0001 rc=0). But
docs/agent-coordination/devbot/SPRINT.md, STATUS.md, and QUEUE.md (last
touched 2026-08-08, commit 2806b5cf4) still say "night dequeue OFF" as
locked truth. One-line fix in each: point at t_72ea765f as the arming record.
Do this before or alongside the job-generation pipeline so the generator
isn't producing jobs against a queue its own SoT docs deny exists.
Parents: none
Born status: blocked (small, but touches SoT truth-lock language — human eyes first)
```

**Card 3 — Worker: build the admission filter (mechanical judgment, no I/O yet)**
```
Title: DevBot job-gen: build admission filter over mesh card fields
Body: Implement the 8-row admission filter from spec-devbot-jobgen.md's
Design sketch (repo scope, path scope, ≤2-file cap, mechanical acceptance,
zero Sierra, no restarts, lane check, risk=low) as a pure function taking a
mesh card's title+body+parents and returning admit/reject+reason. No file
writes, no kanban writes — just the judgment function plus a small fixture
set built from t_700d9953 and t_022c4286 (should admit) and a Sierra-touching
or multi-file card (should reject). Unit-testable in isolation.
Parents: Card 1 (landing-path ruling not required to START this, only to ship it)
Born status: ready (worker card — pure logic, no external dependency to start)
```

**Card 4 — Worker: render job files from admitted cards**
```
Title: DevBot job-gen: render db-NNNN draft job files from admitted mesh cards
Body: Given Card 3's admit output for a mesh card, render a job file matching
the existing frontmatter shape (see db-0008/db-0012/db-0013 as reference
examples) with status: draft, source: mesh:<card_id>, fence per lane
ownership table, and acceptance criteria lifted from the card's own
done-condition language. Reuse the next-id minting pattern from
scripts/next_inbox.py (scans local files + remote branches to avoid
collision) rather than inventing a new id scheme. Cap output at 5 files/run.
Parents: Card 3
Born status: blocked (needs Card 3's filter function to exist first)
```

**Card 5 — Worker: batch landing + HUMAN review card emission**
```
Title: DevBot job-gen: land draft batch + emit one HUMAN review card per run
Body: Take Card 4's rendered files and land them per Card 1's ruling (PR on
claude/* by default until ruled otherwise). Then create exactly one mesh
HUMAN card, born blocked, titled "HUMAN gate: review N draft DevBot jobs
(db-NNNN..db-NNNN)" linking the PR/commit and listing each draft's one-line
acceptance summary. Zero drafts this run = zero card, no PR, silent no-op —
do not open an empty PR or spam an empty review card.
Parents: Card 1, Card 4
Born status: blocked (needs Card 1's ruling + Card 4's renderer)
```

**Card 6 — Worker: wire weekly trigger onto existing triage rhythm**
```
Title: DevBot job-gen: schedule weekly run against t_ca406f9d's triage cadence
Body: Do not invent a new cron/schedule. t_ca406f9d already defines the mesh
board's weekly human-promote triage rhythm — attach this pipeline's run
(Cards 3-5 chained) to that same cadence so Ryan sees generated drafts in
the same weekly pass he's already doing, not a second unrelated ping.
Confirm t_ca406f9d's actual mechanism (cron? manual? T1000 timer?) before
wiring — do not assume, read the card and its linked artifacts first.
Parents: Card 5
Born status: blocked (needs Card 5 working end-to-end before scheduling it unattended)
```

## Open questions

1. **Where do generated drafts land — PR on `claude/*`, or direct commit under an extended coordination-only exception?** `jobs/*.md` isn't currently listed in CLAUDE.md's direct-to-main exception (`inbox-for-*/`, `outbox-from-*/`, `digests/`, ledger appends), and `scripts/pr_efficiency.py classify` would likely call a new file under `docs/agent-coordination/devbot/jobs/` `mixed` or code-adjacent rather than `coordination`. Default to normal PR until Ryan rules otherwise (Card 1 above).

2. **Does a generated `status: draft` job need a distinct lifecycle step (`draft` → `proposed` → `approved`) or is `draft` → `approved` sufficient?** The task brief's template mentions "status MUST be draft or proposed for generated jobs" as two acceptable born-statuses; the existing job files never use `proposed` at all (git history shows only `approved`/`done`). Worth confirming whether `proposed` exists as a distinct signal (e.g., "PM has sanity-checked, awaiting only Ryan's stamp") or whether v1 should just always emit `draft` and let the human review batch be the only intermediate step.

3. **Should the admission filter read `kevin-lab/**` cards at all in v1, or stay scoped to Ryan's lane only?** The ownership table gives `kevin-lab/**` self-merge to Kevin's Claude; a Ryan-side generator proposing jobs that touch Kevin's lane would need his review, not Ryan's, and this spec's single HUMAN-card review surface doesn't currently branch by lane. Simplest v1 answer is likely "filter only admits `fence: ryan`-eligible cards," but that should be an explicit choice, not a default nobody decided.
