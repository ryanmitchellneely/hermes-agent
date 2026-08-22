---
id: PB-011
class: dsh-runtime
match:
  - "danger-full-access"
  - "sandbox permission escalation"
  - "file access denied under workspace-write mode"
verified: 2026-08-22
sources:
  - "k2 t_94a4db9a runs 1453 (deny) / 1454 (clean) — the patch-class live-fire, 2026-08-22"
  - "dsh session trajectory session-370a6a26 (edit tool targeted the clone path; sandbox denied)"
---

**Symptom:** a dsh run on a card that edits an EXISTING repo file reports
BLOCKED asking for "danger-full-access" escalation, claiming workspace-write
is insufficient. Files that exist nowhere yet (new-file cards) never hit this.

**Mechanism (proven from the trajectory, not the model's story):** kanban
worktrees live INSIDE the primary clone
(`~/src/kevin-real-estate-tools/.worktrees/<task>`), so every tracked file has
a TWIN at the clone's own path. A model that finds the file by search or
absolute path picks the clone twin — which is genuinely outside its granted
workspaceRoot — and the sandbox denies it CORRECTLY. The model then asks for
escalation instead of re-pathing. The denial is the fence working; the model's
"needs danger-full-access" is a wrong diagnosis of its own path mistake.

**Fix:** comment path guidance onto the card and unblock — one line naming the
cwd-relative path and stating that absolute paths under the clone root are the
wrong copy. Proven: t_94a4db9a run 1454 completed clean immediately after.
Card authors: write repo-relative paths ("./docs/...") in card bodies, never
absolute ones.

**Do NOT** grant danger-full-access for this, and do not treat the denial as a
sandbox defect (PB-010's corrected lesson applies: prove what was actually
denied before believing the stated reason). Structural cure worth a card if
this recurs: move kanban worktrees OUTSIDE the clone tree so no twin path
exists.
