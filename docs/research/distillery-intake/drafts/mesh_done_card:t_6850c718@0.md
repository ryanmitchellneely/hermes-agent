# W1: restore Kevin DevBot propose to Ryan 120b (tunnel + config.env)

```yaml
id: mesh_done_card:t_6850c718@0
source_kind: mesh_done_card
source_path: t_6850c718
source_ref: t_6850c718@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

Both propose lines commented out in /home/ryan-lab/devbot/config.env — Mac-free DevBot runs with no propose model. Kevin box cannot host one (DS4 owns memory) so cross-box to Ryan Spark gpt-oss:120b. Transport: test curl http://100.67.253.61:11434/api/version from kevin-spark (tailnet direct); if Ollama is loopback-bound, add systemd ssh -L unit cloning the ds4-reverse-tunnel pattern already on the box: local 127.0.0.1:11436 to spark 127.0.0.1:11434. Set DEVBOT_PROPOSE_URL + DEVBOT_MODEL_PROPOSE=gpt-oss:120b. Verify one DevBot cycle with propose landing, then one forced-failure cycle (stop tunnel) — DevBot must degrade to current no-propose behavior, not crash. Rollback: re-comment. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K7.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
