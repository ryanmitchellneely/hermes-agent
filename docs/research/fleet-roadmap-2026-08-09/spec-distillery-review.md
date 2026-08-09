# SPEC

## Distillery Review Agent (v1)

The missing half of the T1000 Distillery intake pipeline. The sweep
(`~/.t1000/scripts/distillery_intake_sweep.py`) pulls durable artifacts into
draft rows automatically. Nothing pre-judges them or batches them for Ryan —
he faces 161 raw rows one file at a time. This spec adds the review layer:
cluster, pre-judge file/skip/supersede with one-line rationales, surface
small decision batches, apply only what Ryan approves.

## Problem + evidence

- **The queue is real and growing, and nothing is filed.** As of this read
  (`docs/research/distillery-intake/index.json`, `generated_at:
  2026-08-09T13:11:15Z`), there are **161 rows, all `status: draft`** — zero
  `filed`, zero `skipped`. Breakdown: 119 `mesh_done_card`, 23
  `skill_reference`, 11 `signal_log_entry`, 8 `plan`. Git history shows this
  arrived in two waves: `e5834a8e7` (141-row backfill baseline) then
  `4a6428a6e` ("15 new drafts from 2026-08-09 morning cards").
- **The sweep is fully live and already flagged this exact failure mode
  itself.** The intake `README.md` warns: *"Left untouched, all of them flip
  to `stale` five days later in one batch. Either bulk-triage the backlog
  (`--mark …=skipped` on what is genuinely history) or expect one loud stale
  report the first time the threshold passes."* `staleness_days: 5`
  (`config.yaml`) measured from `captured_at`; most of the backlog has
  `captured_at: 2026-08-09T03:15:16Z` (3 distinct backfill timestamps total,
  all 2026-08-09), so the mass flip to `stale` lands **~2026-08-14T03:15Z** —
  five days from now.
- **The sweep cron is armed and will not slow down.** `hermes cron list --all`
  shows "Distillery intake sweep (silent-when-clean)" running every 360m,
  delivering to `telegram:7869946421`, last run `2026-08-09T08:11:16-05:00
  ok`. Every 6h it can add more rows on top of the 161 already unreviewed.
- **The design doc explicitly punted this exact job.** §7 point 7 of
  `distillery-intake-sweep-design.md`: *"Never auto-transitions `draft` →
  `filed`/`skipped` — those are human calls... This card does not specify
  that verb."* The implementer card (`t_9c64c42a`, done) built `--mark
  ID=filed|skipped` — a mechanism, not a workflow. Nothing clusters,
  nothing recommends, nothing batches.
- **Manual clustering doesn't scale.** Mesh card `t_048f0c5c` — the
  hand-curated content model for what a *good* filed tranche looks like (5
  candidate rows, grouped by theme, one-line rationale each) — has sat
  `blocked` since 2026-08-07 waiting on Ryan to hand-triage it. Two days,
  zero rows filed. Hand-curation is real work that competes with everything
  else Ryan does; it will not clear 161 rows.
- **The wrap-up ritual already assumes a decider exists — it doesn't yet.**
  `~/.claude/skills/kanban-checkin/SKILL.md` (already patched, step 7) tells
  every session to check the draft queue and "decide, not re-discover," but
  today that dumps the burden on whichever agent happens to run
  `kanban-checkin` next, ad hoc, with no clustering or batching. This spec is
  what step 7 is actually pointing at.

## V1 scope

- **One review pass per day** (no-agent script cron, not a dispatched
  agent — see Design sketch): read `index.json` rows with `status` in
  `{draft, stale}`.
- **Cluster + judge via the house-pinned local LLM.** Send
  title/summary/source_kind/source_path/notes for the day's candidate rows to
  `gpt-oss:120b` on Ryan Spark (`127.0.0.1:11435/v1/chat/completions`,
  OpenAI-compatible — same call shape already used in
  `~/.t1000/scripts/ds4_baseline_bench.py`). Ask for: (a) cluster groupings
  of related rows, (b) a verdict per row — `file`, `skip`, or
  `supersede` (flag as a likely duplicate of another row in the batch) —
  (c) a one-line rationale per verdict.
- **Batch cap of 8 decisions**, matching the sweep's own
  `format_report(max_per_section=8)` convention and Ryan's stated review
  capacity. Priority order: `stale` rows first (oldest `captured_at` first),
  then `draft` rows oldest-first.
- **Render a reviewable batch file**, one per day:
  `docs/research/distillery-intake/reviews/<YYYY-MM-DD>.md`. Same
  human-edit-round-trip idiom the sweep already uses for `drafts/<id>.md`
  (`status:` field / `## notes`): here it's a `decision:` field per row,
  default blank, Ryan edits to `approve` to accept the proposed verdict.
  Blank (or anything else) means defer — untouched, resurfaced in a later
  batch.
