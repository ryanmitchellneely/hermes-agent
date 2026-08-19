---
id: PB-005
class: credentials
match:
  - "missing credentials"
  - "could not read Username"
  - "gh auth"
  - "No API key"
verified: 2026-08-19
sources:
  - "mesh t_7fa5ce83 (root cause + fix), t_df743692, t_12ecbf2f"
  - "T1000 7ec01d2703 (GH_TOKEN mint seam)"
---

**Symptom:** GitHub (or any keychain-backed) auth works interactively but every
launchd-spawned worker fails with missing credentials.

**Diagnosis:** `gh` stores its token in the macOS keyring and git uses
`credential.helper=osxkeychain` — both are login-session-bound. Launchd workers
run outside the login session and cannot unlock either. Nothing is
misconfigured; the credential *store* is invisible.

**Fix (the established pattern):** mint short-lived tokens from a GitHub App
via `~/.t1000/bin/k2app-token`; git gets it through the fleet gitconfig
credential helper (`GIT_CONFIG_GLOBAL=~/.t1000/fleet-gitconfig` in the gateway
plist), gh gets it through `HERMES_KANBAN_GH_TOKEN_CMD` → worker `GH_TOKEN`
(T1000 `7ec01d2703`). Any new credentialed tool in the fleet should reuse this
mint, not grow a second mechanism.

**Don't:** put a long-lived PAT in env/files — the hourly-expiring App token's
expiry is the point. And never a token in argv or a push URL (leaks via `ps`).
