# Build findings — local provider thinking control

Measured on branch `ryan/local-thinking-control` with `scripts/probe_provider_wire_body.py` before any engine change. The stub is the only socket. Config reached the process only through a temporary `HERMES_HOME` (`$TMPDIR/hermes-thinking-control-probe`).

## Stage A premise is false for auxiliary calls

Per-provider `extra_body` does **not** reach the wire on every path the work order named.

| Path | `providers.stub.extra_body.chat_template_kwargs.enable_thinking: false` on the wire? |
|---|---|
| aux (`call_llm`, task `title_generation` routed to `stub`) | No. Captured body is only `messages` and `model`. |
| main-stream (`AIAgent.run_conversation`, provider resolved to `custom`) | Yes. Boolean `false`, not the string. |
| moa reference (`aggregate_moa_context`, `max_tokens: 4096`) | Yes. Boolean `false`. |

A1 therefore exits 1. The three captured bodies are `tests/fixtures/provider_wire_body/{aux,main-stream,moa}.json`. They are not a green Stage A.

Why aux misses it: `call_llm` builds `extra_body` from `auxiliary.<task>.extra_body` plus the caller's `extra_body` argument (`agent/auxiliary_client.py`, `_get_task_extra_body`). The named-provider client resolver uses `providers.stub` for `base_url` and `api_key` only. It does not copy `extra_body`. MoA does copy it: `_slot_runtime` puts `request_overrides.extra_body` on the `call_llm` kwargs. The main agent does too: `resolve_runtime_provider` returns that override and `ChatCompletionsTransport._build_kwargs_from_profile` merges it.

A2 (the only delta is deleting the provider `extra_body` block) exits 1 and names all three paths. main-stream and moa lose the key, so on those paths the key in A1 came from config, not from the probe. Aux lacks the key in both runs, which is the same fact as above.

Stage A is not a universal thinking-off switch. Auxiliary tasks that go through `call_llm` without an explicit `extra_body` never see `providers.<name>.extra_body`. Stage B still has to map reasoning on all three paths. No engine code was changed to make A1 green, and `extra_body` was not moved onto the auxiliary task.

## Probe selection

Agent init also POSTs `{"name": "stub-model"}` at the stub (model-metadata probe). The judged body for each path is the chat-completions request: the captured object that contains `messages`. For MoA that is the object whose `max_tokens` is 4096. The main-stream chat body also carries `stream: true` and `stream_options.include_usage`.

## Golden bytes for B5

`tests/fixtures/provider_wire_body/golden/*.body` are the raw socket bytes for aux, main-stream, main-nonstream, and moa with no `extra_body` and no `thinking_control`, captured on this branch while the engine still matched `fork/main`. Two back-to-back runs (different stub ports) hashed identical. The probe pins `HERMES_HOME` to `/tmp/hermes-thinking-control-probe` (not `tempfile.gettempdir()`), because `scripts/run_tests.sh` starts from `env -i` and drops `TMPDIR`; a `$TMPDIR`-based home would change the system prompt and fail B5 under the test runner. The main-agent system prompt still embeds that path, the OS line (`macOS (15.5)`), and the frozen date `Tuesday, September 29, 2026` (`hermes_time.now` pinned inside the probe). A re-run of this probe on this machine matches those bytes.

## Spec note carried into Stage B

The load-time warning is specified as covering every non-`none` effort `parse_reasoning_effort()` can return, i.e. `VALID_REASONING_EFFORTS` (`minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra`). The Qwen map printed in the work order omits `minimal` and `ultra`. The DS4 map printed there (`{high: high, xhigh: max, max: max}`) also omits `minimal`, `low`, `medium`, and `ultra`. The implementation warns against the full set. Those two printed maps therefore warn. A map that covers every non-`none` effort does not. Bar B7's clause that the printed maps produce no warning contradicts the algorithm sentence; the algorithm is what ships.
