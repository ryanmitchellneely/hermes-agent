# Distillery connection rule: every durable artifact gets an intake row — automate the sweep

```yaml
id: mesh_done_card:t_8b3c9a73@0
source_kind: mesh_done_card
source_path: t_8b3c9a73
source_ref: t_8b3c9a73@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

Ryan directive 2026-08-08 evening: nothing we touch should be disconnected from the Distillery. Sharpened proposal (fable-desktop): the unit of connection is the durable ARTIFACT (spec, signal, decision, lesson, shipped fix), not every touch — and the mechanism should be PULL, not per-actor discipline: a Distillery intake sweep that subscribes to the systems of record (~/.hermes/plans/ new files, signal-log entries/, mesh cards reaching done, fleet skill references/ changes) and drafts intake rows automatically, with a staleness check that flags unswept artifacts — observability-principle style, the check must be automatic or the rule will silently rot. Implementation candidates: extend the kanban-checkin skill wrap-up ritual + a T1000 cron. Related: t_048f0c5c (current intake tranche, has 6 candidate rows from tonight in comments), t_ecf2e67f (Distillery-to-T1000 port brief, done), K2-side #4419 hunger nudge + rising-tails deferred followup. Needs Ryan to confirm scope (mesh-only vs all boards) before a worker builds the sweep.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
