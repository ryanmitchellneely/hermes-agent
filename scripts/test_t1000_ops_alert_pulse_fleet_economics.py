#!/usr/bin/env python3
"""Fleet-economics weekly heartbeat leg of the ops pulse (t_da2f74c4).

t1000_fleet_economics_weekly.py writes cache/fleet-economics-weekly-heartbeat.json
on every run (clean or degraded), scheduled Mondays 13:00 local (hermes cron
fd3903262e8b). These fixtures pin the states that must page and the one that
must not:

  - fresh state, every input ok                  -> silent
  - state file missing                           -> WARN (cron never landed)
  - state older than the threshold               -> WARN STALE
  - an input reports ok: false                   -> WARN naming it

Run: python3 -m unittest test_t1000_ops_alert_pulse_fleet_economics
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
    spec = importlib.util.spec_from_file_location("t1000_ops_pulse_fleetecon_uut", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.HOME = home
    mod.DESK = home
    mod.STATE_PATH = home / "cache" / "ops-alert-pulse-state.json"
    mod.FLEET_ECON_HEARTBEAT_PATH = home / "cache" / "fleet-economics-weekly-heartbeat.json"
    return mod


def _ts(age_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class FleetEconomicsBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_module(self.home)
        self.hb_path = self.home / "cache" / "fleet-economics-weekly-heartbeat.json"

    def write_hb(self, **overrides):
        hb = {
            "ts": _ts(),
            "week": "2026-W36",
            "inputs": {
                "distillery_state": {"ok": True, "newest": _ts(), "note": "fine"},
                "kanban": {"ok": True, "newest": _ts(), "note": "fine"},
                "lane_prs": {"ok": True, "newest": _ts(), "note": "fine"},
                "savings_series": {"ok": True, "newest": _ts(), "note": "fine"},
                "sweep_ledger": {"ok": True, "newest": _ts(), "note": "fine"},
                "telemetry": {"ok": True, "newest": _ts(), "note": "fine"},
            },
        }
        hb.update(overrides)
        self.hb_path.write_text(json.dumps(hb))
        return hb


class SilentTests(FleetEconomicsBase):
    def test_fresh_state_every_input_ok_is_silent(self):
        self.write_hb()
        self.assertEqual(self.mod._fleet_economics_heartbeat(), [])


class PagingTests(FleetEconomicsBase):
    def test_missing_state_file_warns(self):
        warns = self.mod._fleet_economics_heartbeat()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("missing", warns[0])
        self.assertIn("fd3903262e8b", warns[0])

    def test_stale_state_warns_stale(self):
        self.write_hb(ts=_ts(int(self.mod.FLEET_ECON_STALE_SECS) + 3600))
        warns = self.mod._fleet_economics_heartbeat()
        self.assertTrue(any("STALE" in w for w in warns), warns)

    def test_input_not_ok_warns_naming_it(self):
        hb = self.write_hb()
        hb["inputs"]["k2_spend"] = {
            "ok": False,
            "newest": "-",
            "note": "hub export path unreadable",
        }
        self.hb_path.write_text(json.dumps(hb))
        warns = self.mod._fleet_economics_heartbeat()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("k2_spend", warns[0])
        self.assertIn("UNAVAILABLE", warns[0])

    def test_non_k2_spend_input_not_ok_warns_naming_it(self):
        hb = self.write_hb()
        hb["inputs"]["kanban"] = {"ok": False, "newest": "-", "note": "boards dir unreadable"}
        self.hb_path.write_text(json.dumps(hb))
        warns = self.mod._fleet_economics_heartbeat()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("kanban", warns[0])
        self.assertIn("boards dir unreadable", warns[0])

    def test_unreadable_state_warns(self):
        self.hb_path.write_text("{not json")
        warns = self.mod._fleet_economics_heartbeat()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("unreadable", warns[0])

    def test_unparseable_ts_warns(self):
        self.write_hb(ts="not-a-timestamp")
        warns = self.mod._fleet_economics_heartbeat()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("no parseable ts", warns[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
