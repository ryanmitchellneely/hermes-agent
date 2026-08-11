"""Tests for kanban goal_mode — per-card Ralph-style goal loop.

Covers three layers:

1. DB: goal_mode / goal_max_turns persist through create_task + from_row,
   and a legacy DB (without the columns) migrates cleanly.
2. Spawn: _default_spawn sets the HERMES_KANBAN_GOAL_MODE env vars only
   when the card opts in.
3. Loop: goals.run_kanban_goal_loop continuation / completion / budget
   behaviour, driven entirely through injected callbacks (no live model).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb
from hermes_cli import goals


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


# ---------------------------------------------------------------------------
# DB layer
# ---------------------------------------------------------------------------





def test_legacy_db_migrates_goal_columns(tmp_path, monkeypatch):
    """A tasks table created without goal columns must gain them on init."""
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    db_path = kb.kanban_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Minimal legacy schema: tasks table missing goal_mode / goal_max_turns.
    legacy = sqlite3.connect(db_path)
    legacy.execute(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT,
            assignee TEXT,
            status TEXT NOT NULL DEFAULT 'ready',
            priority INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at INTEGER NOT NULL,
            started_at INTEGER,
            completed_at INTEGER,
            workspace_kind TEXT NOT NULL DEFAULT 'scratch',
            workspace_path TEXT,
            claim_lock TEXT,
            claim_expires INTEGER
        )
        """
    )
    legacy.execute(
        "INSERT INTO tasks (id, title, status, priority, created_at, workspace_kind) "
        "VALUES ('legacy1', 'old', 'ready', 0, 1, 'scratch')"
    )
    legacy.commit()
    legacy.close()

    # init_db runs the additive migration.
    kb.init_db()
    with kb.connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")}
        assert "goal_mode" in cols
        assert "goal_max_turns" in cols
        task = kb.get_task(conn, "legacy1")
    # Existing row keeps the safe default.
    assert task.goal_mode is False
    assert task.goal_max_turns is None


# ---------------------------------------------------------------------------
# Spawn env
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Goal loop logic (callback-injected, no live model)
# ---------------------------------------------------------------------------

def _patch_judge(monkeypatch, verdicts):
    """Make judge_goal return a scripted sequence of verdicts."""
    seq = list(verdicts)

    def _fake_judge(goal, response, subgoals=None, background_processes=None, **_kw):
        v = seq.pop(0) if seq else "done"
        # 5-tuple contract: verdict, reason, parse failure, wait, transport failure.
        return v, f"scripted:{v}", False, None, False

    monkeypatch.setattr(goals, "judge_goal", _fake_judge)


def test_loop_blocks_when_judge_permanently_unreachable(monkeypatch):
    """A permanently broken judge must not burn the whole turn budget.

    A transport failure surfaces as "continue", so the loop would re-poke a
    worker that has nothing left to do for every remaining turn. After N
    consecutive transport failures, block for human review instead — the same
    posture GoalManager.evaluate_after_turn takes.
    """
    def _always_transport_fail(goal, response, subgoals=None,
                               background_processes=None, **_kw):
        return "continue", "judge error: TimeoutError", False, None, True

    monkeypatch.setattr(goals, "judge_goal", _always_transport_fail)

    turns = []
    blocked = []
    res = goals.run_kanban_goal_loop(
        task_id="t1",
        goal_text="do the thing",
        run_turn=lambda p: turns.append(p) or "still working",
        task_status_fn=lambda: "running",
        block_fn=lambda r: blocked.append(r),
        first_response="started",
        max_turns=20,
    )

    assert res["outcome"] == "blocked_judge_unreachable"
    assert blocked and "unreachable" in blocked[0].lower()
    # Bailed out well before exhausting the 20-turn budget.
    assert len(turns) < 20


def test_loop_transport_failure_streak_resets_on_success(monkeypatch):
    """Intermittent blips must not accumulate into a spurious block."""
    seq = [True, True, False, True, True, False]

    def _flaky(goal, response, subgoals=None, background_processes=None, **_kw):
        tf = seq.pop(0) if seq else False
        if tf:
            return "continue", "judge error: TimeoutError", False, None, True
        return "continue", "keep going", False, None, False

    monkeypatch.setattr(goals, "judge_goal", _flaky)

    blocked = []
    res = goals.run_kanban_goal_loop(
        task_id="t1",
        goal_text="do the thing",
        run_turn=lambda p: "still working",
        task_status_fn=lambda: "running",
        block_fn=lambda r: blocked.append(r),
        first_response="started",
        max_turns=7,
    )

    assert res["outcome"] != "blocked_judge_unreachable", (
        "a reachable judge in between must reset the streak"
    )