- **Delivery: Telegram, same channel the sweep already uses**
  (`telegram:7869946421`). Surface-file-written-before-send, exactly the
  `kevin_digest.py` pattern (`SURFACE.write_text(body)` before delivery) —
  message body is the cluster summary + counts + pointer to the day's
  `reviews/<date>.md`; full rationale detail lives in the file, not the
  Telegram message.
- **Apply step reuses the sweep's own write path — no new writer.**
  `distillery_review_agent.py --apply <date>` reads back `decision: approve`
  rows from that day's review file and calls
  `distillery_intake_sweep.py --mark id=filed` (verdict `file`) or
  `--mark id=skipped` (verdict `skip`, or `supersede` — see Gates & risks
  for why `supersede` maps to `skipped`+notes, not a new status). This is
  the *only* thing that ever flips a row's status; the review agent itself
  never touches `index.json` directly.
- **`file` also appends one line to a new `FILED-LOG.md`** (repo-tracked,
  `docs/research/distillery-intake/FILED-LOG.md`) — row id, title, and a
  short "where this should land" pointer drawn from the LLM's own rationale
  (e.g. "→ router-policies KB page" or "→ already covered, no new doc
  needed"). This satisfies the agreed v1 definition of filing
  (status flip + pointer); it does not write the KB page/skill update itself.
- **Cron registered PAUSED**, armed only after a human gate reviews a live
  dry-run against the real backlog — same ceremony `t_e6fd0cb3` already used
  for the sweep itself ("agents must not self-GREEN").

## Non-goals

- **No auto-filing without approval.** Every status flip traces back to an
  explicit `decision: approve` a human wrote into a review file. No
  confidence threshold auto-applies anything in v1.
- **No deeper filing.** `FILED-LOG.md` is a pointer, not the artifact. Writing
  the actual KB page, updating a skill's `references/`, or editing
  `PATTERN-LEDGER` is out of scope — a human or a future agent does that
  follow-through by hand, starting from the pointer.
- **No new Telegram command parsing / bot reply handling.** Decisions
  round-trip through the `reviews/<date>.md` file, exactly like the sweep's
  existing `drafts/<id>.md` idiom. Building a second channel (2-way Telegram,
  a mesh HUMAN card, a Slack-style reply parser) is explicitly deferred —
  see Open questions.
- **No new model, no second Spark tenant.** Judge calls hit the
  already-pinned `gpt-oss:120b` only. Never load a different model on Ryan
  Spark; every request sets `keep_alive` ≤30m (house rule — see
  `KEEP_ALIVE=-1`-pins-forever landmine already logged from the dual-box
  residency work).
- **No schema change to the sweep.** `superseded` remains sweep-owned
  (fingerprint-triggered only); the review agent's `--mark` calls are
  restricted to the same `filed`/`skipped` pair the CLI already accepts
  (`STATUS_TERMINAL = ("filed", "skipped")` in
  `distillery_intake_sweep.py`). No new sweep code ships as part of this
  spec.
- **No commitment to beat the 2026-08-14 staleness flip.** At 8
  decisions/day, 161 rows takes ~20 days — it will not clear before most
  rows flip to `stale` on 2026-08-14. That flip is explicitly *not* treated
  as a failure: per the sweep's own design (§6), `stale` rows "keep aging in
  place; a human action still moves them to filed/skipped" — it's a louder
  label, not a lost row. Review continues unaffected after the flip.
- **No board expansion, no K2 Distillery/PATTERN-LEDGER/Buzz writes.**
  Inherits the sweep's own boundaries verbatim (mesh-only, T1000-local,
  never K2-facing).

## Design sketch

```
daily cron (no-agent script, e.g. 09:00 CT)
        │
        ▼
distillery_review_agent.py
        │  1. load index.json, filter status ∈ {draft, stale}
        │  2. skip rows already in an open (undecided) prior batch
        │     (~/.t1000/cache/distillery-review-pending.json)
        │  3. select next ≤8: stale-oldest-first, then draft-oldest-first
        │  4. POST 127.0.0.1:11435/v1/chat/completions (gpt-oss:120b,
        │     keep_alive ≤30m) — rows' title/summary/source_kind/path/notes
        │     → clusters + verdict(file|skip|supersede) + 1-line rationale
        │  5. write docs/research/distillery-intake/reviews/<date>.md
        │     (SURFACE.write_text pattern — file before send)
        │  6. deliver Telegram summary → telegram:7869946421
        │     (silent if no candidate rows this run — matches sweep contract)
        ▼
Ryan reads reviews/<date>.md, edits `decision: approve` per row he accepts
        │
        ▼
distillery_review_agent.py --apply <date>  (next day's run, or on demand)
        │  for each decision: approve row:
        │    verdict file      → sweep --mark id=filed   + append FILED-LOG.md
        │    verdict skip      → sweep --mark id=skipped
        │    verdict supersede → sweep --mark id=skipped + notes: "dup of <id>"
        ▼
index.json updated via the sweep's own --mark path (no new writer)
```

