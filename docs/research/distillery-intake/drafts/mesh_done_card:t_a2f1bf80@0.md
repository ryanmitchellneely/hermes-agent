# Build hermes3:8b-16k-km model from q4_K_M base

```yaml
id: mesh_done_card:t_a2f1bf80@0
source_kind: mesh_done_card
source_path: t_a2f1bf80
source_ref: t_a2f1bf80@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Create a Modelfile that uses the q4_K_M base model and sets num_ctx=16384. Run the conversion to produce hermes3:8b-16k-km.gguf and store it at ~/models/hermes3/8b-16k-km.gguf. Verify file size and checksum.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
