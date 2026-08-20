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
  - "mesh t_e26a4c82 runs 973/974/97x (cloud K2 acceptance, three attempts)"
  - "probe matrix on k2vps 2026-08-20 01:20-02:00Z (see measurement table below)"
---

**Symptom:** on the VPS, a dsh run reports the work understood but not done,
citing sandbox/permission restrictions — sometimes claiming it wrote the file
"to /tmp instead". Raw tool-call fragments (`</tool_call>`, `</function>`)
often leak into the model's prose on the same runs.

**What is actually measured** (k2vps, dsh 0.1.0-rc.6 AND rc.8 identical,
worker user `t1000`, `--profile headless`):

| workspace | owner | result |
|---|---|---|
| `/tmp/dsh-probe` | root | ✗ denied |
| `/tmp/dsh-owned` | t1000 | ✓ **wrote** |
| `/tmp` (explicit path target) | t1000 | ✓ **wrote** |
| `/opt/t1000/home/wstest` | t1000 | ✗ denied |
| same, with `TMPDIR` pointed at it | t1000 | ✗ denied (TMPDIR *is* honored — node put its loader dir there — but the write still refused) |
| K2 worktree under `/opt/t1000/home/src/...` | t1000, `touch` proven writable | ✗ denied |

**Diagnosis (honest boundary):** writes land **only under literal `/tmp`**.
The sandbox source (`@deepseek-ai/dsh-sandbox/lib/index.js`) says
`workspace-write` grants `[workspaceRoot, "/tmp", os.tmpdir()]` — but
granting the third slot via `TMPDIR` does not unlock it, so the blocker is
not simply the writable-roots list. Directory ownership is a **separate,
real** precondition (root-owned workspaces fail regardless) — necessary but
not sufficient. Root cause of the non-`/tmp` denial is **still unknown**;
`DSH_PERMISSION_MODE` is not it (that variable is read by nothing in the
package, verified by grep — the wrapper's pin is inert on every platform).

**Fix (interim):** route edit-class cards on the VPS to the hermes `worker`
lane, which writes normally. dsh stays a read/analysis lane there. On the
Mac desk the same binary historically wrote into K2 worktrees fine (PRs
#5149, #5160), so this is environment-specific, not a flat "Linux" verdict.

**Candidate unlock, untested (needs a human call):** point
`DSH_TARGET_REPO` at a clone under `/tmp` so worktrees inherit the one
grant that works. Trade-off: `/tmp` is volatile across reboots, so the
clone must be re-creatable on demand.

**Don't:** trust *or* dismiss the model's stated reason. This entry has been
wrong twice by doing each in turn — first concluding "dsh can't write on
Linux" (mechanism wrong), then "it's only ownership" (over-corrected from a
`/tmp` test that could not distinguish the two, because `/tmp` is granted
unconditionally). Probe the mechanism with a matrix that varies one thing at
a time, and check for the artifact with `ls`.
