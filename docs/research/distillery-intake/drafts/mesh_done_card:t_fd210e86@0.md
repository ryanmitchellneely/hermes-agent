# W3: width ladders — batched-session (Kevin) + NUM_PARALLEL (Ryan)

```yaml
id: mesh_done_card:t_fd210e86@0
source_kind: mesh_done_card
source_path: t_fd210e86
source_ref: t_fd210e86@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

Both width ceilings unmeasured: prior 1-to-4 ladder ran against the NUM_PARALLEL=2 cap, void above 2 (defect 3). Kevin box: --batched-session N in {2,4}, concurrent golden applies, keep largest N with p95 <=1.5x N=1 baseline. Ryan box: NUM_PARALLEL 2 to 4 in its OWN window (restart drops all pins; 120b reload takes minutes, kills in-flight workers); if 4x131k KV does not fit, serve 120b at num_ctx 65536 — never sacrifice the 64k threshold for width. Outputs = swarm max_N (Kevin) + private max_N (Ryan), the B17 C2.5 numbers governance needs. Precheck (OQ4): confirm Ollama systemd supervision + listen address on Ryan Spark. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K3/R12.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
