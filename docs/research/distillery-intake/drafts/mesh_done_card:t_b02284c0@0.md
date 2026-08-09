# HUMAN gate: re-enroll kevin-spark/DS4 as agentic dispatch lane (post-W2 ctx 65536)

```yaml
id: mesh_done_card:t_b02284c0@0
source_kind: mesh_done_card
source_path: t_b02284c0
source_ref: t_b02284c0@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

Opens only after W2 (t_01ac807e) verifies DS4 real ctx 65536 + lockstep providers.kevin-spark.context_length bump in all three configs (root + worker + orchestrator). Context: t_59505920 established that DS4 at ctx 32768 cannot serve agentic kanban dispatch (harness hard floor MINIMUM_CONTEXT_LENGTH=64_000 at agent-init). Interim resolution repointed the orchestrator profile default from kevin-spark/deepseek-v4-flash to spark/gpt-oss:120b (backup: profiles/orchestrator/config.yaml.bak-pre-t_59505920), so clearing the floor via W2 does NOT silently resume any default traffic on DS4 — re-enrollment is this explicit decision. DECISION for Ryan: after W2 lands, should DS4 become a default agentic lane again (orchestrator default back? worker default? per-card set-model only?), or stay non-default? Consider deciding together with / after W4 B-vs-D (t_a97cf1e6) since lane roles may change entirely under pivot-D. To close: Ryan comments the chosen routing + which config lines changed (or 'stay per-card only'), then complete. NO agent may flip the default back without this card.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
