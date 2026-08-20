---
id: PB-010
class: dsh-runtime
match:
  - "sandbox permissions restrictions"
  - "unable to perform the actual file modification"
  - "permission issues when trying to create the file"
  - "grant the necessary permission or allow the creation of new files"
verified: 2026-08-20
sources:
  - "mesh t_e26a4c82 runs 973/974 (cloud K2 acceptance)"
  - "probe matrix /tmp/dsh-probe (root-owned, denied) vs /tmp/dsh-owned (t1000-owned, WROTE) — rc.6 and rc.8 identical"
---

**Symptom:** a dsh run reports the work understood but not done, citing
sandbox/permission restrictions; the model may claim it wrote the file
"to /tmp instead", and raw tool-call fragments (`</tool_call>`) can leak
into its prose.

**Diagnosis:** the workspace directory is **not owned by the user dsh runs
as**. dsh's `workspace-write` mode grants exactly `workspaceRoot`, `/tmp`,
and `os.tmpdir()` — but a grant is not a chmod: ordinary POSIX ownership
still applies underneath. A root-created workspace with a `t1000` worker
denies every write, and the model then narrates a plausible-sounding
sandbox story around it.

**Fix:** `chown -R <worker-user> <workspace>` (and its parent clone). On
the VPS the whole home needed it once after migration — `rsync -a`
preserved Mac UIDs. Verify with a scratch probe as the worker user before
blaming the harness:
`sudo -u <user> ... dsh --profile headless --patch <yml> "create a file named x.txt containing ok"`
then `ls` for the artifact.

**Don't:** conclude "dsh cannot write on Linux" — it can, in both rc.6 and
rc.8 (measured 2026-08-20). And do not flip
`DSH_PERMISSION_MODE=danger-full-access` chasing this: that env var is read
by **nothing** in the package on any platform (verified by source grep) —
the wrapper's pin is inert, and the real mode comes from the
`dsh-sandbox-policy` plugin's `defaultMode`.

**Correction record (2026-08-19 → 08-20):** this entry first claimed dsh's
write toolchain was broken on Linux. That was wrong. The probe dirs used to
"prove" it were root-owned, so every write was denied by plain filesystem
permissions; two models' confabulation-shaped explanations made the wrong
story fit. The lesson survives in inverted form: **a model's stated reason
is unreliable in BOTH directions** — do not trust its explanation, and do
not dismiss it either; probe the mechanism (ownership, mode, artifact
presence) directly.
