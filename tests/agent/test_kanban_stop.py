"""Tests for the kanban worker turn-end stop guard."""

from __future__ import annotations

import sqlite3

import pytest

from agent.kanban_stop import (
    board_task_status,
    build_kanban_stop_nudge,
    kanban_stop_nudge_enabled,
    session_called_kanban_terminal,
    task_reached_terminal_state,
)


@pytest.fixture
def clear_kanban_env(monkeypatch):
    for var in ("HERMES_KANBAN_TASK", "HERMES_KANBAN_STOP_NUDGE", "HERMES_KANBAN_DB"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def _make_board(tmp_path, task_id: str, status: str) -> str:
    """Minimal board DB with one task row; returns its path."""
    db_path = tmp_path / "kanban.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT)")
        conn.execute("INSERT INTO tasks (id, status) VALUES (?, ?)", (task_id, status))
        conn.commit()
    finally:
        conn.close()
    return str(db_path)






def test_env_can_disable(clear_kanban_env):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_abc")
    clear_kanban_env.setenv("HERMES_KANBAN_STOP_NUDGE", "0")
    assert kanban_stop_nudge_enabled() is False
    assert build_kanban_stop_nudge(messages=[]) is None


def test_nudge_when_no_terminal_tool(clear_kanban_env):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_46be8aa5")
    messages = [
        {"role": "user", "content": "work kanban task"},
        {
            "role": "assistant",
            "content": "Let me write the comprehensive recipe.",
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {"name": "kanban_heartbeat", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "name": "kanban_heartbeat", "tool_call_id": "1", "content": "ok"},
    ]
    nudge = build_kanban_stop_nudge(messages=messages, attempts=0)
    assert nudge is not None
    assert "kanban_complete" in nudge
    assert "kanban_block" in nudge
    assert "t_46be8aa5" in nudge
    assert "protocol violation" in nudge.lower() or "protocol" in nudge.lower()


def test_no_nudge_after_kanban_complete(clear_kanban_env):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_abc")
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {"name": "kanban_complete", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "name": "kanban_complete", "tool_call_id": "1", "content": "done"},
    ]
    assert session_called_kanban_terminal(messages) is True
    assert build_kanban_stop_nudge(messages=messages) is None


# ── Board state is the authority (phantom "still running" nag) ────────
# An ACP-backed worker reaches the board through the CLI, so its session
# messages carry no kanban_complete tool_call. Scanning messages alone
# nagged a task that was already `done`.


@pytest.mark.parametrize("status", ["done", "blocked", "archived", "cancelled"])
def test_no_nudge_when_board_says_terminal(clear_kanban_env, tmp_path, status):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_e1a86e85")
    clear_kanban_env.setenv(
        "HERMES_KANBAN_DB", _make_board(tmp_path, "t_e1a86e85", status)
    )
    # No terminal tool_call in this session — the CLI shell-out case.
    messages = [{"role": "assistant", "content": "completed via hermes kanban CLI"}]

    assert board_task_status() == status
    assert task_reached_terminal_state() is True
    assert build_kanban_stop_nudge(messages=messages, attempts=0) is None


def test_nudge_still_fires_while_board_says_running(clear_kanban_env, tmp_path):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_live01")
    clear_kanban_env.setenv(
        "HERMES_KANBAN_DB", _make_board(tmp_path, "t_live01", "running")
    )
    messages = [{"role": "assistant", "content": "Let me write the report now."}]

    assert task_reached_terminal_state() is False
    nudge = build_kanban_stop_nudge(messages=messages, attempts=0)
    assert nudge is not None
    assert "t_live01" in nudge


def test_unknown_board_state_does_not_suppress_nudge(clear_kanban_env, tmp_path):
    """Missing/unreadable DB must not silence a genuine violation."""
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_nodb01")
    clear_kanban_env.setenv("HERMES_KANBAN_DB", str(tmp_path / "absent.db"))
    messages = [{"role": "assistant", "content": "Let me write the report now."}]

    assert board_task_status() is None
    assert task_reached_terminal_state() is False
    assert build_kanban_stop_nudge(messages=messages, attempts=0) is not None


def test_board_row_missing_does_not_suppress_nudge(clear_kanban_env, tmp_path):
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_missing")
    clear_kanban_env.setenv(
        "HERMES_KANBAN_DB", _make_board(tmp_path, "t_other", "done")
    )
    messages = [{"role": "assistant", "content": "Let me write the report now."}]

    assert board_task_status() is None
    assert build_kanban_stop_nudge(messages=messages, attempts=0) is not None


def test_board_read_is_read_only(clear_kanban_env, tmp_path):
    """The guard must never mutate the shared board DB."""
    db_path = _make_board(tmp_path, "t_ro01", "running")
    clear_kanban_env.setenv("HERMES_KANBAN_TASK", "t_ro01")
    clear_kanban_env.setenv("HERMES_KANBAN_DB", db_path)

    import os

    before = os.stat(db_path).st_mtime_ns
    assert board_task_status() == "running"
    assert os.stat(db_path).st_mtime_ns == before






# ── Integration: agent nudge + dispatcher bounded retry ──────────────
# These tests verify the two layers compose correctly: the agent-side
# nudge fires first (up to 2 attempts), and if the worker still exits
# without a terminal call, the dispatcher's bounded retry (streak of 3)
# handles it.  See also tests/hermes_cli/test_kanban_core_functionality.py
# for the dispatcher-side streak tests.




