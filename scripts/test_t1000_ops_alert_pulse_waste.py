#!/usr/bin/env python3
"""The dsh verdict-waste threshold, proven without a network (harness t_70595c66).

Eight dsh-lane PRs sat unverdicted for more than 72h before the 2026-09-01
routing ruling and zero instruments said so. `_dsh_verdict_waste()` is that
instrument. These fixtures pin the three things it would be easy to get
subtly wrong and never notice in production:

  - a verdict only counts from a NON-author, non-`github-actions[bot]` login
    (the automated lane posts INCONCLUSIVE notices, and on #5834 it posted a
    fabricated objection — an unreviewed PR must not look reviewed);
  - the threshold fires at N, not above N;
  - a checker that cannot measure says UNMEASURED and writes `measured: false`,
    never a comforting zero.

No network and no real desk: the module's single GET seam (`_gh_get`) and
`k2_intake_sync._mint_bot_token` are both stubbed, and the desk is a tempdir.

Run: python3 scripts/test_t1000_ops_alert_pulse_waste.py
     python3 -m unittest scripts.test_t1000_ops_alert_pulse_waste
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "t1000_ops_alert_pulse.py"
LANE = "k2-dsh-lane[bot]"
REPO = "joinsov/kevin-real-estate-tools"


def _load_module(home: Path):
    """Import a fresh copy of the pulse with every desk-rooted path in `home`."""
    os.environ["HERMES_HOME"] = str(home)
    spec = importlib.util.spec_from_file_location("t1000_ops_pulse_waste_uut", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # DESK is resolved at import from the script's own parent when it has a
    # scripts/ dir, so pin it: this checkout does, and the tests would
    # otherwise write the real cache file next to the real pulse state.
    mod.HOME = home
    mod.DESK = home
    mod.STATE_PATH = home / "cache" / "ops-alert-pulse-state.json"
    mod.DSH_WASTE_CACHE = home / "cache" / "k2-dsh-waste.json"
    return mod


def _pr(number: int, age_h: float, login: str = LANE, title: str = "a lane PR") -> dict:
    created = datetime.now(timezone.utc) - timedelta(hours=age_h)
    return {
        "number": number,
        "title": title,
        "user": {"login": login},
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _comment(login: str, body: str) -> dict:
    return {"user": {"login": login}, "body": body}


class FakeGitHub:
    """Serves the two paths the checker asks for, with real pagination."""

    def __init__(self, pulls: list[dict], comments: dict[int, list[dict]] | None = None):
        self.pulls = pulls
        self.comments = comments or {}
        self.paths: list[str] = []

    def __call__(self, path: str, token: str):
        self.paths.append(path)
        parsed = urllib.parse.urlparse(path)
        qs = urllib.parse.parse_qs(parsed.query)
        page = int(qs.get("page", ["1"])[0])
        per_page = int(qs.get("per_page", ["100"])[0])
        start = (page - 1) * per_page
        if parsed.path == f"/repos/{REPO}/pulls":
            return self.pulls[start : start + per_page]
        if parsed.path.startswith(f"/repos/{REPO}/issues/"):
            number = int(parsed.path.rsplit("/", 2)[1])
            return self.comments.get(number, [])[start : start + per_page]
        raise AssertionError(f"unexpected path {path}")


class FakeWrapper:
    def __init__(self):
        self.revoked: list[str] = []

    def _revoke_installation_token(self, token):
        self.revoked.append(token)


class WasteBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_module(self.home)
        self.wrapper = FakeWrapper()
        self._install_intake_stub(lambda: (self.wrapper, "tok-fake"))
        for key in ("T1000_DSH_WASTE_MIN", "T1000_DSH_WASTE_AGE_H", "T1000_DSH_WASTE_REPO"):
            os.environ.pop(key, None)

    def _install_intake_stub(self, mint):
        """Put a stub `k2_intake_sync` in sys.modules so the real one is never run."""
        stub = type(sys)("k2_intake_sync")
        stub._mint_bot_token = mint
        prev = sys.modules.get("k2_intake_sync")
        sys.modules["k2_intake_sync"] = stub

        def restore():
            if prev is None:
                sys.modules.pop("k2_intake_sync", None)
            else:
                sys.modules["k2_intake_sync"] = prev

        self.addCleanup(restore)
        return stub

    def run_checker(self, pulls, comments=None):
        self.gh = FakeGitHub(pulls, comments)
        self.mod._gh_get = self.gh
        return self.mod._dsh_verdict_waste()

    def cache(self) -> dict:
        return json.loads((self.home / "cache" / "k2-dsh-waste.json").read_text())


class ThresholdTests(WasteBase):
    def test_exactly_threshold_warns_and_names_every_pr(self):
        warns = self.run_checker([_pr(n, 100, title=f"title {n}") for n in range(1, 6)])
        self.assertEqual(len(warns), 1, warns)
        for n in range(1, 6):
            self.assertIn(f"#{n} age=100h title {n}", warns[0])
        self.assertIn("5 lane PRs open >72h", warns[0])
        cache = self.cache()
        self.assertTrue(cache["measured"])
        self.assertEqual(cache["open_lane_prs"], 5)
        self.assertEqual(len(cache["unverdicted_over_age"]), 5)
        self.assertEqual(cache["threshold"], 5)
        self.assertIsNone(cache["error"])

    def test_below_threshold_is_silent_but_still_writes_the_json(self):
        warns = self.run_checker([_pr(n, 100) for n in range(1, 5)])
        self.assertEqual(warns, [])
        cache = self.cache()
        self.assertTrue(cache["measured"])
        self.assertEqual(cache["open_lane_prs"], 4)
        self.assertEqual(len(cache["unverdicted_over_age"]), 4)

    def test_env_knobs_move_the_threshold_and_the_age(self):
        os.environ["T1000_DSH_WASTE_MIN"] = "3"
        os.environ["T1000_DSH_WASTE_AGE_H"] = "10"
        self.addCleanup(os.environ.pop, "T1000_DSH_WASTE_MIN", None)
        self.addCleanup(os.environ.pop, "T1000_DSH_WASTE_AGE_H", None)
        warns = self.run_checker([_pr(n, 20) for n in range(1, 4)])
        self.assertEqual(len(warns), 1, warns)
        self.assertEqual(self.cache()["threshold"], 3)


class VerdictTests(WasteBase):
    def test_non_author_verdicts_clear_the_prs(self):
        pulls = [_pr(n, 100) for n in range(1, 6)]
        comments = {
            n: [_comment("ryan-claude", "Verdict: APPROVE-WITH-NITS")] for n in range(1, 6)
        }
        self.assertEqual(self.run_checker(pulls, comments), [])
        self.assertEqual(self.cache()["unverdicted_over_age"], [])

    def test_author_own_verdict_does_not_count(self):
        pulls = [_pr(n, 100) for n in range(1, 6)]
        comments = {n: [_comment(LANE, "Verdict: APPROVE")] for n in range(1, 6)}
        warns = self.run_checker(pulls, comments)
        self.assertEqual(len(warns), 1, "a PR must not stamp itself")
        self.assertEqual(len(self.cache()["unverdicted_over_age"]), 5)

    def test_github_actions_verdict_does_not_count(self):
        pulls = [_pr(n, 100) for n in range(1, 6)]
        comments = {
            n: [_comment("github-actions[bot]", "Verdict: **BLOCK** fabricated objection")]
            for n in range(1, 6)
        }
        warns = self.run_checker(pulls, comments)
        self.assertEqual(len(warns), 1, "CI talking to itself is not a review")
        self.assertEqual(len(self.cache()["unverdicted_over_age"]), 5)

    def test_a_young_pr_never_counts_even_unverdicted(self):
        pulls = [_pr(n, 100) for n in range(1, 5)] + [_pr(99, 1)]
        warns = self.run_checker(pulls)
        self.assertEqual(warns, [], "the fifth PR is 1h old, not stalled")
        cache = self.cache()
        self.assertEqual(cache["open_lane_prs"], 5)
        self.assertEqual(len(cache["unverdicted_over_age"]), 4)

    def test_non_lane_prs_are_ignored(self):
        pulls = [_pr(n, 100, login="kevandkaitrealestate-byte") for n in range(1, 9)]
        self.assertEqual(self.run_checker(pulls), [])
        self.assertEqual(self.cache()["open_lane_prs"], 0)


class UnmeasuredTests(WasteBase):
    def test_mint_failure_is_unmeasured_not_zero(self):
        def boom():
            raise RuntimeError("bot identity incomplete")

        self._install_intake_stub(boom)
        warns = self.run_checker([_pr(n, 100) for n in range(1, 9)])
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("UNMEASURED", warns[0])
        self.assertIn("count unknown, not zero", warns[0])
        cache = self.cache()
        self.assertFalse(cache["measured"])
        self.assertEqual(cache["open_lane_prs"], 0)
        self.assertIn("token mint failed", cache["error"])

    def test_a_failed_get_is_unmeasured_and_revokes_the_token(self):
        def explode(path, token):
            raise OSError("connection reset")

        self.mod._gh_get = explode
        warns = self.mod._dsh_verdict_waste()
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("UNMEASURED", warns[0])
        self.assertFalse(self.cache()["measured"])
        self.assertEqual(self.wrapper.revoked, ["tok-fake"])


class PaginationTests(WasteBase):
    def test_120_open_prs_across_two_pages_are_all_seen(self):
        warns = self.run_checker([_pr(n, 100) for n in range(1, 121)])
        self.assertEqual(len(warns), 1, warns)
        cache = self.cache()
        self.assertEqual(cache["open_lane_prs"], 120)
        self.assertEqual(len(cache["unverdicted_over_age"]), 120)
        pull_pages = [p for p in self.gh.paths if "/pulls?" in p]
        self.assertEqual(len(pull_pages), 2, pull_pages)
        self.assertIn("page=2", pull_pages[1])

    def test_a_verdict_on_the_second_comment_page_still_clears(self):
        pulls = [_pr(n, 100) for n in range(1, 6)]
        filler = [_comment("someone", "no verdict here") for _ in range(100)]
        comments = {
            n: filler + [_comment("ryan-claude", "Verdict: REQUEST-CHANGES")]
            for n in range(1, 6)
        }
        self.assertEqual(self.run_checker(pulls, comments), [])


class TokenTests(WasteBase):
    def test_the_token_is_revoked_on_the_clean_path(self):
        self.run_checker([_pr(1, 100)])
        self.assertEqual(self.wrapper.revoked, ["tok-fake"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
