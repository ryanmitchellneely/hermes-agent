# W2: DS4 ctx 32768 to 65536 + kv-disk 64GB; KV/token + TTFT soak

```yaml
id: mesh_done_card:t_01ac807e@0
source_kind: mesh_done_card
source_path: t_01ac807e
source_ref: t_01ac807e@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

65536 clears both thresholds (35.7k kanban worker prompt; Hermes 64k local-worker minimum). NOT 100000 yet — the unit value is an aspiration someone typed, not a measurement. Verify: real 35.7k worker prompt probe returns 200 not 400; prefill ~60k and record ds4-server RSS delta + kv dir growth = KV bytes/token; one clean overnight soak in journal. Then kv-disk-space-mb to 65536 (2.9TB NVMe) and measure warm-vs-cold TTFT on the DevBot system prompt (warm <=50 percent cold). 100k only if RAM KV at 65k leaves >=10GB slack. Lockstep: providers.kevin-spark.context_length. CHECK FIRST (OQ3): is the Hermes 64k minimum a hard router gate — does clearing 65k auto-enroll DS4 for worker cards (silent traffic change)? Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K1/K2.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
