"""Proof tests for model-failover chain: two-strike demote, cooldown, sticky revert (P2)."""

from __future__ import annotations

import json
from pathlib import Path

from agent.model_failover import (
    FailClass,
    FailoverConfig,
    ModelFailoverPolicy,
    classify_http_status,
)


def _policy(tmp_path: Path, **overrides) -> ModelFailoverPolicy:
    cfg = FailoverConfig(
        preferred_provider="xai",
        preferred_model="grok-4.5",
        chain=[
            {"provider": "openrouter", "model": "anthropic/claude-sonnet-4"},
            {"provider": "openai", "model": "gpt-4o"},
        ],
        strikes_to_demote=2,
        cooldown_sec=60.0,
        sustained_failover_alert_sec=100.0,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    pol = ModelFailoverPolicy(
        cfg,
        clock=now,
        log_path=tmp_path / "route.jsonl",
        alert_path=tmp_path / "alert.json",
    )
    pol._clock_state = clock  # type: ignore[attr-defined]
    return pol


def test_classify_402_429():
    assert classify_http_status(402) == FailClass.BILLING
    assert classify_http_status(429) == FailClass.RATE_LIMIT
    assert classify_http_status(503) == FailClass.SERVER


def test_two_strikes_demote_then_cooldown_skip(tmp_path: Path):
    pol = _policy(tmp_path)
    clock = pol._clock_state  # type: ignore[attr-defined]

    assert pol.record_failure("xai", FailClass.RATE_LIMIT) is False  # strike 1
    assert pol.in_cooldown("xai") is False

    assert pol.record_failure("xai", FailClass.BILLING) is True  # strike 2 → demote
    assert pol.in_cooldown("xai") is True

    # During cooldown, select must not re-burn preferred
    picked = pol.select()
    assert picked is not None
    assert picked["provider"] == "openrouter"

    # Advance halfway — still cooldown
    clock["t"] = 30.0
    assert pol.in_cooldown("xai") is True
    assert pol.select()["provider"] == "openrouter"

    # Decisions logged
    assert (tmp_path / "route.jsonl").is_file()
    lines = (tmp_path / "route.jsonl").read_text(encoding="utf-8").strip().splitlines()
    actions = [json.loads(l)["action"] for l in lines]
    assert "demote" in actions
    assert "cooldown_skip" in actions


def test_timeout_failover_within_chain(tmp_path: Path):
    pol = _policy(tmp_path)
    pol.record_failure("xai", FailClass.TIMEOUT)
    pol.record_failure("xai", FailClass.TIMEOUT)
    picked = pol.select()
    assert picked["provider"] == "openrouter"

    # openrouter also dies
    pol.record_failure("openrouter", FailClass.SERVER, model="anthropic/claude-sonnet-4")
    pol.record_failure("openrouter", FailClass.SERVER)
    picked = pol.select()
    assert picked["provider"] == "openai"


def test_sticky_auto_revert_after_probe(tmp_path: Path):
    pol = _policy(tmp_path)
    clock = pol._clock_state  # type: ignore[attr-defined]

    pol.record_failure("xai", FailClass.RATE_LIMIT)
    pol.record_failure("xai", FailClass.RATE_LIMIT)
    assert pol.select()["provider"] == "openrouter"

    clock["t"] = 61.0  # cooldown expired
    assert pol.in_cooldown("xai") is False

    # Probe fails → stay on fallback
    assert pol.maybe_revert(probe=lambda p, m: False) is False
    assert pol.active["provider"] == "openrouter"

    clock["t"] = 100.0
    assert pol.maybe_revert(probe=lambda p, m: True) is True
    assert pol.active["provider"] == "xai"
    assert pol.active["model"] == "grok-4.5"

    actions = [d.action for d in pol.decisions]
    assert "revert" in actions


def test_sustained_failover_alerts(tmp_path: Path):
    pol = _policy(tmp_path, sustained_failover_alert_sec=50.0)
    clock = pol._clock_state  # type: ignore[attr-defined]

    pol.record_failure("xai", FailClass.BILLING)
    pol.record_failure("xai", FailClass.BILLING)
    pol.mark_on_fallback("openrouter", model="anthropic/claude-sonnet-4")

    clock["t"] = 40.0
    assert pol.check_sustained_failover() is False

    clock["t"] = 55.0
    assert pol.check_sustained_failover() is True
    alert = json.loads((tmp_path / "alert.json").read_text(encoding="utf-8"))
    assert alert["status"] == "alert"
    assert alert["preferred_provider"] == "xai"
    assert "fallback" in alert["message"].lower()


def test_record_success_clears_strikes(tmp_path: Path):
    pol = _policy(tmp_path)
    pol.record_failure("xai", FailClass.TIMEOUT)
    assert pol._state("xai").strikes == 1
    pol.record_success("xai")
    assert pol._state("xai").strikes == 0
    # Two lifetime failures far apart should not demote after success reset
    pol.record_failure("xai", FailClass.TIMEOUT)
    assert pol.in_cooldown("xai") is False


def test_no_retry_downed_provider_during_cooldown(tmp_path: Path):
    """Simulated 402/429/timeout: does not retry downed provider during cooldown."""
    pol = _policy(tmp_path)
    for fc in (FailClass.BILLING, FailClass.RATE_LIMIT, FailClass.TIMEOUT):
        pol = _policy(tmp_path)
        pol.record_failure("xai", fc)
        demoted = pol.record_failure("xai", fc)
        assert demoted is True
        for _ in range(5):
            picked = pol.select()
            assert picked is not None
            assert picked["provider"] != "xai"
