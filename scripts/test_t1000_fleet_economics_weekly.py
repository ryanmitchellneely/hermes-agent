#!/usr/bin/env python3
"""Unit tests for t1000_fleet_economics_weekly.py (t_da2f74c4).

Every collector takes an injectable path/db/function argument, so these tests
never touch a real VPS path — everything is a temp fixture built with the
same schema columns observed live on k2vps (task_events/task_runs, the sweep
ledger's pipe table, the telemetry jsonl shape, provider_classes.json).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import t1000_fleet_economics_weekly as fem  # noqa: E402

UTC = timezone.utc


def _dt(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


class ParseIsoWeekTests(unittest.TestCase):
    def test_explicit_week(self):
        start, end, label = fem.parse_iso_week("2026-W36")
        self.assertEqual(label, "2026-W36")
        self.assertEqual(start.isoweekday(), 1)
        self.assertEqual((end - start).days, 7)

    def test_default_is_current_week(self):
        today = _dt(2026, 9, 3).date()  # a Thursday, ISO week 36 (Mon Aug 31 .. Sun Sep 6)
        start, end, label = fem.parse_iso_week(None, today=today)
        self.assertEqual(start, _dt(2026, 8, 31).date())
        self.assertEqual(label, "2026-W36")

    def test_bad_format_raises(self):
        with self.assertRaises(Exception):
            fem.parse_iso_week("not-a-week")


class TelemetrySummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "provider_classes.json").write_text(
            json.dumps({"custom:mbp-mlx": "local"}), encoding="utf-8"
        )

    def _write_day(self, day: str, records: list[dict]) -> None:
        path = self.root / f"model_calls-{day}.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

    def test_calls_and_tokens_by_class(self):
        week_start = _dt(2026, 9, 1)
        week_end = _dt(2026, 9, 8)
        in_window_ms = int(_dt(2026, 9, 2, 12, 0).timestamp() * 1000)
        out_window_ms = int(_dt(2026, 8, 20).timestamp() * 1000)
        self._write_day(
            "2026-09-02",
            [
                {
                    "provider": "spark",
                    "model": "hermes3:8b",
                    "ts_epoch_ms": in_window_ms,
                    "tokens_available": True,
                    "total_tokens": 100,
                },
                {
                    "provider": "claude-acp",
                    "model": "sonnet",
                    "ts_epoch_ms": in_window_ms + 1000,
                    "tokens_available": False,
                },
                {
                    "provider": "anthropic",
                    "model": "claude-sonnet-5",
                    "ts_epoch_ms": in_window_ms + 2000,
                    "tokens_available": True,
                    "total_tokens": 50,
                },
            ],
        )
        # Out-of-window record lives in ITS OWN earlier day-file, matching the
        # real store's append-only-per-day layout (freshness reads only the
        # newest file's last line — an out-of-order timestamp inside the
        # newest file is not a shape the real store ever produces).
        self._write_day(
            "2026-08-20",
            [
                {
                    "provider": "spark",
                    "model": "hermes3:8b",
                    "ts_epoch_ms": out_window_ms,
                    "tokens_available": True,
                    "total_tokens": 999,
                }
            ],
        )
        metrics, freshness = fem.telemetry_summary(
            week_start, week_end, now=_dt(2026, 9, 2, 13, 0), tel_dir=self.root
        )
        self.assertEqual(metrics["calls_by_class"].get("local"), 1)
        self.assertEqual(metrics["calls_by_class"].get("subscription"), 1)
        self.assertEqual(metrics["calls_by_class"].get("metered"), 1)
        self.assertEqual(metrics["tokens_by_class"].get("local"), 100)
        # subscription row had tokens_available False -> never summed
        self.assertNotIn("subscription", metrics["tokens_by_class"])
        self.assertEqual(freshness["status"], "ok")
        self.assertTrue(freshness["ok"])

    def test_empty_store_is_unavailable(self):
        metrics, freshness = fem.telemetry_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 2), tel_dir=self.root
        )
        self.assertEqual(metrics["calls_by_class"], {})
        self.assertFalse(freshness["ok"])
        self.assertEqual(freshness["status"], "UNAVAILABLE")


def _make_board_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE task_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            run_id INTEGER,
            kind TEXT NOT NULL,
            payload TEXT,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at INTEGER NOT NULL,
            ended_at INTEGER,
            resolved_model TEXT,
            resolved_provider TEXT
        );
        """
    )
    conn.commit()
    conn.close()


class KanbanSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.boards_dir = Path(self.tmp.name)

    def test_escalations_and_runs_in_window(self):
        board_dir = self.boards_dir / "mesh"
        board_dir.mkdir()
        db_path = board_dir / "kanban.db"
        _make_board_db(db_path)

        in_window = int(_dt(2026, 9, 2).timestamp())
        out_window = int(_dt(2026, 8, 1).timestamp())
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO task_events (task_id, kind, payload, created_at) VALUES (?,?,?,?)",
            (
                "t_1",
                "model_escalated",
                json.dumps(
                    {
                        "from_model": "gpt-oss:120b",
                        "from_provider": "spark",
                        "to_model": "sonnet",
                        "to_provider": "claude-acp",
                    }
                ),
                in_window,
            ),
        )
        conn.execute(
            "INSERT INTO task_events (task_id, kind, payload, created_at) VALUES (?,?,?,?)",
            ("t_2", "model_escalated", json.dumps({"to_provider": "spark", "to_model": "x"}), out_window),
        )
        conn.execute(
            "INSERT INTO task_runs (task_id, status, started_at, resolved_provider) "
            "VALUES (?,?,?,?)",
            ("t_1", "done", in_window, "claude-acp"),
        )
        conn.execute(
            "INSERT INTO task_runs (task_id, status, started_at, resolved_provider) "
            "VALUES (?,?,?,?)",
            ("t_3", "done", in_window, ""),
        )
        conn.commit()
        conn.close()

        metrics, freshness = fem.kanban_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 3), boards_dir=self.boards_dir
        )
        self.assertEqual(metrics["escalations_by_board"], {"mesh": 1})
        self.assertEqual(metrics["escalations_to_paid_by_board"], {"mesh": 1})
        self.assertEqual(metrics["runs_total_by_board"]["mesh"], 2)
        self.assertEqual(metrics["runs_resolved_by_board"]["mesh"], 1)
        self.assertEqual(freshness["status"], "ok")

    def test_no_boards_is_unavailable(self):
        metrics, freshness = fem.kanban_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 3), boards_dir=self.boards_dir
        )
        self.assertEqual(metrics["boards_seen"], 0)
        self.assertFalse(freshness["ok"])


