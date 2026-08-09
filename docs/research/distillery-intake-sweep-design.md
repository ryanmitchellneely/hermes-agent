# Distillery intake sweep — design

**Card:** mesh `t_216ac84b` (parent: `t_8b3c9a73`, Ryan decision recorded 2026-08-08 21:13)
**Scope:** MESH-ONLY, PULL mechanism, artifact-unit connection. This is recon +
design only — no code ships on this card. Implementer card is `t_9c64c42a`; cron
wiring is `t_a7553997`; Ryan arm/review gate is `t_e6fd0cb3`.

## 0. Locked decisions (do not re-litigate)

- Board source list is **mesh-only** for v1. Board expansion later is a config
  change (add a slug to `boards:`), never a schema change.
- Mechanism is **PULL** (a sweep reads systems of record on a cadence), not
  per-actor discipline (no "every agent must log a row" rule).
- Unit of connection is the durable **artifact** — a spec, signal, decision,
  lesson, or shipped fix — not every touch/edit/commit.
- No K2 product Distillery rebuild. No `PATTERN-LEDGER`/k2-hub intake logic
  ported. The K2 file below is cited for its **shape** (promote → idempotent →
  heartbeat → quiet-unless-actionable), never imported or wired.
- P0–P3 native ports (reconciler, refuse-to-serve, failover policy,
  `wrap_untrusted`) are already shipped — see
  `~/.t1000/skills/software-development/t1000-hermes-ops/references/distillery-native-ports.md`.
  This design is unrelated to that STOP list; don't conflate the two.

## 1. Systems of record (v1, mesh-only)

| # | Source | What "new" means | Freshness fingerprint |
|---|--------|-------------------|------------------------|
| 1 | `~/.hermes/plans/*.md` | file not yet drafted, or content changed since last draft | sha256 of file bytes |
| 2 | `~/Documents/T1000/docs/research/signal-log/entries/SIG-*.md` | new entry file, or content changed | sha256 of file bytes |
| 3 | mesh kanban DB (`~/.t1000/kanban/boards/mesh/kanban.db`), `tasks` table | `status='done' AND completed_at > last_checkpoint` | `(task_id, completion_generation)` — already monotonic, no hash needed |
| 4 | skill `references/` trees (v1: `local-inference-fleet` only, config-listed) | new or changed file under a configured `references/` dir | sha256 of file bytes |

Verified live paths (2026-08-08 22:xx):
- `~/.hermes/plans/` — 9 files, newest `2026-08-08_214100-mesh-efficiency-pack.md`
- `signal-log/entries/` — 11 `SIG-*.md` files
- `mesh` `kanban.db` `tasks.completed_at` is an epoch int; `completion_generation`
  increments on every successful completion including manual no-run completions
  (confirmed via `.schema tasks`) — this is the right re-completion signal, not
  `completed_at` alone, since a card can be reopened and re-`done`.
- `local-inference-fleet` skill ships `references/*.md` under
  `~/.t1000/profiles/worker/skills/software-development/local-inference-fleet/references/`
  (24 files as of this sweep) — no repo-tracked mirror exists today, so the
  fingerprint source is the live profile skill tree, not a repo path.

Content-hash fingerprints (not mtime) are deliberate: `git checkout`/clone
resets mtimes without changing content, which would otherwise flood the sweep
with false "new artifact" drafts on every fresh checkout.

## 2. What counts as durable artifact vs noise

| Source | Include | Exclude |
|--------|---------|---------|
| Plans | every file (a plan existing at all is a decision record) | none in v1 |
| Signal-log entries | `posture` ∈ {steal, spike, adopt} always; `posture: watch` included (still citation-worthy) | `posture` ∈ {ignore}; `bucket: noise` |
| Mesh done cards | every `status='done'` card by default | cards whose title matches a configured exclude-pattern, e.g. `^HUMAN review: PR #` (the `pr-kanban-sync` review-tracking wrapper cards — those are process bookkeeping, not artifacts) |
| Skill references | every changed file under a configured `references/` dir | none in v1 |

