# Kanban goal-judge: 30s hardcoded timeout + ignored transport_failed = false rejections

```yaml
id: mesh_done_card:t_4123e041@0
source_kind: mesh_done_card
source_path: t_4123e041
source_ref: t_4123e041@0
board: mesh
captured_at: 2026-08-09T03:15:16Z
status: stale
status_changed_at: 2026-08-20T21:31:20Z
superseded_by: null
```

Root cause traced live 2026-08-08 (fable-desktop) after t_253717ee completion was rejected 'judge error: TimeoutError'. Three stacked defects: (1) hermes_cli/kanban.py ~L2196 calls judge_goal() without a timeout arg, so DEFAULT_JUDGE_TIMEOUT=30.0 (goals.py L48) applies with no config knob on the kanban path — auxiliary.goal_judge.provider/model overrides exist via get_text_auxiliary_client but no timeout override. (2) The judge inherits the MAIN model lane — currently claude-acp opus[1m], a slow-thinking model on a lane contended by every concurrent worker; 30s is structurally tight for it. (3) judge_goal docstring says transport errors fail OPEN with transport_failed=True so callers can track consecutive failures — but the kanban call site unpacks transport_failed into _ and hard-rejects any verdict != done, converting a transient transport timeout into a completion rejection. The goal-loop caller and kanban caller disagree on timeout semantics. Fix sketch (pick per Ryan): pass a config-read timeout (auxiliary.goal_judge.timeout, default 120) at the kanban call site; distinguish transport_failed=True as retry-with-backoff or warn-and-allow-with-audit-comment rather than silent hard reject; optionally route goal_judge to a faster subscription lane. Evidence: one timeout sample (22:0x retry), first rejection was legitimately empty-evidence. Do NOT weaken the judge itself — evidence-gated completion caught a real bare complete tonight and that discipline is right.

Set `status:` above to `filed` or `skipped` once reviewed (the sweep reads your edit back and never re-drafts mesh_done_card rows it has already seen).

## notes
