# Investigate dispatcher dead-pid worker crashes (runs 130/131/134/137/138)

```yaml
id: mesh_done_card:t_a3b59911@0
source_kind: mesh_done_card
source_path: t_a3b59911
source_ref: t_a3b59911@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Five runs died tonight with pid-not-alive or rc=0 protocol violations, all on cards touching Ryan Spark (t_c582db54 eviction x2, t_44c99649 D-test x3), across different model lanes (grok-4.5 xai-oauth, opus claude-acp) — so the model lane is probably not the cause; suspect the spawn path on Ryans-MacBook-Pro dispatcher (locks 18183 and 39332 both present). Burned the 2-failure circuit breaker on both cards; the work itself was fine (eviction succeeded manually in one curl). Check dispatcher logs around 19:05-19:16 2026-08-08 for spawn/kill causes. If a third card crashes the same way the spawn path is confirmed as the suspect. Source pointers: ~/Documents/T1000/hermes_cli/kanban_db.py run outcomes; mesh events on the two cards.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
