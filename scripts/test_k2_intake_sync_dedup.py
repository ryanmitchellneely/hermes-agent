#!/usr/bin/env python3
"""A done card with an OPEN PR is in flight, not failed (harness t_6a69ecd2).

Replays 2026-09-01. The zombie-slot loop in `sync()` treated any done/archived
routed card whose artifact still read live as a failed attempt: free the slot,
count the attempt, re-mint next pass. But a KB page stays STALE precisely
UNTIL its fix merges, so a card whose PR was merely still open looked
identical to one that failed. The second card minted for
`docs/knowledge-base/adversarial-review-loop-findings.md` produced PR #5860,
whose citations were fabricated, while PR #5857 was open on the same file.

Run: python3 scripts/test_k2_intake_sync_dedup.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "k2_intake_sync.py"
ARTIFACT = "docs/knowledge-base/adversarial-review-loop-findings.md"
CARD = "t_4588f937"
RKEY = f"wiki-staleness::{ARTIFACT}"
REAL_RESULT = (
    "dsh headless ok in 92.9s. kanban request-review | git/PR: "
    "https://github.com/joinsov/kevin-real-estate-tools/pull/5857"
)


def _load_module(home: Path):
    """Import a fresh copy of the module with its desk pointed at `home`."""
    os.environ["HERMES_HOME"] = str(home)
    os.environ["K2_INTAKE_CLONE"] = str(home / "clone")
    os.environ["K2_INTAKE_THROTTLE_SECS"] = "0"
    os.environ.pop("K2_INTAKE_GH_TOKEN", None)
    spec = importlib.util.spec_from_file_location("k2_intake_sync_dedup_uut", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # DESK is resolved at import from the checkout's own cache/ dir when it has
    # one, so pin it: a developer checkout that grows a cache/ would otherwise
    # aim these tests at the real state file and the real board db.
    mod.HOME = home
    mod.DESK = home
    mod.STATE_PATH = home / "cache" / "k2-intake-state.json"
    mod.HEARTBEAT_PATH = home / "cache" / "k2-intake-heartbeat.json"
    return mod


def _hermes_stub(args):
    return subprocess.CompletedProcess(args, 0, stdout="Created t_b0000001\n", stderr="")


class MintRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, spec, artifact, sources=None):
        self.calls.append((spec["key"], artifact, sources))
        return "t_new"


class DedupBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        (self.home / "clone").mkdir()
        self.mod = _load_module(self.home)
        self.addCleanup(self._tmp.cleanup)

    def arrange(self, pr_state, routed=None):
        """The 2026-09-01 board state: one routed card, done, artifact still live.

        `routed` overrides the default single-card state — an empty dict lets
        outage-hold tests exercise the mint loop with no pre-existing card.
        """
        mod = self.mod
        mod.STATE_PATH.write_text(
            json.dumps(
                {
                    "last_run_ts": 0,
                    "cards": {},
                    "routed": (
                        {RKEY: {"card": CARD, "artifact": ARTIFACT}}
                        if routed is None else routed
                    ),
                    "route_attempts": {},
                    "parked_artifacts": {},
                }
            ),
            encoding="utf-8",
        )
        # The real wiki-staleness spec, so the split block cannot drift from
        # what production actually carries.
        mod.CHECKERS = [s for s in mod.CHECKERS if s["key"] == "wiki-staleness"]
        self.assertEqual(len(mod.CHECKERS), 1)
        mod.run_checker = lambda spec, clone: {
            "count": 1,
            "samples": [f"STALE  {ARTIFACT}"],
            "artifacts": [ARTIFACT],
            "sources_by_artifact": {ARTIFACT: [".github/workflows/pr-gate.yml"]},
        }
        mod._hermes = _hermes_stub
        mod._card_status = lambda card_id: "done"
        mod._card_pr_number = lambda card_id: 5857
        mod._pr_state = lambda number: pr_state
        mod._board_has_workdir = lambda: True
        mod.is_denied = lambda artifact: False
        # Real network probe would fail in a sandbox with no relay to reach;
        # tests that care about outage-hold override this explicitly.
        mod._model_relay_reachable = lambda: True
        self.mint = MintRecorder()
        mod._create_routed_card = self.mint
        return mod

    def state(self):
        return json.loads(self.mod.STATE_PATH.read_text(encoding="utf-8"))


class TestZombieSlotDedup(DedupBase):
    def test_open_pr_holds_the_slot_and_mints_nothing(self):
        """The replay: #5857 open, so the artifact is live BECAUSE it is unmerged."""
        mod = self.arrange("open")
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["dedup_inflight"], 1)
        self.assertEqual(counts["slots_refreed"], 0)
        st = self.state()
        self.assertIn(RKEY, st["routed"])
        self.assertEqual(st["routed"][RKEY]["card"], CARD)
        self.assertEqual(st["route_attempts"], {})

    def test_closed_pr_keeps_todays_behaviour(self):
        """The mutation: a card whose PR closed unmerged really did fail."""
        mod = self.arrange("closed")
        counts = mod.sync(force=True)
        self.assertEqual(len(self.mint.calls), 1)
        self.assertEqual(self.mint.calls[0][1], ARTIFACT)
        st = self.state()
        self.assertEqual(st["route_attempts"][RKEY], 1)
        self.assertEqual(counts["slots_refreed"], 1)
        self.assertEqual(counts["dedup_inflight"], 0)

    def test_unreadable_pr_state_holds_the_slot(self):
        mod = self.arrange(None)
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["dedup_unverified"], 1)
        self.assertEqual(counts["slots_refreed"], 0)
        st = self.state()
        self.assertIn(RKEY, st["routed"])
        self.assertEqual(st["route_attempts"], {})

    def test_merged_pr_frees_the_slot_without_charging_an_attempt(self):
        """Merged + still live is a real re-drift, not a failure: no attempt."""
        mod = self.arrange("merged")
        counts = mod.sync(force=True)
        self.assertEqual(counts["dedup_merged"], 1)
        self.assertEqual(counts["slots_refreed"], 1)
        st = self.state()
        self.assertEqual(st["route_attempts"], {})
        self.assertNotIn(RKEY, st["parked_artifacts"])

    def test_counts_keys_always_present_in_the_heartbeat(self):
        mod = self.arrange("open")
        mod.sync(force=True)
        hb = json.loads(mod.HEARTBEAT_PATH.read_text(encoding="utf-8"))
        for key in ("dedup_inflight", "dedup_unverified", "dedup_merged"):
            self.assertIn(key, hb)


