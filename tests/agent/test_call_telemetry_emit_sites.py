"""MESH-TEL-2b: the two chokepoints that actually emit model-call telemetry.

One line = one model CALL, so the emits sit where a call *completes*, not
where a turn or a run does:

* ``agent/auxiliary_client.py::_validate_llm_response`` — the single
  response-validation chokepoint every non-streaming aux response passes
  through exactly once (the same one ``record_aux_usage`` already uses);
* ``agent/conversation_loop.py`` at the success break, with failures coming
  from its counterpart ``run_agent.py::_invoke_api_request_error_hook``, the
  single funnel for all three main-loop failure surfaces.

Deliberately NOT per provider adapter — a provider-by-provider wiring is what
leaves a lane silently unattributed when a new adapter lands.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.call_telemetry import iter_records


@pytest.fixture
def rows():
    """Read the isolated per-test telemetry store (pinned by tests/conftest.py)."""
    root = Path(os.environ["T1000_TELEMETRY_DIR"])

    def _read() -> list[dict]:
        return list(iter_records(root))

    return _read


def _openai_usage(prompt=1200, completion=300, cached=200):
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
    )


def _aux_response(model="spark/gpt-oss:120b", usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
        model=model,
        usage=usage,
    )


# --------------------------------------------------------------------------
# chokepoint 1: the auxiliary client
# --------------------------------------------------------------------------


def test_aux_chokepoint_records_one_row_per_response(rows):
    from agent.auxiliary_client import _validate_llm_response

    _validate_llm_response(
        _aux_response(usage=_openai_usage()), "vision", provider="spark"
    )

    written = rows()
    assert len(written) == 1
    row = written[0]
    assert row["provider"] == "spark"
    assert row["task"] == "vision"
    # The model comes off the RESPONSE, so it survives the aux fallback chain.
    assert row["model"] == "spark/gpt-oss:120b"
    assert row["outcome"] == "ok"
    assert row["tokens_available"] is True
    assert row["input_tokens"] == 1000
    assert row["cache_read_tokens"] == 200
    assert row["output_tokens"] == 300


def test_aux_chokepoint_records_a_row_even_without_usage(rows):
    """Attribution (which model ran) must survive a usage-less response."""
    from agent.auxiliary_client import _validate_llm_response

    _validate_llm_response(_aux_response(usage=None), "compression", provider="mbp-ollama")

    row = rows()[0]
    assert row["tokens_available"] is False
    assert row["total_tokens"] is None
    assert (row["provider"], row["model"]) == ("mbp-ollama", "spark/gpt-oss:120b")


def test_aux_chokepoint_is_hit_once_per_call_not_once_per_task(rows):
    from agent.auxiliary_client import _validate_llm_response

    for _ in range(3):
        _validate_llm_response(_aux_response(usage=_openai_usage()), "vision")

    assert len(rows()) == 3


def test_aux_chokepoint_never_breaks_the_call(rows):
    """Accounting must never take down an aux call — same contract as record_aux_usage."""
    from agent.auxiliary_client import _validate_llm_response

    class Exploding:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    response = _aux_response(usage=Exploding())
    assert _validate_llm_response(response, "vision") is response


def test_aux_chokepoint_forwards_the_acp_tokens_available_flag(rows):
    """A recovered ACP count must not be nulled by the tokenless default."""
    from agent.auxiliary_client import _validate_llm_response
    from agent.usage_pricing import acp_usage_namespace

    usage = acp_usage_namespace(
        {
            "inputTokens": 2,
            "outputTokens": 4,
            "cachedReadTokens": 19467,
            "cachedWriteTokens": 16113,
            "totalTokens": 35586,
        }
    )
    _validate_llm_response(
        _aux_response(model="opus[1m]", usage=usage), "vision", provider="claude-acp"
    )

    row = rows()[0]
    assert row["tokens_available"] is True
    assert row["total_tokens"] == 35586


# --------------------------------------------------------------------------
# chokepoint 2: the main conversation loop
# --------------------------------------------------------------------------


def _make_tool_defs(*names):
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]


@pytest.fixture
def agent():
    from run_agent import AIAgent

    with (
        patch(
            "run_agent.get_tool_definitions", return_value=_make_tool_defs("web_search")
        ),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
    a.client = MagicMock()
    a._cached_system_prompt = "You are helpful."
    a._use_prompt_caching = False
    a.compression_enabled = False
    a.save_trajectories = False
    a._api_max_retries = 1
    return a


def _run(agent, prompt="hello"):
    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        return agent.run_conversation(prompt)


def _mock_completion(usage=None, model="test/model"):
    message = SimpleNamespace(
        content="Final answer",
        tool_calls=None,
        reasoning=None,
        reasoning_content=None,
        reasoning_details=None,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        model=model,
        usage=usage,
    )


def test_main_loop_records_a_row_on_a_successful_call(agent, rows):
    agent.provider = "spark"
    agent.model = "gpt-oss:120b"
    agent.reasoning_config = {"enabled": True, "effort": "high"}
    agent.client.chat.completions.create.return_value = _mock_completion(
        usage=_openai_usage(), model="gpt-oss:120b-actual"
    )

    result = _run(agent)
    assert result["completed"] is True

    main_rows = [r for r in rows() if r["task"] == "main_loop"]
    assert len(main_rows) == 1
    row = main_rows[0]
    assert row["provider"] == "spark"
    # Schema: the slug that ACTUALLY ran wins over the configured one.
    assert row["model"] == "gpt-oss:120b-actual"
    assert row["effort"] == "high"
    assert row["outcome"] == "ok"
    assert row["tokens_available"] is True
    assert row["output_tokens"] == 300
    assert isinstance(row["wall_ms"], int)


def test_main_loop_leaves_effort_null_when_reasoning_is_disabled(agent, rows):
    agent.provider = "spark"
    agent.reasoning_config = {"enabled": False, "effort": "high"}
    agent.client.chat.completions.create.return_value = _mock_completion(
        usage=_openai_usage()
    )

    _run(agent)

    assert [r for r in rows() if r["task"] == "main_loop"][0]["effort"] is None


def test_main_loop_records_a_row_when_the_response_carries_no_usage(agent, rows):
    agent.provider = "kevin-spark"
    agent.model = "deepseek-v4-flash"
    agent.client.chat.completions.create.return_value = _mock_completion(usage=None)

    _run(agent)

    row = [r for r in rows() if r["task"] == "main_loop"][0]
    assert row["outcome"] == "ok"
    assert row["tokens_available"] is False
    assert row["total_tokens"] is None
    assert row["provider"] == "kevin-spark"


def test_main_loop_emits_one_row_per_api_call_not_per_turn(agent, rows):
    """A turn that tool-calls once makes two API calls — and two rows."""
    tool_call = SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(name="web_search", arguments="{}"),
    )
    first = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[tool_call],
                    reasoning=None,
                    reasoning_content=None,
                    reasoning_details=None,
                ),
                finish_reason="tool_calls",
            )
        ],
        model="test/model",
        usage=_openai_usage(),
    )
    agent.client.chat.completions.create.side_effect = [
        first,
        _mock_completion(usage=_openai_usage()),
    ]

    with patch.object(agent, "_execute_tool_calls", return_value=[
        {"role": "tool", "tool_call_id": "call_1", "content": "result"}
    ]):
        _run(agent)

    assert len([r for r in rows() if r["task"] == "main_loop"]) == 2


def test_main_loop_records_an_error_row_when_the_provider_raises(agent, rows):
    agent.provider = "spark"
    agent.model = "gpt-oss:120b"
    agent.client.chat.completions.create.side_effect = RuntimeError("upstream exploded")

    _run(agent)

    error_rows = [r for r in rows() if r["outcome"] != "ok"]
    assert error_rows, "a failed provider call must still be attributed"
    row = error_rows[0]
    assert row["outcome"] == "error"
    assert row["error_class"] == "RuntimeError"
    assert row["provider"] == "spark"
    # A failure has no usage — null tokens, never 0.
    assert row["tokens_available"] is False
    assert row["total_tokens"] is None


# --------------------------------------------------------------------------
# outcome mapping on the failure funnel
# --------------------------------------------------------------------------


def _invoke_error_hook(agent, **overrides):
    kwargs = dict(
        task_id="task-1",
        turn_id="turn-1",
        api_request_id="api-1",
        api_call_count=1,
        api_start_time=0.0,
        api_kwargs=None,
        error_type="RuntimeError",
        error_message="boom",
    )
    kwargs.update(overrides)
    agent._invoke_api_request_error_hook(**kwargs)


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"reason": "content_policy_blocked"}, "refusal"),
        ({"reason": "timeout"}, "timeout"),
        ({"error_type": "APITimeoutError"}, "timeout"),
        ({"reason": "rate_limit"}, "error"),
        ({}, "error"),
    ],
)
def test_failure_funnel_maps_reason_to_a_schema_outcome(agent, rows, overrides, expected):
    _invoke_error_hook(agent, **overrides)
    assert rows()[0]["outcome"] == expected


def test_failure_funnel_emits_without_a_lifecycle_hook_configured(agent, rows, monkeypatch):
    """Telemetry must not depend on the user having wired an api_request_error hook.

    The emit sits above the has_hook() early-return for exactly this reason.
    """
    monkeypatch.setattr("hermes_cli.lifecycle.has_hook", lambda name: False)

    _invoke_error_hook(agent)

    assert len(rows()) == 1
    assert rows()[0]["outcome"] == "error"


def test_failure_funnel_never_raises(agent, rows):
    class Boom:
        def __str__(self):
            raise RuntimeError("nope")

    # A provider attribute that explodes must not escape the accounting hook.
    agent.provider = Boom()
    _invoke_error_hook(agent)


# --------------------------------------------------------------------------
# the aux chokepoint's failure counterpart + the fields only it can supply
# --------------------------------------------------------------------------


def _fake_aux_route(
    monkeypatch, response, *, provider="custom", model="m",
    base_url="http://localhost:8001/v1",
):
    """Wire call_llm to a fake client so the REAL aux path runs end to end.

    Nothing about telemetry is stubbed here — the decorator, _build_call_kwargs
    and _validate_llm_response all execute, which is the point: the emit has to
    survive the actual call path, not a hand-built context.
    """
    from agent import auxiliary_client as ac

    class _Completions:
        def create(self, **kwargs):
            if isinstance(response, BaseException):
                raise response
            return response

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=_Completions()),
        base_url=base_url,
    )
    monkeypatch.setattr(
        ac,
        "_resolve_task_provider_model",
        lambda *a, **k: (provider, model, base_url, "key", "chat_completions"),
    )
    monkeypatch.setattr(ac, "_get_cached_client", lambda *a, **k: (fake_client, model))
    return ac


def test_aux_row_carries_wall_ms_and_the_effort_that_actually_went_out(monkeypatch, rows):
    ac = _fake_aux_route(monkeypatch, _aux_response(usage=_openai_usage()))

    ac.call_llm(
        task="judge",
        provider="custom",
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        reasoning_config={"enabled": True, "effort": "high"},
    )

    row = rows()[0]
    assert row["task"] == "judge"
    assert row["effort"] == "high"
    assert isinstance(row["wall_ms"], int)
    assert row["outcome"] == "ok"


def test_aux_row_leaves_effort_null_when_reasoning_is_disabled(monkeypatch, rows):
    ac = _fake_aux_route(monkeypatch, _aux_response(usage=_openai_usage()))

    ac.call_llm(
        task="compression",
        provider="custom",
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        reasoning_config={"enabled": False, "effort": "high"},
    )

    assert rows()[0]["effort"] is None


def test_aux_failure_records_exactly_one_row_with_the_classifier_taxonomy(monkeypatch, rows):
    """A judge that times out must not read as a healthy lane (t_4123e041).

    ``_validate_llm_response`` only sees calls that came back, so without this
    counterpart every aux lane reports a 100% success rate. One row per LOGICAL
    call, however many attempts the fallback chain burned.
    """
    ac = _fake_aux_route(monkeypatch, TimeoutError("Request timed out."))

    with pytest.raises(Exception):
        ac.call_llm(
            task="judge",
            provider="custom",
            model="m",
            messages=[{"role": "user", "content": "hi"}],
        )

    written = rows()
    assert len(written) == 1, f"expected one row per logical aux call, got {written}"
    row = written[0]
    assert row["task"] == "judge"
    assert row["outcome"] == "timeout"
    # error_classifier's taxonomy, not a hand-rolled one.
    assert row["error_class"] == "timeout"
    # A failure has no usage — null tokens, never 0.
    assert row["tokens_available"] is False
    assert row["total_tokens"] is None
    assert isinstance(row["wall_ms"], int)


def test_operator_interrupt_is_not_recorded_as_a_model_failure(rows):
    """Ctrl-C / cancellation is the operator stopping work, not a bad lane."""
    from agent import auxiliary_client as ac

    @ac._relay_auxiliary_call
    def _interrupted(task, **_kw):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _interrupted("compression")

    assert rows() == []


def test_aux_failure_telemetry_never_swallows_the_call_s_error(monkeypatch, rows):
    """Recording a failure must not change what the caller sees.

    The aux client already normalises transport errors into the SDK's own
    ``APIConnectionError`` before re-raising; telemetry sits inside that path
    and must leave it exactly as it found it — the caller still gets an
    exception, and it is not one the accounting code invented.
    """
    from openai import APIConnectionError

    ac = _fake_aux_route(monkeypatch, ValueError("upstream said no"))

    with pytest.raises(APIConnectionError):
        ac.call_llm(
            task="vision",
            provider="custom",
            model="m",
            messages=[{"role": "user", "content": "hi"}],
        )

    # Two same-provider retries plus a fallback sweep, still ONE row: the emit
    # is per logical call, not per physical attempt.
    assert len(rows()) == 1
    # error_classifier folds connection failures into its `timeout` reason —
    # taking its word for it is the point, whatever the label.
    assert rows()[0]["outcome"] != "ok"


# --------------------------------------------------------------------------
# double counting: the card's named hazard
# --------------------------------------------------------------------------


def test_caller_owned_scope_suppresses_the_aux_row(rows):
    from agent.auxiliary_client import _validate_llm_response, caller_records_telemetry

    with caller_records_telemetry():
        _validate_llm_response(_aux_response(usage=_openai_usage()), "moa_aggregator")

    assert rows() == []
    # ...and the suppression is scoped, not sticky.
    _validate_llm_response(_aux_response(usage=_openai_usage()), "vision")
    assert len(rows()) == 1


def test_moa_acting_aggregator_row_is_left_to_the_main_loop(monkeypatch, tmp_path):
    """The acting aggregator is ONE provider call that crosses BOTH chokepoints.

    conversation_loop emits for the response MoA hands back, so the aux row for
    that same call has to be suppressed or every non-streaming MoA turn doubles
    the aggregator's tokens. Advisors must NOT be suppressed — the main loop's
    emit reads the raw (aggregator-only) usage, so the aux row is their only one.
    """
    from agent import auxiliary_client as ac

    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "moa:\n"
        "  default_preset: review\n"
        "  presets:\n"
        "    review:\n"
        "      reference_models:\n"
        "        - provider: openai-codex\n"
        "          model: gpt-5.5\n"
        "      aggregator:\n"
        "        provider: openrouter\n"
        "        model: anthropic/claude-opus-4.8\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))

    owned_by_caller = {}

    def fake_call_llm(**kwargs):
        owned_by_caller[kwargs["task"]] = ac._TELEMETRY_OWNED_BY_CALLER.get()
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok", tool_calls=[]),
                    finish_reason="stop",
                )
            ],
            usage=None,
            model="fake-model",
        )

    monkeypatch.setattr("agent.moa_loop.call_llm", fake_call_llm)
    from agent.moa_loop import MoAChatCompletions

    MoAChatCompletions("review").create(
        messages=[{"role": "user", "content": "q"}], tools=[]
    )

    assert owned_by_caller["moa_aggregator"] is True
    assert owned_by_caller["moa_reference"] is False


def test_main_loop_row_stays_aggregator_only_on_a_moa_turn(agent, rows):
    """Advisor tokens are already recorded at the aux chokepoint.

    conversation_loop folds them into ``canonical_usage`` for the session's
    reported counts, but the telemetry row deliberately reads the RAW
    ``response.usage`` — otherwise advisor spend lands in both places.
    """
    from agent.usage_pricing import CanonicalUsage

    agent.provider = "moa"
    agent.client.consume_reference_usage = MagicMock(
        return_value=(CanonicalUsage(input_tokens=50000, output_tokens=9000), 0.42)
    )
    agent.client.chat.completions.create.return_value = _mock_completion(
        usage=_openai_usage()
    )

    _run(agent)

    row = [r for r in rows() if r["task"] == "main_loop"][0]
    assert row["input_tokens"] == 1000
    assert row["output_tokens"] == 300
    assert row["cache_read_tokens"] == 200


def test_failure_funnel_prefers_the_classifier_reason_for_error_class(agent, rows):
    _invoke_error_hook(agent, error_type="APIStatusError", reason="rate_limit")
    assert rows()[0]["error_class"] == "rate_limit"


def test_failure_funnel_keeps_the_exception_type_when_the_classifier_shrugs(agent, rows):
    """"unknown" tells an operator nothing; the exception's own type does."""
    _invoke_error_hook(agent, error_type="RuntimeError", reason="unknown")
    assert rows()[0]["error_class"] == "RuntimeError"


