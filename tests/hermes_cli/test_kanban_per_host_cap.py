"""Regression tests for Phase 2 R5 — per-host cap extension to
``kanban.max_in_progress_per_profile``
(docs/build-plans/2026-09-03-sandbox-mesh-phase2.md "Dispatcher side").

A profile's own cap entry may now be EITHER a plain int (today, unchanged)
OR a mapping ``{"default": int, "per_host": {<host>: int}}``. These tests
pin: byte-identical dispatch decisions for every existing (int-only) config
shape, per-host refusal at the configured figure, and fail-closed handling
of an unparsable ``per_host`` value (never silently uncapped).

See ``tests/hermes_cli/test_kanban_per_profile_cap.py`` for the pre-existing
int/classic-mapping coverage this extension must not disturb.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest


@pytest.fixture()
def isolated_kanban_home_with_profiles(monkeypatch):
    """Spin up a fresh HERMES_HOME with kanban DB + a few profiles."""
    test_home = tempfile.mkdtemp(prefix="kanban_per_host_cap_test_")
    for prof in ("alpha", "beta", "dsh", "sonnet", "default"):
        os.makedirs(os.path.join(test_home, "profiles", prof), exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", test_home)
    for mod in list(sys.modules.keys()):
        if mod.startswith("hermes_cli") or mod.startswith("hermes_state") or mod == "hermes_constants":
            del sys.modules[mod]
    from hermes_cli import kanban_db
    yield kanban_db


def _fake_spawn(*args, **kwargs):
    return 12345


# --- byte-identical decisions for every existing (int-only) config shape ---


def test_normalize_live_config_shape_unchanged(isolated_kanban_home_with_profiles):
    """The exact live-on-k2vps shape (ADR-087: ``max_in_progress_per_profile:
    dsh: 1``) normalizes to itself, unchanged — no wrapping, no dict-of-dict
    promotion for plain ints."""
    kb = isolated_kanban_home_with_profiles
    live = {"dsh": 1, "sonnet": 4, "default": 2}
    normalized = kb._normalize_per_profile_cap(live)
    assert normalized == {"dsh": 1, "sonnet": 4, "default": 2}
    assert kb._resolve_profile_cap(normalized, "dsh") == 1
    assert kb._resolve_profile_cap(normalized, "sonnet") == 4
    assert kb._resolve_profile_cap(normalized, "beta") == 2  # falls to "default"
    # No profile in an int-only config has a per-host entry to narrow.
    assert kb._resolve_profile_host_cap(normalized, "dsh", "sov-core-01") is None


def test_dispatch_once_byte_identical_for_live_int_config(isolated_kanban_home_with_profiles):
    """dispatch_once's spawn/cap decisions for the live int-only shape are
    exactly what they were before this extension: dsh:1 dispatches exactly
    one worker and defers the rest to skipped_per_profile_capped."""
    kb = isolated_kanban_home_with_profiles
    with kb.connect_closing() as conn:
        kb.create_board(slug="default", name="Test")
        for i in range(3):
            kb.create_task(conn, title=f"d{i}", assignee="dsh")
    with kb.connect_closing() as conn:
        res = kb.dispatch_once(
            conn, spawn_fn=_fake_spawn, dry_run=True,
            max_in_progress_per_profile={"dsh": 1, "sonnet": 4, "default": 2},
        )
    spawned = [s[1] for s in res.spawned]
    capped = [c[1] for c in res.skipped_per_profile_capped]
    assert spawned.count("dsh") == 1, "dsh:1 must dispatch exactly one, exactly as ADR-087 pins today"
    assert capped.count("dsh") == 2


def test_int_entry_has_no_per_host_cap(isolated_kanban_home_with_profiles):
    """An int entry (today's shape) never has a host-scoped constraint —
    the byte-identical-decisions bar, restated at the resolver level."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap({"dsh": 1})
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") is None


# --- per-host cap: the new mapping-of-mapping shape -------------------------


def test_normalize_per_host_mapping_shape(isolated_kanban_home_with_profiles):
    kb = isolated_kanban_home_with_profiles
    raw = {"dsh": {"default": 4, "per_host": {"sov-core-01": 2, "spark-b01b": 1}}}
    normalized = kb._normalize_per_profile_cap(raw)
    assert normalized == {
        "dsh": {"default": 4, "per_host": {"sov-core-01": 2, "spark-b01b": 1}},
    }
    assert kb._resolve_profile_cap(normalized, "dsh") == 4
    assert kb._resolve_profile_host_cap(normalized, "dsh", "sov-core-01") == 2
    assert kb._resolve_profile_host_cap(normalized, "dsh", "spark-b01b") == 1
    # A host not named in per_host is unconstrained BY HOST (only the
    # profile's overall "default" cap applies).
    assert kb._resolve_profile_host_cap(normalized, "dsh", "unnamed-host") is None


def test_per_host_refusal_at_the_configured_figure(isolated_kanban_home_with_profiles):
    """Refuses a worker for a host once that host's own running count
    reaches its per_host figure — even though the profile's overall
    ("default") cap still has headroom."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"default": 10, "per_host": {"sov-core-01": 2}}}
    )
    host_cap = kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01")
    assert host_cap == 2
    assert 1 < host_cap, "below the figure: room"
    assert 2 >= host_cap, "at the figure: refuse"


def test_per_host_entry_unparsable_value_fails_closed(isolated_kanban_home_with_profiles):
    """THE RULING THIS PINS: an unparsable per_host entry disables that
    host (refuse) — it must NEVER be dropped/uncapped, unlike a bad
    top-level (profile-level) entry, which fails open (uncapped)."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"default": 4, "per_host": {"sov-core-01": "junk", "spark-b01b": 2}}}
    )
    assert cap["dsh"]["per_host"]["sov-core-01"] == 0, (
        "unparsable per_host value must fail CLOSED (0 == always refuse), "
        "never be dropped from the mapping (which would read as uncapped)"
    )
    assert cap["dsh"]["per_host"]["spark-b01b"] == 2
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 0
    # A cap of 0 refuses even a currently-idle host (running count 0).
    assert 0 >= kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01")


