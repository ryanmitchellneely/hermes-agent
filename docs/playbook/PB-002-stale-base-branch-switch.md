---
id: PB-002
class: git-flow
match:
  - "Your local changes to the following files would be overwritten by checkout"
  - "failed to create branch"
verified: 2026-08-19
sources:
  - "K2 PR #5156 (fix: preposition_bot_branch)"
  - "mesh t_005bf18a, t_da63b06a run-935"
---

**Symptom:** an automated git flow fails switching/creating a branch with
"local changes would be overwritten", even though the work itself succeeded.

**Diagnosis:** the flow edited files first and branched second, and the
workspace's base was stale relative to the branch's cut point (`origin/main`).
Any file differing between the two bases makes git refuse the switch. Root
enabler: worktrees cut from a stale local `main` (the K2 primary checkout's
main is chronically behind — see K2 memory "main checkout is STALE").

**Fix:** branch **before** editing, from freshly-fetched `origin/<base>`
(`git fetch origin main && git checkout -B <branch> origin/main` on a clean
tree). The dsh wrapper does this since #5156 (`preposition_bot_branch`). If
seen again in the dsh lane: check deployed-wrapper drift
(`md5 -q ~/.t1000/bin/dsh_kanban_worker.py ~/.t1000/src/kevin-real-estate-tools/docs/agent-coordination/devbot/harness-bench/dsh_kanban_worker.py`).

**Don't:** stash/pop or commit-then-cherry-pick around it — that keeps the
stale-base editing problem and adds conflict surface (ruling (a) over (b),
t_005bf18a).