# ─────────────── provider identity: "auto" is not a lane ────────────────
#
# Every aux task on a stock desk is configured ``provider: auto`` and a worker
# launched ``--provider kevin-spark`` arrives here as bare ``custom``. Both are
# routing decisions, not identities — recorded raw they make "how much deepseek
# vs 120b, by lane" unanswerable, which is the question the store exists for.


@pytest.fixture
def desk(monkeypatch, tmp_path):
    """A config with two named local providers, like the real desk has."""
    from agent import call_telemetry as ct

    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "providers:\n"
        "  flashbox:\n"
        "    base_url: http://127.0.0.1:8889/v1\n"
        "    model: deepseek-v4-flash\n"
        "  ollamabox:\n"
        "    base_url: http://127.0.0.1:11434/v1\n"
        "    model: hermes3:8b\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    ct._IDENTITY_CACHE.clear()
    yield ct
    ct._IDENTITY_CACHE.clear()


@pytest.mark.parametrize("label", ["auto", "custom", "", "unknown", "auxiliary"])
def test_sentinel_labels_are_upgraded_to_the_entry_that_owns_the_endpoint(desk, label):
    assert desk.resolve_provider_identity(
        label, "http://127.0.0.1:8889/v1", "deepseek-v4-flash"
    ) == "custom:flashbox"


