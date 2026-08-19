---
id: PB-007
class: worker-protocol
match:
  - "without calling kanban_complete or kanban_block"
  - "protocol violation"
verified: 2026-08-19
sources:
  - "mesh t_672d9832 runs 929/930 (two crashes before a clean run)"
  - "K2 harness-bench/dsh_kanban_worker.py (structural fix: terminator in finally)"
---

**Symptom:** run marked `crashed` with "worker exited cleanly (rc=0) without
calling kanban_complete or kanban_block — protocol violation".

**Diagnosis:** the worker did work (possibly all of it) but never emitted its
one terminal kanban call — TUI bail-outs, single-turn exits, and wrappers that
crash between work and terminator are the usual causes. The work may be
sitting uncommitted in the card's worktree.

**Fix:** BEFORE re-running, check the card's worktree for completed-but-
unreported work (`git -C ~/Documents/T1000/.worktrees/<task> status`) — rescue
it, don't redo it. For new lanes: own the terminator structurally (emit
complete/block from a `finally`, the dsh-wrapper pattern), never by prompting.

**Don't:** trust a completion summary that claims artifacts — verify the
commit/file exists. This class produced two false completions in two days
(2026-08-17/18).
