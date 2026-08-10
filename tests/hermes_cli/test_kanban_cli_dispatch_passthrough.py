"""Regression tests for #33488 (CLI max_in_progress / max_spawn / per-profile
config passthrough) and #29415 (kanban_swarm humanizer skill ref).

These two fixes are bundled because they're both small, both touch the
kanban dispatcher's CLI surface, and they each guard against a silent
operator footgun that only manifests in long-running setups.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def isolated_kanban_home(monkeypatch):
    """Spin up a fresh HERMES_HOME with a clean kanban DB."""
    test_home = tempfile.mkdtemp(prefix="kanban_cli_passthrough_")
    os.makedirs(os.path.join(test_home, "profiles", "default"), exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", test_home)
    for mod in list(sys.modules.keys()):
        if mod.startswith("hermes_cli") or mod.startswith("hermes_state") or mod == "hermes_constants":
            del sys.modules[mod]
    yield test_home


def test_cli_dispatch_passes_max_in_progress_from_config(isolated_kanban_home, monkeypatch):
    """#33488: hermes kanban dispatch must pass kanban.max_in_progress from
    config to dispatch_once. Without this, the global concurrency cap is
    unreachable from the CLI even though it works from the gateway."""
    from hermes_cli import kanban as kb_cli
    from hermes_cli import kanban_db

    # Configure max_in_progress in the loaded config.
    fake_config = {
        "kanban": {
            "max_in_progress": 3,
            "max_spawn": 5,
            "default_assignee": "default",
            "max_in_progress_per_profile": 2,
        }
    }
    monkeypatch.setattr(
        "hermes_cli.config.load_config", lambda: fake_config
    )

    captured = {}

    def fake_dispatch_once(conn, **kwargs):
        captured.update(kwargs)
        return kanban_db.DispatchResult()

    monkeypatch.setattr(kanban_db, "dispatch_once", fake_dispatch_once)

    args = argparse.Namespace(dry_run=True, max=None, failure_limit=2, json=False)
    kb_cli._cmd_dispatch(args)

    # Every config value must have reached dispatch_once.
    assert captured.get("max_in_progress") == 3, (
        f"CLI must pass kanban.max_in_progress from config; got {captured.get('max_in_progress')!r}"
    )
    assert captured.get("max_spawn") == 5, (
        f"CLI must pass kanban.max_spawn from config when --max is not provided; got {captured.get('max_spawn')!r}"
    )
    assert captured.get("default_assignee") == "default"
    assert captured.get("max_in_progress_per_profile") == 2


def test_cli_max_flag_overrides_config_max_spawn(isolated_kanban_home, monkeypatch):
    """--max on the CLI takes precedence over kanban.max_spawn in config.
    The CLI flag is the explicit operator signal; config is the default."""
    from hermes_cli import kanban as kb_cli
    from hermes_cli import kanban_db

    fake_config = {"kanban": {"max_spawn": 10}}
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: fake_config)

    captured = {}
    monkeypatch.setattr(
        kanban_db, "dispatch_once",
        lambda conn, **kw: (captured.update(kw), kanban_db.DispatchResult())[1],
    )

    args = argparse.Namespace(dry_run=True, max=2, failure_limit=2, json=False)
    kb_cli._cmd_dispatch(args)

    assert captured.get("max_spawn") == 2, (
        f"CLI --max=2 must override config kanban.max_spawn=10; got {captured.get('max_spawn')!r}"
    )


# ---------------------------------------------------------------------------
# AUDIT-2026-08-08-worker-cap-and-lab.md follow-up (1): CLI dispatch must
# flock the same `.dispatcher.lock` a running gateway holds — a concurrent
# gateway tick and an unguarded CLI dispatch could each see "under cap" and
# each spawn, bursting past kanban.max_in_progress_per_profile even though
# dispatch_once() is internally consistent per call.
# ---------------------------------------------------------------------------


def test_cli_dispatch_skips_when_gateway_holds_dispatcher_lock(isolated_kanban_home, monkeypatch):
    from hermes_cli import kanban as kb_cli
    from hermes_cli import kanban_db

    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {})

    called = {"dispatch_once": False}

    def fake_dispatch_once(conn, **kwargs):
        called["dispatch_once"] = True
        return kanban_db.DispatchResult()

    monkeypatch.setattr(kanban_db, "dispatch_once", fake_dispatch_once)
    monkeypatch.setattr(
        "gateway.kanban_watchers._acquire_singleton_lock",
        lambda path: (None, "contended"),
    )

    args = argparse.Namespace(dry_run=False, max=None, failure_limit=2, json=False)
    rc = kb_cli._cmd_dispatch(args)

    assert rc == 0
    assert called["dispatch_once"] is False, (
        "must not call dispatch_once while the gateway holds the lock"
    )


def test_cli_dispatch_acquires_and_releases_lock_when_free(isolated_kanban_home, monkeypatch):
    from hermes_cli import kanban as kb_cli
    from hermes_cli import kanban_db

    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {})
    monkeypatch.setattr(
        kanban_db, "dispatch_once", lambda conn, **kw: kanban_db.DispatchResult()
    )

    sentinel = object()
    acquired = {}
    released = {}

    def fake_acquire(path):
        acquired["path"] = path
        return sentinel, "held"

    def fake_release(handle):
        released["handle"] = handle

    monkeypatch.setattr("gateway.kanban_watchers._acquire_singleton_lock", fake_acquire)
    monkeypatch.setattr("gateway.kanban_watchers._release_singleton_lock", fake_release)

    args = argparse.Namespace(dry_run=False, max=None, failure_limit=2, json=False)
    rc = kb_cli._cmd_dispatch(args)

    assert rc == 0
    assert acquired.get("path") is not None
    assert released.get("handle") is sentinel, "must release the lock it acquired"


def test_cli_dispatch_dry_run_bypasses_lock_check(isolated_kanban_home, monkeypatch):
    """--dry-run makes no spawns/writes, so it must never even touch the
    dispatcher lock — it stays usable for visibility while a gateway owns
    the board."""
    from hermes_cli import kanban as kb_cli
    from hermes_cli import kanban_db

    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {})

    called = {"dispatch_once": False}

    def fake_dispatch_once(conn, **kwargs):
        called["dispatch_once"] = True
        return kanban_db.DispatchResult()

    monkeypatch.setattr(kanban_db, "dispatch_once", fake_dispatch_once)

    def fail_if_called(path):
        raise AssertionError("dry-run must not touch the dispatcher lock at all")

    monkeypatch.setattr("gateway.kanban_watchers._acquire_singleton_lock", fail_if_called)

    args = argparse.Namespace(dry_run=True, max=None, failure_limit=2, json=False)
    rc = kb_cli._cmd_dispatch(args)

    assert rc == 0
    assert called["dispatch_once"] is True


