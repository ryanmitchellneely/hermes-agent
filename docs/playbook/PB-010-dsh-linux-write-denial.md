---
id: PB-010
class: dsh-runtime
match:
  - "sandbox permissions restrictions"
  - "unable to perform the actual file modification"
  - "permission issues when trying to create the file"
  - "grant the necessary permission or allow the creation of new files"
verified: 2026-08-21
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

## Correction (2026-08-21) — root cause found; everything above is symptom archaeology

**The sandbox was never the blocker.** Instrumented on k2vps (strace -f -e
trace=execve on live headless runs):

1. bwrap cannot run unprivileged on this box (Ubuntu 24.04,
   `kernel.apparmor_restrict_unprivileged_userns=1` denies the uid map), so
   the runner chain falls back to Landlock — which **works**: the launcher
   run by hand with `--rw <workspace>` wrote into
   `/opt/t1000/home/wstest` (the exact class the matrix above marks denied).
   Probe verdict "partial (older ABI)" is informational, not disabling.
2. Under the lane's pinned model (`qwen3-coder:30b` via the ollama
   `openai-completions` route), the model's tool-call XML **never parses**:
   strace shows ZERO sandbox spawns, raw `</tool_call>` fragments leak into
   prose, no file appears. No tool executed, nothing was denied — the model
   then **confabulated "sandbox permission restrictions"**, and those exact
   phrases became this entry's match lines.
3. Same probe pinned to `gpt-oss:120b` on the same route: the write tool
   executes and the file lands in the workspace, first try.
4. End-to-end receipt: smoke card `t_75d24720` → dsh (gpt-oss:120b) wrote
   `SMOKE.md` in a K2 worktree → wrapper draft PR **#5320** by
   `app/k2-dsh-lane`. Full lane parity on the VPS.

**Fix (live 2026-08-21):** deployed `dsh-k2-local.yml` default flipped
`qwen3-coder:30b` → `gpt-oss:120b`. The read-only-lane interim above is
RETIRED. The Mac never differed in kernel or sandbox — it ran DS4-flash,
whose tool calls parse.

**Standing lesson (third instance for this entry):** the matrix varied
workspace and ownership but never THE MODEL, and `/tmp` "successes" were
parse-luck noise. When a harness reports permission errors, first prove a
tool call EXECUTED (strace for the launcher spawn) before believing any
stated reason. Ownership rows remain true as plain DAC.
