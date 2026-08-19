---
id: PB-009
class: git-ritual
match:
  - "CHECKOUT FLIPPED"
  - "cannot pull with rebase"
  - "You have unstaged changes"
verified: 2026-08-19
sources:
  - "T1000 reflog 08-13..08-17 (1-second round-trip pattern; 08-17 09:27 stranded)"
  - "mesh t_7f340677, t_62a4b558"
---

**Symptom:** the T1000 primary checkout (`~/Documents/T1000`) is found on
`main` instead of `ryan/herald-0.20-cutover`; the pulse guard fires
"T1000 CHECKOUT FLIPPED", or a gateway restart silently loads main's
dispatcher (dsh seam absent, wrong models).

**Diagnosis:** a non-atomic "sync main" ritual —
`git checkout main && git pull --rebase origin main && git checkout <back>` —
run from a shell or agent session. The reflog shows the healthy form as a
1-second round-trip pair; when the chain breaks after leg one (Ctrl-C, a
pull refused by a dirty tree, a closed terminal), nothing returns the
checkout. This is how the 2026-08-17 09:27 flip stranded the gateway on
main for a day and a half.

**Fix:** never flip the primary checkout to update main. Use
`git -C ~/Documents/T1000 fetch origin main:main` — it fast-forwards the
local `main` ref with HEAD untouched (works whenever main is not the
checked-out branch). If you find the checkout flipped: do NOT restart the
gateway; check `git status` for stranded uncommitted work first, then
restore with `git checkout ryan/herald-0.20-cutover` (see t_62a4b558 for
the recovery precedent).

**Don't:** run `checkout main && pull && checkout -` chains in the primary
T1000 checkout — even carefully. The pulse guard will catch a strand within
30 minutes, but the ritual itself is the defect.
