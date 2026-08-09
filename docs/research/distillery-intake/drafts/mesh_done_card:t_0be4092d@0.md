# Flash lab: default Ollama kanban workers to reasoning=none

```yaml
id: mesh_done_card:t_0be4092d@0
source_kind: mesh_done_card
source_path: t_0be4092d
source_ref: t_0be4092d@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

After Flash ctx gate fix: Ollama rejects xhigh. Pin reasoning=none (or medium) when provider is spark/mbp-ollama for kanban workers. Evidence: t_3a7f19db HTTP 400 xhigh. Prefer config default for local providers if available; else document set_reasoning_effort on pin.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
