# W0: delete phantom ds4-pro/deepseek-pro aliases in t1000 config

```yaml
id: mesh_done_card:t_cf82f21c@0
source_kind: mesh_done_card
source_path: t_cf82f21c
source_ref: t_cf82f21c@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

~/.t1000/config.yaml approx lines 689-694 + deepseek-v4-pro in providers.kevin-spark.models — all silently serve 2-bit Flash (real Pro is 430GB, impossible on 121GB). context_length already reconciled to 32768; keep in lockstep with any runtime --ctx change. No restart needed; no other consumers found in sweep. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K6, defect 2.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
