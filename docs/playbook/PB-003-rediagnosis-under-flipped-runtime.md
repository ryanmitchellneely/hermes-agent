---
id: PB-003
class: meta-diagnosis
match:
  - "max_in_progress_per_profile"
  - "cap of 2"
  - "not enforced"
verified: 2026-08-19
sources:
  - "mesh t_841ec671, t_672d9832 (both re-diagnosed a fixed bug)"
  - "T1000 652ec52669 (the pre-existing fix, with tests)"
---

**Symptom:** dispatcher/gateway behavior contradicts config (caps not binding,
a seam missing, a feature silently absent), and a card is about to be filed or
fixed for it.

**Diagnosis (check FIRST, before fixing anything):** the running gateway may be
executing the wrong checkout. On 2026-08-17 the T1000 checkout flipped to
`main`; every "dispatcher bug" observed that night was a symptom of running
1700-commits-divergent code, and two worker runs re-implemented (worse) a fix
that already existed on `ryan/herald-0.20-cutover`.

**Fix:** before diagnosing dispatcher misbehavior: (1)
`git -C ~/Documents/T1000 branch --show-current` — expect
`ryan/herald-0.20-cutover`; (2) `git log` the relevant file on that branch for
an existing fix; (3) only then file/fix. The checkout-flipper itself is STILL
unidentified (t_7f340677) — verify the branch before and after every gateway
restart.

**Don't:** merge `d717b33315` (the redundant, untested cap fix) — cutover's
`652ec52669` is the good one.
