## Findings

### P0: Stage A Probe Fails to Validate `extra_body` Propagation (Section 2, Bar A1)
**What is wrong:** The work order claims Stage A proves that `extra_body` reaches the wire. However, the spec for the probe script (`scripts/probe_provider_wire_body.py`) states it "writes a temporary `HERMES_HOME`... and drives three real call paths." It does **not** specify that the probe must invoke the actual T1000 agent code (`agent/auxiliary_client.py`, etc.) using that config. If the builder implements the probe by manually constructing HTTP requests with the `extra_body` payload (bypassing the application's config loading and request building logic), the test will pass even if the application code completely ignores `extra_body`. This renders Bar A1 and A2 useless for validating the "config mitigation" goal.
**Concrete fix:** Explicitly mandate that the probe script must instantiate the real `AuxiliaryClient` and `ChatCompletionsTransport` classes, injecting the temporary `HERMES_HOME` via environment variables or dependency injection, and trigger calls through the standard public APIs (e.g., `client.generate_title()`, `transport.chat()`). The test must fail if the application code does not read `extra_body` from the config and merge it into the request.

### P1: Ambiguous MoA Call Path Coverage (Section 3, Spec & Bar B1)
**What is wrong:** The spec states MoA calls "route through one of the above; confirm which, and cover it." This is ambiguous. If MoA uses a distinct code path (e.g., a specialized aggregator client) that does not share the `_build_call_kwargs` logic with `auxiliary_client.py` or `chat_completions.py`, the builder might implement the fix in the wrong place or miss the MoA path entirely. Bar B1 requires tests over "three builders," but if the builder assumes MoA reuses `auxiliary_client` when it actually uses a separate internal helper, the tests will pass while the bug persists in production.
**Concrete fix:** Remove the ambiguity. Explicitly identify the MoA entry point (e.g., `agent/moa_loop.py::_execute_reference_call`). Require that the `thinking_control` logic be extracted into a shared utility function (e.g., `utils/reasoning.py::apply_thinking_control`) called by *all three* distinct entry points. Bar B1 must explicitly mock/patch the HTTP layer for the specific MoA function identified, not just the generic builders.

### P1: Missing Validation for `chat_template_kwargs` Merge Logic (Section 3, Bar B1)
**What is wrong:** The spec requires: "Caller- or config-supplied `chat_template_kwargs` keys win over generated ones: merge, don't overwrite." Bar B1 asserts the exact `chat_template_kwargs` for standard cases but does not explicitly test the *conflict* case where a user provides a conflicting key in `extra_body` (e.g., user sets `enable_thinking: true` while config says `false`). Without a specific test case for this precedence rule, a builder could implement a simple dictionary update (`dict.update()`) which overwrites user keys with generated ones, violating the spec. Bar B4(iii) mentions a "dedicated merge test" but it is listed under mutation proofs, not as a primary functional bar.
**Concrete fix:** Add a specific test case to Bar B1: "When `extra_body` contains `chat_template_kwargs: {enable_thinking: true}` and the provider config generates `enable_thinking: false`, the final request body must contain `enable_thinking: true`." This must be a pass/fail bar, not just a mutation target.

### P2: Unsafe Deploy Step for Live Config (Section 5)
**What is wrong:** The deploy notes state: "Config for `spark`... is added at the same time" as the code cherry-pick. If the code cherry-pick fails or is rolled back, the live config will still contain `thinking_control` keys that the old code does not understand. While the spec says providers without `thinking_control` behave as today, it does not explicitly guarantee that *unknown* keys in the provider config are ignored safely by the *old* code. If the old code crashes on unexpected keys, the rollback is broken.
**Concrete fix:** Add a pre-deploy check or a post-rollback verification step. Explicitly state that the old code must be verified to ignore unknown provider keys (or that the config change is strictly additive and safe for the old code) before the cherry-pick. Alternatively, require the config change to be applied *after* the code is verified running, not "at the same time."

### P2: Bar A4 Success Metric Ambiguity (Section 2, Bar A4)
**What is wrong:** "Success = `length` share below 20%." This metric is highly dependent on traffic mix. If the traffic mix changes (e.g., more long-context requests), the `length` share could rise above 20% even if thinking is successfully disabled. This could lead to a false negative (rejecting a working fix) or false positive (accepting a broken fix if traffic drops).
**Concrete fix:** Define the success metric relative to a baseline or control. E.g., "Success = `length` share is reduced by at least 50% compared to the pre-deploy baseline, OR absolute share is below 20%."

## Converged?
NO

Verdict: REVISE
