#!/usr/bin/env python3
"""flash-next completion liveness pulse (harness t_83348309, 2026-09-06).

`_flash_next_liveness()` (added earlier the same day) only proves the
:11439 tunnel's /health and /v1/models endpoints answer -- it never proves a
real completion works. `_flashnext_liveness()` is the second, independent
leg that mirrors `_ds4_liveness()`: a tiny real chat completion through the
same tunnel. These fixtures pin the three outcomes that matter:

  - healthy completion -> silent (no WARN)
  - the tunnel itself unreachable (connection refused / timeout / DNS) ->
    WARN that names it CHANNEL, never confused with "the model is down"
  - a well-formed-looking response that carries a top-level "error" key, or
    an HTTP error status, or no choices at all -> WARN naming it MODEL, the
    same failure signature `_ds4_liveness()` already treats as a broken
    completion path rather than an unreachable channel

No network: the module's single completion seam
(`_flashnext_completion_request`) is stubbed, and the desk is a tempdir.

Run: python3 scripts/test_t1000_ops_alert_pulse_flashnext_liveness.py
     python3 -m unittest scripts.test_t1000_ops_alert_pulse_flashnext_liveness
"""
from __future__ import annotations

import importlib.util
import os
import sys
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "t1000_ops_alert_pulse.py"


def _load_module(home: Path):
    """Import a fresh copy of the pulse with every desk-rooted path in `home`."""
    os.environ["HERMES_HOME"] = str(home)
    spec = importlib.util.spec_from_file_location(
        "t1000_ops_pulse_flashnext_liveness_uut", MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # DESK is resolved at import from the script's own parent when it has a
    # scripts/ dir, so pin it: this checkout does, and the tests would
    # otherwise write the real cache file next to the real pulse state.
    mod.HOME = home
    mod.DESK = home
    mod.STATE_PATH = home / "cache" / "ops-alert-pulse-state.json"
    return mod


class FlashnextLivenessBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_module(self.home)

    def run_checker(self, fake_request):
        self.mod._flashnext_completion_request = fake_request
        return self.mod._flashnext_liveness()


class HealthyTests(FlashnextLivenessBase):
    def test_a_healthy_completion_is_silent(self):
        def fake_request():
            return {"choices": [{"message": {"content": "OK"}}]}

        self.assertEqual(self.run_checker(fake_request), [])

    def test_length_truncated_reasoning_choices_still_pass(self):
        # qwen3.8-flash-next can spend the whole max_tokens budget on
        # reasoning_content before any visible content is emitted (same
        # false-positive trap `_ds4_liveness()` already documents) -- a
        # non-empty choices list with no error key is success, full stop.
        def fake_request():
            return {"choices": [{"finish_reason": "length"}], "id": "chatcmpl-x"}

        self.assertEqual(self.run_checker(fake_request), [])


class ChannelUnreachableTests(FlashnextLivenessBase):
    def test_connection_refused_warns_and_names_channel(self):
        def fake_request():
            raise ConnectionRefusedError("[Errno 61] Connection refused")

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("CHANNEL", warns[0])
        self.assertIn("UNKNOWN, not bad", warns[0])

    def test_timeout_warns_and_names_channel(self):
        def fake_request():
            raise TimeoutError("timed out")

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("CHANNEL", warns[0])


class ModelFailureTests(FlashnextLivenessBase):
    def test_http_error_warns_and_names_model_not_channel(self):
        def fake_request():
            raise urllib.error.HTTPError(
                self.mod.FLASHNEXT_LIVENESS_URL, 500, "Internal Server Error", {}, io.BytesIO(b"")
            )

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("MODEL", warns[0])
        self.assertIn("500", warns[0])
        self.assertNotIn("CHANNEL", warns[0], "an HTTP error is a distinct failure from unreachable")

    def test_error_key_body_warns_and_names_model(self):
        def fake_request():
            return {"error": {"message": "cuda prefill state reset failed"}}

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("MODEL", warns[0])
        self.assertIn("cuda prefill state reset failed", warns[0])

    def test_no_choices_at_all_warns_and_names_model(self):
        def fake_request():
            return {"id": "chatcmpl-x", "object": "chat.completion"}

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("MODEL", warns[0])
        self.assertIn("no choices", warns[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
