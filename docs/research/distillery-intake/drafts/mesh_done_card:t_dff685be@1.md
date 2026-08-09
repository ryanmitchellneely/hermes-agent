# Ensure P2 sustained-failover alert is human-visible

```yaml
id: mesh_done_card:t_dff685be@1
source_kind: mesh_done_card
source_path: t_dff685be
source_ref: t_dff685be@1
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

P2 already writes the sustained-failover alert to alert_path. Residual only: make sure Ryan actually sees it.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
