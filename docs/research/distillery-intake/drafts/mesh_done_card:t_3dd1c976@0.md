# Edit devbot config.env on Kevin box to enable propose model gpt-oss:120b

```yaml
id: mesh_done_card:t_3dd1c976@0
source_kind: mesh_done_card
source_path: t_3dd1c976
source_ref: t_3dd1c976@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

Uncomment propose lines in /home/ryan-lab/devbot/config.env and set DEVBOT_PROPOSE_URL pointing to the tunnel endpoint and DEVBOT_MODEL_PROPOSE=gpt-oss:120b. Ensure config changes are committed.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