class TestBlockedSlotRelease(DedupBase):
    """Harness card t_5c1dbcd7, 2026-09-03: all ten MAX_ROUTED_IN_FLIGHT slots
    were held by blocked cards that had ended in an honest wrapper gate
    refusal and never opened a PR — the old blocked branch held the slot
    forever with no PR check. A blocked card is only really awaiting a human
    while a PR is open on it; otherwise it is a finished attempt, freed the
    same way a failed done/archived card is.

    That free is about IN-FLIGHT BUDGET only (t_1817dcad): it lets OTHER
    artifacts route, but it must not make THIS page look brand new. The card
    that just froze is still `blocked` — not done/archived — so the page
    itself stays gated (`skipped_open_page`) until that card resolves or is
    archived; see TestPageLevelDedup for the gate in isolation."""

    def arrange_blocked(self, pr_number, pr_state=None):
        mod = self.arrange(pr_state)
        mod._card_status = lambda card_id: "blocked"
        mod._card_pr_number = lambda card_id: pr_number
        return mod

    def test_no_pr_frees_the_slot_but_the_page_stays_gated(self):
        mod = self.arrange_blocked(None)
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        st = self.state()
        self.assertEqual(st["route_attempts"][RKEY], 1)
        self.assertEqual(counts["blocked_released"], 1)
        self.assertEqual(counts["held_blocked"], 0)
        self.assertEqual(counts["slots_refreed"], 1)
        self.assertEqual(counts["skipped_open_page"], 1)

    def test_open_pr_holds_the_slot(self):
        mod = self.arrange_blocked(5857, "open")
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["held_blocked"], 1)
        self.assertEqual(counts["blocked_released"], 0)
        st = self.state()
        self.assertIn(RKEY, st["routed"])
        self.assertEqual(st["route_attempts"], {})

    def test_closed_pr_frees_the_slot_but_the_page_stays_gated(self):
        mod = self.arrange_blocked(5857, "closed")
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        st = self.state()
        self.assertEqual(st["route_attempts"][RKEY], 1)
        self.assertEqual(counts["blocked_released"], 1)
        self.assertEqual(counts["held_blocked"], 0)
        self.assertEqual(counts["skipped_open_page"], 1)

    def test_unreadable_pr_holds_the_slot(self):
        mod = self.arrange_blocked(5857, None)
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["dedup_unverified"], 1)
        self.assertEqual(counts["blocked_released"], 0)
        st = self.state()
        self.assertIn(RKEY, st["routed"])
        self.assertEqual(st["route_attempts"], {})

    def test_second_blocked_no_pr_outcome_parks_the_artifact(self):
        """The card already failed once with no PR; a second blocked-no-PR
        outcome hits MAX_ROUTE_ATTEMPTS and parks instead of re-minting."""
        mod = self.arrange_blocked(None)
        st = self.state()
        st["route_attempts"][RKEY] = 1
        mod.STATE_PATH.write_text(json.dumps(st), encoding="utf-8")
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        st = self.state()
        self.assertEqual(st["route_attempts"][RKEY], 2)
        self.assertIn(RKEY, st["parked_artifacts"])
        self.assertEqual(counts["parked_failing"], 1)
        self.assertEqual(counts["blocked_released"], 1)
        self.assertEqual(counts["parked_skipped"], 1)


