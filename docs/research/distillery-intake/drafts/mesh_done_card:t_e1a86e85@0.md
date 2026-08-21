# MESH-TEL-2: instrument model + provider + effort + tokens at the call boundary

```yaml
id: mesh_done_card:t_e1a86e85@0
source_kind: mesh_done_card
source_path: t_e1a86e85
source_ref: t_e1a86e85@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

THE GAP THAT MAKES RYAN'S QUESTION UNANSWERABLE. VERIFIED 2026-08-08 against ~/.t1000/kanban/boards/mesh/kanban.db (schema) — Ryan's ask: 'how many model calls, what effort, what success rate, how much deepseek vs 120b, how many tokens.' Today that question is NOT answerable. task_runs columns are: id, task_id, profile, step_key, status, claim_lock, claim_expires, worker_pid, worker_birth_id, max_runtime_seconds, last_heartbeat_at, started_at, ended_at, outcome, summary, metadata, error, recovery_status, start_* — NO model column, NO provider column, NO token columns. Model/effort exist ONLY as task_events rows (model_override_set n=35, reasoning_effort_set n=30) and only when EXPLICITLY OVERRIDDEN, against claimed n=117 — so roughly 70% of runs have no recorded model at all. Token counts exist nowhere. And a run is not a call: one run makes many model calls, so run counts are a floor, not a call count.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
