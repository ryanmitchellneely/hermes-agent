---
id: PB-004
class: launchd-env
match:
  - "FileNotFoundError"
  - "command not found"
  - "No such file or directory: 'dsh'"
  - "executable not found on PATH"
verified: 2026-08-19
sources:
  - "K2 DEEPSEEK-HARNESS-LANE.md §9 (two PATH traps, one blocked dispatch each)"
  - "mesh t_3e630202, t_6ad51c8c"
repair: "REPORT-ONLY launchd-PATH audit, modify nothing: read /Users/ryan/Library/LaunchAgents/ai.hermes.gateway.plist.mac-glass and confirm (a) ProgramArguments[0] is an absolute path, not a bare command, and (b) EnvironmentVariables.PATH leads with /Users/ryan/Documents/T1000/venv/bin before any system path entry. Completion summary must state PASS/FAIL for each of the two checks, quoting the actual ProgramArguments[0] value and the first three PATH entries. Do not edit, copy, or delete anything."
repair_assignee: worker
repair_auto: true
repair_class: report
---

**Symptom:** a worker/child process can't find an executable that works fine in
your terminal.

**Diagnosis:** two stacking traps. (1) POSIX resolves a bare executable name
against the **parent's** PATH, not the child's `env=` dict — launchd's minimal
PATH has no nvm/homebrew. (2) npm's prefix pin can put a binary in the v20
tree even when installed by v22's npm.

**Fix:** use absolute paths for child argv[0] in anything launchd-spawned;
lead the child PATH with the needed tree only for what the *script's shebang*
resolves (e.g. `NODE22` first so `env node` finds v22).

**Don't:** "fix" it by editing the plist PATH per-tool — the absolute-path rule
in the spawning code is the durable form.