class TestPageLevelDedup(DedupBase):
    """Harness card t_1817dcad, measured 2026-09-04/05: k2-intake-sync minted
    two "KB verify" cards three hours apart for the SAME page — t_d876036f
    (11:43) and t_80567e48 (14:47), both targeting
    docs/knowledge-base/llm-context-windows-and-prompt-caps.md, both opening
    PRs (#6156, #6170) that stamped the same file with different
    verification tables. The zombie-release scan (TestBlockedSlotRelease)
    freed `routed[rkey]` — an IN-FLIGHT BUDGET decision — the instant the
    first card read blocked-with-no-PR, and the very next mint pass then
    treated the page as brand new. `_page_has_open_card` closes that gap by
    checking the LAST card minted for the page directly, off `last_card`,
    which — unlike `routed[rkey]` — is never cleared by a capacity free.

    These tests seed `last_routed_card` directly with `routed={}`, so the
    gate is exercised in isolation, with no zombie-release scan in the loop
    at all (that mechanic is TestBlockedSlotRelease/TestZombieSlotDedup)."""

    def seed_last_card(self, mod, card=CARD):
        st = self.state()
        st["last_routed_card"] = {RKEY: card}
        mod.STATE_PATH.write_text(json.dumps(st), encoding="utf-8")

    def test_any_non_terminal_status_blocks_a_new_mint(self):
        """(1) same page, prior card open (any non-terminal status:
        ready/running/blocked/todo) -> not minted, counter +1."""
        for status in ("ready", "running", "blocked", "todo"):
            with self.subTest(status=status):
                mod = self.arrange(None, routed={})
                self.seed_last_card(mod)
                mod._card_status = lambda card_id, s=status: s
                counts = mod.sync(force=True)
                self.assertEqual(self.mint.calls, [])
                self.assertEqual(counts["skipped_open_page"], 1)

    def test_done_with_merged_or_closed_pr_mints(self):
        """(2) prior card done and its PR merged/closed -> minted."""
        for pr_state in ("merged", "closed"):
            with self.subTest(pr_state=pr_state):
                mod = self.arrange(pr_state, routed={})
                self.seed_last_card(mod)
                mod._card_status = lambda card_id: "done"
                mod._card_pr_number = lambda card_id: 5857
                counts = mod.sync(force=True)
                self.assertEqual(len(self.mint.calls), 1)
                self.assertEqual(counts["skipped_open_page"], 0)
                self.assertEqual(counts["skipped_unreadable"], 0)

    def test_done_with_open_pr_does_not_mint(self):
        """(3) prior card done but its PR is still open -> not minted."""
        mod = self.arrange("open", routed={})
        self.seed_last_card(mod)
        mod._card_status = lambda card_id: "done"
        mod._card_pr_number = lambda card_id: 5857
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["skipped_open_page"], 1)

    def test_archived_with_no_pr_mints(self):
        """(4) prior card archived, no PR -> minted."""
        mod = self.arrange(None, routed={})
        self.seed_last_card(mod)
        mod._card_status = lambda card_id: "archived"
        mod._card_pr_number = lambda card_id: None
        counts = mod.sync(force=True)
        self.assertEqual(len(self.mint.calls), 1)
        self.assertEqual(counts["skipped_open_page"], 0)
        self.assertEqual(counts["skipped_unreadable"], 0)

    def test_unreadable_status_does_not_mint(self):
        """(5a) the prior card's status cannot be read -> not minted,
        counted (fails closed, same direction as `_card_status` itself)."""
        mod = self.arrange(None, routed={})
        self.seed_last_card(mod)
        mod._card_status = lambda card_id: None
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["skipped_unreadable"], 1)
        self.assertEqual(counts["skipped_open_page"], 0)

    def test_unreadable_pr_state_does_not_mint(self):
        """(5b) the prior card is done/archived but its PR state cannot be
        read -> not minted, counted (fails closed, same direction as
        `_pr_state` itself)."""
        mod = self.arrange(None, routed={})  # arrange(None) => _pr_state -> None
        self.seed_last_card(mod)
        mod._card_status = lambda card_id: "done"
        mod._card_pr_number = lambda card_id: 5857
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["skipped_unreadable"], 1)

    def test_no_prior_card_at_all_mints(self):
        """A page with no last-known card at all is unaffected by the gate
        (the ordinary new-artifact path)."""
        mod = self.arrange(None, routed={})
        counts = mod.sync(force=True)
        self.assertEqual(len(self.mint.calls), 1)
        self.assertEqual(counts["skipped_open_page"], 0)
        self.assertEqual(counts["skipped_unreadable"], 0)


