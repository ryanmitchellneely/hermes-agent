**Round-3 Resolution Check**

1.  **P1 top_level_effort untested**: **Resolved**. The spec explicitly states: "Top-level `reasoning_effort` is never set for these providers... no `top_level_effort` option; not built." This removes the ambiguity and the untested code path.
2.  **P2 B3 logging frequency**: **Resolved**. Bar B3 now specifies: "asserted with a log capture scoped to the single call." This ensures the WARNING is verified per-request, preventing false positives from global log state.
3.  **P1 call-site gap**: **Resolved**. The spec mandates: "called DIRECTLY inside the bodies of exactly two request builders... not from a shared intermediate helper." Bar B2 explicitly exercises the main-agent path both streaming and non-streaming, ensuring coverage of the specific builder branches.

**New Findings**

**P1: Ambiguity in "Main-Agent" Entry Point for Probe (Stage A/B)**
*   **Location**: Stage A Spec (b) and Stage B Bar B2.
*   **Issue**: The spec requires the probe to drive "one main-agent turn through the real agent entry that uses `agent/transports/chat_completions.py`". However, `AIAgent`/`run_agent` is a high-level orchestrator. It may invoke `chat_completions.py` indirectly via a transport factory or a wrapper that *does* use a shared intermediate helper (e.g., a generic `build_request` utility) before hitting the specific builder.
*   **Risk**: If the "real agent entry" uses a shared helper that *doesn't* call `apply_thinking_control` directly (because the spec only mandates the *builder* calls it directly, not the transport wrapper), the probe might fail to capture the `chat_template_kwargs` if the wrapper strips or ignores `extra_body` before passing it to the builder. The spec assumes `extra_body` flows transparently from config -> agent -> transport -> builder. If the transport layer sanitizes `extra_body` or rebuilds the request dict, the direct call in the builder might be bypassed or overwritten.
*   **Fix**: The spec must explicitly verify that the `extra_body` passed to the `chat_completions.py` builder *contains* the `thinking_control`-generated keys. The probe should assert that the *input* to the builder (or the output of the transport layer) contains the expected `chat_template_kwargs`, not just the final wire body. Alternatively, the spec must confirm that the specific `AIAgent` path used in the probe *does not* use a shared intermediate helper that bypasses the direct call requirement.

**P1: Missing Validation of `effort_map` Completeness in Config Loader**
*   **Location**: Stage B Spec, `thinking_control` block definition.
*   **Issue**: The spec allows `effort_map` to be partial (e.g., `{low: low}`). If a user configures `effort_map: {low: low}` but the system default or a specific task requests `high`, the logic says: "An E not in `effort_map` is dropped... and logged once at WARNING."
*   **Risk**: This is silent degradation. If `spark` is configured with a partial map, and T1000 defaults to `high` (which is not in the map), thinking is enabled (`enable_thinking: true`) but *no effort is sent*. For Qwen, the default effort is `xhigh`. If `high` is dropped, the model uses its default (`xhigh`). This might be acceptable, but if the user *intended* to control effort and made a typo (e.g., `hight`), they get no warning until runtime, and the behavior is subtly different from "no effort control" (which might imply `low` or `medium` depending on template defaults).
*   **Fix**: The config loader (or a validation step in the helper) should warn or error if the *default* effort for the provider (or the most common efforts) are missing from `effort_map`. At minimum, the WARNING in B3 must be distinct from a "missing key" error. The spec should clarify if "dropped" means "template default applies" or "no effort key sent". The current text says "no effort key sent", which implies template default. This is risky if the template default is `xhigh` (expensive/slow) and the user expected `high`.

**Verdict: REVISE**

## Converged?
NO
