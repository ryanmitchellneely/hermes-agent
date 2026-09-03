#!/usr/bin/env python3
"""Distillery intake sweep heartbeat leg of the ops pulse (mesh t_a4d3ea5b).

The sweep ran for three weeks against nonexistent source paths and its cron
reported "silent (empty output)" — the same signature as a clean tick. These
fixtures pin the four states that must page and the two that must not:

  - fresh state, every source counted            -> silent
  - state file missing                           -> WARN (sweep never ran)
  - state older than the threshold               -> WARN STALE
  - a source whose path does not exist           -> WARN MISSING
  - a source at zero on ONE sweep                -> silent (transient)
  - the same source at zero on TWO sweeps        -> WARN persistent

Run: python3 -m unittest test_t1000_ops_alert_pulse_distillery_intake
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "t1000_ops_alert_pulse.py"


def _load_module(home: Path):
    os.environ["HERMES_HOME"] = str(home)
    spec = importlib.util.spec_from_file_location("t1000_ops_pulse_distillery_uut", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.HOME = home
    mod.DESK = home
    mod.STATE_PATH = home / "cache" / "ops-alert-pulse-state.json"
    return mod


def _ts(age_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class DistilleryIntakeBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_module(self.home)
        self.state_path = self.home / "cache" / "distillery-intake-sweep-state.json"

    def write_state(self, **overrides):
        st = {
            "ts": _ts(),
            "new": 0,
            "stale": 0,
            "superseded": 0,
            "total_rows": 10,
            "sources": {
                "plan": {"path": "/x/plans", "exists": True, "count": 6},
                "signal_log_entry": {"path": "/x/sig", "exists": True, "count": 80},
                "mesh_done_card:steals": {"path": "/x/steals.db", "exists": True, "count": 12},
            },
        }
        st.update(overrides)
        self.state_path.write_text(json.dumps(st))
        return st


class SilentTests(DistilleryIntakeBase):
    def test_fresh_state_with_counts_is_silent(self):
        self.write_state()
        self.assertEqual(self.mod._distillery_intake(), [])

    def test_zero_on_one_sweep_is_silent_but_remembered(self):
        st = self.write_state()
        st["sources"]["plan"]["count"] = 0
        self.state_path.write_text(json.dumps(st))
        self.assertEqual(self.mod._distillery_intake(), [])
        saved = json.loads(self.state_path.read_text())
        self.assertEqual(saved["prev_zero_sources"], ["plan"])


class PagingTests(DistilleryIntakeBase):
    def test_missing_state_file_warns(self):
        warns = self.mod._distillery_intake()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("never ran", warns[0])

    def test_stale_state_warns_stale(self):
        self.write_state(ts=_ts(int(self.mod.DISTILLERY_INTAKE_STALE_SECS) + 3600))
        warns = self.mod._distillery_intake()
        self.assertTrue(any("STALE" in w for w in warns), warns)

    def test_missing_source_path_warns_missing(self):
        st = self.write_state()
        st["sources"]["signal_log_entry"] = {"path": "/nope", "exists": False, "count": 0}
        self.state_path.write_text(json.dumps(st))
        warns = self.mod._distillery_intake()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("MISSING", warns[0])
        self.assertIn("signal_log_entry", warns[0])

    def test_zero_on_two_consecutive_sweeps_warns(self):
        st = self.write_state(prev_zero_sources=["plan"])
        st["sources"]["plan"]["count"] = 0
        self.state_path.write_text(json.dumps(st))
        warns = self.mod._distillery_intake()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("two consecutive", warns[0])
        self.assertIn("plan", warns[0])

    def test_old_state_without_sources_map_warns_once(self):
        st = self.write_state()
        del st["sources"]
        self.state_path.write_text(json.dumps(st))
        warns = self.mod._distillery_intake()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("no per-source counts", warns[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
