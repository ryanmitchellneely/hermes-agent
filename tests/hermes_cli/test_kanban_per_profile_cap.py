"""Regression tests for #21582 — per-profile concurrency cap in dispatcher.

When ``kanban.max_in_progress_per_profile`` is set, no single profile
gets more than N workers running at once even if the global
``max_in_progress`` cap would allow it. Prevents one profile's local
model / API quota / browser pool from being overwhelmed by a fan-out.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest


@pytest.fixture()
def isolated_kanban_home_with_profiles(monkeypatch):
    """Spin up a fresh HERMES_HOME with kanban DB + alpha/beta profiles."""
    test_home = tempfile.mkdtemp(prefix="kanban_per_profile_cap_test_")
    for prof in ("alpha", "beta", "default"):
        os.makedirs(os.path.join(test_home, "profiles", prof), exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", test_home)
    for mod in list(sys.modules.keys()):
        if mod.startswith("hermes_cli") or mod.startswith("hermes_state") or mod == "hermes_constants":
            del sys.modules[mod]
    from hermes_cli import kanban_db
    yield kanban_db


def _fake_spawn(*args, **kwargs):
    return 12345




def test_cap_2_balances_two_profiles(isolated_kanban_home_with_profiles):
    """With cap=2: 2 alpha + 2 beta dispatched; remaining 3 alpha + 1 beta
    deferred to skipped_per_profile_capped."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        for i in range(5):
            kb.create_task(conn, title=f"a{i}", assignee="alpha")
        for i in range(3):
            kb.create_task(conn, title=f"b{i}", assignee="beta")
    with kb.connect_closing() as conn:
        res = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=True,
            max_in_progress_per_profile=2,
        )
    spawn_assignees = [s[1] for s in res.spawned]
    capped_assignees = [c[1] for c in res.skipped_per_profile_capped]
    assert spawn_assignees.count("alpha") == 2
    assert spawn_assignees.count("beta") == 2
    assert capped_assignees.count("alpha") == 3
    assert capped_assignees.count("beta") == 1




def test_capped_tasks_dispatched_on_subsequent_tick(isolated_kanban_home_with_profiles):
    """A task deferred this tick because its profile was at cap should be
    eligible for dispatch on the next tick (after running tasks complete).
    This verifies the cap is per-tick state, not a permanent block."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        ids = [kb.create_task(conn, title=f"a{i}", assignee="alpha") for i in range(3)]

    # First tick: cap=1, only 1 alpha dispatched
    with kb.connect_closing() as conn:
        res1 = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=False,
            max_in_progress_per_profile=1,
        )
    assert len(res1.spawned) == 1
    assert len(res1.skipped_per_profile_capped) == 2

    # Simulate the running task completing — set it back to done so the
    # 'running' count drops
    spawned_id = res1.spawned[0][0]
    with kb.connect_closing() as conn:
        with kb.write_txn(conn):
            conn.execute(
                "UPDATE tasks SET status = 'done', claim_lock = NULL WHERE id = ?",
                (spawned_id,),
            )

    # Second tick: 1 more alpha should now dispatch
    with kb.connect_closing() as conn:
        res2 = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=False,
            max_in_progress_per_profile=1,
        )
    assert len(res2.spawned) == 1
    assert len(res2.skipped_per_profile_capped) == 1
    assert res2.spawned[0][0] != spawned_id  # different task this time




def test_mapping_cap_widens_one_profile_only(isolated_kanban_home_with_profiles):
    """THE RULING THIS PINS (Ryan, 2026-08-13): sonnet widened to 6 while
    every other profile keeps the DS4 load throttle of 2. The cap accepts a
    mapping {profile: n, "default": n}; a profile absent from the map falls
    back to "default"."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        for i in range(8):
            kb.create_task(conn, title=f"s{i}", assignee="alpha")   # the widened lane
        for i in range(4):
            kb.create_task(conn, title=f"w{i}", assignee="beta")    # falls to default
    with kb.connect_closing() as conn:
        res = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=True,
            max_in_progress_per_profile={"alpha": 6, "default": 2},
        )
    spawned = [s[1] for s in res.spawned]
    capped = [c[1] for c in res.skipped_per_profile_capped]
    assert spawned.count("alpha") == 6, "widened profile must get its own cap"
    assert spawned.count("beta") == 2, "unlisted profile must fall back to default"
    assert capped.count("alpha") == 2
    assert capped.count("beta") == 2


def test_mapping_default_only_equals_legacy_int(isolated_kanban_home_with_profiles):
    """Negative control: {"default": 2} must behave exactly like the legacy
    int 2 — if it doesn't, the mapping path has different semantics and every
    existing config translation is wrong."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        for i in range(5):
            kb.create_task(conn, title=f"a{i}", assignee="alpha")
        for i in range(3):
            kb.create_task(conn, title=f"b{i}", assignee="beta")
    with kb.connect_closing() as conn:
        res = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=True,
            max_in_progress_per_profile={"default": 2},
        )
    spawned = [s[1] for s in res.spawned]
    assert spawned.count("alpha") == 2 and spawned.count("beta") == 2


def test_mapping_without_default_leaves_unlisted_uncapped(isolated_kanban_home_with_profiles):
    """No "default" key = unlisted profiles are UNCAPPED (documented semantics
    — the map only constrains who it names)."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        for i in range(4):
            kb.create_task(conn, title=f"a{i}", assignee="alpha")
        for i in range(4):
            kb.create_task(conn, title=f"b{i}", assignee="beta")
    with kb.connect_closing() as conn:
        res = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=True,
            max_in_progress_per_profile={"alpha": 1},
        )
    spawned = [s[1] for s in res.spawned]
    assert spawned.count("alpha") == 1
    assert spawned.count("beta") == 4, "unlisted profile with no default must be uncapped"


def test_mapping_invalid_values_dropped_not_poisonous(isolated_kanban_home_with_profiles):
    """A junk value for one profile must not disable the whole cap."""
    kb = isolated_kanban_home_with_profiles
    assert kb._normalize_per_profile_cap({"alpha": "junk", "default": 2}) == {"default": 2}
    assert kb._normalize_per_profile_cap({"alpha": 0}) is None
    assert kb._normalize_per_profile_cap(2) == 2
    assert kb._normalize_per_profile_cap(None) is None
    assert kb._resolve_profile_cap({"alpha": 6, "default": 2}, "alpha") == 6
    assert kb._resolve_profile_cap({"alpha": 6, "default": 2}, "beta") == 2
    assert kb._resolve_profile_cap({"alpha": 6}, "beta") is None
