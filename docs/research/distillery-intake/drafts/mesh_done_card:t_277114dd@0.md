# B P1: Fix kanban-workable + kanban-health skip-bad-board

```yaml
id: mesh_done_card:t_277114dd@0
source_kind: mesh_done_card
source_path: t_277114dd
source_ref: t_277114dd@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

Both CLIs die: `no such table: tasks` on empty/broken board (e.g. .omc). Glance surface dead.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
