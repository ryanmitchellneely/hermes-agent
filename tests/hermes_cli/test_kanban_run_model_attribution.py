"""FLEET-ECON-0 (t_e7e74c61): task_runs.resolved_model/resolved_provider.

Closes the "~48% of completions carry no model stamp" gap: a task with an
explicit model_override already recorded it on the ``tasks`` row, but a
profile-default run (no override) recorded nothing at all anywhere the
dispatcher could see after spawn. These tests pin the fix at the one point
it can be observed without a live worker subprocess: the claim-time stamp
onto ``task_runs``.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest
import yaml


@pytest.fixture()
def isolated_kanban_home_with_profiles(monkeypatch):
    """Fresh HERMES_HOME with a kanban DB + two named profiles.

    ``coder`` carries a config.yaml default model/provider (the common case:
    no task-level override, worker falls through to profile config).
    ``bare`` has no config.yaml at all (defensive case: resolution finds
    nothing and must not raise).
    """
    test_home = tempfile.mkdtemp(prefix="kanban_run_model_attribution_test_")
    coder_dir = os.path.join(test_home, "profiles", "coder")
    os.makedirs(coder_dir, exist_ok=True)
    with open(os.path.join(coder_dir, "config.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump({"model": {"default": "gpt-oss:120b", "provider": "spark"}}, fh)
    os.makedirs(os.path.join(test_home, "profiles", "bare"), exist_ok=True)
    os.makedirs(os.path.join(test_home, "profiles", "default"), exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", test_home)
    for mod in list(sys.modules.keys()):
        if mod.startswith("hermes_cli") or mod.startswith("hermes_state") or mod == "hermes_constants":
            del sys.modules[mod]
    from hermes_cli import kanban_db

    yield kanban_db


def _fake_spawn(*args, **kwargs):
    return 12345


def _current_run_row(kb, conn, task_id):
    task = kb.get_task(conn, task_id)
    return conn.execute(
        "SELECT resolved_model, resolved_provider FROM task_runs WHERE id = ?",
        (task.current_run_id,),
    ).fetchone()


def test_explicit_override_is_stamped_verbatim(isolated_kanban_home_with_profiles):
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        task_id = kb.create_task(
            conn,
            title="t1",
            assignee="coder",
            model_override="sonnet",
            provider_override="claude-acp",
        )
    with kb.connect_closing() as conn:
        kb.dispatch_once(conn, spawn_fn=_fake_spawn, dry_run=False)
    with kb.connect_closing() as conn:
        row = _current_run_row(kb, conn, task_id)
        assert row["resolved_model"] == "sonnet"
        assert row["resolved_provider"] == "claude-acp"


def test_profile_default_run_is_stamped_from_config(isolated_kanban_home_with_profiles):
    """THE gap this card closes: no override set, so the dispatcher must
    resolve the profile's own config.yaml default and stamp it -- instead of
    leaving resolved_model NULL the way task_runs did before this fix."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        task_id = kb.create_task(
            conn, title="t2", assignee="coder",
        )
    with kb.connect_closing() as conn:
        kb.dispatch_once(conn, spawn_fn=_fake_spawn, dry_run=False)
    with kb.connect_closing() as conn:
        row = _current_run_row(kb, conn, task_id)
        assert row["resolved_model"] == "gpt-oss:120b"
        assert row["resolved_provider"] == "spark"


def test_profile_with_no_config_yaml_leaves_columns_null(isolated_kanban_home_with_profiles):
    """No override, no resolvable profile default: NULL, not a guess or a
    crash. A missing attribution stays honestly missing."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        task_id = kb.create_task(
            conn, title="t3", assignee="bare",
        )
    with kb.connect_closing() as conn:
        kb.dispatch_once(conn, spawn_fn=_fake_spawn, dry_run=False)
    with kb.connect_closing() as conn:
        row = _current_run_row(kb, conn, task_id)
        assert row["resolved_model"] is None
        assert row["resolved_provider"] is None


def test_review_run_is_stamped_from_dispatch_once(
    isolated_kanban_home_with_profiles,
):
    """Review claims on this tree keep the implementer assignee (no
    review_profiles rewrite). The stamp must still fire through the real
    review lane of ``dispatch_once`` and record that profile's default."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        task_id = kb.create_task(
            conn, title="t4", assignee="coder",
        )
        kb.claim_task(conn, task_id)
        kb.request_review(conn, task_id, summary="ready for review", force=True)
    with kb.connect_closing() as conn:
        kb.dispatch_once(conn, spawn_fn=_fake_spawn, dry_run=False)
    with kb.connect_closing() as conn:
        row = _current_run_row(kb, conn, task_id)
        assert row["resolved_model"] == "gpt-oss:120b"
        assert row["resolved_provider"] == "spark"
