# Build report — local provider thinking control

Branch `ryan/local-thinking-control`. Stage B commit `d66f297e0c`. Fix round 1 commit `9d4cda5d56`. Probe and fixtures are `c6a0b05701` and `6a513800bb`. Interpreter `.venv/bin/python` (Python 3.11.15). Nothing was pushed. A4 and section 5 were not run.

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
| B4 | PASS | four mutations below, each reverted before the next; none committed | 1, 1, 1, 1 |
| B5 | PASS | same command as B1 (`test_b5_golden_bytes_without_thinking_control`). Also `HERMES_PROBE_HOME=/tmp/hermes-thinking-control-probe-alt.W0k7TM HERMES_PROBE_FROZEN_NOW=2019-07-04T01:02:03+00:00 .venv/bin/python scripts/probe_provider_wire_body.py --mode golden --check-golden tests/fixtures/provider_wire_body/golden` | 0 |
| B6 | PASS | same command as B1 | 0 |
| B7 | PASS | same command as B1 (`test_b7_partial_map_warns_and_complete_map_does_not`) | 0 |
| §5 | NOT RUN | Deploy notes. Not this seat. | — |

B6 summary from the fix-round re-run of that runner: 3 files, 227 tests passed, 0 failed (runner wall 15.6s). `test_thinking_control.py` 53, `test_auxiliary_client.py` 172, `test_custom_provider_extra_body.py` 2.

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

The committed golden bytes are unchanged. They were captured while the engine still matched `fork/main` (see `BUILD-FINDINGS.md`). Comparison parses both bodies and replaces each system message's text with `<system-message>`, then compares every other field exactly. The default probe home `/tmp/hermes-thinking-control-probe` and frozen date `2026-09-29` pass. The alternate command in the B5 row (different `HERMES_HOME`, frozen date `2019-07-04`) also exits 0. The test checks that the captured main-stream system text contains that alternate home and `Thursday, July 04, 2019`, and that this text is not the committed golden's system text.

## B7

The load-time warning was not changed. It still names every `VALID_REASONING_EFFORTS` value absent from the map. The test now checks the corrected maps:

- `effort_map: {low: low}` logs one warning, `providers.stub.thinking_control: effort_map is missing efforts minimal, medium, high, xhigh, max, ultra`.
- The corrected Qwen map (`minimal: low`, `low: low`, `medium: medium`, `high: xhigh`, `xhigh: xhigh`, `max: xhigh`, `ultra: xhigh`) logs no such warning.
- The corrected DS4 map (`minimal: high`, `low: high`, `medium: high`, `high: high`, `xhigh: max`, `max: max`, `ultra: max`) logs no such warning.

A1 remains FAIL. Provider `extra_body` still does not reach the auxiliary wire. See `BUILD-FINDINGS.md`.
