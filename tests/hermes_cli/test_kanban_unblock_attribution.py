"""Park/unpark provenance (t_481edae3): no anonymous de-gating.

Live defect 2026-08-19 (arctic t_b1e5129c): a deliberately parked card was
unblocked 46 seconds later with an EMPTY event payload — human? tool?
dashboard click? The board could not say, and an unattended worker then
produced a wrong-by-construction diff. These tests pin: every 'unblocked'
and 'scheduled' event carries a "by", an explicit author wins, and the
resolver falls back HERMES_KANBAN_EVENT_AUTHOR -> HERMES_PROFILE -> OS user.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest


@pytest.fixture()
def kb(monkeypatch):
    test_home = tempfile.mkdtemp(prefix="kanban_unblock_attribution_")
    monkeypatch.setenv("HERMES_HOME", test_home)
    for mod in list(sys.modules.keys()):
        if mod.startswith("hermes_cli") or mod.startswith("hermes_state") or mod == "hermes_constants":
            del sys.modules[mod]
    from hermes_cli import kanban_db

    return kanban_db


def _last_event(kb_mod, conn, task_id, kind):
    row = conn.execute(
        "SELECT payload FROM task_events WHERE task_id = ? AND kind = ? "
        "ORDER BY id DESC LIMIT 1",
        (task_id, kind),
    ).fetchone()
    import json

    return json.loads(row["payload"]) if row and row["payload"] else {}


def _mk_blocked_task(kb_mod, conn):
    kb_mod.create_board(slug="default", name="Test")
    task_id = kb_mod.create_task(conn, title="t", assignee="worker")
    kb_mod.claim_task(conn, task_id)
    kb_mod.block_task(conn, task_id, reason="park", kind="needs_input")
    return task_id


def test_unblock_records_explicit_author(kb, monkeypatch):
    with kb.connect_closing() as conn:
        task_id = _mk_blocked_task(kb, conn)
        assert kb.unblock_task(conn, task_id, author="dashboard")
        assert _last_event(kb, conn, task_id, "unblocked")["by"] == "dashboard"


def test_unblock_resolves_profile_when_no_author(kb, monkeypatch):
    monkeypatch.setenv("HERMES_PROFILE", "sneaky-worker")
    monkeypatch.delenv("HERMES_KANBAN_EVENT_AUTHOR", raising=False)
    with kb.connect_closing() as conn:
        task_id = _mk_blocked_task(kb, conn)
        assert kb.unblock_task(conn, task_id)
        assert _last_event(kb, conn, task_id, "unblocked")["by"] == "sneaky-worker"


def test_unblock_falls_back_to_os_user(kb, monkeypatch):
    monkeypatch.delenv("HERMES_PROFILE", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_EVENT_AUTHOR", raising=False)
    import getpass

    with kb.connect_closing() as conn:
        task_id = _mk_blocked_task(kb, conn)
        assert kb.unblock_task(conn, task_id)
        by = _last_event(kb, conn, task_id, "unblocked")["by"]
        assert by == getpass.getuser()
        assert by  # never empty — the defect was an empty payload


def test_event_author_env_override_wins(kb, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_EVENT_AUTHOR", "cron:nightly")
    monkeypatch.setenv("HERMES_PROFILE", "worker")
    with kb.connect_closing() as conn:
        task_id = _mk_blocked_task(kb, conn)
        assert kb.unblock_task(conn, task_id)
        assert _last_event(kb, conn, task_id, "unblocked")["by"] == "cron:nightly"


def test_schedule_records_author_too(kb, monkeypatch):
    monkeypatch.setenv("HERMES_PROFILE", "parker")
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        task_id = kb.create_task(conn, title="t", assignee="worker")
        assert kb.schedule_task(conn, task_id, reason="waiting on tuesday")
        ev = _last_event(kb, conn, task_id, "scheduled")
        assert ev["by"] == "parker"
        assert ev["reason"] == "waiting on tuesday"