class K2SpendSummaryTests(unittest.TestCase):
    """k2_spend_summary() reads the hub's own GET /api/v1/llm-spend (round-2
    fix) — never the production db directly. env_path/http_get are both
    injectable so these tests touch neither the real file nor the network."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_path = Path(self.tmp.name) / "k2-hub.env"

    def test_token_read_from_env_file(self):
        self.env_path.write_text('LIGHTHOUSE_API_TOKEN="shh-token"\n', encoding="utf-8")
        token, reason = fem._read_env_file_var(
            self.env_path, fem.K2_HUB_SPEND_TOKEN_ENV_NAMES
        )
        self.assertEqual(token, "shh-token")
        self.assertIsNone(reason)

    def test_totals_via_injected_http_get(self):
        metrics, freshness = fem.k2_spend_summary(
            _dt(2026, 9, 1),
            _dt(2026, 9, 8),
            now=_dt(2026, 9, 4),
            http_get=lambda url, token: {
                "last_7d_usd": 4.0,
                "by_model_7d": [
                    {"key": "gpt-4o", "cost": 3.0, "tokens": 1000, "calls": 5},
                    {"key": "claude-sonnet-5", "cost": 1.0, "tokens": 200, "calls": 2},
                ],
            },
        )
        self.assertTrue(metrics["available"])
        self.assertAlmostEqual(metrics["total_usd"], 4.0)
        self.assertEqual(metrics["top_models"][0]["model_id"], "gpt-4o")
        self.assertEqual(freshness["ok"], True)

    def test_unreadable_token_file_degrades_gracefully(self):
        missing = Path(self.tmp.name) / "does-not-exist" / "k2-hub.env"
        metrics, freshness = fem.k2_spend_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), env_path=missing
        )
        self.assertFalse(metrics["available"])
        self.assertEqual(freshness["status"], "UNAVAILABLE")
        self.assertIn("LIGHTHOUSE_API_TOKEN", freshness["note"])

    def test_env_file_present_but_no_token_set(self):
        self.env_path.write_text("SOME_OTHER_VAR=1\n", encoding="utf-8")
        metrics, freshness = fem.k2_spend_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), env_path=self.env_path
        )
        self.assertFalse(metrics["available"])
        self.assertEqual(freshness["status"], "UNAVAILABLE")
        self.assertIn("LIGHTHOUSE_API_TOKEN", freshness["note"])


class SweepLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "SWEEP-LEDGER.md"
        self.path.write_text(
            "\n".join(
                [
                    "# dsh clean-sweep ledger",
                    "",
                    "| pr | merged_at | reds_seen | red_classes | verdict | waivers | qualifies | why | seat |",
                    "|---|---|---|---|---|---|---|---|---|",
                    "| 6001 | 2026-09-02T13:29 | - | - | APPROVE | - | yes | merged clean | grok |",
                    "| 6002 | 2026-09-03T11:32 | claude-review@af3 | unknown | APPROVE | - | no | red: unknown | legacy |",
                    "| 5689 | 2026-08-01T13:07 | - | - | APPROVE | - | yes | merged clean | legacy |",
                ]
            ),
            encoding="utf-8",
        )

    def test_rows_in_window_and_qualifies(self):
        metrics, freshness = fem.sweep_ledger_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), ledger_path=self.path
        )
        self.assertEqual(metrics["rows_in_window"], 2)
        self.assertEqual(metrics["qualifies_yes"], 1)
        self.assertEqual(freshness["status"], "ok")

    def test_missing_ledger(self):
        metrics, freshness = fem.sweep_ledger_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), ledger_path=Path("/nonexistent")
        )
        self.assertEqual(metrics["rows_in_window"], 0)
        self.assertFalse(freshness["ok"])


class LanePrSummaryTests(unittest.TestCase):
    def _fake_gh_get(self, url, token):
        from urllib.parse import urlparse, parse_qs, unquote

        parsed = urlparse(url)
        if parsed.path == "/search/issues":
            q = unquote(parse_qs(parsed.query)["q"][0])
            if "is:merged" in q:
                return {"total_count": 1, "items": []}
            if "is:open" in q:
                return {
                    "total_count": 1,
                    "items": [{"number": 103, "created_at": "2026-09-03T00:00:00Z"}],
                }
            # plain "created:" opened query
            return {
                "total_count": 3,
                "items": [
                    {"number": 101, "created_at": "2026-09-01T10:00:00Z"},
                    {"number": 102, "created_at": "2026-09-02T09:00:00Z"},
                    {"number": 103, "created_at": "2026-09-03T00:00:00Z"},
                ],
            }
        if parsed.path.endswith("/pulls"):
            page = parse_qs(parsed.query).get("page", ["1"])[0]
            if page != "1":
                return []  # only one page of fixture data
            # Sorted by updated_at desc, as the real endpoint returns:
            # 202 (closed, unmerged, in-window) newest, 201 (merged, in-window)
            # next, 203 (closed, unmerged, OUT of window) oldest — its
            # updated_at predates the window start, which is what makes the
            # real function stop paginating after this one page.
            return [
                {
                    "number": 202,
                    "user": {"login": "k2-dsh-lane[bot]"},
                    "state": "closed",
                    "merged_at": None,
                    "closed_at": "2026-09-03T09:00:00Z",
                    "updated_at": "2026-09-03T09:00:00Z",
                },
                {
                    "number": 201,
                    "user": {"login": "k2-dsh-lane[bot]"},
                    "state": "closed",
                    "merged_at": "2026-09-02T10:00:00Z",
                    "closed_at": "2026-09-02T10:00:00Z",
                    "updated_at": "2026-09-02T10:00:00Z",
                },
                {
                    "number": 203,
                    "user": {"login": "k2-dsh-lane[bot]"},
                    "state": "closed",
                    "merged_at": None,
                    "closed_at": "2026-08-01T09:00:00Z",
                    "updated_at": "2026-08-01T09:00:00Z",
                },
            ]
        if "/issues/101/comments" in parsed.path:
            return [{"body": "Verdict: APPROVE", "created_at": "2026-09-01T10:30:00Z"}]
        if "/issues/102/comments" in parsed.path:
            return [{"body": "Verdict: APPROVE-WITH-NITS", "created_at": "2026-09-04T09:00:00Z"}]
        if "/issues/103/comments" in parsed.path:
            return []
        raise AssertionError(f"unexpected url {url}")

    def test_fetch_closed_unmerged_count_direct(self):
        """Round-3 unit test: _fetch_closed_unmerged_count() in isolation
        against a fake single pulls page holding one merged, one
        closed-unmerged, and one out-of-window PR (per captain's ask)."""

        def fake_pulls_page(url, token):
            return self._fake_gh_get(url, token)

        count, ok = fem._fetch_closed_unmerged_count(
            fake_pulls_page,
            "joinsov/kevin-real-estate-tools",
            None,
            "app/k2-dsh-lane",
            "2026-09-01T00:00:00Z",
            "2026-09-08T00:00:00Z",
        )
        self.assertEqual(count, 1)  # only PR 202 (closed, unmerged, in-window)
        self.assertTrue(ok)

    def test_opened_merged_closed_and_verdict_latency(self):
        metrics, freshness = fem.lane_pr_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), gh_get=self._fake_gh_get
        )
        self.assertEqual(metrics["opened"], 3)
        self.assertEqual(metrics["merged"], 1)
        self.assertEqual(metrics["closed_unmerged"], 1)
        self.assertEqual(metrics["ttfv_n"], 2)
        self.assertAlmostEqual(metrics["ttfv_median_min"], 1455.0)
        # p90 stays nearest-rank (matches telemetry_digest.percentile): with
        # n=2, rank=ceil(0.9*2)=2 -> the larger sample.
        self.assertAlmostEqual(metrics["ttfv_p90_min"], 2880.0)
        self.assertEqual(metrics["open_zero_verdict"], 1)
        self.assertTrue(freshness["ok"])

    def test_fetch_failure_marks_unavailable(self):
        def _boom(url, token):
            return {}

        metrics, freshness = fem.lane_pr_summary(
            _dt(2026, 9, 1), _dt(2026, 9, 8), now=_dt(2026, 9, 4), gh_get=_boom
        )
        self.assertFalse(freshness["ok"])
        self.assertEqual(freshness["status"], "UNAVAILABLE")


class FreshnessFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_savings_series_fresh_and_stale(self):
        path = Path(self.tmp.name) / "series.jsonl"
        path.write_text(
            json.dumps({"date": "2026-09-01", "calls": 10}) + "\n"
            + json.dumps({"date": "2026-09-03", "calls": 20}) + "\n",
            encoding="utf-8",
        )
        fresh = fem.savings_series_freshness(now=_dt(2026, 9, 3, 12, 0), path=path)
        self.assertEqual(fresh["status"], "ok")

        stale = fem.savings_series_freshness(now=_dt(2026, 9, 10), path=path)
        self.assertEqual(stale["status"], "STALE")

    def test_distillery_state_freshness(self):
        path = Path(self.tmp.name) / "state.json"
        path.write_text(json.dumps({"ts": "2026-09-04T08:00:00Z"}), encoding="utf-8")
        fresh = fem.distillery_state_freshness(now=_dt(2026, 9, 4, 10, 0), path=path)
        self.assertEqual(fresh["status"], "ok")
        stale = fem.distillery_state_freshness(now=_dt(2026, 9, 5, 10, 0), path=path)
        self.assertEqual(stale["status"], "STALE")

    def test_missing_files_are_unavailable(self):
        missing = Path(self.tmp.name) / "nope.json"
        fresh = fem.distillery_state_freshness(now=_dt(2026, 9, 4), path=missing)
        self.assertFalse(fresh["ok"])
        self.assertEqual(fresh["status"], "UNAVAILABLE")


class LeadingNumberTests(unittest.TestCase):
    def test_plain_int(self):
        self.assertEqual(fem._leading_number("42 calls"), 42.0)

    def test_dollar(self):
        self.assertEqual(fem._leading_number("$1,234.50 total"), 1234.50)

    def test_non_numeric(self):
        self.assertIsNone(fem._leading_number("claude-acp: 3, xai-oauth: 2"))


