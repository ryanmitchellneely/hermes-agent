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

    def arrange(self, pr_state):
        """The 2026-09-01 board state: one routed card, done, artifact still live."""
        mod = self.mod
        mod.STATE_PATH.write_text(
            json.dumps(
                {
                    "last_run_ts": 0,
                    "cards": {},
                    "routed": {RKEY: {"card": CARD, "artifact": ARTIFACT}},
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