Row schema for `reviews/<date>.md` (per row, inside a cluster group):

```yaml
id: <row id from index.json>
cluster: <short cluster label the LLM assigned>
verdict: file | skip | supersede
rationale: <one line>
supersede_of: <row id>   # only present when verdict=supersede
decision:                 # human-edited, blank = defer
```

Dual-write matches house convention: canonical script in
`~/Documents/T1000/scripts/distillery_review_agent.py`, cron-invoked copy at
`~/.t1000/scripts/distillery_review_agent.py` — same split the sweep itself
uses, for the same reason (`~/.t1000/config.yaml` writes are refused by agent
tools; keeping this feature's state in the repo-tracked tree avoids that
friction).

## Gates & risks

- **LLM misjudgment is not a write risk, only a review-quality risk** —
  every verdict is a recommendation behind a mandatory `decision: approve`
  gate; nothing applies without it. Worst case is a bad rationale Ryan skims
  past and defers, not a bad file/skip landing silently.
- **`keep_alive` / second-tenant risk on Ryan Spark.** Every judge call must
  set `keep_alive` ≤30m and must never load any model other than the
  already-pinned `gpt-oss:120b` — violating either directly repeats the
  `KEEP_ALIVE=-1` un-TTL'd-load-pins-forever landmine already hit once on
  this box.
- **`supersede` has no real home in the existing schema.** `--mark` only
  accepts `filed`/`skipped` (`STATUS_TERMINAL` in the sweep script);
  `superseded` is set exclusively by the sweep's own fingerprint-change
  logic. v1's workaround — `supersede` verdict → `--mark id=skipped` +
  a `notes:` line citing the row it duplicates — is a real compromise, not
  a clean mapping. Flagged in Open questions.
- **Race with the sweep's own 6h cron.** New drafts can land mid-review-cycle.
  Mitigation: the apply step only ever acts on rows explicitly listed in a
  given day's `reviews/<date>.md` snapshot — never "whatever `index.json`
  currently says" — so a same-day new arrival can't get swept into a batch
  it wasn't judged in.
- **161-row backlog vs. the 2026-08-14 staleness flip.** Explicitly not a
  gate to "beat" (see Non-goals) — but Acceptance criteria requires the dry
  run be proven against the *real, current* backlog before arming, so the
  size of the problem is visible to Ryan at arm-decision time, not
  discovered later.
- **New repo-committed surfaces (`reviews/*.md`, `FILED-LOG.md`) must
  actually get committed**, not left dirty — same audit-trail rationale the
  design doc already gives for putting the whole intake store in the repo
  (§4: git history as free audit trail). A review batch that's judged but
  never committed is functionally invisible to any other agent or session.
- **Silent cron failure is itself a gap.** This is a new cron; it must
  register with the same `hermes cron list --all` / last-run monitoring the
  sweep and hygiene sweep already use, so a broken judge call (e.g. Spark
  down) shows up as a stale "last run" rather than nothing happening and no
  one noticing.

## Acceptance criteria

- [ ] `distillery_review_agent.py` exists (repo canonical +
      `~/.t1000/scripts/` dual-write copy); `--dry-run` writes nothing and
      prints the proposed batch to stdout.
- [ ] Run against the real, current backlog (161 rows as of this spec):
      dry run produces ≥1 batch of ≤8 rows, grouped into clusters, each row
      carrying a verdict (`file`/`skip`/`supersede`) and a one-line
      rationale, sourced only from `gpt-oss:120b` at
      `127.0.0.1:11435/v1/chat/completions` with `keep_alive` ≤30m verified
      in the request payload, and no other model touched on Ryan Spark.
- [ ] `docs/research/distillery-intake/reviews/<date>.md` is written with a
      human-editable `decision:` field per row and round-trips on the next
      run exactly like the sweep's existing `status:`/`## notes` idiom.
- [ ] `--apply` only changes status for rows with `decision: approve`,
      verified live: mark one real row `approve`, run `--apply`, confirm
      its `index.json` status is now `filed` or `skipped` via the sweep's
      own `--mark`, and (for a `file` verdict) one new line lands in
      `FILED-LOG.md`.
- [ ] A row left with `decision:` blank is provably untouched after
      `--apply` and reappears as a candidate in the next day's batch.
- [ ] Cron registered no-agent, silent when there are no candidate rows,
      delivering to `telegram:7869946421`, created **PAUSED**.
