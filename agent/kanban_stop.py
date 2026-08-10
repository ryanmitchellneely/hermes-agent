"""Turn-end guard for kanban workers.

Kanban workers must end with ``kanban_complete`` or ``kanban_block``. Models
(especially GLM / Qwen families) sometimes narrate the next step
("Let me write the report now") and stop with ``finish_reason=stop`` and no
tool calls. Hermes treats that as a clean exit → ``rc=0`` → dispatcher
``protocol_violation``.

This module is policy-only: when a kanban worker tries to finish without a
terminal board tool, return a bounded synthetic nudge so the conversation
loop continues instead of exiting.

The guard is *session*-scoped but the board is the authority. A worker can
reach a terminal state without a ``kanban_complete`` tool_call in this
session's messages — an ACP-backed worker that shelled out to
``hermes kanban ... complete`` is the common case. Scanning messages alone
then nags a worker whose task is already ``done``, which trains operators to
ignore a warning that is real everywhere else. So the message scan is only
the fast path: before nagging we read the task's live status from the board.
"""

from __future__ import annotations

import os
import sqlite3
import urllib.parse
from typing import Any, Iterable, Optional


_TERMINAL_KANBAN_TOOLS = frozenset({"kanban_complete", "kanban_block"})

# Board statuses that mean this run has nothing left to do. ``running`` and
# ``ready`` are deliberately absent — those are the states the nudge exists
# for. Both US and UK spellings of cancelled are accepted defensively.
_TERMINAL_TASK_STATUSES = frozenset(
    {"done", "blocked", "archived", "cancelled", "canceled"}
)

_DEFAULT_MAX_ATTEMPTS = 2


def kanban_stop_nudge_enabled() -> bool:
    """Return whether the kanban stop-guard is active for this process.

    On when ``HERMES_KANBAN_TASK`` is set (dispatcher-spawned worker), unless
    ``HERMES_KANBAN_STOP_NUDGE`` explicitly disables it.
    """
    env = os.environ.get("HERMES_KANBAN_STOP_NUDGE")
    if env is not None and env.strip().lower() in {"0", "false", "no", "off"}:
        return False
    task = (os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    return bool(task)


def _tool_call_name(tc: Any) -> str:
    if isinstance(tc, dict):
        fn = tc.get("function")
        if isinstance(fn, dict):
            return str(fn.get("name") or "")
        return str(tc.get("name") or "")
    fn = getattr(tc, "function", None)
    if fn is not None:
        return str(getattr(fn, "name", "") or "")
    return str(getattr(tc, "name", "") or "")


def session_called_kanban_terminal(messages: Iterable[dict] | None) -> bool:
    """True if this conversation already invoked a terminal kanban tool."""
    if not messages:
        return False
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "assistant":
            for tc in msg.get("tool_calls") or []:
                if _tool_call_name(tc) in _TERMINAL_KANBAN_TOOLS:
                    return True
        elif role == "tool":
            name = str(msg.get("name") or "")
            if name in _TERMINAL_KANBAN_TOOLS:
                return True
    return False


def _resolve_board_db_path() -> Optional[str]:
    """Path to this worker's board DB, or None when it can't be resolved.

    ``HERMES_KANBAN_DB`` is injected by the dispatcher on every worker spawn
    (hermes_cli/kanban_db.py ``_default_spawn``), so it is the cheap path and
    is board-correct by construction. Falling back to the resolver keeps
    non-dispatched callers (tests, manual runs) working.
    """
    direct = (os.environ.get("HERMES_KANBAN_DB") or "").strip()
    if direct:
        return direct
    try:
        from hermes_cli.kanban_db import kanban_db_path

        return str(kanban_db_path())
    except Exception:
        return None


def board_task_status(task_id: Optional[str] = None) -> Optional[str]:
    """Live ``tasks.status`` for this worker's task, or None if unknown.

    Read-only and never raises: an unreadable/locked/missing DB returns None
    so the caller falls back to session-scoped behaviour rather than
    suppressing a genuine protocol-violation nudge.
    """
    tid = (task_id or os.environ.get("HERMES_KANBAN_TASK") or "").strip()
    if not tid:
        return None
    db_path = _resolve_board_db_path()
    if not db_path or not os.path.exists(db_path):
        return None

    conn = None
    try:
        uri = "file:" + urllib.parse.quote(os.path.abspath(db_path)) + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        row = conn.execute("SELECT status FROM tasks WHERE id = ?", (tid,)).fetchone()
    except Exception:
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if not row:
        return None
    return str(row[0] or "").strip().lower() or None


def task_reached_terminal_state(task_id: Optional[str] = None) -> bool:
    """True only when the board itself says this task is terminal.

    Unknown status (no DB, no row, read error) is reported as False — the
    genuine clean-exit detector must keep firing when we can't prove the work
    is finished.
    """
    return (board_task_status(task_id) or "") in _TERMINAL_TASK_STATUSES


def build_kanban_stop_nudge(
    *,
    messages: Iterable[dict] | None = None,
    attempts: int = 0,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    task_id: Optional[str] = None,
) -> Optional[str]:
    """Return a synthetic follow-up when a kanban worker exits without a terminal tool.

    Returns ``None`` when the guard should not fire (not a kanban worker,
    already completed/blocked, or nudge budget exhausted).
    """
    if not kanban_stop_nudge_enabled():
        return None
    if attempts >= max_attempts:
        return None
    if session_called_kanban_terminal(messages):
        return None
    # Board is the authority. A worker can be terminal without a terminal
    # tool_call in THIS session (ACP backends reach the board through the
    # CLI). Nagging a `done` task is the phantom-violation bug.
    if task_reached_terminal_state(task_id):
        return None

    tid = (task_id or os.environ.get("HERMES_KANBAN_TASK") or "").strip() or "this task"
    return (
        "[System: You are a Hermes kanban worker. A plain-text reply is NOT a "
        "terminal state for the board.\n\n"
        f"Task `{tid}` is still `running`. Ending now without a board tool "
        "causes a protocol violation (clean exit with no "
        "`kanban_complete` / `kanban_block`).\n\n"
        "Do this immediately in your next response — do not narrate intent:\n"
        "1. Finish any remaining deliverable (write the required file(s) now).\n"
        "2. Call `kanban_complete(summary=..., artifacts=[...])` if the work "
        "is done, OR `kanban_block(reason=...)` if you are blocked.\n\n"
        "Never end a turn with only a promise of future action. Repeated "
        "protocol violations will block this task and require manual intervention.]"
    )


__all__ = [
    "board_task_status",
    "build_kanban_stop_nudge",
    "kanban_stop_nudge_enabled",
    "session_called_kanban_terminal",
    "task_reached_terminal_state",
]
