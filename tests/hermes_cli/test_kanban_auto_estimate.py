"""Tests for the auto-estimate-on-create queue (t_5716d9c5).

``create_task`` stamps every eligible new row ``estimate_status='pending'``
so the dispatcher's auto-estimate tick (``gateway/kanban_watchers.py``) can
drain it without blocking task creation. See the ``estimate_status`` column
comment in ``kanban_db.SCHEMA_SQL`` for the full state machine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


def test_create_task_defaults_to_pending_estimate(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="wire up the widget", assignee="alice")
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "pending"
    finally:
        conn.close()


def test_create_task_skips_estimate_when_model_override_given(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(
            conn, title="pinned task", assignee="alice",
            model_override="grok-4.5", provider_override="xai-oauth",
        )
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "skipped"
    finally:
        conn.close()


def test_create_task_skips_estimate_for_triage(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="needs specifying", assignee="alice", triage=True)
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "skipped"
    finally:
        conn.close()


def test_create_task_respects_auto_estimate_false(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(
            conn, title="opt out", assignee="alice", auto_estimate=False,
        )
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "skipped"
    finally:
        conn.close()


def test_list_tasks_needing_estimate_returns_pending_oldest_first(kanban_home):
    conn = kb.connect()
    try:
        skipped = kb.create_task(
            conn, title="already pinned", assignee="alice", model_override="sonnet",
        )
        first = kb.create_task(conn, title="first pending", assignee="alice")
        second = kb.create_task(conn, title="second pending", assignee="alice")

        pending = kb.list_tasks_needing_estimate(conn, limit=10)
        pending_ids = [t.id for t in pending]

        assert skipped not in pending_ids
        assert pending_ids == [first, second]
    finally:
        conn.close()


def test_list_tasks_needing_estimate_respects_limit(kanban_home):
    conn = kb.connect()
    try:
        for i in range(5):
            kb.create_task(conn, title=f"task {i}", assignee="alice")
        pending = kb.list_tasks_needing_estimate(conn, limit=2)
        assert len(pending) == 2
    finally:
        conn.close()


def test_set_estimate_status_transitions_and_drops_from_queue(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="pending task", assignee="alice")
        assert kb.set_estimate_status(conn, tid, "done") is True
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "done"
        assert tid not in [t.id for t in kb.list_tasks_needing_estimate(conn, limit=10)]
    finally:
        conn.close()


def test_set_estimate_status_rejects_invalid_value(kanban_home):
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="pending task", assignee="alice")
        with pytest.raises(ValueError):
            kb.set_estimate_status(conn, tid, "bogus")
    finally:
        conn.close()


def test_set_estimate_status_false_for_missing_task(kanban_home):
    conn = kb.connect()
    try:
        assert kb.set_estimate_status(conn, "t_doesnotexist", "done") is False
    finally:
        conn.close()


def test_legacy_rows_backfilled_as_skipped_on_migration(kanban_home):
    """A DB written before the estimate_status column existed must not
    dump every historical task into the auto-estimate queue on upgrade.

    Simulates a genuinely pre-migration DB by dropping the column after
    creation (so existing rows lose their 'pending' value entirely, the
    same shape a DB that predates this column has) and re-running
    ``init_db`` to force the additive migration + backfill to fire again.
    """
    conn = kb.connect()
    try:
        tid = kb.create_task(conn, title="pre-migration task", assignee="alice")
        conn.execute("DROP INDEX IF EXISTS idx_tasks_estimate_status")
        conn.execute("ALTER TABLE tasks DROP COLUMN estimate_status")
        conn.commit()
    finally:
        conn.close()

    # Re-run the migration pass explicitly (mirrors opening an old DB again).
    kb.init_db()
    conn = kb.connect()
    try:
        task = kb.get_task(conn, tid)
        assert task.estimate_status == "skipped"
        assert tid not in [t.id for t in kb.list_tasks_needing_estimate(conn, limit=10)]
    finally:
        conn.close()
