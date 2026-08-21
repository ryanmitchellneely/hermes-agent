# Session closeout — 64k floor fix + lab boards (2026-08-08)

```yaml
id: skill_reference:a86a179e24adc5f7
source_kind: skill_reference
source_path: ~/.t1000/profiles/worker/skills/software-development/local-inference-fleet/references/session-2026-08-08-ctx-lab-closeout.md
source_ref: 44a70334c1d73bbf
board: null
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

1. **Root cause:** `get_custom_provider_context_length` ignored entry-level `providers.*.context_length` when `models` was list-shaped (`{name: {}}`). DS4 advertise 32k → Hermes 64k refuse → kanban crash with no tokens.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts skill_reference rows it has already seen).

## notes