This table is config-driven (`filters:` block, §5), not hardcoded — a filter is
a false-negative risk (silently dropping something real) worse than a false
positive (one extra draft row a human skips in two seconds), so v1 defaults
toward inclusion and only excludes patterns with a demonstrated reason (the
PR-sync wrapper cards, ~40+ of which would otherwise flood every sweep run).

## 3. Draft intake row schema

One JSON object per row, keyed by a stable `id`. Markdown rendering (§4) is a
view over this data, not a second source of truth.

```yaml
id: <source_kind>:<idempotency_key>       # stable, see below
source_kind: plan | signal_log_entry | mesh_done_card | skill_reference
source_path: str          # file path (repo-relative or ~-relative) OR mesh task id
source_ref: str           # sha256[:16] for files; "task_id@completion_generation" for kanban rows
title: str                # derived: first H1/H2 for md files, task title for kanban rows
captured_at: str           # ISO8601 UTC, when the sweep first saw this fingerprint
status: draft | filed | skipped | stale | superseded
status_changed_at: str     # ISO8601 UTC
summary: str | null        # short auto-excerpt (first non-heading paragraph / card body head); human may overwrite
board: str | null          # "mesh" for kanban-sourced rows; null for file-sourced rows (reserved for multi-board v2)
superseded_by: str | null  # id of the newer draft row, set only when status=superseded
notes: str                 # human-editable freeform; sweep only appends, never overwrites
```

**Idempotency key:**
- File sources (`plan`, `signal_log_entry`, `skill_reference`):
  `sha256(f"{source_kind}:{relpath}:{content_sha256}")[:16]`. Re-running the
  sweep against an unchanged file recomputes the same key and is a no-op.
- `mesh_done_card`: `f"{task_id}@{completion_generation}"`. A card marked
  `done`, reopened, and re-`done`d produces a new key — the old draft row is
  transitioned to `superseded` (§3 status lifecycle) rather than silently
  overwritten, so the review trail shows both completions.

**Status lifecycle:**

```
        (sweep finds new fingerprint)
                    │
                    ▼
                  draft ──(human files it)──────────► filed
                    │
                    ├──(human reviews, decides noise)─► skipped
                    │
                    ├──(age > staleness_days, still draft)─► stale
                    │        (stale rows keep aging in place;
                    │         a human action still moves them
                    │         to filed/skipped)
                    │
                    └──(source fingerprint changes again)─► superseded
                             (new row created with status=draft,
                              old row's superseded_by = new id)
```

`filed` and `skipped` are terminal for that fingerprint — the sweep never
re-drafts a row it has already seen with the same `source_ref`. Only a fresh
fingerprint (content actually changed, or a card re-completed) creates a new
row.

## 4. Where drafts live

**Decision: repo-tracked markdown + JSON index, under
`~/Documents/T1000/docs/research/distillery-intake/`** — not
`~/.t1000/state/`.

```
docs/research/distillery-intake/
├── config.yaml          # sources, boards, filters, staleness_days (§5)
├── index.json           # machine-readable: array of the row schema in §3, one file, sweep-owned
└── drafts/
    └── <id>.md           # human-readable rendering of one row, regenerated from index.json on every sweep run
```

**Rationale (repo path over `~/.t1000/state/`):**
1. **Parity with the pattern it extends.** Signal-log — the closest existing
   analog, and the thing this design doc itself gets filed under
   (`docs/research/`) — already lives in the repo, not in `~/.t1000/`. A second
   "review queue" living in a different tree is an unforced inconsistency.
2. **Git history is a free audit trail.** When a draft flips to `filed` or
   `stale`, the diff shows exactly when and (via commit) by what session.
   `~/.t1000/state/` is not git-tracked and has no such trail.
