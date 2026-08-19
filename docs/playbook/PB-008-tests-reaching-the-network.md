---
id: PB-008
class: test-hygiene
match:
  - "suite suddenly slow"
  - "TimeoutExpired"
  - "kind:transient"
verified: 2026-08-19
sources:
  - "K2 PR #5156 (fetch stub; suite 124s -> 4s)"
---

**Symptom:** a test suite's runtime jumps by minutes after a change, or a
stubbed-path test starts failing with a timeout/transient classification.

**Diagnosis:** a code path added under test now performs real network I/O the
stubs don't intercept — the giveaway pairing is "new subprocess/network call in
prod code" + "fixture uses a real remote URL". In the #5156 case a new
`git fetch` in the wrapper fetched the actual monorepo from GitHub with desk
keychain credentials, inside the unit suite, until its 120s timeout fired.

**Fix:** stub the specific call in the passthrough (match on argv), and in prod
code convert hung-subprocess timeouts to a **non-retrying** failure class
(capability, not transient) so a wedged call can't re-dispatch forever.

**Don't:** accept a mysteriously slow suite as "CI being CI" — time it; the
delta is a real call hiding somewhere.
