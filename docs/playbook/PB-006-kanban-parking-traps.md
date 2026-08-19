---
id: PB-006
class: kanban-mechanics
match:
  - "claimed two minutes"
  - "initial-status blocked"
  - "recompute_ready"
  - "cannot block t_"
verified: 2026-08-19
sources:
  - "kanban-checkin skill (verified-live section, 2026-08-08/09)"
---

**Symptom:** a card meant to wait for a human gets claimed and run by the
dispatcher anyway; or a `block` verb silently does nothing.

**Diagnosis:** parking-state traps, all verified live: (1) a parentless card is
promoted back to `ready` by `recompute_ready()` regardless of
`--initial-status blocked`; (2) unassigned is NOT safe — `default_assignee:
worker` auto-assigns and spawns; (3) `block` refuses `todo` cards and fails
quietly; (4) comments never gate the dispatcher — only status and parents do.

**Fix:** create, then **immediately** `hermes kanban block <id> "<gate>"
--kind needs_input`, then `show` to confirm `status: blocked`. For a todo
card: `schedule <id>` (works from todo) or `promote --force` then block. Gate
children BEFORE unblocking parents.

**Don't:** trust `create --initial-status blocked` alone, and don't park with
a comment.
