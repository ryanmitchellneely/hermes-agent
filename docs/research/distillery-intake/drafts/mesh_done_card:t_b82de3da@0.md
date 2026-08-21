# HUMAN Ryan: Distillery backfill staleness + commit-vs-wipe the 141 draft rows

```yaml
id: mesh_done_card:t_b82de3da@0
source_kind: mesh_done_card
source_path: t_b82de3da
source_ref: t_b82de3da@0
board: mesh
captured_at: 2026-08-09T13:11:15Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Sweep is built+proven (48 tests green, idempotent, 141 draft rows in docs/research/distillery-intake/index.json: 99 mesh_done_card, 23 skill_reference, 11 signal_log, 8 plan). Two Ryan decisions unblock t_9c64c42a and must precede arming the cron (t_e6fd0cb3): (1) commit or wipe the 141 untracked draft files; (2) backfill staleness — all 141 carry 08-09 captured_at, so at staleness_days:5 they ALL flip stale on 08-14 as one noise batch; either backdate captured_at to source mtime or exempt backfill rows from the first sweep (recommend: commit + backdate).

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
