# Kevin twice-daily system digest — BUILT (v1 Ryan-facing; cron arm pending Ryan)

```yaml
id: mesh_done_card:t_6fb2c9c3@0
source_kind: mesh_done_card
source_path: t_6fb2c9c3
source_ref: t_6fb2c9c3@0
board: mesh
captured_at: 2026-08-09T13:02:57Z
status: draft
status_changed_at: 2026-08-09T13:02:57Z
superseded_by: null
```

Deterministic zero-LLM digest showing how much work the system handled: mesh done/running/blocked-human counts (12h window, tiles with 08:00+17:00 CT cadence), box health from the residency heartbeat's cache (~/.t1000/cache/spark-residency-last.json — no extra SSH), DevBot scoreboard (jobs/apply_ok/p50/$saved), Distillery intake counts, named human queue. Script: ~/.t1000/scripts/kevin_digest.py. Surface written BEFORE send: ~/.t1000/kanban/KEVIN-DIGEST-latest.md (readable even when delivery fails). Test-run verified 2026-08-09 07:36 CT (28 cards/12h, boxes render, DevBot 8/8). PENDING RYAN (classifier-gated, by design): (1) register cron — hermes cron create '0 8,17 * * *' --name 'K2 system digest' --script kevin_digest.py --no-agent --deliver telegram:7869946421; (2) after reading 2-3 Ryan-facing digests, arm the Kevin channel via REACH_KEVIN_FIRE=1 reach kevin notify --fire (fail-closed dual gate; Chamberlain TG on k2vps) — arming a standing outbound channel to Kevin is explicitly Ryan's call. FOLLOW-UPS not in v1: dead-man's switch (alert if KEVIN-DIGEST-latest.md mtime >14h — one check in desk-health cron), kevin-box scoreboard rows sync home.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
