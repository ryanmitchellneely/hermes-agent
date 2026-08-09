# W0: evict qwen2.5-coder:32b on Ryan Spark; retarget spark-code alias

```yaml
id: mesh_done_card:t_c582db54@0
source_kind: mesh_done_card
source_path: t_c582db54
source_ref: t_c582db54@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

29GB resident, 0/5 worker cards. Unload without restart: POST :11434/api/generate with model=qwen2.5-coder:32b keep_alive=0. Keep weights on disk (deletion needs explicit Ryan OK; buys nothing vs 3.3TB free). Retarget spark-code alias (currently qwen2.5-coder:32b) to qwen3-coder:30b@spark after D-test pull; drop both qwen2.5 entries from provider models list. Freed 29GB funds NUM_PARALLEL slots + on-demand pool. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-R10.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
