# DSpark spec-dec: download draft now (W0); enable W3 golden-gated

```yaml
id: mesh_done_card:t_8d13e461@0
source_kind: mesh_done_card
source_path: t_8d13e461
source_ref: t_8d13e461@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Flags verified REAL in deployed ds4-server binary 2026-08-08 (--dspark --mtp --dspark-confidence --dspark-strict --mtp-draft --mtp-margin). Draft gguf NOT downloaded. W0 (safe anytime): ./download_model.sh ds4f-dspark = 6GB into /srv/ryan-lab/ds4/gguf/. W3 (own restart window): append --dspark --mtp <gguf-dir>/DeepSeek-V4-Flash-DSpark-support-0731.gguf --temp 0. NOTE temp 0 = greedy for the whole lane; gate = rerun code goldens, apply_ok >= baseline 9/9-equiv, then p50 wall (24.5s baseline, target <=15s). Rollback: remove flags; mandatory if apply_ok regresses (lane runs unattended). Spec: ~/.hermes/plans/2026-08-08_182809-fable-dual-box-model-residency-handoff-RESPONSE.md S2-K4.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