def test_per_host_negative_or_zero_value_fails_closed(isolated_kanban_home_with_profiles):
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"default": 4, "per_host": {"sov-core-01": 0, "spark-b01b": -1}}}
    )
    assert cap["dsh"]["per_host"]["sov-core-01"] == 0
    assert cap["dsh"]["per_host"]["spark-b01b"] == 0


def test_per_host_entry_missing_default_and_per_host_is_dropped(isolated_kanban_home_with_profiles):
    """An entry with neither a usable default nor any usable per_host data
    is dropped like any other invalid top-level entry (falls back to the
    outer 'default' key, or uncapped if there isn't one) — this is the
    fail-OPEN top-level behaviour, deliberately distinct from per_host's
    fail-CLOSED behaviour above."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"default": "junk", "per_host": {}}, "default": 3}
    )
    assert "dsh" not in cap
    assert kb._resolve_profile_cap(cap, "dsh") == 3


def test_per_host_entry_with_only_per_host_no_default(isolated_kanban_home_with_profiles):
    """A profile entry may narrow specific hosts without setting an
    overall default — the profile stays globally uncapped while specific
    hosts are still bounded."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap({"dsh": {"per_host": {"sov-core-01": 1}}})
    assert kb._resolve_profile_cap(cap, "dsh") is None
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 1


def test_resolve_profile_host_cap_none_cap_or_empty_host(isolated_kanban_home_with_profiles):
    kb = isolated_kanban_home_with_profiles
    assert kb._resolve_profile_host_cap(None, "dsh", "sov-core-01") is None
    assert kb._resolve_profile_host_cap({"dsh": 1}, "dsh", "") is None
    assert kb._resolve_profile_host_cap({"dsh": 1}, "dsh", None) is None
