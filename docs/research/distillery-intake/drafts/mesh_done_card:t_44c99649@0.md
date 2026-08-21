# W0: D-test — qwen3-coder:30b >=20 goldens on Ryan Spark (gates W4)

```yaml
id: mesh_done_card:t_44c99649@0
source_kind: mesh_done_card
source_path: t_44c99649
source_ref: t_44c99649@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Pull 18.6GB to Ryan Spark (model currently only on MBP mbp-ollama). Every request MUST pass keep_alive TTL <=30m — box has global OLLAMA_KEEP_ALIVE=-1, an un-TTLd load is a silent permanent pin. Run >=20 FILE-fence code goldens (same protocol as Flash 9/9). D wins if apply_ok>=95% AND p50 wall<=30s AND free floor holds. Feeds W4 B-vs-D decision card; artifact doubles as documented cold-standby code lane (failover, spec S8). Safe concurrent with Kevin DS4 per bakeoff doc (different host). Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S3.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
