"""Fleet GitHub auth for kanban workers (t_7fa5ce83).

Launchd-spawned workers run outside the login session: gh's keyring and
git's osxkeychain helper are both invisible to them, so every
GitHub-touching card blocked with "missing credentials". git is covered by
a GIT_CONFIG_GLOBAL credential helper; gh reads only GH_TOKEN/GITHUB_TOKEN
from env. These tests pin the dispatcher-side mint: when the operator
names a token helper via HERMES_KANBAN_GH_TOKEN_CMD, its stdout becomes
the worker's GH_TOKEN — best-effort, never blocking the spawn.
"""

import os

import pytest


class _Proc:
    pid = 4321


def _make_task(kb):
    return kb.Task(
        id="t_ghtoken",
        title="push something",
        body=None,
        assignee="default",
        status="in_progress",
        priority=0,
        created_by=None,
        created_at=0,
        started_at=None,
        completed_at=None,
        workspace_kind="scratch",
        workspace_path=None,
        claim_lock=None,
        claim_expires=None,
        tenant=None,
    )


@pytest.fixture()
def spawn_env(monkeypatch, tmp_path):
    """Run _default_spawn with Popen stubbed; return the captured env."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    import subprocess as _sp

    from hermes_cli import kanban_db as kb

    captured = {}
    _real_popen = _sp.Popen

    def _fake_popen(cmd, **kwargs):
        # The token-mint path goes through subprocess.run -> Popen too;
        # let the real helper script execute so these tests exercise the
        # actual mint, and only intercept the worker spawn itself.
        if cmd and str(cmd[0]).endswith("token-helper"):
            return _real_popen(cmd, **kwargs)
        captured["env"] = kwargs["env"]
        return _Proc()

    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    monkeypatch.setattr(kb, "_retag_legacy_worker_sessions", lambda _root: None)
    monkeypatch.setattr(kb, "worker_logs_dir", lambda board=None: tmp_path / "logs")

    def _run():
        workspace = str(tmp_path / "ws")
        os.makedirs(workspace, exist_ok=True)
        kb._default_spawn(_make_task(kb), workspace)
        return captured["env"]

    return _run


def _write_helper(tmp_path, script_body):
    helper = tmp_path / "token-helper"
    helper.write_text("#!/bin/sh\n" + script_body + "\n")
    helper.chmod(0o700)
    return str(helper)


def test_helper_stdout_becomes_gh_token(spawn_env, monkeypatch, tmp_path):
    helper = _write_helper(tmp_path, "echo ghs_minted_token")
    monkeypatch.setenv("HERMES_KANBAN_GH_TOKEN_CMD", helper)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    env = spawn_env()

    assert env["GH_TOKEN"] == "ghs_minted_token"


def test_inherited_token_wins_over_helper(spawn_env, monkeypatch, tmp_path):
    """The helper is a fallback, not an override — an operator-supplied
    token (e.g. a test env, or the dsh wrapper's own mint) must survive."""
    helper = _write_helper(tmp_path, "echo ghs_should_not_be_used")
    monkeypatch.setenv("HERMES_KANBAN_GH_TOKEN_CMD", helper)
    monkeypatch.setenv("GH_TOKEN", "ghs_inherited")

    env = spawn_env()

    assert env["GH_TOKEN"] == "ghs_inherited"


def test_failing_helper_never_blocks_the_spawn(spawn_env, monkeypatch, tmp_path):
    """A mint failure leaves the worker exactly as credential-less as it
    would have been before this feature — spawn still happens, no token."""
    helper = _write_helper(tmp_path, "echo boom >&2; exit 1")
    monkeypatch.setenv("HERMES_KANBAN_GH_TOKEN_CMD", helper)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    env = spawn_env()

    assert "GH_TOKEN" not in env


def test_unset_helper_is_a_no_op(spawn_env, monkeypatch):
    monkeypatch.delenv("HERMES_KANBAN_GH_TOKEN_CMD", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    env = spawn_env()

    assert "GH_TOKEN" not in env