class TestOutageHold(DedupBase):
    """Harness incident 2026-09-03 ~19:30Z: the model host behind the dsh
    sandbox relay (kevin-spark, 100.125.80.66:11435) went unreachable and
    every routed card the dispatcher then claimed refused at attestation
    within seconds, ending `blocked`. The blocked-release rule
    (TestBlockedSlotRelease) must not book that as artifact failure: no
    attempt charged, no park — and no NEW card minted while the relay is
    down, so an outage cannot mint a doomed replacement in the same pulse
    it just freed."""

    OUTAGE_SUMMARY = (
        "sandbox refused: attestation failed for the dsh container: the "
        "model endpoint is NOT reachable from the container"
    )
    TRANSPORT_SUMMARY = "dsh: TRANSPORT: Connection error: dial tcp timeout"

    def arrange_blocked_outage(self, summary):
        mod = self.arrange(None)
        mod._card_status = lambda card_id: "blocked"
        mod._card_pr_number = lambda card_id: None
        mod._card_last_run_summary = lambda card_id: summary
        mod._model_relay_reachable = lambda: True
        return mod

    def test_outage_summary_frees_slot_without_charging_attempt(self):
        """(a) blocked + outage summary -> freed, no attempt, not parked."""
        mod = self.arrange_blocked_outage(self.OUTAGE_SUMMARY)
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["outage_released"], 1)
        self.assertEqual(counts["blocked_released"], 0)
        st = self.state()
        self.assertNotIn(RKEY, st["routed"])
        self.assertEqual(st["route_attempts"], {})
        self.assertNotIn(RKEY, st["parked_artifacts"])

    def test_transport_error_also_matches(self):
        mod = self.arrange_blocked_outage(self.TRANSPORT_SUMMARY)
        counts = mod.sync(force=True)
        self.assertEqual(counts["outage_released"], 1)
        st = self.state()
        self.assertEqual(st["route_attempts"], {})

    def test_ordinary_gate_refusal_counts_an_attempt(self):
        """(b) blocked + ordinary gate refusal -> slot frees for capacity,
        route_attempts still counts it, but the page itself stays gated
        (t_1817dcad) since the card is still `blocked`, not done/archived."""
        mod = self.arrange_blocked_outage(
            "dsh headless refused: gate wiring-check failed"
        )
        counts = mod.sync(force=True)
        self.assertEqual(counts["outage_released"], 0)
        self.assertEqual(self.mint.calls, [])
        st = self.state()
        self.assertEqual(st["route_attempts"][RKEY], 1)
        self.assertEqual(counts["blocked_released"], 1)
        self.assertEqual(counts["outage_hold"], 0)
        self.assertEqual(counts["skipped_open_page"], 1)

    def test_outage_seen_holds_new_minting_this_pulse(self):
        """(c) outage seen this pulse -> no new card minted."""
        mod = self.arrange_blocked_outage(self.OUTAGE_SUMMARY)
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["outage_hold"], 1)
        self.assertGreaterEqual(counts["outage_deferred"], 1)

    def test_probe_failing_with_no_outage_cards_holds(self):
        """(d) relay probe failing with no outage cards -> hold."""
        mod = self.arrange(None, routed={})
        mod._model_relay_reachable = lambda: False
        counts = mod.sync(force=True)
        self.assertEqual(self.mint.calls, [])
        self.assertEqual(counts["outage_hold"], 1)
        self.assertGreaterEqual(counts["outage_deferred"], 1)
        self.assertEqual(counts["outage_released"], 0)

    def test_probe_ok_no_outage_mints_as_before(self):
        """(e) relay probe ok, no outage -> mints as before."""
        mod = self.arrange(None, routed={})
        mod._model_relay_reachable = lambda: True
        counts = mod.sync(force=True)
        self.assertEqual(len(self.mint.calls), 1)
        self.assertEqual(counts["outage_hold"], 0)
        self.assertEqual(counts["outage_deferred"], 0)

    def test_heartbeat_always_carries_the_outage_keys(self):
        mod = self.arrange_blocked_outage(self.OUTAGE_SUMMARY)
        mod.sync(force=True)
        hb = json.loads(mod.HEARTBEAT_PATH.read_text(encoding="utf-8"))
        for key in ("outage_hold", "outage_released", "outage_deferred"):
            self.assertIn(key, hb)


