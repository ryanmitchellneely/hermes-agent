"""Tests for hermes_cli/sandbox_hosts.py — Phase 2 R5's reviewed constant
list of pooled sandbox hosts (docs/build-plans/2026-09-03-sandbox-mesh-
phase2.md "Dispatcher side").

Fail-closed on every ambiguous case: missing/unparsable file -> no hosts,
non-amd64 excluded, disabled excluded, a duplicate name refuses the WHOLE
file. The loader and selector never discover hosts at runtime — no
network, no DNS, no subprocess/tailscale call anywhere in this module.
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
    "enabled": True,
    "arch": "amd64",
    "max_in_progress": 2,
}
HOST_B = {
    "name": "sov-forge",
    "address": "100.1.1.2",
    "account": "t1000-pool",
    "identity_file": "/opt/t1000/home/.ssh/pool_key",
    "enabled": True,
    "arch": "amd64",
    "max_in_progress": 1,
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
    assert hosts[0].max_in_progress == 2
    assert hosts[0].arch == "amd64"
    assert hosts[0].address == "100.1.1.1"


def test_non_amd64_host_excluded(tmp_path):
    """THE MUTATION m1 TARGET: the arch filter must actually exclude a
    non-amd64 host, never let it through."""
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


def test_malformed_single_entry_dropped_not_whole_file(tmp_path):
    """A host missing a usable capacity figure is dropped; the rest of
    the reviewed list still loads."""
    broken = {**HOST_B, "name": "broken-host", "max_in_progress": "not-a-number"}
    path = _write(tmp_path, {"hosts": [HOST_A, broken]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]


def test_entry_missing_name_dropped_not_whole_file(tmp_path):
    nameless = {k: v for k, v in HOST_B.items() if k != "name"}
    path = _write(tmp_path, {"hosts": [HOST_A, nameless]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]


def test_non_positive_max_in_progress_dropped(tmp_path):
    zero_cap = {**HOST_B, "name": "zero-cap-host", "max_in_progress": 0}
    path = _write(tmp_path, {"hosts": [HOST_A, zero_cap]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-core-01"]


def test_multiple_enabled_amd64_hosts_preserve_file_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_B, HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert [h.name for h in hosts] == ["sov-forge", "sov-core-01"], (
        "file order must be preserved, never reordered by name/capacity/etc."
    )


# --- select_pool_host: deterministic, list-order, no discovery -------------


def test_selector_picks_first_host_with_room_in_list_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    assert sh.select_pool_host(hosts, {}) == "sov-core-01"


def test_selector_skips_full_host_for_next_in_order(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    # sov-core-01's own max_in_progress is 2.
    assert sh.select_pool_host(hosts, {"sov-core-01": 2}) == "sov-forge"


def test_selector_returns_none_when_all_hosts_full(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A, HOST_B]})
    hosts = sh.load_sandbox_hosts(path)
    result = sh.select_pool_host(hosts, {"sov-core-01": 2, "sov-forge": 1})
    assert result is None, "None means 'fall back to k2vps locally', exactly today"


def test_selector_never_selects_a_host_absent_from_the_file(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    result = sh.select_pool_host(hosts, {"ghost-host": 0, "sov-core-01": 2})
    assert result is None
    assert result != "ghost-host"


def test_selector_composes_host_cap_as_a_minimum(tmp_path):
    """A profile's per-host cap narrows the host's own max_in_progress —
    it never raises the ceiling above the host's own figure."""
    path = _write(tmp_path, {"hosts": [HOST_A]})  # own max_in_progress: 2
    hosts = sh.load_sandbox_hosts(path)
    # Narrowed to 1 for this profile; running count 1 must refuse.
    assert sh.select_pool_host(hosts, {"sov-core-01": 1}, host_cap={"sov-core-01": 1}) is None
    # host_cap higher than the host's own figure never raises the ceiling
    # (running=2 still hits the host's own max_in_progress of 2).
    assert sh.select_pool_host(hosts, {"sov-core-01": 2}, host_cap={"sov-core-01": 99}) is None
    # host_cap of 0 (fail-closed per_host figure) refuses outright.
    assert sh.select_pool_host(hosts, {"sov-core-01": 0}, host_cap={"sov-core-01": 0}) is None


def test_selector_empty_hosts_list_returns_none():
    assert sh.select_pool_host([], {"anything": 0}) is None


def test_selector_defaults_running_count_to_zero(tmp_path):
    path = _write(tmp_path, {"hosts": [HOST_A]})
    hosts = sh.load_sandbox_hosts(path)
    assert sh.select_pool_host(hosts) == "sov-core-01"


# --- pool_host_env: the one env-var handshake -------------------------------


def test_pool_host_env_set_when_a_host_selected():
    assert sh.pool_host_env("sov-core-01") == {"DSH_POOL_HOST": "sov-core-01"}


def test_pool_host_env_empty_when_none_selected():
    assert sh.pool_host_env(None) == {}


def test_pool_host_env_empty_when_empty_string():
    assert sh.pool_host_env("") == {}


# --- no runtime discovery, anywhere in load or select -----------------------


def test_load_and_select_never_touch_the_network(tmp_path, monkeypatch):
    """THE MUTATION m3 TARGET: patch socket + subprocess so any discovery
    attempt raises; load and select must complete without ever calling
    either — membership is exactly what the reviewed file says."""

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
    selected = sh.select_pool_host(hosts, {"sov-core-01": 2})
    assert selected == "sov-forge"
    env = sh.pool_host_env(selected)
    assert env == {"DSH_POOL_HOST": "sov-forge"}
