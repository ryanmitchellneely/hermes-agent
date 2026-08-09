# W0: DevBot scoreboard — populate tok/s (currently None on all rows)

```yaml
id: mesh_done_card:t_cf7fd6cd@0
source_kind: mesh_done_card
source_path: t_cf7fd6cd
source_ref: t_cf7fd6cd@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

FLASH-SCOREBOARD.jsonl records apply_ok + wall only; tok/s is None on every row for every model. Fix: record completion_tokens/wall at write time. Success metric M2 requires 100 percent of new rows populated; W3 dspark and D-test comparisons depend on it. Related: t_d754cc37 (lane migration via standings). Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S12.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
