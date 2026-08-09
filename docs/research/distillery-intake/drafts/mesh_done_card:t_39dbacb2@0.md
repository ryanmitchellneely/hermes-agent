# Dual-load policy doc: DS4 active ⇒ Kevin Ollama heavy cold

```yaml
id: mesh_done_card:t_39dbacb2@0
source_kind: mesh_done_card
source_path: t_39dbacb2
source_ref: t_39dbacb2@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

While `ds4.service` is active on spark-b01b, do **not** run Ollama heavy generate (120B / 32B coder / large loads) on Kevin. Ollama may listen cold on :11434.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
