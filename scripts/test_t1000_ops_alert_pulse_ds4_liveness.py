#!/usr/bin/env python3
"""DS4 flash liveness pulse (models-board t_c765b8f4, 2026-09-02).

The on-box kevin-spark watchdog only ever sees the container from its own
loopback; `_ds4_liveness()` is the second, independent leg — a cheap real
completion through the k2vps model-proxy tailnet path (the ONLY way DS4 is
reachable from k2vps). These fixtures pin the four outcomes that matter:

  - healthy completion -> silent (no WARN)
  - the channel itself unreachable (connection refused / timeout / DNS) ->
    WARN that names it CHANNEL, never confused with "the model is down"
  - the model-proxy rejects the token (401) -> WARN naming it an auth
    problem, not a generic failure
  - a well-formed-looking response that carries a top-level "error" key ->
    WARN, the same failure signature the on-box watchdog's completion gate
    already treats as failed

No network and no real desk: the module's single completion seam
(`_ds4_completion_request`) is stubbed, the token file is a tempdir fixture,
and the desk is a tempdir.

Run: python3 scripts/test_t1000_ops_alert_pulse_ds4_liveness.py
     python3 -m unittest scripts.test_t1000_ops_alert_pulse_ds4_liveness
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
        "t1000_ops_pulse_ds4_liveness_uut", MODULE_PATH
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


class DS4LivenessBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        (self.home / "secrets").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_module(self.home)
        self.token_path = self.home / "secrets" / "model-proxy.env"
        self.token_path.write_text("K2_LOCAL_API_KEY=fake-token-not-real\n")
        self.mod.DS4_LIVENESS_TOKEN_ENV = self.token_path

    def run_checker(self, fake_request):
        self.mod._ds4_completion_request = fake_request
        return self.mod._ds4_liveness()


class HealthyTests(DS4LivenessBase):
    def test_a_healthy_completion_is_silent(self):
        def fake_request(token):
            self.assertEqual(token, "fake-token-not-real")
            return {"choices": [{"message": {"content": "OK"}}]}

        self.assertEqual(self.run_checker(fake_request), [])

    def test_reasoning_model_choices_with_no_visible_content_still_pass(self):
        # deepseek-v4-flash can consume the whole max_tokens budget on
        # reasoning_content before any visible content is emitted (same
        # false-positive trap the on-box watchdog's completion gate already
        # documents) -- non-empty choices + no error key is success, full stop.
        def fake_request(token):
            return {"choices": [{"finish_reason": "length"}], "id": "chatcmpl-x"}

        self.assertEqual(self.run_checker(fake_request), [])


class ChannelUnreachableTests(DS4LivenessBase):
    def test_connection_refused_warns_and_names_channel(self):
        def fake_request(token):
            raise ConnectionRefusedError("[Errno 61] Connection refused")

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("CHANNEL", warns[0])
        self.assertIn("UNKNOWN, not bad", warns[0])

    def test_timeout_warns_and_names_channel(self):
        def fake_request(token):
            raise TimeoutError("timed out")

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("CHANNEL", warns[0])


class AuthTests(DS4LivenessBase):
    def test_401_warns_and_names_auth(self):
        def fake_request(token):
            raise urllib.error.HTTPError(
                self.mod.DS4_LIVENESS_URL, 401, "Unauthorized", {}, io.BytesIO(b"")
            )

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("auth", warns[0].lower())
        self.assertNotIn("CHANNEL", warns[0], "401 is a distinct failure from unreachable")

    def test_5xx_warns_with_the_status_code(self):
        def fake_request(token):
            raise urllib.error.HTTPError(
                self.mod.DS4_LIVENESS_URL, 503, "Service Unavailable", {}, io.BytesIO(b"")
            )

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("503", warns[0])


class MalformedResponseTests(DS4LivenessBase):
    def test_error_key_body_warns(self):
        def fake_request(token):
            return {"error": {"message": "cuda prefill state reset failed"}}

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("error", warns[0].lower())
        self.assertIn("cuda prefill state reset failed", warns[0])

    def test_no_choices_at_all_warns(self):
        def fake_request(token):
            return {"id": "chatcmpl-x", "object": "chat.completion"}

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("no choices", warns[0])


class TokenTests(DS4LivenessBase):
    def test_missing_token_file_warns_without_touching_the_network(self):
        self.mod.DS4_LIVENESS_TOKEN_ENV = self.home / "secrets" / "does-not-exist.env"
        called = []

        def fake_request(token):
            called.append(token)
            return {"choices": [{}]}

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("token unreadable", warns[0])
        self.assertEqual(called, [], "must not attempt the network without a token")

    def test_token_value_never_appears_in_the_warn_text(self):
        def fake_request(token):
            raise ConnectionRefusedError("refused")

        warns = self.run_checker(fake_request)
        self.assertEqual(len(warns), 1, warns)
        self.assertNotIn("fake-token-not-real", warns[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
