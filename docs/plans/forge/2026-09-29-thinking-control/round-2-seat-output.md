Round-1 Findings Grading:
1. **Resolved.** The probe now strictly enforces real entry points and socket inspection, eliminating the risk of hand-built requests.
2. **Resolved.** MoA path is explicitly defined via `call_llm`, and the shared helper architecture is clearly specified.
3. **Resolved.** Merge precedence is covered by B1b with specific conflict and merge cases.
4. **Resolved.** Deploy ordering includes a pre-check for unknown keys and a safe rollback sequence.
5. **Resolved.** Metric definition is precise, using absolute shares and request counts to account for traffic mix.

New Findings:
**P1 | Section 3, Bar B1 | Missing Negative Fixture for `reasoning_effort`**
Bar B1 asserts the *absence* of `reasoning_effort` for `none`/`low` cases. However, if the implementation incorrectly defaults to sending `reasoning_effort` when `enabled: False`, a simple "absence" check might pass if the test fixture doesn't explicitly seed a case where `reasoning_effort` *should* be present but isn't, or if the assertion logic is flawed. More critically, B1 does not explicitly test that `reasoning_effort` is *absent* when `effort_key` is omitted in the config, even if `enabled: True`.
*Fix:* Add a specific test case in B1: `thinking_control` with `effort_key: null` (or omitted) and `enabled: True`. Assert `reasoning_effort` is NOT in the body.

**P1 | Section 3, Bar B4(iv) | Mutation Proof Ambiguity**
B4(iv) removes the helper call from `chat_completions.py` only. It claims the main-agent case of B2 fails. However, B2 is a *builder-executed* bar (likely unit/integration). If B2 is a unit test mocking the socket, removing the helper call might just result in an empty body or a crash, not necessarily a "failure" that distinguishes it from other bugs. More importantly, if the helper is called *before* the builder, removing the call in the builder might not affect the body if the body was already mutated. The spec says the helper is called *from* the builder. If the builder calls it, removing the call means the helper never runs. This is fine. But the risk is that B2 might pass if the test doesn't strictly verify the *source* of the mutation.
*Fix:* Clarify that B4(iv) must fail because the `chat_template_kwargs` are missing from the captured body in the main-agent path, while the auxiliary path (if tested in the same run) still has them. Ensure the test distinguishes between "missing key" and "wrong value".

**P2 | Section 2, Bar A1 | Fixture Commitment Risk**
A1 requires committing captured bodies as fixtures. If the stub server's response or the SDK's internal serialization (e.g., JSON key ordering, whitespace) varies slightly between runs or environments, the fixture comparison might be brittle.
*Fix:* Specify that the fixture comparison should be semantic (parsed JSON equality) rather than byte-identical, unless byte-identity is strictly required for B5. For A1, semantic equality is sufficient to prove the key reached the wire.

**P2 | Section 5, Deploy Notes | Cherry-Pick Conflict Risk**
The deploy notes mention cherry-picking onto `ryan/herald-0.20-cutover`. If this branch has diverged significantly from `fork/main`, the cherry-pick might conflict, especially in `chat_completions.py` or `auxiliary_client.py`. The order doesn't specify a conflict resolution strategy or a requirement to test the cherry-picked branch locally before the "announced window".
*Fix:* Add a step: "Resolve any cherry-pick conflicts locally and run the full test suite on the cherry-picked branch before the announced window."

## Converged?
NO

Verdict: REVISE
