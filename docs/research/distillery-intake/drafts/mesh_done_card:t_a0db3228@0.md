# HUMAN Ryan: refresh spark-residency manifest to post-W2 truth (stops critical-drift TG spam)

```yaml
id: mesh_done_card:t_a0db3228@0
source_kind: mesh_done_card
source_path: t_a0db3228
source_ref: t_a0db3228@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

The 15-min residency heartbeat has returned green:false with 2 CRITICAL drifts on every tick since W2 (~06:30 CT 08-09), spamming Ryan's Telegram — it will train alarm-blindness if left. Cause: manifest still encodes pre-W2 wants. Fix (Ryan-only-write repo sovereign-consulting): edit tools/spark-residency/manifest/kevin-spark.yaml — live-want ctx 65536 + kv-disk 8192; unit-want 65536 NOT 100000 (spec §10 rejects the 100k aspiration). Then confirm next heartbeat tick goes green. Related: t_12a8a8cf stays open until this lands.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