def test_two_local_lanes_do_not_collapse_into_one_bucket(desk):
    flash = desk.resolve_provider_identity("auto", "http://127.0.0.1:8889/v1", "x")
    ollama = desk.resolve_provider_identity("auto", "http://127.0.0.1:11434/v1", "y")
    assert flash != ollama, "deepseek vs 120b is unanswerable if both say 'custom'"


@pytest.mark.parametrize("label", ["openrouter", "claude-acp", "nous", "anthropic"])
def test_real_provider_identities_pass_through_untouched(desk, label):
    assert desk.resolve_provider_identity(label, "http://127.0.0.1:8889/v1", "m") == label


def test_unrecoverable_sentinel_keeps_its_original_label(desk):
    """Better a row that says "auto" than one that invents a lane."""
    assert desk.resolve_provider_identity("auto", None, None) == "auto"
    assert desk.resolve_provider_identity("auto", "http://nope.invalid/v1", "m") == "auto"


def test_identity_lookup_is_memoized(desk, monkeypatch):
    """It runs on every model call and reads config from disk — cache or bust."""
    calls = []
    import hermes_cli.runtime_provider as rp

    real = rp.canonical_custom_identity

    def counting(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(rp, "canonical_custom_identity", counting)
    for _ in range(25):
        desk.resolve_provider_identity("auto", "http://127.0.0.1:8889/v1", "m")
    assert len(calls) == 1


def test_identity_resolution_never_raises(desk, monkeypatch):
    import hermes_cli.runtime_provider as rp

    def boom(**kwargs):
        raise RuntimeError("config on fire")

    monkeypatch.setattr(rp, "canonical_custom_identity", boom)
    assert desk.resolve_provider_identity("auto", "http://127.0.0.1:8889/v1", "m") == "auto"


def test_aux_row_records_the_resolved_lane_not_the_auto_sentinel(monkeypatch, rows, desk):
    ac = _fake_aux_route(
        monkeypatch,
        _aux_response(usage=_openai_usage()),
        provider="auto",
        base_url="http://127.0.0.1:11434/v1",
    )

    ac.call_llm(
        task="approval",
        provider="auto",
        model="m",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert rows()[0]["provider"] == "custom:ollamabox"


def test_wall_ms_excludes_the_emit_s_own_work(monkeypatch, rows, desk):
    """wall_ms measures the CALL, not the recording of it.

    The identity lookup reads config on its first miss (~85ms once per route
    per process). Evaluated as a sibling kwarg it lands inside wall_ms and
    inflates exactly one row per lane — in the one field whose job is timing.
    """
    from agent import call_telemetry as ct

    ac = _fake_aux_route(
        monkeypatch,
        _aux_response(usage=_openai_usage()),
        provider="auto",
        base_url="http://127.0.0.1:11434/v1",
    )

    real = ct.resolve_provider_identity

    def slow(*args, **kwargs):
        import time as _t

        _t.sleep(0.25)
        return real(*args, **kwargs)

    monkeypatch.setattr(ct, "resolve_provider_identity", slow)

    ac.call_llm(
        task="approval",
        provider="auto",
        model="m",
        messages=[{"role": "user", "content": "hi"}],
    )

    row = rows()[0]
    assert row["provider"] == "custom:ollamabox", "the slow lookup still ran"
    assert row["wall_ms"] < 250, f"emit work leaked into wall_ms: {row['wall_ms']}ms"
