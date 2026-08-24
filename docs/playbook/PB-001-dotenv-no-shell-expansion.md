---
id: PB-001
class: env-config
match:
  - "does not point at a file: $HOME"
  - "does not point at a file: ~"
  - "No such file or directory: '$"
verified: 2026-08-19
sources:
  - "K2 PR #5156 (lane doc §10 failure classes)"
  - "mesh t_da63b06a run-934"
repair: "REPORT-ONLY env-file audit, modify nothing: run grep -nE '\$HOME|\$[A-Z_]+/|~/' on /opt/t1000/home/.env and /opt/t1000/home/secrets/dsh-bot.env (the live fleet env files on k2vps; the Mac copies this entry originally named are a frozen mirror since the 2026-08-19 VPS flip). Completion summary must list every non-absolute-path line found in either file, or state CLEAN if none. If the failing card's own error text names a path from an env file other than these two, name that file explicitly as a NEW SITE. Do not edit, copy, or delete anything."
repair_assignee: worker
repair_auto: true
repair_class: report
---

**Symptom:** a path or credential env var works when a shell script sources the
env file, but a Python consumer reports the literal string `$HOME/...` (or
`$VAR/...`) as a missing file.

**Diagnosis:** python-dotenv does not expand bare `$VAR` shell syntax; shell
`source` does. Any env file with both consumer classes silently forks meaning.
`Path.expanduser()` only handles `~`, not `$HOME`.

**Fix:** use absolute paths in env files that any non-shell consumer reads
(`/Users/ryan/...`, never `$HOME/...`). Fixed live in `~/.t1000/secrets/dsh-bot.env`
and `~/.t1000/.env` on 2026-08-18.

**Don't:** add expansion logic to each consumer — the file is the shared
surface; fix the file.
