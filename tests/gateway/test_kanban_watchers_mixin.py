"""Tests for the extracted GatewayKanbanWatchersMixin (god-file Phase 3).

The kanban watcher loops were lifted out of gateway/run.py into a mixin that
GatewayRunner inherits. These tests confirm the mixin exposes the methods and
that GatewayRunner picks them up via the MRO (behavior-neutral relocation).
"""

from __future__ import annotations

import inspect
import json

from gateway import kanban_watchers as kw
from gateway.kanban_watchers import GatewayKanbanWatchersMixin

KANBAN_METHODS = [
    "_kanban_notifier_watcher",
    "_kanban_dispatcher_watcher",
    "_kanban_advance",
    "_kanban_unsub",
    "_kanban_rewind",
    "_deliver_kanban_artifacts",
]


def test_mixin_defines_kanban_methods():
    for m in KANBAN_METHODS:
        assert hasattr(GatewayKanbanWatchersMixin, m), f"mixin missing {m}"


# --- dispatcher heartbeat (mesh t_e2f6312c) ---------------------------------
#
# The dispatcher's tick loop stopped claiming for ~16h on 2026-08-10 with no
# crash and no traceback — the gateway process itself stayed healthy. A
# zero-activity tick was never logged at all, so log silence could not tell
# "idle" from "dead". These tests cover the pure heartbeat writer directly,
# since the loop that calls it is an always-running async coroutine that
# isn't practical to drive end-to-end in a unit test.


def test_write_dispatcher_heartbeat_writes_atomically(tmp_path, monkeypatch):
    path = tmp_path / "kanban_dispatcher_status.json"
    monkeypatch.setattr(kw, "_DISPATCHER_HEARTBEAT_PATH", path)
    kw._write_dispatcher_heartbeat(interval_s=90.0, bad_ticks=0)
    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    doc = json.loads(path.read_text())
    assert doc["interval_s"] == 90.0
    assert doc["bad_ticks"] == 0
    assert "ts" in doc and "iso" in doc


def test_write_dispatcher_heartbeat_overwrites_on_every_call(tmp_path, monkeypatch):
    path = tmp_path / "kanban_dispatcher_status.json"
    monkeypatch.setattr(kw, "_DISPATCHER_HEARTBEAT_PATH", path)
    kw._write_dispatcher_heartbeat(interval_s=90.0, bad_ticks=3)
    first = json.loads(path.read_text())
    kw._write_dispatcher_heartbeat(interval_s=90.0, bad_ticks=0)
    second = json.loads(path.read_text())
    # Unconditional per-tick call: a healthy tick after a stuck run must
    # overwrite, not append — a watcher reads the latest state only.
    assert first["bad_ticks"] == 3
    assert second["bad_ticks"] == 0
    assert second["ts"] >= first["ts"]


def test_write_dispatcher_heartbeat_never_raises_on_bad_path(monkeypatch):
    # A directory that cannot be created (parent is a file, not a dir) must
    # not propagate — the heartbeat writer's whole job is to never be able
    # to take down the loop it reports on.
    monkeypatch.setattr(kw, "_DISPATCHER_HEARTBEAT_PATH", __file__ + "/impossible/status.json")
    kw._write_dispatcher_heartbeat(interval_s=90.0, bad_ticks=0)  # must not raise


