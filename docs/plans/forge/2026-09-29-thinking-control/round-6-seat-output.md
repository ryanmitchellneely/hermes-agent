## Round-5 Resolution Check

1.  **P1 B1 switch value**: **Resolved**. The spec now explicitly asserts `chat_template_kwargs` by equality, ensuring `switch_key` is `false` for `none` and `true` for other efforts, with exact mapped values.
2.  **P1 B4(iv) isolation**: **Resolved**. The probe output format (`PATH ... PASS|FAIL`) and the specific requirement for B4(iv) to show main-agent failure while aux/moa pass in the same run, excluding crashes, correctly isolates the mutation.

## New P0/P1 Findings

**None.**

The work order is robust.
*   **Stage A** correctly isolates config propagation via a stub server, avoiding false positives from code defaults.
*   **Stage B** correctly handles the vocabulary mismatch (Qwen vs DS4) via explicit `effort_map` and prevents raw pass-through of invalid efforts.
*   **Isolation** is enforced by testing `chat_completions.py` and `auxiliary_client.py` separately in B4(iv).
*   **Safety** is ensured by B5 (byte-identical for non-configured providers) and the explicit DO-NOTs.
*   **Deploy** is gated and includes a pre-check for unknown key tolerance on the running branch.

The logic for `none` (sending `enable_thinking: false`) vs `low/high` (sending `enable_thinking: true` + `reasoning_effort`) is consistent with the measured problem (vLLM/TensorFold ignoring top-level `reasoning` but respecting `chat_template_kwargs`). The merge precedence (caller wins) is correctly specified and tested in B1b.

## Converged?
YES

Verdict: APPROVE