- [ ] A live dry-run proof (counts + one full sample cluster) is pasted into
      the arm-gate card before anyone requests Ryan arm the cron — same
      ceremony as `t_e6fd0cb3` ("agents must not self-GREEN").

## Card decomposition

**C1 — HUMAN: Ryan decide — review-agent v1 design choices**
Confirm before code: (1) Telegram-only delivery vs. a mesh HUMAN card
(spec recommends Telegram — matches the sweep's existing channel, avoids a
new per-day card that competes with real work cards); (2) batch size 8/day
and priority order (stale-oldest-first, then draft-oldest-first); (3)
`supersede` → `skipped`+notes workaround is acceptable for v1 (see Gates &
risks); (4) daily cadence, proposed 09:00 CT.
Parents: `t_216ac84b` (the sweep design doc this spec extends).
Born status: **blocked**.

**C2 — Worker: implement `distillery_review_agent.py` cluster+judge pass**
Build the script per Design sketch: load `index.json`, filter/prioritize
draft+stale rows, call `gpt-oss:120b` at `127.0.0.1:11435/v1/chat/completions`
(keep_alive ≤30m, no other model on Spark), render clusters+verdicts+
rationales into `docs/research/distillery-intake/reviews/<date>.md` with a
human-editable `decision:` field. `--dry-run` must write nothing.
Parents: C1.
Born status: **ready**.

**C3 — Worker: implement `--apply` path + `FILED-LOG.md`**
Add `--apply <date>` to `distillery_review_agent.py`: read back
`decision: approve` rows from that day's review file, call
`distillery_intake_sweep.py --mark id=filed|skipped` (map `supersede`→
`skipped`+notes citing the duplicate row id), and append one pointer line
to `docs/research/distillery-intake/FILED-LOG.md` for every `file` verdict
applied. Must never touch `index.json` directly — only via the sweep's own
`--mark`.
Parents: C2.
Born status: **ready**.

**C4 — Worker: wire T1000 cron (disarmed) + live dry-run proof**
Register `distillery_review_agent.py` as a T1000 no-agent cron (daily,
proposed 09:00 CT, deliver `telegram:7869946421`, silent-when-clean),
mirroring `distillery_sweep_cron.sh`'s wrapper shape. Create it **paused**.
Run one real `--dry-run` against the live 161-row backlog and paste the
counts + one full sample cluster (with rationale) into this card's
completion comment as proof, same as the sweep's own `t_a7553997` proof
step.
Parents: C2, C3.
Born status: **ready**.

**C5 — HUMAN: arm gate — review dry-run proof, arm review-agent cron**
Skim C4's dry-run proof (cluster quality, verdict sanity, rationale
usefulness). Decide: arm the cron as-is, arm with a config tweak (batch
size/cadence), or leave paused pending changes. Mirrors `t_e6fd0cb3`'s
close recipe exactly (`GREEN — cron armed` / `GREEN — leave disarmed until
<condition>` / `CHANGES — <one line>`); agents must not self-GREEN.
Parents: C4.
Born status: **blocked**.

**C6 — Worker: one-time backlog bootstrap pass (optional)**
If C1 or C5 opts in: run one oversized first batch (Ryan-specified size,
e.g. 20–30 rows in one review file instead of 8) against the pre-existing
141+15-row backfill specifically, to blunt how much of the queue is still
`draft` when the 2026-08-14 staleness flip hits. Steady-state cadence
reverts to the C1-agreed batch size immediately after. Skip this card
entirely if C1/C5 decide the default 8/day cadence plus the "stale is
cosmetic" framing (Non-goals) is good enough.
Parents: C1.
Born status: **ready**.

## Open questions (max 3)

1. **Delivery channel:** this spec defaults to reusing the sweep's existing
   Telegram target on the grounds that it's the established channel and
   avoids a new per-day mesh card competing with real work — but should
   review batches instead fold into the existing twice-daily `kevin_digest.py`
   surface (one more section, zero new channels) rather than a standalone
   Telegram ping? Trades channel-count for digest-length.
2. **`supersede`'s schema gap:** v1 maps it to `skipped` + a notes
   annotation because `--mark` only accepts `filed`/`skipped` and
   `superseded` is sweep-fingerprint-owned. Is that workaround permanent, or
   should a v2 add a real cross-row `superseded_by`-writing verb to
   `distillery_intake_sweep.py`?
3. **Backlog vs. staleness deadline:** given 161 rows / 8 per day ≈ 20 days
   to clear, and the mass staleness flip lands 2026-08-14 (5 days out) — is
   the "stale is cosmetic, keep cadence at 8/day" stance (Non-goals) actually
   acceptable to Ryan, or does he want the C6 bootstrap pass to run
   unconditionally on day one regardless of dry-run quality?
