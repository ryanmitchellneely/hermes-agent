"""MESH-TEL-2c: the ACP lanes must report real tokens, not a hardcoded zero.

``agent/claude_acp_client.py`` and ``agent/copilot_acp_client.py`` used to
build ``SimpleNamespace(prompt_tokens=0, completion_tokens=0, ...)`` after
every turn, so the subscription lanes read as free and any
local-vs-subscription split came out inverted.

The counts were on the wire the whole time: ACP's ``session/prompt`` response
carries ``PromptResponse.usage``, and the clients discarded the result. Probed
live against ``claude-agent-acp`` 0.62.0, a one-word prompt answered with::

    {"stopReason": "end_turn",
     "usage": {"inputTokens": 2, "outputTokens": 4, "cachedReadTokens": 19467,
               "cachedWriteTokens": 16113, "totalTokens": 35586}}

``usage`` is optional in the ACP schema (still marked UNSTABLE), so the
tokenless fallback has to stay honest too: absent usage means
``tokens_available=False``, never a fake zero.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.claude_acp_client import ClaudeACPClient
from agent.copilot_acp_client import CopilotACPClient
from agent.usage_pricing import acp_usage_namespace, normalize_usage

# Verbatim from the live claude-agent-acp 0.62.0 probe.
LIVE_ACP_USAGE = {
    "inputTokens": 2,
    "outputTokens": 4,
    "cachedReadTokens": 19467,
    "cachedWriteTokens": 16113,
    "totalTokens": 35586,
}


# --------------------------------------------------------------------------
# the shape projection
# --------------------------------------------------------------------------


def test_acp_usage_round_trips_through_normalize_usage_without_loss():
    """ACP reports four separate buckets; normalize_usage reads the OpenAI shape."""
    canonical = normalize_usage(
        acp_usage_namespace(LIVE_ACP_USAGE), provider="claude-acp"
    )

    assert canonical.input_tokens == 2
    assert canonical.output_tokens == 4
    assert canonical.cache_read_tokens == 19467
    assert canonical.cache_write_tokens == 16113
    # ACP's own totalTokens sums all four buckets — so must ours.
    assert canonical.total_tokens == LIVE_ACP_USAGE["totalTokens"]


def test_acp_prompt_tokens_are_cache_inclusive():
    """ACP inputTokens EXCLUDES cache; chat-completions prompt_tokens includes it."""
    usage = acp_usage_namespace(LIVE_ACP_USAGE)

    assert usage.prompt_tokens == 2 + 19467 + 16113
    assert usage.completion_tokens == 4
    assert usage.prompt_tokens_details.cached_tokens == 19467
    assert usage.prompt_tokens_details.cache_write_tokens == 16113


def test_thought_tokens_map_to_reasoning():
    usage = acp_usage_namespace({**LIVE_ACP_USAGE, "thoughtTokens": 900})
    assert normalize_usage(usage, provider="claude-acp").reasoning_tokens == 900


@pytest.mark.parametrize("absent", [None, {}, "not-a-dict", []])
def test_absent_usage_is_flagged_unavailable_not_zero(absent):
    """The honest answer for a turn the transport said nothing about."""
    usage = acp_usage_namespace(absent)
    assert usage.tokens_available is False
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0


def test_recovered_usage_is_flagged_available():
    assert acp_usage_namespace(LIVE_ACP_USAGE).tokens_available is True


def test_all_zero_usage_is_flagged_unavailable():
    """A transport that answers with explicit zeros still has no data to report."""
    zeros = {
        "inputTokens": 0,
        "outputTokens": 0,
        "cachedReadTokens": 0,
        "cachedWriteTokens": 0,
        "totalTokens": 0,
    }
    assert acp_usage_namespace(zeros).tokens_available is False


# --------------------------------------------------------------------------
# claude-acp: the client must read the session/prompt result
# --------------------------------------------------------------------------


def _claude_client() -> ClaudeACPClient:
    return ClaudeACPClient(acp_command="/nonexistent/claude-agent-acp", acp_cwd="/tmp")


def test_claude_acp_non_streaming_reports_recovered_tokens(monkeypatch):
    client = _claude_client()
    monkeypatch.setattr(
        client, "_run_prompt", lambda *a, **k: ("hello", "", LIVE_ACP_USAGE)
    )

    completion = client._create_chat_completion(
        model="opus[1m]", messages=[{"role": "user", "content": "hi"}]
    )

    assert completion.usage.prompt_tokens == 35582
    assert completion.usage.completion_tokens == 4
    assert completion.usage.total_tokens == 35586
    assert completion.usage.tokens_available is True


def test_claude_acp_streaming_final_chunk_reports_recovered_tokens(monkeypatch):
    client = _claude_client()
    monkeypatch.setattr(
        client, "_run_prompt", lambda *a, **k: ("hello", "", LIVE_ACP_USAGE)
    )

    chunks = list(
        client._create_chat_completion(
            model="opus[1m]",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
    )

    # The usage-bearing chunk is the trailing one with no choices.
    final = chunks[-1]
    assert final.choices == []
    assert final.usage.total_tokens == 35586
    assert final.usage.tokens_available is True


def test_claude_acp_falls_back_to_unavailable_when_result_omits_usage(monkeypatch):
    """PromptResponse.usage is optional — absent must not become a fake zero."""
    client = _claude_client()
    monkeypatch.setattr(client, "_run_prompt", lambda *a, **k: ("hello", "", None))

    completion = client._create_chat_completion(
        model="opus[1m]", messages=[{"role": "user", "content": "hi"}]
    )

    assert completion.usage.tokens_available is False
    assert completion.usage.total_tokens == 0


def test_claude_acp_run_prompt_returns_usage_from_the_session_prompt_result(
    monkeypatch,
):
    """The regression that mattered: the result used to be thrown away."""
    client = _claude_client()
    calls: list[str] = []

    def fake_request(method, params, **kwargs):
        calls.append(method)
        if method == "session/prompt":
            text_parts = kwargs.get("text_parts")
            if text_parts is not None:
                text_parts.append("ok")
            return {"stopReason": "end_turn", "usage": LIVE_ACP_USAGE}
        return {}

    monkeypatch.setattr(client, "_request_unlocked", fake_request)
    monkeypatch.setattr(client, "_ensure_process_unlocked", lambda **k: None)
    monkeypatch.setattr(client, "_ensure_session_unlocked", lambda **k: None)
    client._session_id = "sess-1"

    text, reasoning, usage = client._run_prompt_unlocked(
        [{"role": "user", "content": "hi"}], timeout_seconds=5
    )

    assert "session/prompt" in calls
    assert text == "ok"
    assert reasoning == ""
    assert usage == LIVE_ACP_USAGE


def test_claude_acp_survives_a_result_that_is_not_a_dict(monkeypatch):
    client = _claude_client()

    def fake_request(method, params, **kwargs):
        return "unexpected-string-result"

    monkeypatch.setattr(client, "_request_unlocked", fake_request)
    monkeypatch.setattr(client, "_ensure_process_unlocked", lambda **k: None)
    monkeypatch.setattr(client, "_ensure_session_unlocked", lambda **k: None)
    client._session_id = "sess-1"

    _, _, usage = client._run_prompt_unlocked(
        [{"role": "user", "content": "hi"}], timeout_seconds=5
    )
    assert usage is None


# --------------------------------------------------------------------------
# copilot-acp
# --------------------------------------------------------------------------


def test_copilot_acp_reports_recovered_tokens_when_the_transport_supplies_them(
    monkeypatch,
):
    """Not verified live (no copilot binary available) — the client reads
    PromptResponse.usage either way, so it is correct in both worlds."""
    client = CopilotACPClient(acp_cwd="/tmp")
    monkeypatch.setattr(
        client, "_run_prompt", lambda *a, **k: ("hello", "", LIVE_ACP_USAGE)
    )

    completion = client._create_chat_completion(
        model="gpt-5", messages=[{"role": "user", "content": "hi"}]
    )

    assert completion.usage.total_tokens == 35586
    assert completion.usage.tokens_available is True


def test_copilot_acp_reports_unavailable_when_the_transport_stays_silent(monkeypatch):
    client = CopilotACPClient(acp_cwd="/tmp")
    monkeypatch.setattr(client, "_run_prompt", lambda *a, **k: ("hello", "", None))

    completion = client._create_chat_completion(
        model="gpt-5", messages=[{"role": "user", "content": "hi"}]
    )

    assert completion.usage.tokens_available is False
    assert completion.usage.prompt_tokens == 0


# --------------------------------------------------------------------------
# the telemetry hand-off
# --------------------------------------------------------------------------


def test_recovered_acp_usage_beats_the_tokenless_default_in_telemetry():
    """claude-acp is in TOKENLESS_PROVIDERS, so recovery must say so explicitly.

    Auto-detection would flag the row ``tokens_available=false`` and null every
    token field — discarding exactly the counts 2c just recovered. The emit
    sites forward the flag the usage object now carries.
    """
    from agent.call_telemetry import build_record

    usage = acp_usage_namespace(LIVE_ACP_USAGE)

    auto = build_record(provider="claude-acp", model="opus[1m]", usage=usage)
    assert auto["tokens_available"] is False, "the default is still tokenless"

    forwarded = build_record(
        provider="claude-acp",
        model="opus[1m]",
        usage=usage,
        tokens_available=usage.tokens_available,
    )
    assert forwarded["tokens_available"] is True
    assert forwarded["input_tokens"] == 2
    assert forwarded["output_tokens"] == 4
    assert forwarded["cache_read_tokens"] == 19467
    assert forwarded["cache_write_tokens"] == 16113
    assert forwarded["total_tokens"] == 35586


def test_tokenless_acp_usage_still_writes_null_tokens():
    from agent.call_telemetry import TOKEN_FIELDS, build_record

    usage = acp_usage_namespace(None)
    record = build_record(
        provider="claude-acp",
        model="opus[1m]",
        usage=usage,
        tokens_available=usage.tokens_available,
    )

    assert record["tokens_available"] is False
    for field in TOKEN_FIELDS:
        assert record[field] is None, f"{field} must be null, not {record[field]!r}"


def test_non_acp_usage_is_untouched_by_the_flag_convention():
    """Every other provider leaves tokens_available absent -> auto-detection."""
    from agent.call_telemetry import build_record

    openai_usage = SimpleNamespace(
        prompt_tokens=1200,
        completion_tokens=300,
        total_tokens=1500,
        prompt_tokens_details=SimpleNamespace(cached_tokens=200),
    )
    record = build_record(
        provider="spark",
        model="gpt-oss:120b",
        usage=openai_usage,
        tokens_available=getattr(openai_usage, "tokens_available", None),
    )

    assert record["tokens_available"] is True
    assert record["total_tokens"] == 1500
