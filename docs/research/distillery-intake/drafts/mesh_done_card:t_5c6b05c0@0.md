# DevBot preflight: fail closed if CODE_URL/tunnel down mid-job

```yaml
id: mesh_done_card:t_5c6b05c0@0
source_kind: mesh_done_card
source_path: t_5c6b05c0
source_ref: t_5c6b05c0@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

LaunchAgent KeepAlive exists; DevBot jobs can still hang/fail opaquely if proxy dies mid-run.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
