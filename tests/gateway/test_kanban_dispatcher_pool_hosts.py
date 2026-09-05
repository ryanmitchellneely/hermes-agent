"""Tests for the Phase 2 R5 dispatcher-startup pool-state helpers in
gateway/kanban_watchers.py — docs/build-plans/2026-09-03-sandbox-mesh-
phase2.md "Dispatcher side". Both functions are pure and called once at
dispatcher start purely to produce the operator-visible startup log line
("kanban dispatcher: per-host caps=..." / "...pool hosts enabled=...");
neither makes a dispatch/cap decision itself — see
tests/hermes_cli/test_kanban_per_host_cap.py and
tests/hermes_cli/test_sandbox_hosts.py for the functions that do.

Mirrors the extraction pattern _resolve_auto_decompose_settings already
established (tests/gateway/test_kanban_auto_decompose_live.py): the full
``_kanban_dispatcher_watcher`` loop is an always-running async coroutine
that isn't practical to drive end-to-end in a unit test, so the config-
parsing logic it depends on is pulled into small top-level functions that
are tested directly instead.
"""
from __future__ import annotations

import tempfile

import yaml

from gateway.kanban_watchers import _per_host_caps_preview, _resolve_pool_hosts


# --- _per_host_caps_preview --------------------------------------------------


def test_preview_empty_for_plain_int_config():
    assert _per_host_caps_preview(2) == {}


def test_preview_empty_for_none_config():
    assert _per_host_caps_preview(None) == {}


def test_preview_empty_for_classic_mapping_shape():
    """Today's shape (2026-08-13 ruling: sonnet widened to 6) has nothing
    per-host to show."""
    assert _per_host_caps_preview({"sonnet": 6, "default": 2}) == {}


def test_preview_surfaces_per_host_entries_only():
    raw = {
        "dsh": {"default": 4, "per_host": {"sov-core-01": 2}},
        "sonnet": 6,
    }
    assert _per_host_caps_preview(raw) == {"dsh": {"sov-core-01": 2}}


def test_preview_never_raises_on_garbage_input():
    assert _per_host_caps_preview(object()) == {}
    assert _per_host_caps_preview("garbage") == {}
    assert _per_host_caps_preview([1, 2, 3]) == {}


# --- _resolve_pool_hosts ------------------------------------------------------


def test_resolve_pool_hosts_reads_the_reviewed_file(tmp_path):
    doc = {
        "hosts": [
            {
                "name": "sov-core-01",
                "address": "100.1.1.1",
                "account": "t1000-pool",
                "identity_file": "/opt/t1000/home/.ssh/pool_key",
                "enabled": True,
                "arch": "amd64",
                "max_in_progress": 2,
            },
        ]
    }
    (tmp_path / "sandbox_hosts.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    hosts = _resolve_pool_hosts(tmp_path)
    assert [h.name for h in hosts] == ["sov-core-01"]


def test_resolve_pool_hosts_missing_file_returns_empty():
    with tempfile.TemporaryDirectory() as d:
        assert _resolve_pool_hosts(d) == []


def test_resolve_pool_hosts_never_raises_on_bad_home():
    # A value sandbox_hosts_path can't even join (e.g. None) must still
    # fail safe to [] rather than raise and take dispatcher startup down.
    assert _resolve_pool_hosts(None) == []
