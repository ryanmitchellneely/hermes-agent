---
id: PB-010
class: dsh-runtime
match:
  - "sandbox permissions restrictions"
  - "unable to perform the actual file modification"
  - "</tool_call>"
  - "grant the necessary permission or allow the creation of new files"
verified: 2026-08-19
sources:
  - "mesh t_e26a4c82 runs 973/974 (cloud K2 acceptance)"
  - "direct probes /tmp/dsh-probe (both qwen3-coder:30b and gpt-oss:120b, bwrap installed made no difference)"
---

**Symptom:** a dsh-lane card on the VPS reports the work "understood" but not
done, citing sandbox/permission restrictions; or raw tool-call fragments
(`</tool_call>`, `</function>`) leak into the model's plain-text output.

**Diagnosis:** dsh 0.1.0-rc.6's file-write toolchain does not function on
Linux — probed directly with two different models in a world-writable scratch
dir under `workspace-write`: neither can create a file, and installing
bubblewrap changes nothing. The models' "permission restrictions" explanations
are CONFABULATED — they describe their own inert tool calls, not a real
policy. Do not trust the model's stated reason for this class; probe with
`ls` for the artifact.

**Investigation state (2026-08-19, time-boxed source read):** the sandbox
source (`@deepseek-ai/dsh-sandbox/lib/index.js`, readable) proves
`workspace-write` ALWAYS allows `/tmp` — and probes in /tmp are denied, so
the runtime mode is not workspace-write on Linux. Bigger: **nothing in the
package reads `DSH_PERMISSION_MODE`** — the wrapper's env pin is a no-op on
every platform (on macOS it merely coincided with a permissive default).
Mode really comes from the `dsh-sandbox-policy` plugin's `defaultMode`
(host composition, not located in the minified dist); a patch-overlay guess
(`id: sandbox-policy`) did not take (silent-skip or wrong theory). The
recurring leak of raw `</tool_call>` fragments from two different models
suggests the write TOOL may not register at all on Linux — which would
produce exactly these symptoms regardless of mode.

**Fix (interim):** route edit-class cards on the VPS to the hermes `worker`
lane (writes proven live during V0). Keep dsh cards read/analysis-only on
Linux until the write path is fixed. Fix paths to investigate: read dsh's
sandbox/tool-registration source for Linux, try a newer rc, or file upstream
(deepseek-ai/deepseek-harness) with the probe transcript.

**Don't:** flip `DSH_PERMISSION_MODE=danger-full-access` to "fix" it — on the
VPS the worker user owns the whole home including secrets/, and there is no
evidence the mode is the problem (both modes deny).
