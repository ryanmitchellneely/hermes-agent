"""Tests for hermes_cli/sandbox_hosts.py — Phase 2 R5's reviewed constant
list of pooled sandbox hosts (docs/build-plans/2026-09-03-sandbox-mesh-
phase2.md "Dispatcher side").

Fail-closed on every ambiguous case: missing/unparsable file -> no hosts,
non-amd64 excluded, disabled excluded, a duplicate name refuses the WHOLE
file. The loader and selector never discover hosts at runtime — no
network, no DNS, no subprocess/tailscale call anywhere in this module.

Round 3 (2026-09-05, captain's decision): a row is host identity and
transport ONLY — name, address, account, identity_file, host_key, enabled,
arch. There is no per-row capacity figure any more; the per-host cap comes
exclusively from config.yaml's kanban.max_in_progress_per_profile.<profile>
.per_host, resolved via kanban_db._resolve_profile_host_cap and threaded
into select_pool_host's host_cap argument.
"""
from __future__ import annotations

import socket
import subprocess

import yaml

from hermes_cli import sandbox_hosts as sh


def _write(tmp_path, doc):
    path = tmp_path / "sandbox_hosts.yaml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return path


HOST_A = {
    "name": "sov-core-01",
    "address": "100.1.1.1",
    "account": "t1000-pool",
    "identity_file": "/opt/t1000/home/.ssh/pool_key",
    "host_key": "sov-core-01.tailnet ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA-host-a",
    "enabled": True,
    "arch": "amd64",
}
HOST_B = {
    "name": "sov-forge",
    "address": "100.1.1.2",
    "account": "t1000-pool",
    "identity_file": "/opt/t1000/home/.ssh/pool_key",
    "host_key": "sov-forge.tailnet ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA-host-b",
    "enabled": True,
    "arch": "amd64",
}


# --- sandbox_hosts_path ------------------------------------------------------


def test_sandbox_hosts_path_is_direct_child_of_hermes_home(tmp_path):
    assert sh.sandbox_hosts_path(tmp_path) == tmp_path / "sandbox_hosts.yaml"


# --- load_sandbox_hosts: fail-closed shapes ---------------------------------


def test_missing_file_returns_no_hosts(tmp_path):
    assert sh.load_sandbox_hosts(tmp_path / "sandbox_hosts.yaml") == []


def test_unparsable_yaml_returns_no_hosts(tmp_path):
    path = tmp_path / "sandbox_hosts.yaml"
    path.write_text("hosts: [this is not: valid: yaml: at all", encoding="utf-8")
    assert sh.load_sandbox_hosts(path) == []


def test_wrong_top_level_shape_returns_no_hosts(tmp_path):
    path = _write(tmp_path, ["not", "a", "mapping"])
    assert sh.load_sandbox_hosts(path) == []


def test_hosts_key_not_a_list_returns_no_hosts(tmp_path):
    path = _write(tmp_path, {"hosts": "nope"})
    assert sh.load_sandbox_hosts(path) == []


def test_hosts_key_missing_returns_no_hosts(tmp_path):
    path = _write(tmp_path, {"other_key": 1})
    assert sh.load_sandbox_hosts(path) == []


def test_empty_hosts_list_returns_no_hosts(tmp_path):
    path = _write(tmp_path, {"hosts": []})
    assert sh.load_sandbox_hosts(path) == []


# --- load_sandbox_hosts: filtering ------------------------------------------


def test_enabled_amd64_host_is_returned(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]
    assert hosts[0].arch == "amd64"
    assert hosts[0].address == "100.1.1.1"


def test_non_amd64_host_excluded(tmp_path):
    aarch64_host = {**HOST_A, "name": "kevin-spark", "arch": "aarch64", "enabled": True}
    path = _write(tmp_path, {"hosts": [aarch64_host]})
    assert sh.load_sandbox_hosts(path) == []


