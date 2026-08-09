# W1: adopt existing ds4.service — add Install+Restart, parity migrate

```yaml
id: mesh_done_card:t_d1947f46@0
source_kind: mesh_done_card
source_path: t_d1947f46
source_ref: t_d1947f46@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: draft
status_changed_at: 2026-08-09T03:15:16Z
superseded_by: null
```

Unit EXISTS at /etc/systemd/system/ds4.service with admission gates (>=105GiB MemAvailable + empty Ollama at start), MemoryHigh=105G/MemoryMax=112G, receipt sha pins — but NO Install section (static), Restart=no, and live server is a MANUAL foreground launch with downgraded flags (32768/4096 vs unit 100000/8192). Do: add Install WantedBy=multi-user.target; Restart=on-failure RestartSec=10; ExecStart to parity ctx 32768 + kv-disk 8192 (one change: the supervisor). Window: announce, stop manual proc, verify admission preconds, systemctl enable --now ds4, golden apply, overnight watch. Rollback: disable + manual relaunch (write exact cmd verbatim in runbook — today it lives only in ps output). MUST precede all flag work. Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K5.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
