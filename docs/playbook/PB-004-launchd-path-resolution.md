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
repair: "REPORT-ONLY spawn-PATH audit, modify nothing: from inside this card's own run (a gateway child, so its env IS the live spawn surface) run echo \$PATH and command -v python3. PASS if PATH leads with /opt/t1000/venv/bin before any system entry AND python3 resolves inside /opt/t1000/venv/bin; FAIL otherwise, quoting the first three PATH entries and the resolved python3 path. (The Mac launchd plists this entry documents are glassed since the 2026-08-19 VPS flip; the gateway's child env is the live surface for the same failure class, and the unit file itself is root-only -- audit the inherited env, not the config.) Do not edit, copy, or delete anything."
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
