# MESH-INFRA-2 handoff — code cards default to worktree isolation

Task: t_e7a105c5
Branch / worktree: mesh/t_e7a105c5 @ /Users/ryan/Documents/T1000/.worktrees/t_e7a105c5
Date: 2026-08-11

## Problem

Concurrent kanban workers shared one working tree (dir:main or scratch editing main).
Board mesh had `default_workdir=/Users/ryan/Documents/T1000` but no `project_id`.
CLI/tools hard-defaulted `--workspace scratch`, so create never auto-promoted.

## What shipped (code)

1. **Board policy** `resolve_board_default_workspace_kind()` in `hermes_cli/kanban_db.py`
   - explicit `default_workspace_kind` if set
   - else `worktree` when `project_id` set
   - else `worktree` when `default_workdir` is a git repo
   - else `scratch`
2. **`create_task(workspace_kind=None)`** applies that policy when kind is omitted.
   Explicit `scratch` still opts out (ops cards).
3. **dir:main rewrite** — `dir:` pointing at board git default_workdir or any repo root becomes a fresh per-task worktree (stops minting shared main checkouts).
4. **Cross-profile fallback** — if board `project_id` does not resolve in this profile's `projects.db`, drop the id but still promote to worktree via git default_workdir.
5. **bind-board / project create --board** now writes **both** `project_id` and `default_workdir` on `board.json` (was workdir-only).
6. **CLI** `--workspace` default is `auto` (omit); tools no longer coerce omitted kind to scratch.
7. **GC** `hermes kanban gc --worktree-retention-days N` (default 14) via `gc_stale_worktrees()` — only `…/.worktrees/<task_id>` for done/archived past retention; never main checkout.

## Live board config applied

- Created project `t1000` (`p_a2b7f4bf`) primary `/Users/ryan/Documents/T1000`
- Bound mesh: `board.json` now has `project_id=p_a2b7f4bf` + existing default_workdir
- Seeded `t1000` project into other profile `projects.db` copies under `~/.t1000/profiles/*`
- Dry-run create (archived): kind=worktree, path=`…/.worktrees/t_e6f76ae1`, branch=`t1000/t_e6f76ae1-…`

## Prune policy (ops)

```
hermes kanban gc --worktree-retention-days 14
```

Recommend weekly cron (or piggyback existing hygiene). Safe shape only:
`<repo>/.worktrees/<task_id>` for terminal tasks older than N days; deletes local task branch best-effort; `git worktree prune` after.

## Deliverable-loss (t_8d35ac4f)

Partial solve for **code cards**: worktree/dir are preserved on complete (scratch still deleted).
Once code is on the runtime path + mesh project bind, new code cards stop landing in deleted scratch workspaces by default.
Still remaining for t_8d35ac4f: teach workers the scratch contract; optional archive-on-complete for true scratch deliverables.

## Tests

```
PYTHONPATH=. pytest tests/hermes_cli/test_kanban_board_workspace_policy.py \
  tests/hermes_cli/test_kanban_board_project.py \
  tests/hermes_cli/test_kanban_project_link.py \
  tests/hermes_cli/test_kanban_worktree_isolation.py -q
# 16 passed
```

## Deploy note

Runtime `hermes` imports `/Users/ryan/Documents/T1000/hermes_cli` (main tree), not this worktree.
Merge/cherry-pick `mesh/t_e7a105c5` (or land the diff) for full policy on all entry points.
Board `project_id` alone already helps **old** create_task when the creator profile can resolve the project (scratch→worktree upgrade).

## Explicitly NOT done

- No body-path NLP dispatch refuse
- No self-approve — review requested for Ryan
- Did not migrate existing 44 dir:T1000 rows (only stops new ones; optional follow-up)

## Changed files

- hermes_cli/kanban_db.py
- hermes_cli/kanban.py
- hermes_cli/projects_cmd.py
- tools/kanban_tools.py
- plugins/kanban/dashboard/plugin_api.py
- tests/hermes_cli/test_kanban_board_workspace_policy.py (new)
