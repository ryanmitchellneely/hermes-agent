# Build report — local provider thinking control

Branch `ryan/local-thinking-control`. Stage B commit `d66f297e0c`. Fix round 1 commit `9d4cda5d56`. Fix round 2 commits `1ad27be0bc` (resolve for the requested model; keep non-dict kwargs), `6347efd194` (summary call site), `fafc4d90ff` (bars B8–B10). The suite below ran on `fafc4d90ff`. Probe and fixtures are `c6a0b05701` and `6a513800bb`. Interpreter `.venv/bin/python` (Python 3.11.15). Nothing was pushed. A4 and section 5 were not run.

| Bar | Result | Command | Exit |
|---|---|---|---|
| A1 | FAIL | `.venv/bin/python scripts/probe_provider_wire_body.py --mode stage-a` | 1 |
| A2 | PASS | `.venv/bin/python scripts/probe_provider_wire_body.py --mode stage-a --omit-extra-body` | 1 |
| A3 | NOT RUN | Reviewer seat. Not executed here. | — |
| A4 | NOT RUN | Human-gated deploy. Not this seat. | — |
| B1 | PASS | `scripts/run_tests.sh tests/agent/test_thinking_control.py tests/agent/test_auxiliary_client.py tests/agent/test_custom_provider_extra_body.py` | 0 |
| B1a | PASS | same command as B1 | 0 |
| B1b | PASS | same command as B1 | 0 |
| B2 | PASS | same command as B1 (`test_b2_probe_qwen_wire`) | 0 |
| B3 | PASS | same command as B1 (`test_b3_unmapped_effort_logs_once_for_the_call`, `test_b3_probe_unmapped_effort_on_the_wire`) | 0 |
| B4 | PASS | four mutations below, each reverted before the next; none committed. Not re-mutated in fix round 2 (reviewer-executed). | 1, 1, 1, 1 |
| B5 | PASS | same command as B1 (`test_b5_golden_bytes_without_thinking_control`) | 0 |
| B6 | PASS | same command as B1 | 0 |
| B7 | PASS | same command as B1 (`test_b7_partial_map_warns_and_complete_map_does_not`) | 0 |
| B8 | PASS | same command as B1 (`test_b8_requested_model_override_beats_the_main_model`) | 0 |
| B9 | PASS | same command as B1 (`test_b9_iteration_summary_maps_kwargs_on_the_socket`) | 0 |
| B10 | PASS | same command as B1 (`test_b10_nondict_caller_kwargs_reach_the_wire_unchanged`) | 0 |
| §5 | NOT RUN | Deploy notes. Not this seat. | — |

B6 summary from the fix-round 2 re-run of that runner, on `fafc4d90ff`: 3 files, 230 tests passed, 0 failed (runner wall 15.6s). `test_thinking_control.py` 56, `test_auxiliary_client.py` 172, `test_custom_provider_extra_body.py` 2. That run is B1, B1a, B1b, B2, B3, B5, B6, B7, B8, B9, and B10. B4 was not mutated again.

## A1 and A2

Re-run with the Stage B code present and no `thinking_control` block in the probe config. A1 still exits 1:

- `PATH aux FAIL lacks chat_template_kwargs.enable_thinking`
- `PATH main-stream PASS chat_template_kwargs.enable_thinking is false`
- `PATH moa PASS chat_template_kwargs.enable_thinking is false`

Provider `extra_body` still does not reach the auxiliary wire. That is the finding in `BUILD-FINDINGS.md`. The aux task was not given an `extra_body` to force A1 green.

A2's only delta is `--omit-extra-body`. It exits 1 and names all three paths: aux, main-stream, and moa, each `lacks chat_template_kwargs.enable_thinking`.

## B4

Recorded against Stage B commit `d66f297e0c`, before the effort maps were completed. Not re-run in fix round 1. Each mutation was restored (`RESTORED True`). No traceback and no collection error.