def test_disabled_host_excluded(tmp_path):
    disabled = {**HOST_A, "enabled": False}
    path = _write(tmp_path, {"hosts": [disabled]})
    assert sh.load_sandbox_hosts(path) == []


def test_enabled_as_truthy_string_is_not_true_fails_closed(tmp_path):
    """Strict boolean check — a YAML string "true" (or any non-bool
    truthy value) must NOT count as enabled."""
    stringy = {**HOST_A, "enabled": "true"}
    path = _write(tmp_path, {"hosts": [stringy]})
    assert sh.load_sandbox_hosts(path) == []


def test_enabled_missing_defaults_to_excluded(tmp_path):
    no_enabled_key = {k: v for k, v in HOST_A.items() if k != "enabled"}
    path = _write(tmp_path, {"hosts": [no_enabled_key]})
    assert sh.load_sandbox_hosts(path) == []


def test_duplicate_name_refuses_whole_file(tmp_path):
    dup = {**HOST_B, "name": "sov-core-01"}
    path = _write(tmp_path, {"hosts": [HOST_A, dup]})
    assert sh.load_sandbox_hosts(path) == [], "a duplicate name must refuse the WHOLE file"


def test_duplicate_name_refuses_even_when_one_copy_ineligible(tmp_path):
    """A name collision is a structural review error independent of
    enabled/arch — must refuse even if only one copy would have been
    eligible on its own."""
    dup_ineligible = {**HOST_A, "enabled": False, "arch": "aarch64"}
    path = _write(tmp_path, {"hosts": [HOST_A, dup_ineligible]})
    assert sh.load_sandbox_hosts(path) == []


def test_entry_missing_name_dropped_not_whole_file(tmp_path):
    nameless = {k: v for k, v in HOST_B.items() if k != "name"}
    path = _write(tmp_path, {"hosts": [HOST_A, nameless]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]


def test_multiple_enabled_amd64_hosts_preserve_file_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_B, HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-forge", "sov-core-01"], (
        "file order must be preserved, never reordered by name/capacity/etc."
    )


# --- load_sandbox_hosts: round 3 schema — identity/transport only, no cap --


def test_row_with_the_seven_schema_fields_loads(tmp_path):
    """The full agreed row schema (captain's round-3 decision): name,
    address, account, identity_file, host_key, enabled, arch. All seven
    are accepted; the six non-name fields land on the returned object
    exactly as written (enabled is a gate, not a stored field — by
    construction every returned host was enabled)."""
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert len(hosts) == 1
    host = hosts[0]
    assert host.name == "sov-core-01"
    assert host.address == "100.1.1.1"
    assert host.account == "t1000-pool"
    assert host.identity_file == "/opt/t1000/home/.ssh/pool_key"
    assert host.host_key == "sov-core-01.tailnet ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA-host-a"
    assert host.arch == "amd64"


def test_row_without_max_in_progress_loads_identically(tmp_path):
    """THE ROUND-3 REGRESSION THE CRITIC FOUND, pinned: the K2 wrapper's
    own loader never reads a per-row capacity figure, so a row that omits
    ``max_in_progress`` entirely — exactly what a K2-side-authored file
    looks like — must load IDENTICALLY to one that includes it. Before
    this round, ``int(raw.get("max_in_progress"))`` raised on the missing
    key and the entry was silently dropped.

    THE MUTATION TARGET for this round: restoring that requirement must
    turn this test red.
    """
    without_cap = HOST_A  # HOST_A never carries a max_in_progress key at all
    with_cap = {**HOST_A, "max_in_progress": 2}  # a stray/legacy key is just ignored
    assert "max_in_progress" not in without_cap  # sanity-check the fixture

    dir_without = tmp_path / "without"
    dir_with = tmp_path / "with"
    dir_without.mkdir()
    dir_with.mkdir()

    hosts_without = sh.load_sandbox_hosts(_write(dir_without, {"hosts": [without_cap]}))
    hosts_with = sh.load_sandbox_hosts(_write(dir_with, {"hosts": [with_cap]}))

    assert len(hosts_without) == 1
    assert hosts_without == hosts_with, (
        "a row without max_in_progress must load byte-identically to the "
        "same row with an (ignored) max_in_progress key"
    )
    assert hosts_without[0].name == "sov-core-01"


