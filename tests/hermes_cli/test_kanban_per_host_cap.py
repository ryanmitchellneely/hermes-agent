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
    # An int entry has no host-scoped data to narrow it -- so it applies
    # for every host, unchanged, exactly like _resolve_profile_cap's own
    # answer (2026-09-05: the resolution rule is now one function, same
    # behaviour for every entry shape -- see _resolve_profile_host_cap).
    assert kb._resolve_profile_host_cap(normalized, "dsh", "sov-core-01") == 1


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


def test_int_entry_returns_that_cap_for_every_host(isolated_kanban_home_with_profiles):
    """An int entry (today's shape) has no host-scoped data to narrow it
    with, so the SAME resolution rule (see _resolve_profile_host_cap)
    returns that cap for every host queried — never None/unconstrained,
    never host-specific. dispatch_once itself never calls this resolver
    (still an unwired stub — Phase 2 R1-R4), so this is purely about the
    resolver's own documented contract, not a live dispatch-decision
    change."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap({"dsh": 1})
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 1
    assert kb._resolve_profile_host_cap(cap, "dsh", "some-other-host") == 1


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
    # A host not named in per_host falls back to the profile's own
    # "default" (2026-09-05: closes the asymmetry with _resolve_profile_cap's
    # own profile->"default" fallback -- see _resolve_profile_host_cap).
    assert kb._resolve_profile_host_cap(normalized, "dsh", "unnamed-host") == 4


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


# --- round-2 fail-closed parse edges (critic MINORs, 2026-09-05) ------------


def test_per_host_bool_figure_fails_closed(isolated_kanban_home_with_profiles):
    """A YAML boolean literal for one host's figure must NOT parse as
    int(True) == 1 / int(False) == 0 via Python's bool-is-an-int-subclass
    quirk -- it is refused (normalized to 0) exactly like any other
    unparsable figure, never silently accepted as a typed cap."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {
            "dsh": {
                "default": 4,
                "per_host": {"sov-core-01": True, "spark-b01b": False, "sov-forge": 2},
            }
        }
    )
    assert cap["dsh"]["per_host"]["sov-core-01"] == 0, (
        "bool True must fail CLOSED (0), never silently parse as int(True) == 1"
    )
    assert cap["dsh"]["per_host"]["spark-b01b"] == 0, (
        "bool False must also refuse -- it must never coincidentally read as "
        "'correctly parsed to 0', it was never a valid figure to begin with"
    )
    assert cap["dsh"]["per_host"]["sov-forge"] == 2, "a real int figure is untouched"
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 0
    assert kb._resolve_profile_host_cap(cap, "dsh", "spark-b01b") == 0


def test_per_host_non_mapping_block_refuses_whole_profile(isolated_kanban_home_with_profiles):
    """When the ENTIRE per_host value isn't a mapping (a list, a string,
    an int -- or a bool, structurally the same failure), the profile's
    per-host data is unparsable: refuse pool dispatch for EVERY host on
    that profile. Never falls back to unconstrained (None) and never
    falls back to the entry's own valid "default", even when "default"
    is itself perfectly usable."""
    kb = isolated_kanban_home_with_profiles
    for bad_per_host in ([1, 2, 3], "not-a-dict", 5, True, 5.5):
        cap = kb._normalize_per_profile_cap(
            {"dsh": {"default": 4, "per_host": bad_per_host}}
        )
        assert cap["dsh"]["per_host"] is None, (
            f"malformed per_host {bad_per_host!r} must normalize to the "
            "refuse-every-host sentinel (None), not {} (unconstrained)"
        )
        assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 0
        assert kb._resolve_profile_host_cap(cap, "dsh", "some-other-host") == 0, (
            "refuses EVERY host, not just one named in the (malformed) block"
        )


def test_per_host_non_mapping_block_refuses_even_without_a_default(isolated_kanban_home_with_profiles):
    """The malformed-per_host sentinel must survive even when "default"
    is ALSO unusable -- the entry must not be dropped (which would fall
    back to the outer "default" profile, or to fully uncapped): a
    profile whose per_host block could not be parsed must stay refused,
    not silently disappear into some other cap."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"per_host": "garbage"}, "default": 9}
    )
    assert "dsh" in cap, "a malformed per_host block must keep the entry, not drop it"
    assert cap["dsh"]["per_host"] is None
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 0
    # Confirm it's really refusing, not silently inheriting the outer default=9.
    assert kb._resolve_profile_cap(cap, "dsh") is None


def test_resolve_host_cap_missing_default_uses_valid_per_host(isolated_kanban_home_with_profiles):
    """No usable "default" on the entry at all -- the queried host's own
    per_host figure, when valid, still resolves (most-specific wins even
    when there's nothing broader to fall back to)."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap({"dsh": {"per_host": {"sov-core-01": 3}}})
    assert kb._resolve_profile_host_cap(cap, "dsh", "sov-core-01") == 3


def test_resolve_host_cap_missing_per_host_entry_uses_valid_default(isolated_kanban_home_with_profiles):
    """The queried host has no entry in per_host at all, but the
    profile's own "default" is valid -- resolves via the default. Same
    "most-specific-wins, else the broader figure applies" rule as
    _resolve_profile_cap's profile->"default" fallback, one level down."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"dsh": {"default": 5, "per_host": {"sov-core-01": 2}}}
    )
    assert kb._resolve_profile_host_cap(cap, "dsh", "some-other-host") == 5


def test_resolve_host_cap_both_missing_refuses(isolated_kanban_home_with_profiles):
    """Neither the queried host's own per_host figure nor the profile's
    "default" resolves to anything usable -- refuse (0), never None
    (which would read as "unconstrained")."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap({"dsh": {"per_host": {"sov-core-01": 3}}})
    assert kb._resolve_profile_host_cap(cap, "dsh", "some-other-host") == 0


def test_resolve_host_cap_outer_default_fallback_closes_asymmetry(isolated_kanban_home_with_profiles):
    """Direct regression test for the critic's own probe (round-1 review,
    MINOR #3): a profile absent from cap entirely inherits the outer
    "default" profile's mapping entry (exactly like _resolve_profile_cap
    already did), and THEN resolves per-host on top of it -- both the
    per_host-listed host and an unlisted one now resolve correctly for
    an "unlisted" profile name that was never a key in cap at all."""
    kb = isolated_kanban_home_with_profiles
    cap = kb._normalize_per_profile_cap(
        {"default": {"default": 5, "per_host": {"sov-core-01": 1}}, "sonnet": 6}
    )
    assert kb._resolve_profile_cap(cap, "unlisted") == 5
    assert kb._resolve_profile_host_cap(cap, "unlisted", "sov-core-01") == 1
    assert kb._resolve_profile_host_cap(cap, "unlisted", "some-other-host") == 5
