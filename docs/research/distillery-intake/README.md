# Distillery intake — review queue

Pull-based intake sweep. It reads the systems of record where durable
artifacts actually land, fingerprints each one, and drafts a review row.
**Drafts are for a human to file** — the sweep never writes into K2 Distillery,
`PATTERN-LEDGER`, or Buzz, and never auto-files anything.

- **Design:** `../distillery-intake-sweep-design.md` (mesh card `t_216ac84b`)
- **Script:** `scripts/distillery_intake_sweep.py` (repo SoT)
  · dual-written to `~/.t1000/scripts/distillery_intake_sweep.py` for cron
- **Tests:** `tests/scripts/test_distillery_intake_sweep.py`

## Layout

```
docs/research/distillery-intake/
├── config.yaml      # sources, boards, filters, staleness_days — the whole scope surface
├── index.json       # sweep-owned ledger (idempotency + status). Do not hand-edit.
└── drafts/<id>.md   # one file per row — this is what you review
```

## Run it

```bash
cd ~/Documents/T1000

# What would it draft? (writes nothing)
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run

# Real tick — silent when nothing is new or newly stale (cron contract)
./venv/bin/python scripts/distillery_intake_sweep.py

# Machine-readable
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --json

# Debug one source at a time
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --source plan
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --source signal_log_entry
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --source mesh_done_card
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --source skill_reference

# Only artifacts touched recently
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --since 1d
./venv/bin/python scripts/distillery_intake_sweep.py --dry-run --since 2026-08-01
```

The `~/.t1000/` copy needs explicit paths (it refuses to guess, so it can't
seed a second store against the wrong tree):

```bash
~/Documents/T1000/venv/bin/python ~/.t1000/scripts/distillery_intake_sweep.py \
  --repo-root ~/Documents/T1000 \
  --intake-dir ~/Documents/T1000/docs/research/distillery-intake
```

## Reviewing a draft

Open `drafts/<id>.md`, then either:

```bash
# flip the verdict from the CLI
./venv/bin/python scripts/distillery_intake_sweep.py --mark plan:cbcceb5dbe851aca=filed
./venv/bin/python scripts/distillery_intake_sweep.py --mark mesh_done_card:t_abc@1=skipped
```

…or edit the draft file directly: change `status:` to `filed`/`skipped` and
write anything you like under `## notes`. The next sweep reads both back into
`index.json`. `filed` and `skipped` are terminal — that fingerprint is never
re-drafted.

## What it sweeps

| Source | Where | New means |
|--------|-------|-----------|
| `plan` | `~/.hermes/plans/*.md` | file unseen, or content changed |
| `signal_log_entry` | `docs/research/signal-log/entries/SIG-*.md` | ditto, minus `posture: ignore` / `bucket: noise` |
| `mesh_done_card` | `~/.t1000/kanban/boards/mesh/kanban.db` | card `done` at a `completion_generation` not yet seen |
| `skill_reference` | configured `references/` trees (v1: `local-inference-fleet`) | file unseen, or content changed |

Fingerprints are **content hashes, not mtimes** — a fresh `git clone` resets
mtimes and would otherwise re-draft everything.

## Scope expansion

Adding a board is a config edit and nothing else:

```yaml
boards:
  - mesh
  - k2      # <- that is the entire change
```

Same for a new skill `references/` tree (`sources.skill_references.trees`).
No script edit, no schema change.

## Staleness

Any row still `draft` more than `staleness_days` (default 5) after
`captured_at` flips to `stale` on the next tick, and stale rows are reported
louder than new ones. The check is a side effect of the sweep running at all —
there is no separate watchdog to remember.

**First-run note:** the initial sweep backfilled 141 rows (8 plans, 11 signal
entries, 99 mesh done cards, 23 skill references). Left untouched, all of them
flip to `stale` five days later in one batch. Either bulk-triage the backlog
(`--mark … =skipped` on what is genuinely history) or expect one loud stale
report the first time the threshold passes.

## Not in scope

No K2 Distillery rebuild, no `PATTERN-LEDGER`/`k2-hub` imports, no Buzz wiring,
no auto-filing to any Kevin-facing surface. Filing is always a human action.
