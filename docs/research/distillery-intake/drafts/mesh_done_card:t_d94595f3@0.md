# W4 DECISION: B vs D end-state (after D-test + W3 numbers)

```yaml
id: mesh_done_card:t_d94595f3@0
source_kind: mesh_done_card
source_path: t_d94595f3
source_ref: t_d94595f3@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

B (specialization) approved-with-changes as the bridge state. D = Kevin box mirrors Ryan stack (identical gpt-oss:120b digest already on both disks) + qwen3-coder:30b on-demand code lane. If the W0 D-test passes (apply_ok>=95, p50<=30s, floors hold) this decision OPENS — not auto-pivot: Kevin-box change, needs both acks (governance S7). D gains: symmetry, real failover, one engine, ~67GB freed on Kevin box. D forfeits: dspark spec-dec, nominal long-ctx lane. Fable tilt: D is likely the better end-state if numbers hold. Early-revisit triggers: dspark <=1.2x or regresses apply_ok; ctx ladder cannot clear 65k in memory; any unexplained ds4-server crash in the 2-week soak. Also gated here: 98GB hybrid quant (default NO) and engine side-door (llama-server, not vLLM, if ever). Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S3/S9/S10.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
