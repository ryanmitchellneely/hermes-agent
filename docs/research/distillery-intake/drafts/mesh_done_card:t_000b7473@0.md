# W3: requant hermes3:8b-16k Q4_0 to Q4_K_M (golden-gated); retire dup

```yaml
id: mesh_done_card:t_000b7473@0
source_kind: mesh_done_card
source_path: t_000b7473
source_ref: t_000b7473@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Q4_0 is the crudest quant present and sits on the JSON/tool-format path (masterclass quant-fidelity rule, SIG-20260806-01). Build hermes3:8b-16k-km via Modelfile FROM the q4_K_M base + num_ctx 16384. Gate: T1000 golden eval accuracy >= current Q4_0 scores BEFORE any alias moves. Then repoint spark-format + both boxes DEVBOT_MODEL_FORMAT (Kevin box uses plain hermes3:8b — this swap also retires the duplicate, R13). Rollback: repoint back; keep Q4_0 on disk until 2-week retro. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-R11/R13.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