def test_host_key_and_identity_file_pass_through_unchanged(tmp_path):
    """Both opaque-string fields are stored exactly as written — never
    trimmed, validated, or transformed."""
    raw = {
        **HOST_A,
        "identity_file": "  /opt/t1000/home/.ssh/pool_key  ",
        "host_key": "ssh-ed25519 AAAA_NOT_A_REAL_KEY_JUST_A_STRING user@host",
    }
    path = _write(tmp_path, {"hosts": [raw]})
    hosts = sh.load_sandbox_hosts(path)
    assert hosts[0].identity_file == "  /opt/t1000/home/.ssh/pool_key  "
    assert hosts[0].host_key == "ssh-ed25519 AAAA_NOT_A_REAL_KEY_JUST_A_STRING user@host"


def test_unknown_extra_key_is_ignored(tmp_path):
    """A key this loader doesn't recognize (a stale max_in_progress, or
    anything else) is never a reason to drop the entry or the file — the
    row still loads with exactly the seven recognized fields honoured."""
    raw = {**HOST_A, "max_in_progress": "not-a-number", "some_future_field": {"nested": True}}
    path = _write(tmp_path, {"hosts": [raw]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]
    assert hosts[0].address == "100.1.1.1"


# --- select_pool_host: deterministic, list-order, no discovery -------------


def test_selector_picks_first_host_with_room_in_list_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    host_cap = {"sov-core-01": 2, "sov-forge": 1}
    assert sh.select_pool_host(hosts, {}, host_cap=host_cap) == "sov-core-01"


def test_selector_skips_full_host_for_next_in_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    host_cap = {"sov-core-01": 2, "sov-forge": 1}
    assert sh.select_pool_host(hosts, {"sov-core-01": 2}, host_cap=host_cap) == "sov-forge"


def test_selector_returns_none_when_all_hosts_full(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    host_cap = {"sov-core-01": 2, "sov-forge": 1}
    result = sh.select_pool_host(
        hosts, {"sov-core-01": 2, "sov-forge": 1}, host_cap=host_cap
    )
    assert result is None, "None means 'fall back to k2vps locally', exactly today"


def test_selector_never_selects_a_host_absent_from_the_file(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    result = sh.select_pool_host(
        hosts,
        {"ghost-host": 0, "sov-core-01": 2},
        host_cap={"ghost-host": 5, "sov-core-01": 2},
    )
    assert result is None
    assert result != "ghost-host"


def test_selector_uses_the_configured_host_cap_directly(tmp_path):
    """Round 3: the row no longer carries its own max_in_progress —
    host_cap (built from kanban_db._resolve_profile_host_cap) is the ONLY
    source of capacity now, used as-is, never composed against a per-row
    figure that no longer exists."""
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert sh.select_pool_host(hosts, {"sov-core-01": 1}, host_cap={"sov-core-01": 2}) == "sov-core-01"
    assert sh.select_pool_host(hosts, {"sov-core-01": 2}, host_cap={"sov-core-01": 2}) is None
    # host_cap of 0 (a fail-closed per_host figure) refuses outright, even
    # at a running count of 0.
    assert sh.select_pool_host(hosts, {"sov-core-01": 0}, host_cap={"sov-core-01": 0}) is None


def test_selector_refuses_host_with_neither_per_host_nor_default(tmp_path):
    """THE ROUND-3 FAIL-CLOSED RULE (captain's decision): a host absent
    from host_cap, or resolving to None ("no per_host entry and no
    default" for that profile — kanban_db._resolve_profile_host_cap's own
    words), is refused outright — never falls back to "uncapped". There is
    no row-level max_in_progress left to fall back on any more."""
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert sh.select_pool_host(hosts, {}, host_cap={}) is None
    assert sh.select_pool_host(hosts, {}, host_cap={"sov-core-01": None}) is None
    # host_cap omitted entirely -- still refused, never unconstrained.
    assert sh.select_pool_host(hosts, {}) is None
    assert sh.select_pool_host(hosts) is None


def test_selector_honours_config_yaml_per_host_cap_via_resolver(tmp_path):
    """End-to-end round 2 + round 3: the per-host cap comes from
    config.yaml's kanban.max_in_progress_per_profile.<profile>.per_host,
    resolved through kanban_db._resolve_profile_host_cap — never from the
    reviewed row itself, which carries no cap of its own any more."""
    from hermes_cli.kanban_db import _normalize_per_profile_cap, _resolve_profile_host_cap

    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    config_cap = _normalize_per_profile_cap(
        {"dsh": {"default": 4, "per_host": {"sov-core-01": 1}}}
    )
    host_cap = {h.name: _resolve_profile_host_cap(config_cap, "dsh", h.name) for h in hosts}
    # sov-core-01 narrowed to 1 by its own per_host entry; sov-forge (not
    # listed in per_host) falls back to the profile's own "default" of 4.
    assert host_cap == {"sov-core-01": 1, "sov-forge": 4}
    assert sh.select_pool_host(hosts, {"sov-core-01": 1}, host_cap=host_cap) == "sov-forge"
    assert sh.select_pool_host(hosts, {"sov-core-01": 0}, host_cap=host_cap) == "sov-core-01"

    # A profile with no cap entry and no top-level "default" at all -- both
    # hosts refuse (never uncapped), per the same resolver.
    no_cap_config = _normalize_per_profile_cap({"sonnet": 6})
    no_host_cap = {
        h.name: _resolve_profile_host_cap(no_cap_config, "dsh", h.name) for h in hosts
    }
    assert no_host_cap == {"sov-core-01": None, "sov-forge": None}
    assert sh.select_pool_host(hosts, {}, host_cap=no_host_cap) is None


def test_selector_empty_hosts_list_returns_none():
    assert sh.select_pool_host([], {"anything": 0}) is None


def test_selector_defaults_running_count_to_zero(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert sh.select_pool_host(hosts, host_cap={"sov-core-01": 2}) == "sov-core-01"


# --- pool_host_env: the one env-var handshake -------------------------------


def test_pool_host_env_set_when_a_host_selected():
    assert sh.pool_host_env("sov-core-01") == {"DSH_POOL_HOST": "sov-core-01"}


def test_pool_host_env_empty_when_none_selected():
    assert sh.pool_host_env(None) == {}


def test_pool_host_env_empty_when_empty_string():
    assert sh.pool_host_env("") == {}


# --- no runtime discovery, anywhere in load or select -----------------------


def test_load_and_select_never_touch_the_network(tmp_path, monkeypatch):
    """Patch socket + subprocess so any discovery attempt raises; load and
    select must complete without ever calling either — membership is
    exactly what the reviewed file says."""

    def _boom_getaddrinfo(*a, **k):
        raise AssertionError("sandbox_hosts must never call socket.getaddrinfo (no runtime discovery)")

    def _boom_run(*a, **k):
        raise AssertionError("sandbox_hosts must never call subprocess.run (no runtime discovery)")

    def _boom_popen(*a, **k):
        raise AssertionError("sandbox_hosts must never call subprocess.Popen (no runtime discovery)")

    monkeypatch.setattr(socket, "getaddrinfo", _boom_getaddrinfo)
    monkeypatch.setattr(subprocess, "run", _boom_run)
    monkeypatch.setattr(subprocess, "Popen", _boom_popen)

    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    assert len(hosts) == 2
    selected = sh.select_pool_host(
        hosts, {"sov-core-01": 2}, host_cap={"sov-core-01": 2, "sov-forge": 1}
    )
    assert selected == "sov-forge"
    env = sh.pool_host_env(selected)
    assert env == {"DSH_POOL_HOST": "sov-forge"}