1. Raw effort, skipping the map lookup. `.venv/bin/python -m pytest tests/agent/test_thinking_control.py::test_b1_builders_map_effort_and_drop_legacy_reasoning -q --tb=line -x` → exit 1. `AssertionError` on `test_b1_builders_map_effort_and_drop_legacy_reasoning[low-ds4-aux]`: body was `{'thinking': True, 'reasoning_effort': 'low'}` against `{'thinking': True}`. Then `.venv/bin/python scripts/probe_provider_wire_body.py --mode stage-b --reasoning high --thinking-control qwen --paths aux` → exit 1. `PATH aux FAIL expected reasoning_effort xhigh and never high, got ctk={'enable_thinking': True, 'reasoning_effort': 'high'}`.
2. Legacy `reasoning` left in the body. Same B1 pytest command → exit 1. `AssertionError` on `[none-qwen-aux]`: `'reasoning'` still in `{'reasoning': {'enabled': False}, 'chat_template_kwargs': {'enable_thinking': False}}`.
3. Merge swapped to `{**existing, **generated}`. `.venv/bin/python -m pytest tests/agent/test_thinking_control.py::test_b1b_caller_kwargs_win_and_merge -q --tb=line -x` → exit 1. `AssertionError` on `[aux]`: `{'enable_thinking': False}` != `{'enable_thinking': True}`.
4. Both `apply_thinking_control` calls removed from `agent/transports/chat_completions.py` only. `.venv/bin/python scripts/probe_provider_wire_body.py --mode stage-b --reasoning none --thinking-control qwen` → exit 1. `PATH aux PASS`, `PATH main-stream FAIL` (`chat_template_kwargs=null`, top-level `reasoning_effort="none"`), `PATH main-nonstream FAIL` (same), `PATH moa PASS`.

## B5

The committed golden bytes are unchanged. They were captured while the engine still matched `fork/main` (see `BUILD-FINDINGS.md`). Comparison parses both bodies and replaces each system message's text with `<system-message>`, then compares every other field exactly. Fix round 2 re-ran this as `test_b5_golden_bytes_without_thinking_control` inside the B1 command (exit 0), not as a separate probe process. That test checks the default probe home and an alternate `HERMES_HOME` with frozen date `2019-07-04`: the captured main-stream system text contains that alternate home and `Thursday, July 04, 2019`, and is not the committed golden's system text.

## B7

The load-time warning was not changed. It still names every `VALID_REASONING_EFFORTS` value absent from the map. The test now checks the corrected maps:

- `effort_map: {low: low}` logs one warning, `providers.stub.thinking_control: effort_map is missing efforts minimal, medium, high, xhigh, max, ultra`.
- The corrected Qwen map (`minimal: low`, `low: low`, `medium: medium`, `high: xhigh`, `xhigh: xhigh`, `max: xhigh`, `ultra: xhigh`) logs no such warning.
- The corrected DS4 map (`minimal: high`, `low: high`, `medium: high`, `high: high`, `xhigh: max`, `max: max`, `ultra: max`) logs no such warning.

## B8, B9, B10

Re-run on `fafc4d90ff` with the same runner as B1. Exit 0.

- B8: config main model `x-ai/grok-main`, `agent.reasoning_effort: high`, override `spark-qwen: none`. Aux and MoA (`task="moa_reference"`) bodies for `spark-qwen` are `{enable_thinking: false}`. `spark-plain`, which has no override, is `{enable_thinking: true, reasoning_effort: xhigh}`. An explicit caller `reasoning_config` of `low` still wins over the override.
- B9: `handle_max_iterations` against a `127.0.0.1` stub. The summary POST carries `chat_template_kwargs: {enable_thinking: true, reasoning_effort: xhigh}` for effort `high` on the Qwen map. No top-level `reasoning` or `reasoning_effort`.
- B10: caller `chat_template_kwargs: "x"` is still `"x"` on the aux body, and one WARNING from `agent.thinking_control` names provider `stub`.

A1 remains FAIL. Provider `extra_body` still does not reach the auxiliary wire. See `BUILD-FINDINGS.md`.