class TestCardPrNumber(DedupBase):
    def _db(self, rows_tasks, rows_comments=()):
        mod = self.mod
        db = mod.DESK / "kanban" / "boards" / mod.BOARD / "kanban.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db)
        conn.execute("create table tasks (id text primary key, result text)")
        conn.execute(
            "create table task_comments (id integer primary key, task_id text, "
            "author text, body text, created_at text)"
        )
        conn.executemany("insert into tasks values (?, ?)", rows_tasks)
        conn.executemany("insert into task_comments values (?, ?, ?, ?, ?)", rows_comments)
        conn.commit()
        conn.close()

    def test_parses_the_pr_out_of_a_real_result_string(self):
        self._db([(CARD, REAL_RESULT)])
        self.assertEqual(self.mod._card_pr_number(CARD), 5857)

    def test_falls_back_to_the_newest_comment(self):
        self._db(
            [(CARD, "dsh headless ok in 92.9s. kanban complete")],
            [
                (1, CARD, "dsh", "starting", "2026-09-01T01:00:00Z"),
                (2, CARD, "dsh", REAL_RESULT, "2026-09-01T02:00:00Z"),
            ],
        )
        self.assertEqual(self.mod._card_pr_number(CARD), 5857)

    def test_no_pr_anywhere_reads_none(self):
        self._db([(CARD, "blocked: needs_input")])
        self.assertIsNone(self.mod._card_pr_number(CARD))

    def test_missing_db_reads_none(self):
        self.assertIsNone(self.mod._card_pr_number(CARD))


class TestPrStateFailsClosed(DedupBase):
    def test_missing_bot_env_returns_none_without_touching_the_network(self):
        import urllib.request

        mod = self.mod
        os.environ.pop("K2_INTAKE_GH_TOKEN", None)
        os.environ["K2_INTAKE_BOT_ENV"] = str(self.home / "secrets" / "nope.env")
        self.addCleanup(os.environ.pop, "K2_INTAKE_BOT_ENV", None)

        real = urllib.request.urlopen

        def refuse(*a, **k):
            raise AssertionError("network attempted with no credential")

        urllib.request.urlopen = refuse
        self.addCleanup(setattr, urllib.request, "urlopen", real)
        self.assertIsNone(mod._pr_state(5857))


