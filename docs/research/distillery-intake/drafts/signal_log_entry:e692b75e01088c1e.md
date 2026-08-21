# Cross-model KV cache transfer within LLM families (NVIDIA)

```yaml
id: signal_log_entry:e692b75e01088c1e
source_kind: signal_log_entry
source_path: ~/Documents/T1000/docs/research/signal-log/entries/SIG-20260808-03_cross-model-kv-transfer.md
source_ref: 7f2ade1e9d01903a
board: null
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

NVIDIA research: **map KV cache from model A → model B inside the same family** (e.g. Qwen3 14B→32B) with **training-free closed-form linear maps** (per head/layer, RoPE stripped then reapplied). Target **skips prefill**; conversion **~2.7–25× faster** than re-prefill; accuracy retention often high when head dims match.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts signal_log_entry rows it has already seen).

## notes