def test_loop_stops_when_worker_already_completed(monkeypatch):
    # Worker called kanban_complete on its first turn — no judging needed.
    _patch_judge(monkeypatch, ["continue"])  # should never be consulted
    turns = []

    res = goals.run_kanban_goal_loop(
        task_id="t1",
        goal_text="do the thing",
        run_turn=lambda p: turns.append(p) or "x",
        task_status_fn=lambda: "done",
        block_fn=lambda r: pytest.fail("should not block"),
        first_response="done already",
    )
    assert res["outcome"] == "completed_by_worker"
    assert turns == []  # no extra turns






# ---------------------------------------------------------------------------
# CLI judge gate tests (hermes kanban complete bypass fix)
# ---------------------------------------------------------------------------

class TestCLIJudgeGate:
    """hermes kanban complete must apply the same goal_mode judge gate as the
    kanban_complete tool (Issue #38367 sibling gap).

    Uses mocks for kb.get_task and kb.complete_task to avoid depending on the
    full kanban_db schema; the gate logic is the unit under test.
    """

    def _run(self, monkeypatch, *, goal_mode=True, judge_available=True,
             verdict="done", reason="", complete_ok=True, summary="done",
             transport_failed=False, comments=None):
        import argparse
        import types
        from unittest.mock import MagicMock
        from hermes_cli.kanban import _cmd_complete

        fake_task = types.SimpleNamespace(
            goal_mode=goal_mode,
            title="Finish report",
            body="acceptance: criteria",
        )
        fake_conn = MagicMock()
        complete_calls: list = []

        def fake_connect_closing():
            from contextlib import contextmanager
            @contextmanager
            def _cm():
                yield fake_conn
            return _cm()

        def fake_complete_task(conn, tid, **kw):
            complete_calls.append(tid)
            return complete_ok

        monkeypatch.setattr("hermes_cli.kanban.kb.get_task", lambda conn, tid: fake_task)
        monkeypatch.setattr("hermes_cli.kanban.kb.complete_task", fake_complete_task)
        monkeypatch.setattr("hermes_cli.kanban.kb.connect_closing", fake_connect_closing)
        monkeypatch.setattr("hermes_cli.kanban._worker_run_id_for", lambda _: None)

        _aux_client = (object(), "judge-model") if judge_available else (None, None)
        monkeypatch.setattr(
            "agent.auxiliary_client.get_text_auxiliary_client",
            lambda name: _aux_client,
        )
        # Match the real judge_goal contract:
        # (verdict, reason, parse_failed, wait_directive, transport_failed)
        # Patched at the source so the shared gate helper
        # (goals.judge_kanban_completion) is exercised for real.
        monkeypatch.setattr(
            "hermes_cli.goals.judge_goal",
            lambda **kw: (verdict, reason, False, None, transport_failed),
        )
        # No real backoff sleep in tests.
        monkeypatch.setattr("hermes_cli.goals.KANBAN_GATE_RETRY_BACKOFF", 0)
        monkeypatch.setattr(
            "hermes_cli.kanban.kb.add_comment",
            lambda conn, tid, *, author, body: (
                comments.append((author, body)) if comments is not None else None
            ),
        )

        args = argparse.Namespace(task_ids=["t1"], summary=summary, result=None, metadata=None)
        return _cmd_complete(args), complete_calls

    def test_judge_rejects_premature_completion(self, monkeypatch):
        rc, complete_calls = self._run(
            monkeypatch, verdict="continue", reason="criteria not met"
        )
        assert rc != 0, "judge rejection must produce non-zero exit code"
        assert complete_calls == [], (
            "complete_task must NOT be invoked when the judge rejects"
        )


    def test_non_goal_mode_task_skips_gate(self, monkeypatch):
        """Plain (non-goal_mode) tasks are never sent to the judge."""
        rc, complete_calls = self._run(monkeypatch, goal_mode=False)
        assert rc == 0
        assert complete_calls == ["t1"]

    def test_transport_failure_does_not_reject_completion(self, monkeypatch):
        """A judge that can't be REACHED must not reject a completion.

        judge_goal reports transport errors as ("continue", ..., True). The
        gate used to read only the "continue" and hard-reject, turning a
        network blip into "your finished work is rejected".
        """
        comments: list = []
        rc, complete_calls = self._run(
            monkeypatch,
            verdict="continue",
            reason="judge error: TimeoutError",
            transport_failed=True,
            comments=comments,
        )
        assert rc == 0, "transport failure must fail OPEN, not reject"
        assert complete_calls == ["t1"]
        # ...and the fail-open must be auditable on the board, not silent.
        assert len(comments) == 1
        author, body = comments[0]
        assert author == "goal-judge"
        assert "unreachable" in body.lower()

    def test_real_continue_verdict_still_rejects(self, monkeypatch):
        """The evidence gate is NOT weakened: a genuine verdict still rejects."""
        comments: list = []
        rc, complete_calls = self._run(
            monkeypatch,
            verdict="continue",
            reason="no evidence provided",
            transport_failed=False,
            comments=comments,
        )
        assert rc != 0
        assert complete_calls == []
        assert comments == [], "a real rejection is not a fail-open"