class MintImportsTheWrapperLikeAModule(unittest.TestCase):
    """The deployed wrapper declares @dataclass classes; importing it by path
    without registering it in sys.modules raised AttributeError on the first
    production run (2026-09-01 21:25Z, held as dedup_unverified). Pin the
    registration with a stand-in wrapper of the same shape."""

    def test_mint_uses_the_wrappers_own_functions(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / "k.pem"
            key.write_text("not a real key\n")
            envf = Path(td) / "dsh-bot.env"
            envf.write_text(
                f"DSH_BOT_APP_ID=1\nDSH_BOT_INSTALLATION_ID=2\nexport DSH_BOT_APP_KEY_PATH={key}\n"
            )
            wrapper = Path(td) / "fake_wrapper.py"
            wrapper.write_text(
                "from dataclasses import dataclass\n"
                "@dataclass\nclass BotIdentity:\n    name: str = 'x'\n"
                "def _mint_installation_token(app_id, installation_id, key_path):\n"
                "    return f'tok-{app_id}-{installation_id}-{key_path.name}'\n"
                "def _revoke_installation_token(token):\n    pass\n"
            )
            home = Path(td) / "home"
            (home / "cache").mkdir(parents=True)
            (home / "clone").mkdir()
            mod = _load_module(home)
            saved = {k: os.environ.get(k) for k in ("K2_INTAKE_BOT_ENV", "K2_INTAKE_WRAPPER_PATH")}
            try:
                os.environ["K2_INTAKE_BOT_ENV"] = str(envf)
                os.environ["K2_INTAKE_WRAPPER_PATH"] = str(wrapper)
                w, tok = mod._mint_bot_token()
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            self.assertEqual(tok, "tok-1-2-k.pem")
            self.assertTrue(hasattr(w, "_revoke_installation_token"))


class ThrottleDefaultTests(unittest.TestCase):
    """`_load_module` always pins K2_INTAKE_THROTTLE_SECS=0 for the other
    tests' isolation, so it can't be reused here — load a second copy the
    same way but leave the throttle env var alone."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        (self.home / "clone").mkdir()
        self.addCleanup(self._tmp.cleanup)

    def _load(self):
        os.environ["HERMES_HOME"] = str(self.home)
        os.environ["K2_INTAKE_CLONE"] = str(self.home / "clone")
        os.environ.pop("K2_INTAKE_GH_TOKEN", None)
        spec = importlib.util.spec_from_file_location(
            "k2_intake_sync_throttle_uut", MODULE_PATH
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_default_throttle_is_three_hours(self):
        os.environ.pop("K2_INTAKE_THROTTLE_SECS", None)
        mod = self._load()
        self.assertEqual(mod.THROTTLE_SECS, 3 * 3600)

    def test_env_var_still_overrides_the_default(self):
        os.environ["K2_INTAKE_THROTTLE_SECS"] = "42"
        mod = self._load()
        self.assertEqual(mod.THROTTLE_SECS, 42)


class RoutedCapDefaultTests(unittest.TestCase):
    """Raised 2026-09-02 (Ryan): the lane cleared its queue in under an hour
    at the old 6/3 caps, so the cap itself was the binding constraint."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        (self.home / "clone").mkdir()
        self.addCleanup(self._tmp.cleanup)

    def _load(self):
        os.environ["HERMES_HOME"] = str(self.home)
        os.environ["K2_INTAKE_CLONE"] = str(self.home / "clone")
        os.environ.pop("K2_INTAKE_GH_TOKEN", None)
        spec = importlib.util.spec_from_file_location(
            "k2_intake_sync_routed_cap_uut", MODULE_PATH
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_default_routed_caps_are_ten_in_flight_five_per_run(self):
        os.environ.pop("K2_INTAKE_MAX_ROUTED_IN_FLIGHT", None)
        os.environ.pop("K2_INTAKE_MAX_ROUTED_PER_RUN", None)
        mod = self._load()
        self.assertEqual(mod.MAX_ROUTED_IN_FLIGHT, 10)
        self.assertEqual(mod.MAX_NEW_ROUTED_PER_RUN, 5)


class ModelProbeEnvTests(unittest.TestCase):
    """MODEL_HOST/MODEL_PORT and the off-switch are resolved at import time
    from K2_INTAKE_MODEL_PROBE, so — same pattern as ThrottleDefaultTests —
    the env var must be set before the module is loaded."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / "cache").mkdir()
        (self.home / "clone").mkdir()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(os.environ.pop, "K2_INTAKE_MODEL_PROBE", None)

    def _load(self):
        os.environ["HERMES_HOME"] = str(self.home)
        os.environ["K2_INTAKE_CLONE"] = str(self.home / "clone")
        os.environ.pop("K2_INTAKE_GH_TOKEN", None)
        spec = importlib.util.spec_from_file_location(
            "k2_intake_sync_probe_uut", MODULE_PATH
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_default_target_is_the_kevin_spark_relay(self):
        os.environ.pop("K2_INTAKE_MODEL_PROBE", None)
        mod = self._load()
        self.assertEqual(mod.MODEL_HOST, "100.125.80.66")
        self.assertEqual(mod.MODEL_PORT, 11435)
        self.assertFalse(mod.MODEL_PROBE_DISABLED)

    def test_off_disables_the_probe_and_reads_as_reachable(self):
        os.environ["K2_INTAKE_MODEL_PROBE"] = "off"
        mod = self._load()
        self.assertTrue(mod.MODEL_PROBE_DISABLED)
        self.assertTrue(mod._model_relay_reachable())

    def test_host_port_override(self):
        os.environ["K2_INTAKE_MODEL_PROBE"] = "127.0.0.1:9"
        mod = self._load()
        self.assertEqual(mod.MODEL_HOST, "127.0.0.1")
        self.assertEqual(mod.MODEL_PORT, 9)
        self.assertFalse(mod.MODEL_PROBE_DISABLED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
