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

## Review batches (cluster + judge pass)

Reading 160+ raw draft rows one file at a time doesn't scale. The review
agent pre-judges a small batch per run and lets you accept/defer in bulk.

- **Design:** `../fleet-roadmap-2026-08-09/spec-distillery-review.md` (mesh
  card `t_216ac84b` spec parent; card `t_0d8b422e` = "C2", this script)
- **Script:** `scripts/distillery_review_agent.py` (repo SoT)
  · dual-written to `~/.t1000/scripts/distillery_review_agent.py`
- **Tests:** `tests/scripts/test_distillery_review_agent.py`

```bash
cd ~/Documents/T1000

# Judge the next batch for real (candidates only — never touches index.json)
# but write nothing. Prints the proposed clusters/verdicts/rationales.
./venv/bin/python scripts/distillery_review_agent.py --dry-run

# Real run: writes docs/research/distillery-intake/reviews/<date>.md and
# records the batch's row ids in ~/.t1000/cache/distillery-review-pending.json
# so they aren't re-drafted into tomorrow's batch before you've decided.
./venv/bin/python scripts/distillery_review_agent.py
```

Selects up to 8 rows (`status` in `{draft, stale}`, stale-oldest-first then
draft-oldest-first, skipping anything already sitting in an undecided prior
batch), sends title/summary/source_kind/source_path/notes to the
house-pinned local judge (`gpt-oss:120b` on Ryan Spark, `keep_alive` ≤30m,
no other model touched — see the script's module docstring for why it hits
Ollama's native `/api/chat` rather than the `/v1/chat/completions` path the
spec names), and renders one `reviews/<date>.md` file with a
human-editable `decision:` field per row — same round-trip idiom as
`status:` above. Edit `decision: approve` to accept a row's proposed
verdict (`file`/`skip`/`supersede`); leave it blank to defer.

**v1 scope note (card C2 only):** this script never writes `index.json` —
applying `decision: approve` rows (`--apply`, `distillery_intake_sweep.py
--mark`, `FILED-LOG.md`) and cron wiring are separate follow-on cards (C3,
C4) and are not implemented yet. Running the commands above is safe against
the real backlog: `--dry-run` writes nothing at all, and a real run only
ever writes a new `reviews/<date>.md` plus the pending-cache — it cannot
flip any row's status.

## Not in scope

No K2 Distillery rebuild, no `PATTERN-LEDGER`/`k2-hub` imports, no Buzz wiring,
no auto-filing to any Kevin-facing surface. Filing is always a human action.
