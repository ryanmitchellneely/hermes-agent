# W3 precheck (OQ4): confirm Ollama systemd supervision + listen address on Ryan Spark

```yaml
id: mesh_done_card:t_56f67c50@0
source_kind: mesh_done_card
source_path: t_56f67c50
source_ref: t_56f67c50@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

Precheck (OQ4) for W3 width ladders (spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md OQ4, S8). Read-only investigation on Ryan's Spark: (1) how is Ollama supervised -- systemd unit with Environment= lines, or manual foreground launch? (2) does it listen only on 127.0.0.1 or beyond loopback on the tailnet (test locally and via 'curl http://100.67.253.61:11434/api/version' from another host)? Findings determine the restart procedure for the sibling R12 NUM_PARALLEL ladder card and the transport for K7's cross-box propose tunnel. No restart, no config change -- report findings via kanban_comment on this card, then kanban_complete. If supervision mechanism can't be determined from the box itself, kanban_block(kind='needs_input').

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
