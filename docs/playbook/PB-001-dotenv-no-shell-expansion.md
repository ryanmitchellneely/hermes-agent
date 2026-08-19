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
