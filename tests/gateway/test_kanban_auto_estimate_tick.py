"""Tests for the gateway dispatcher's auto-estimate-on-create tick (t_5716d9c5).

Mirrors ``tests/gateway/test_kanban_auto_decompose_live.py``'s settings-
resolution tests, plus functional coverage of ``_auto_estimate_tick`` itself:
draining ``estimate_status='pending'`` tasks, stamping the concrete
model/provider/effort pick onto the same columns the manual board picker
writes, marking failures without retrying them, respecting the per-tick cap,
and never clobbering a manual override that raced in ahead of the tick.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gateway import kanban_watchers as kw
from hermes_cli import kanban_db as kb


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


# ---------------------------------------------------------------------------
# Settings resolution — same live-re-read + fail-safe discipline as
# _resolve_auto_decompose_settings.
# ---------------------------------------------------------------------------


def test_resolve_auto_estimate_settings_enabled_by_default_when_key_absent():
    enabled, per_tick = kw._resolve_auto_estimate_settings(lambda: {"kanban": {}})
    assert enabled is True
    assert per_tick == 5


def test_resolve_auto_estimate_settings_disabled_when_flag_false():
    enabled, _ = kw._resolve_auto_estimate_settings(
        lambda: {"kanban": {"auto_estimate_on_create": False}}
    )
    assert enabled is False


def test_resolve_auto_estimate_settings_custom_per_tick():
    _, per_tick = kw._resolve_auto_estimate_settings(
        lambda: {"kanban": {"auto_estimate_per_tick": 2}}
    )
    assert per_tick == 2


def test_resolve_auto_estimate_settings_fails_safe_on_config_error():
    def _boom():
        raise RuntimeError("config unreadable")

    enabled, per_tick = kw._resolve_auto_estimate_settings(_boom)
    assert enabled is False
    assert per_tick == 5


# ---------------------------------------------------------------------------
# _auto_estimate_tick — functional, against a real (temp) kanban DB.
# ---------------------------------------------------------------------------


def _fake_ok_result(*, model="deepseek-v4-flash", provider="kevin-spark", effort="low"):
    return {
        "ok": True,
        "est_tokens": 8000,
        "complexity": "S",
        "lane": "local",
        "rationale": "small localized edit",
        "model": "aux-mini",
        "risky": False,
        "local_readiness": {"any_ready": True},
        "suggestion": {
            "lane": "local",
            "provider": provider,
            "model": model,
            "label": f"DS4 · {model}",
            "effort": effort,
            "why": "small/scoped — local is enough",
            "local_ok": True,
            "alternatives": [],
        },
    }


def test_auto_estimate_tick_stamps_model_and_effort(kanban_home, monkeypatch):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="tweak a label", assignee="alice")
    finally:
        conn.close()

    from hermes_cli import kanban_estimate as est
    monkeypatch.setattr(est, "run_estimate", lambda title, body: _fake_ok_result())

    processed = kw._auto_estimate_tick(5)
    assert processed == 1

    conn = kb.connect()
    try:
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "done"
        assert task.model_override == "deepseek-v4-flash"
        assert task.provider_override == "kevin-spark"
        assert task.reasoning_effort == "low"
        kinds = [e.kind for e in kb.list_events(conn, tid)]
        assert "estimated" in kinds
    finally:
        conn.close()


def test_auto_estimate_tick_marks_failed_without_retry(kanban_home, monkeypatch):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="vague ask", assignee="alice")
    finally:
        conn.close()

    from hermes_cli import kanban_estimate as est
    monkeypatch.setattr(
        est, "run_estimate",
        lambda title, body: {"ok": False, "reason": "could not parse an estimate from the model"},
    )

    processed = kw._auto_estimate_tick(5)
    assert processed == 1

    conn = kb.connect()
    try:
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "failed"
        assert task.model_override is None
        kinds = [e.kind for e in kb.list_events(conn, tid)]
        assert "estimate_failed" in kinds
        # Must not still be queued — a failed estimate is never retried.
        assert tid not in [t.id for t in kb.list_tasks_needing_estimate(conn, limit=10)]
    finally:
        conn.close()

    # A second tick must be a no-op for this task (no re-attempt).
    calls = {"n": 0}

    def _count_and_fail(title, body):
        calls["n"] += 1
        return {"ok": False, "reason": "still broken"}

    monkeypatch.setattr(est, "run_estimate", _count_and_fail)
    kw._auto_estimate_tick(5)
    assert calls["n"] == 0


def test_auto_estimate_tick_respects_per_tick_cap(kanban_home, monkeypatch):
    conn = kb.connect()
    try:
        ids = [
            kb.create_task(conn, title=f"task {i}", assignee="alice")
            for i in range(3)
        ]
    finally:
        conn.close()

    from hermes_cli import kanban_estimate as est
    monkeypatch.setattr(est, "run_estimate", lambda title, body: _fake_ok_result())

    processed = kw._auto_estimate_tick(1)
    assert processed == 1

    conn = kb.connect()
    try:
        statuses = {tid: kb.get_task(conn, tid).estimate_status for tid in ids}
    finally:
        conn.close()
    assert sorted(statuses.values()) == ["done", "pending", "pending"]


def test_auto_estimate_tick_never_clobbers_a_racing_manual_override(kanban_home, monkeypatch):
    """A human clicking the board picker while the tick's LLM call is
    in-flight must win — auto-estimate only fills in what's still unset."""
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="race me", assignee="alice")
    finally:
        conn.close()

    from hermes_cli import kanban_estimate as est

    def _fake_with_race(title, body):
        # Simulate a human picker write landing between the LLM call and
        # this tick's own re-fetch-before-write.
        race_conn = kb.connect()
        try:
            kb.set_model_override(race_conn, tid, "sonnet", provider="claude-acp")
        finally:
            race_conn.close()
        return _fake_ok_result(model="deepseek-v4-flash", provider="kevin-spark")

    monkeypatch.setattr(est, "run_estimate", _fake_with_race)
    kw._auto_estimate_tick(5)

    conn = kb.connect()
    try:
        task = kb.get_task(conn, tid)
        assert task.model_override == "sonnet"
        assert task.provider_override == "claude-acp"
        # The estimate itself still completed (recorded for provenance) —
        # only the model/provider stamp was skipped.
        assert task.estimate_status == "done"
    finally:
        conn.close()


def test_auto_estimate_tick_skips_when_disabled(kanban_home, monkeypatch):
    """Belt-and-suspenders: a caller that doesn't consult
    _resolve_auto_estimate_settings at all (this test calls the tick
    directly) still only processes what's in the pending queue — this
    documents that gating happens at the call site, not inside the tick."""
    conn = kb.connect()
    try:
        kb.create_task(conn, title="untouched", assignee="alice", auto_estimate=False)
    finally:
        conn.close()

    from hermes_cli import kanban_estimate as est
    calls = {"n": 0}

    def _count(title, body):
        calls["n"] += 1
        return _fake_ok_result()

    monkeypatch.setattr(est, "run_estimate", _count)
    processed = kw._auto_estimate_tick(5)
    assert processed == 0
    assert calls["n"] == 0