3. **Discoverability matches Ryan's actual daily scan surface.** The daily
   build-hygiene sweep (`~/.t1000/scripts/t1000_build_hygiene_sweep.py`)
   already flags *uncommitted repo dirt* every weekday — a repo-path queue
   rides that existing attention channel for free. `~/.t1000/state/` has no
   equivalent "someone will look at this" mechanism; it's where ops/cache
   ephemera goes precisely because nobody scans it.
4. **`~/.t1000/config.yaml` writes are refused by agent tools** (security-
   sensitive; confirmed pitfall in `t1000-hermes-ops`). Keeping this feature's
   config as its own repo-tracked YAML avoids that friction entirely — no
   `hermes config set` ceremony, no risk of the config living somewhere an
   agent can silently fail to edit.

`index.json` is the sweep's own bookkeeping (idempotency ledger + status) so
re-runs don't need to re-parse 40+ markdown files. `drafts/*.md` exist purely
for human review — one file per row, regenerated (not hand-edited past the
`notes:` field, which the sweep round-trips) each run.

## 5. Config surface

`docs/research/distillery-intake/config.yaml` (repo-tracked, not
`~/.t1000/config.yaml`):

```yaml
# Board source list — mesh-only today. Adding a board here is the *entire*
# mechanism for scope expansion; nothing else in the sweep changes.
boards:
  - mesh

sources:
  plans:
    enabled: true
    path: "~/.hermes/plans"
  signal_log:
    enabled: true
    path: "docs/research/signal-log/entries"
  mesh_done_cards:
    enabled: true
    # boards: inherits top-level `boards:` list above
    title_exclude_patterns:
      - "^HUMAN review: PR #"     # pr-kanban-sync wrapper cards — process, not artifact
  skill_references:
    enabled: true
    trees:
      - "~/.t1000/profiles/worker/skills/software-development/local-inference-fleet/references"
      # additional references/ trees are added here, not hardcoded in the script

filters:
  signal_log:
    exclude_posture: [ignore]
    exclude_bucket: [noise]

staleness_days: 5
```

Nothing in the sweep script hardcodes `mesh`, a repo path, or a skill name —
every one of those is a value read from this file. Multi-board v2 is "add a
slug to `boards:` and, if the board lives on a different Mac/host, point
`mesh_done_cards` at the right `kanban.db` path" — no redesign.

## 6. Staleness rule

- `staleness_days` (config, default 5) measured from `captured_at`.
- On every run, the sweep re-evaluates every `status: draft` row: if
  `now - captured_at > staleness_days`, flip `status: stale`. This is a status
  transition, not a separate check — the same sweep tick that drafts new rows
  also ages old ones, so there is exactly one code path to keep correct.
- **The check must run itself.** Per Ryan's framing on the parent card ("the
  check must be automatic or the rule will silently rot"), staleness detection
  is not a thing a human periodically remembers to look for — it's a
  side-effect of the cron tick existing at all (§7). If the cron stops firing,
  that failure is caught by normal cron/heartbeat monitoring (existing
  `t1000_ops_alert_pulse.py` pattern), not by a separate watchdog for this
  feature.
- `stale` rows are reported louder than plain `draft` rows in the cron's
  Telegram summary (§7) — they're the signal that review is actually falling
  behind, not just that new material exists.

## 7. CLI / cron shape

Mirrors `~/.t1000/scripts/t1000_build_hygiene_sweep.py` exactly: no-agent,
silent-if-nothing-changed, dual-write SoT (home script + repo copy), report
only.

```
Script:   ~/.t1000/scripts/distillery_intake_sweep.py
          (+ repo copy ~/Documents/T1000/scripts/distillery_intake_sweep.py)
Dedup:    ~/.t1000/cache/distillery-intake-sweep-state.json
          (fingerprint of last-reported {new_count, stale_count} — only
          re-notify on change, same pattern as the hygiene sweep and the
          ops-alert-pulse dedup state)
Cadence:  proposed every 6h (matches the K2 reference cron's period; distillery
          intake is not urgent enough for the 2h pr-kanban-sync cadence)
Cron:     --no-agent, deliver telegram:7869946421, silent if nothing new/stale
Heartbeat: none required — this is a `--no-agent` script cron, not a dispatched
          kanban worker, so `kanban_heartbeat` doesn't apply. Liveness is
          covered by normal cron last-run monitoring (`hermes cron list --all`,
          already part of the standing audit recipe).
```