class BuildPageIntegrationTests(unittest.TestCase):
    """End-to-end: build_page() over an isolated set of fixtures, dry-run style."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out_dir = Path(self.tmp.name) / "economics"

        # Point every default path at empty/temp locations so build_page()'s
        # internal calls (which use module DEFAULT_* constants for the
        # collectors it does not let main() override individually) hit
        # harmless empty fixtures rather than any real path.
        self._patched = {
            "DEFAULT_KANBAN_BOARDS_DIR": fem.DEFAULT_KANBAN_BOARDS_DIR,
            "K2_HUB_ENV_PATH": fem.K2_HUB_ENV_PATH,
            "DEFAULT_SWEEP_LEDGER": fem.DEFAULT_SWEEP_LEDGER,
            "DEFAULT_SAVINGS_SERIES": fem.DEFAULT_SAVINGS_SERIES,
            "DEFAULT_DISTILLERY_STATE": fem.DEFAULT_DISTILLERY_STATE,
            "DEFAULT_K2_INTAKE_SYNC_PATH": fem.DEFAULT_K2_INTAKE_SYNC_PATH,
            "_gh_http_get": fem._gh_http_get,
            "_resolve_telemetry_dir": fem._resolve_telemetry_dir,
        }
        empty = Path(self.tmp.name)
        fem.DEFAULT_KANBAN_BOARDS_DIR = empty / "no-boards"
        fem.K2_HUB_ENV_PATH = empty / "no-k2-hub.env"
        fem.DEFAULT_SWEEP_LEDGER = empty / "no-ledger.md"
        fem.DEFAULT_SAVINGS_SERIES = empty / "no-series.jsonl"
        fem.DEFAULT_DISTILLERY_STATE = empty / "no-state.json"
        fem.DEFAULT_K2_INTAKE_SYNC_PATH = empty / "no-sync.py"
        # build_page() has no per-call gh_get override (main() never needs
        # one), so the integration test stubs the module's real-HTTP default
        # instead of letting it reach the live GitHub API. Token minting
        # already fails closed against the nonexistent sync path above; this
        # stub is what stops the *unauthenticated* fallback call.
        fem._gh_http_get = lambda url, token: {}
        # Same isolation for telemetry: build_page() doesn't expose a tel_dir
        # override, so pin the resolver itself rather than letting it fall
        # through to whatever HERMES_HOME/T1000_TELEMETRY_DIR happen to be
        # set to on the machine actually running these tests.
        fem._resolve_telemetry_dir = lambda: empty / "no-telemetry"

        def addCleanupRestore():
            for key, value in self._patched.items():
                setattr(fem, key, value)

        self.addCleanup(addCleanupRestore)

    def test_first_run_has_no_prior_week_block(self):
        page, week_label, out_dir, now, inputs, *_ = fem.build_page(
            "2026-W36", now=_dt(2026, 9, 3, 12, 0), out_dir=self.out_dir
        )
        self.assertIn("## Header", page)
        self.assertIn("## Freshness", page)
        self.assertIn("no prior week file found", page)
        self.assertEqual(week_label, "2026-W36")
        self.assertIn("telemetry", inputs)
        self.assertIn("lane_prs", inputs)

    def test_second_run_diffs_against_prior_week(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "2026-W35.md").write_text(
            "\n".join(
                [
                    "## Header",
                    "",
                    "| Metric | Value |",
                    "|---|---|",
                    "| Local calls (7d) | 10 |",
                    "",
                    "## Freshness",
                ]
            ),
            encoding="utf-8",
        )
        page, *_ = fem.build_page("2026-W36", now=_dt(2026, 9, 3, 12, 0), out_dir=self.out_dir)
        self.assertIn("Local calls (7d): 10 ->", page)


class HeartbeatTests(unittest.TestCase):
    def test_write_heartbeat_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache" / "heartbeat.json"
            fem.write_heartbeat(
                path,
                week_label="2026-W36",
                now=_dt(2026, 9, 3),
                inputs={"telemetry": {"ok": True, "newest": "2026-09-03T00:00:00Z", "note": "x"}},
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["week"], "2026-W36")
            self.assertIn("telemetry", payload["inputs"])
            self.assertTrue(payload["inputs"]["telemetry"]["ok"])


if __name__ == "__main__":
    unittest.main()