Behavior:
1. Load `config.yaml` + `index.json`.
2. For each enabled source, enumerate current fingerprints; diff against
   `index.json`. New/changed fingerprints → new `draft` rows (old row, if any,
   → `superseded`).
3. Re-evaluate all `draft` rows for staleness (§6).
4. Write updated `index.json` + regenerate `drafts/*.md` for any row that
   changed status this run.
5. If `new_count == 0 and newly_stale_count == 0` since the last reported
   state: print nothing (silent tick).
6. Otherwise: print a short report (counts + up to N titles per source) —
   this is what the no-agent cron delivers verbatim to Telegram, same
   contract as the hygiene sweep.
7. **Never** auto-transitions `draft` → `filed`/`skipped` — those are human
   calls, made by editing `notes:`/`status:` directly or (v2) via a small
   `hermes`-adjacent CLI verb. This card does not specify that verb; it's
   in scope for `t_9c64c42a`.

## 8. Relationship to related cards

- **`t_048f0c5c`** (manual intake tranche, 6 candidate rows in comments,
  currently `blocked` on Ryan promote) is the **content model**, not a
  dependency. Its rows are hand-curated examples of exactly the shape this
  sweep should produce automatically going forward. The sweep does not read
  from or write to `t_048f0c5c` — it's a separate, human-curated card that
  stays blocked until Ryan acts on it independently. Going forward, tranches
  like it are what the sweep drafts *for* Ryan instead of someone reconstructing
  them by hand each time.
- **`~/.claude/skills/kanban-checkin`** (the "when finishing work, log it"
  wrap-up ritual): the implement/wire cards (`t_9c64c42a`, `t_a7553997`) should
  add one line to that skill's reconciliation section pointing at
  `docs/research/distillery-intake/drafts/` (rows with `status: draft` or
  `stale`) as an additional input during session wrap-up — a human-facing
  nudge, not automation. Not done on this card (design only).
- **K2 `distillery_intake_cron.py`** (`kevin-real-estate-tools/k2-hub/src/k2_hub/handlers/distillery_intake_cron.py`,
  read-only pattern citation): its shape — promote-not-decide, one shared
  capture path, quiet-unless-actionable, bounded by the data itself rather
  than a throttle — is echoed in §6/§7 above (age-bound staleness instead of a
  rate throttle; silent-unless-new-or-stale instead of every-tick chatter). No
  code, table name, or import crosses from that file into this design.

## 9. Out of scope (this design and its implementer cards)

- K2 product Distillery rebuild, `PATTERN-LEDGER`, or `k2-hub` intake logic.
- Any Buzz wiring or K2-hub imports.
- Multi-board support beyond the `boards:` config list existing (no second
  board is wired in v1).
- Auto-filing drafts into `t_048f0c5c`, any K2 cut-book, or Kevin-facing
  surfaces — filing is always a human action.
- A CLI verb for humans to flip `draft → filed/skipped` (implementer's call
  whether that's a `hermes`-adjacent script flag or direct file edit).
- Multi-Mac / VPS kanban DB paths (mesh today runs on this Mac only).

## 10. Acceptance check (self-review against the card's list)

- [x] Draft row schema with fields, enums, idempotency key, status lifecycle — §3
- [x] Storage location decided with rationale (repo path, not `~/.t1000/state/`) — §4
- [x] Durable-artifact-vs-noise filters — §2
- [x] Staleness rule + self-running observability — §6
- [x] Config surface separating source/board list from schema — §5
- [x] CLI/cron shape mirroring `t1000_build_hygiene_sweep.py` — §7
- [x] Relationship to `t_048f0c5c` and `kanban-checkin` — §8
- [x] Out-of-scope list — §9
- [x] Live paths verified (not assumed) — §1
