"""Tests for the usage + success surface (scripts/telemetry_digest.py).

The load-bearing ones are the first two classes: they pin the two correctness
rules the surface exists to enforce.

* ``TestTokensAvailableContract`` — a ``tokens_available=false`` row must never
  reach a sum and must stay visible as its own count. Regressing this makes
  the subscription lanes read as free and inverts every local-vs-hosted
  comparison, which is the exact failure MESH-TEL-2a shipped ahead of its
  callers to prevent.
* ``TestCostClassification`` — local-vs-hosted comes from provider identity,
  never from a caller-set boolean. ``LAB-SCOREBOARD.jsonl`` carries 22 rows
  tagging ``sonnet`` / ``opus`` / ``grok-4.5`` as ``is_local=true``; a row
  making that claim here must still classify by its provider.

All fixtures are synthetic and written under tmp_path. ``tests/conftest.py``
additionally pins ``T1000_TELEMETRY_DIR`` per-test so nothing here can append
to (or read) the real store.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import telemetry_digest as digest  # noqa: E402


# ── fixtures ───────────────────────────────────────────────────────────────


def _row(
    *,
    provider="anthropic",
    model="claude-opus-4-5",
    lane="worker",
    effort="high",
    outcome="ok",
    tokens_available=True,
    input_tokens=100,
    output_tokens=50,
    cache_read_tokens=0,
    cache_write_tokens=0,
    reasoning_tokens=0,
    wall_ms=1000,
    ttft_ms=None,
    ts_epoch_ms=1786406705788,
    task="main_loop",
    board="mesh",
    **extra,
):
    """Build one schema-v1 record.

    Mirrors ``agent/call_telemetry.py:build_record``: when
    ``tokens_available`` is false every token field is ``None``, never ``0``.
    """
    record = {
        "schema_version": 1,
        "ts_epoch_ms": ts_epoch_ms,
        "board": board,
        "lane": lane,
        "task": task,
        "provider": provider,
        "model": model,
        "effort": effort,
        "tokens_available": tokens_available,
        "wall_ms": wall_ms,
        "ttft_ms": ttft_ms,
        "outcome": outcome,
    }
    if tokens_available:
        prompt = input_tokens + cache_read_tokens + cache_write_tokens
        record.update(
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
                "reasoning_tokens": reasoning_tokens,
                "prompt_tokens": prompt,
                "total_tokens": prompt + output_tokens,
            }
        )
    else:
        record.update(
            {
                field: None
                for field in (
                    "input_tokens",
                    "output_tokens",
                    "cache_read_tokens",
                    "cache_write_tokens",
                    "reasoning_tokens",
                    "prompt_tokens",
                    "total_tokens",
                )
            }
        )
    record.update(extra)
    return record


def _store(tmp_path, rows, name="model_calls-2026-08-10.jsonl"):
    root = tmp_path / "telemetry"
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    return root


# ── THE contract ───────────────────────────────────────────────────────────


class TestTokensAvailableContract:
    def test_tokenless_rows_never_enter_a_sum(self):
        """A tokenless row contributes nothing — not even zero — to any total.

        If someone later "simplifies" the accumulator to sum token fields
        unconditionally, the null fields coerce to 0 and this stays green only
        because the totals are unchanged... so assert the WITH-tokens row is
        the entire total, and that adding tokenless rows does not move it.
        """
        with_tokens = [_row(input_tokens=1000, output_tokens=500)]
        plus_tokenless = with_tokens + [
            _row(provider="claude-acp", model="opus[1m]", tokens_available=False)
            for _ in range(5)
        ]

        base = digest.summarize(with_tokens)["overall"]
        mixed = digest.summarize(plus_tokenless)["overall"]

        assert base["total_tokens"] == 1500
        assert mixed["total_tokens"] == 1500, "tokenless rows moved a token total"
        assert mixed["input_tokens"] == base["input_tokens"] == 1000
        assert mixed["output_tokens"] == base["output_tokens"] == 500

    def test_tokenless_row_carrying_literal_zeros_is_still_excluded(self):
        """Defence in depth: do not rely on the writer nulling the fields.

        ``build_record`` writes ``null`` today, so a consumer that summed
        blindly would still get the right total — the bug would hide until the
        day some path emits the old hardcoded ``0`` usage object again. This
        row is exactly that: ``tokens_available=false`` WITH zeros present.
        The flag, not the field values, must be what excludes it.
        """
        honest = _row(input_tokens=1000, output_tokens=500)
        regressed = dict(
            honest,
            provider="claude-acp",
            model="opus[1m]",
            tokens_available=False,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_write_tokens=0,
            reasoning_tokens=0,
            prompt_tokens=0,
            total_tokens=0,
        )
        summary = digest.summarize([honest, regressed])
        overall = summary["overall"]

        assert overall["total_tokens"] == 1500
        assert overall["calls_without_tokens"] == 1
        acp = summary["by_model"]["opus[1m]"]
        assert acp["calls_with_tokens"] == 0
        # The lane must read "no data", NOT "0 tokens" — a zero here is what
        # makes a subscription seat look free.
        assert digest._tokens_cell(acp, "total_tokens") == "no data"

    def test_tokenless_rows_are_counted_separately_and_stay_visible(self):
        summary = digest.summarize(
            [
                _row(),
                _row(provider="copilot-acp", model="gpt-5", tokens_available=False),
                _row(provider="copilot-acp", model="gpt-5", tokens_available=False),
            ]
        )
        overall = summary["overall"]
        assert overall["calls"] == 3
        assert overall["calls_with_tokens"] == 1
        assert overall["calls_without_tokens"] == 2

    def test_tokenless_rows_still_count_toward_calls_and_outcomes(self):
        """Excluded from token sums is NOT excluded from the surface.

        Silently dropping the row entirely would hide the call and its failure,
        which is the other half of the same mistake.
        """
        summary = digest.summarize(
            [
                _row(provider="claude-acp", tokens_available=False, outcome="error"),
                _row(provider="claude-acp", tokens_available=False, outcome="ok"),
            ]
        )
        overall = summary["overall"]
        assert overall["calls"] == 2
        assert overall["error"] == 1
        assert overall["ok"] == 1
        assert overall["success_rate"] == 50.0

    def test_group_with_no_token_data_renders_no_data_not_zero(self, tmp_path):
        """``0`` is the misread; the cell must say ``no data``."""
        summary = digest.summarize(
            [_row(provider="claude-acp", model="opus[1m]", tokens_available=False)]
        )
        bucket = summary["by_model"]["opus[1m]"]
        assert digest._tokens_cell(bucket, "total_tokens") == "no data"
        assert "0" != digest._tokens_cell(bucket, "input_tokens")

        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "no data" in body

    def test_tokenless_rows_raise_a_visible_flag(self):
        summary = digest.summarize(
            [_row(), _row(provider="claude-acp", tokens_available=False)]
        )
        kinds = {flag["kind"] for flag in summary["flags"]}
        assert "tokens_missing" in kinds

    def test_tokenless_rows_are_never_priced(self):
        """No token data means no cost claim, even on a metered provider."""
        summary = digest.summarize(
            [_row(provider="anthropic", tokens_available=False)],
            pricing=(object, lambda *a, **k: pytest.fail("priced a tokenless row")),
        )
        assert summary["overall"]["cost_usd"] == 0.0
        assert summary["overall"]["cost_priced_calls"] == 0


# ── attribution ────────────────────────────────────────────────────────────


class TestCostClassification:
    @pytest.mark.parametrize(
        "provider,expected",
        [
            ("spark", "local"),
            ("kevin-spark", "local"),
            ("mbp-ollama", "local"),
            ("claude-acp", "subscription"),
            ("copilot-acp", "subscription"),
            ("openai-codex", "subscription"),
            ("anthropic", "metered"),
            ("openrouter", "metered"),
            ("google", "metered"),
        ],
    )
    def test_known_providers_classify(self, provider, expected):
        assert digest.classify_provider(provider) == expected

    @pytest.mark.parametrize("provider", ["custom", "", None, "some-new-thing"])
    def test_ambiguous_providers_are_unknown_never_guessed(self, provider):
        """``custom`` covers local Ollama AND hosted GLM. Undecidable → unknown."""
        assert digest.classify_provider(provider) == "unknown"

    def test_a_row_claiming_is_local_does_not_override_provider(self):
        """The LAB-SCOREBOARD failure: a hosted model tagged ``is_local=true``.

        Classification must ignore the claim and read the provider.
        """
        summary = digest.summarize(
            [_row(provider="anthropic", model="sonnet", is_local=True)]
        )
        assert summary["by_cost_class"]["metered"]["calls"] == 1
        assert "local" not in summary["by_cost_class"]

    def test_unknown_provider_raises_a_warn_flag_naming_it(self):
        summary = digest.summarize([_row(provider="custom", model="gpt-oss:120b")])
        flags = [f for f in summary["flags"] if f["kind"] == "cost_class_unknown"]
        assert flags, "unattributable provider did not raise a flag"
        assert "custom" in flags[0]["detail"]
        assert flags[0]["severity"] == "warn"

    def test_operator_class_map_resolves_an_ambiguous_provider(self):
        summary = digest.summarize(
            [_row(provider="custom", model="gpt-oss:120b")],
            class_map={"custom": "local"},
        )
        assert summary["by_cost_class"]["local"]["calls"] == 1
        assert not [f for f in summary["flags"] if f["kind"] == "cost_class_unknown"]

    @pytest.mark.parametrize(
        "provider,expected",
        [
            ("custom:spark", "local"),
            ("custom:kevin-spark", "local"),
            ("custom:mbp-ollama", "local"),
            ("custom:openai", "metered"),
            ("custom:claude-acp", "subscription"),
        ],
    )
    def test_qualified_custom_slug_resolves_to_its_named_endpoint(
        self, provider, expected
    ):
        """``custom:<name>`` is the repo's canonical qualified provider form.

        The store records the SAME endpoint both ways -- ``mbp-ollama`` and
        ``custom:mbp-ollama`` are one host. Reading the name out of the
        qualifier is parsing a slug the transport wrote, not inferring hosting.
        """
        assert digest.classify_provider(provider) == expected

    @pytest.mark.parametrize("provider", ["custom", "custom:", "auto", "custom:glm"])
    def test_qualifier_stripping_does_not_manufacture_an_answer(self, provider):
        """Bare ``custom`` and unrecognised names stay unknown.

        ``custom:glm`` is the hosted-GLM case the whole never-guess rule exists
        for: a qualifier alone is not evidence of locality.
        """
        assert digest.classify_provider(provider) == "unknown"

    def test_class_map_full_slug_beats_the_bare_name(self):
        """An operator pinning the exact slug must outrank the name table."""
        assert (
            digest.classify_provider(
                "custom:spark", class_map={"custom:spark": "metered"}
            )
            == "metered"
        )

    def test_class_map_bare_name_still_reaches_a_qualified_slug(self):
        assert (
            digest.classify_provider("custom:glm", class_map={"glm": "metered"})
            == "metered"
        )

    def test_class_map_rejects_bogus_class_names(self, tmp_path):
        path = tmp_path / "map.json"
        path.write_text(json.dumps({"custom": "free-lunch", "spark": "local"}))
        loaded = digest.load_provider_class_map(path)
        assert loaded == {"spark": "local"}

    def test_missing_class_map_is_not_an_error(self, tmp_path):
        assert digest.load_provider_class_map(tmp_path / "nope.json") == {}

    def test_zero_cost_classes_render_their_reason_not_a_bare_zero(self):
        """``$0.0000`` is what makes a paid seat look free."""
        bucket = digest._blank_bucket()
        bucket.update({"cost_priced_calls": 1, "cost_unpriced_calls": 0})
        assert digest._cost_cell(bucket, True, "local") == "$0 (local)"
        assert "seat" in digest._cost_cell(bucket, True, "subscription")
        assert digest._cost_cell(bucket, True, "unknown") == "not attributable"


# ── latency ────────────────────────────────────────────────────────────────


class TestPercentiles:
    def test_nearest_rank_returns_an_observed_value(self):
        values = [10, 20, 30, 40, 100]
        assert digest.percentile(values, 0.5) == 30
        assert digest.percentile(values, 0.95) == 100
        assert digest.percentile(values, 0.0) == 10

    def test_empty_is_none_not_zero(self):
        assert digest.percentile([], 0.5) is None

    def test_p95_surfaces_the_tail_a_mean_hides(self):
        """The whole reason p95 is required: a mean buries the outlier."""
        summary = digest.summarize(
            [_row(wall_ms=100) for _ in range(18)] + [_row(wall_ms=60000) for _ in range(2)]
        )
        overall = summary["overall"]
        assert overall["wall_p50_ms"] == 100
        assert overall["wall_p95_ms"] == 60000
        assert overall["wall_mean_ms"] < overall["wall_p95_ms"] / 5

    def test_p95_does_not_over_report_a_single_outlier(self):
        """Nearest-rank, not interpolated: with 1 slow call in 20, 95% of calls
        really were fast, and p95 must say so. Loosening this to "p95 = the
        worst thing I saw" turns every isolated hiccup into a fake bottleneck.
        """
        summary = digest.summarize(
            [_row(wall_ms=100) for _ in range(19)] + [_row(wall_ms=60000)]
        )
        assert summary["overall"]["wall_p95_ms"] == 100
        assert summary["overall"]["wall_max_ms"] == 60000

    def test_untimed_calls_do_not_count_as_zero_latency(self):
        summary = digest.summarize([_row(wall_ms=500), _row(wall_ms=None)])
        overall = summary["overall"]
        assert overall["wall_samples_n"] == 1
        assert overall["wall_p50_ms"] == 500

    def test_missing_wall_times_are_disclosed_as_a_caveat(self):
        summary = digest.summarize([_row(wall_ms=500), _row(wall_ms=None)])
        assert any("carry no wall_ms" in c for c in summary["caveats"])

    def test_absent_ttft_is_stated_not_invented(self):
        """No ttft means we say what we cannot answer, not fabricate a metric."""
        summary = digest.summarize([_row(ttft_ms=None) for _ in range(3)])
        assert summary["overall"]["ttft_samples_n"] == 0
        assert any("ttft_ms" in caveat for caveat in summary["caveats"])

    def test_ttft_is_used_when_present(self):
        summary = digest.summarize([_row(ttft_ms=250), _row(ttft_ms=750)])
        assert summary["overall"]["ttft_p50_ms"] == 250
        assert summary["overall"]["ttft_samples_n"] == 2


# ── failures stay visible ──────────────────────────────────────────────────


class TestFailureVisibility:
    def test_failures_are_counted_by_kind(self):
        summary = digest.summarize(
            [
                _row(outcome="ok"),
                _row(outcome="error"),
                _row(outcome="timeout"),
                _row(outcome="refusal"),
            ]
        )
        overall = summary["overall"]
        assert (overall["ok"], overall["error"]) == (1, 1)
        assert (overall["timeout"], overall["refusal"]) == (1, 1)
        assert overall["failures"] == 3
        assert overall["success_rate"] == 25.0

    def test_unknown_outcome_is_coerced_to_error_not_dropped(self):
        summary = digest.summarize([_row(outcome="exploded")])
        assert summary["overall"]["error"] == 1
        assert summary["overall"]["calls"] == 1

    def test_failure_section_renders_even_with_zero_failures(self, tmp_path):
        """FLASH-SCOREBOARD's 25/25 was meaningless because failures were invisible."""
        summary = digest.summarize([_row() for _ in range(3)])
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "## Failures" in body
        assert "No failed calls" in body

    def test_thin_samples_are_marked_not_presented_as_reliability(self):
        summary = digest.summarize([_row() for _ in range(3)])
        assert summary["overall"]["low_confidence"] is True
        assert "thin" in digest._rate_cell(summary["overall"])
        assert any(f["kind"] == "thin_data" for f in summary["flags"])

    def test_a_clean_but_large_sample_still_questions_its_own_blind_spot(self):
        summary = digest.summarize([_row() for _ in range(50)])
        kinds = {f["kind"] for f in summary["flags"]}
        assert "no_failures_observed" in kinds
        assert "thin_data" not in kinds


# ── decision hooks ─────────────────────────────────────────────────────────


class TestDecisionFlags:
    def test_model_below_its_lane_average_is_flagged(self):
        rows = [_row(model="good", outcome="ok") for _ in range(20)]
        rows += [_row(model="bad", outcome="error") for _ in range(10)]
        summary = digest.summarize(rows)
        flags = [f for f in summary["flags"] if f["kind"] == "success_below_lane"]
        assert flags and "bad" in flags[0]["subject"]

    def test_a_model_at_the_lane_average_is_not_flagged(self):
        rows = [_row(model=f"m{i % 2}", outcome="ok") for i in range(20)]
        summary = digest.summarize(rows)
        assert not [f for f in summary["flags"] if f["kind"] == "success_below_lane"]

    def test_success_flag_does_not_fire_below_the_sample_floor(self):
        """A flag that fires on n=1 trains the reader to ignore flags."""
        rows = [_row(model="good", outcome="ok") for _ in range(20)]
        rows += [_row(model="rare", outcome="error")]
        summary = digest.summarize(rows)
        subjects = [
            f["subject"] for f in summary["flags"] if f["kind"] == "success_below_lane"
        ]
        assert not any("rare" in subject for subject in subjects)

    def test_higher_effort_buying_nothing_is_flagged(self):
        rows = [_row(model="m", effort="low", outcome="ok") for _ in range(10)]
        rows += [_row(model="m", effort="high", outcome="ok") for _ in range(10)]
        summary = digest.summarize(rows)
        flags = [f for f in summary["flags"] if f["kind"] == "effort_not_earning"]
        assert flags and "high" in flags[0]["subject"]

    def test_higher_effort_that_earns_its_keep_is_not_flagged(self):
        rows = [_row(model="m", effort="low", outcome="error") for _ in range(10)]
        rows += [_row(model="m", effort="high", outcome="ok") for _ in range(10)]
        summary = digest.summarize(rows)
        assert not [f for f in summary["flags"] if f["kind"] == "effort_not_earning"]

    def test_effort_flag_respects_the_sample_floor(self):
        rows = [_row(model="m", effort="low", outcome="ok") for _ in range(10)]
        rows += [_row(model="m", effort="high", outcome="ok")]
        summary = digest.summarize(rows)
        assert not [f for f in summary["flags"] if f["kind"] == "effort_not_earning"]

    def test_idle_models_surface_as_eviction_candidates(self):
        now_ms = 1786406705788
        old = now_ms - 30 * 86400 * 1000
        rows = [
            _row(model="alive", ts_epoch_ms=now_ms),
            _row(model="stale", ts_epoch_ms=old),
        ]
        idle = digest.eviction_candidates(rows, now_ms=now_ms, idle_days=7)
        assert [row["model"] for row in idle] == ["stale"]
        assert idle[0]["idle_days"] == pytest.approx(30, abs=0.5)

    def test_recently_used_models_are_not_eviction_candidates(self):
        now_ms = 1786406705788
        rows = [_row(model="alive", ts_epoch_ms=now_ms - 3600 * 1000)]
        assert digest.eviction_candidates(rows, now_ms=now_ms, idle_days=7) == []


# ── the surface + heartbeat ────────────────────────────────────────────────


class TestCLI:
    def test_writes_surface_and_heartbeat(self, tmp_path):
        root = _store(tmp_path, [_row(), _row(outcome="error")])
        surface = tmp_path / "OUT.md"
        beat = tmp_path / "beat.json"

        code = digest.main(
            [
                "--dir", str(root),
                "--since", "2020-01-01",
                "--out", str(surface),
                "--heartbeat", str(beat),
                "--quiet",
            ]
        )
        assert code == 0
        assert "# Model-call usage + success surface" in surface.read_text()

        payload = json.loads(beat.read_text())
        # Shape matches deploy/kevin-spark/ds4-watchdog.sh so one consumer can
        # read every heartbeat in the fleet.
        for key in ("system", "status", "fired_at", "expected_interval_seconds"):
            assert key in payload
        assert payload["system"] == "telemetry-digest"
        assert payload["calls_in_window"] == 2
        assert payload["failures"] == 1

    def test_heartbeat_is_written_even_when_the_digest_fails(self, tmp_path):
        """A missing status file must mean "the job is dead", never "all fine"."""
        beat = tmp_path / "beat.json"
        code = digest.main(
            [
                "--dir", str(tmp_path / "nope"),
                "--since", "not-a-time-at-all",
                "--heartbeat", str(beat),
                "--quiet",
            ]
        )
        assert code == 2
        payload = json.loads(beat.read_text())
        assert payload["status"] == "error"
        assert payload["system"] == "telemetry-digest"

    def test_empty_window_alerts_by_default(self, tmp_path):
        """Zero calls on a fleet that should be running is a signal, not silence."""
        root = _store(tmp_path, [])
        beat = tmp_path / "beat.json"
        code = digest.main(
            ["--dir", str(root), "--heartbeat", str(beat), "--quiet",
             "--out", str(tmp_path / "o.md")]
        )
        assert code == 1
        assert json.loads(beat.read_text())["status"] == "empty"

    def test_empty_window_can_be_made_non_alerting(self, tmp_path):
        root = _store(tmp_path, [])
        code = digest.main(
            ["--dir", str(root), "--no-heartbeat", "--quiet",
             "--out", str(tmp_path / "o.md"), "--no-alert-on-empty"]
        )
        assert code == 0

    def test_warn_flags_degrade_the_heartbeat(self, tmp_path):
        root = _store(tmp_path, [_row(provider="custom", model="x")])
        beat = tmp_path / "beat.json"
        digest.main(
            ["--dir", str(root), "--since", "2020-01-01", "--heartbeat", str(beat),
             "--quiet", "--out", str(tmp_path / "o.md")]
        )
        payload = json.loads(beat.read_text())
        assert payload["status"] == "degraded"
        assert payload["warn_flags"] >= 1

    def test_surface_is_written_before_stdout_delivery(self, tmp_path, capsys):
        root = _store(tmp_path, [_row()])
        surface = tmp_path / "OUT.md"
        digest.main(
            ["--dir", str(root), "--since", "2020-01-01", "--out", str(surface),
             "--no-heartbeat"]
        )
        printed = capsys.readouterr().out
        assert surface.read_text().strip() == printed.strip()

    def test_json_mode_is_machine_readable(self, tmp_path, capsys):
        root = _store(tmp_path, [_row(), _row(model="other", effort="low")])
        code = digest.main(
            ["--dir", str(root), "--since", "2020-01-01", "--json", "--no-heartbeat"]
        )
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["calls"] == 2
        # tuple-keyed groupings must survive serialization as row lists
        assert isinstance(payload["by_model_effort"], list)
        assert {row["model"] for row in payload["by_model_effort"]} == {
            "claude-opus-4-5",
            "other",
        }
        assert isinstance(payload["by_model_lane"], list)

    def test_reads_across_rotated_daily_files(self, tmp_path):
        """The store rotates daily; a digest that reads one file undercounts.

        Eviction detection in particular globs the whole store on purpose —
        "no calls in 7 days" is meaningless if only today's file is read.
        """
        root = tmp_path / "telemetry"
        root.mkdir()
        day_ms = 86400 * 1000
        now_ms = 1786406705788
        for offset, name in (
            (0, "model_calls-2026-08-10.jsonl"),
            (1, "model_calls-2026-08-09.jsonl"),
            (30, "model_calls-2026-07-11.jsonl"),
        ):
            (root / name).write_text(
                json.dumps(
                    _row(model=f"m{offset}", ts_epoch_ms=now_ms - offset * day_ms)
                )
                + "\n",
                encoding="utf-8",
            )

        surface = tmp_path / "OUT.md"
        code = digest.main(
            ["--dir", str(root), "--since", "2020-01-01", "--out", str(surface),
             "--no-heartbeat", "--quiet"]
        )
        assert code == 0
        body = surface.read_text()
        for model in ("m0", "m1", "m30"):
            assert model in body, f"{model} missing — a rotated file was not read"

        # and the 30-day-old model is the only eviction candidate
        idle = digest.eviction_candidates(
            digest.iter_records(root, None, None), now_ms=now_ms, idle_days=7
        )
        assert [row["model"] for row in idle] == ["m30"]

    def test_torn_final_line_does_not_break_the_digest(self, tmp_path):
        """The store is read while it is being appended to."""
        root = tmp_path / "telemetry"
        root.mkdir()
        (root / "model_calls-2026-08-10.jsonl").write_text(
            json.dumps(_row()) + "\n" + '{"provider": "trunc', encoding="utf-8"
        )
        code = digest.main(
            ["--dir", str(root), "--since", "2020-01-01", "--no-heartbeat",
             "--quiet", "--out", str(tmp_path / "o.md")]
        )
        assert code == 0

    def test_no_data_message_does_not_claim_an_idle_system(self, tmp_path):
        summary = digest.summarize([])
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "emit sites stopped firing" in body


class TestCounterfactual:
    def test_counterfactual_is_absent_unless_requested(self, tmp_path):
        summary = digest.summarize([_row(provider="spark", model="gpt-oss:120b")])
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "not asserted here" in body
        assert "counterfactual" not in summary

    def test_counterfactual_is_labelled_as_an_estimate(self, tmp_path):
        summary = digest.summarize([_row(provider="spark", model="gpt-oss:120b")])
        summary["counterfactual"] = {
            "model": "claude-opus-4-5",
            "would_have_cost_usd": 1.2345,
            "calls": 1,
        }
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "estimate, not a measurement" in body
        assert "is an assumption, not data" in body

    def test_counterfactual_only_reprices_zero_marginal_classes(self):
        """Repricing a metered call against a reference model is double-counting."""
        calls = []

        def fake_estimate(model, usage, **kwargs):
            calls.append(model)
            return type("R", (), {"amount_usd": 1})()

        rows = [
            _row(provider="spark", model="gpt-oss:120b"),
            _row(provider="anthropic", model="claude-opus-4-5"),
        ]
        result = digest.compute_counterfactual(
            rows, "ref-model", (lambda **kw: object(), fake_estimate), {}
        )
        assert result["calls"] == 1
        assert calls == ["ref-model"]

    def test_reference_may_name_its_provider(self):
        """Pricing tables key on (provider, model), so a bare name often misses."""
        seen = {}

        def fake_estimate(model, usage, **kwargs):
            seen["model"] = model
            seen["provider"] = kwargs.get("provider")
            return type("R", (), {"amount_usd": 2})()

        result = digest.compute_counterfactual(
            [_row(provider="spark", model="x")],
            "claude-opus-4-5@anthropic",
            (lambda **kw: object(), fake_estimate),
            {},
        )
        assert seen == {"model": "claude-opus-4-5", "provider": "anthropic"}
        assert result["would_have_cost_usd"] == 2

    def test_unpriceable_reference_reports_why_instead_of_vanishing(self, tmp_path):
        """A requested counterfactual that silently disappears reads as
        "nothing to report" when it actually means "this failed"."""

        def unpriceable(model, usage, **kwargs):
            return type("R", (), {"amount_usd": None})()

        result = digest.compute_counterfactual(
            [_row(provider="spark", model="x")],
            "no-such-model",
            (lambda **kw: object(), unpriceable),
            {},
        )
        assert "error" in result
        assert "no pricing entry" in result["error"]

        summary = digest.summarize([_row(provider="spark", model="x")])
        summary["counterfactual"] = result
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "not computed" in body

    def test_no_eligible_calls_reports_why(self):
        result = digest.compute_counterfactual(
            [_row(provider="anthropic", model="claude-opus-4-5")],
            "ref",
            (lambda **kw: object(), lambda *a, **k: None),
            {},
        )
        assert "nothing to reprice" in result["error"]

    def test_missing_pricing_reports_why(self):
        result = digest.compute_counterfactual(
            [_row(provider="spark", model="x")], "ref", None, {}
        )
        assert "usage_pricing" in result["error"]


class TestTrend:
    """"not just a snapshot in time" — every render carries its direction."""

    def test_absent_previous_window_is_not_a_100_percent_drop(self, tmp_path):
        """No data is not zero. Treating it as zero invents a collapse."""
        assert digest._delta_row("calls", None, 5)[3] == "—"
        assert digest._delta_row("calls", 5, None)[3] == "—"

    def test_delta_reports_direction_and_percentage(self):
        row = digest._delta_row("calls", 10, 15)
        assert row[3].startswith("+5")
        assert "+50%" in row[3]

    def test_delta_handles_a_zero_baseline_without_dividing_by_it(self):
        row = digest._delta_row("calls", 0, 4)
        assert row[3].startswith("+4")
        assert "%" not in row[3]

    def test_trend_section_renders_against_a_prior_window(self, tmp_path):
        day_ms = 86400 * 1000
        now_ms = int(__import__("time").time() * 1000)
        root = tmp_path / "telemetry"
        root.mkdir()
        rows = [_row(ts_epoch_ms=now_ms - 3600 * 1000) for _ in range(4)]
        rows += [
            _row(ts_epoch_ms=now_ms - int(1.5 * day_ms), outcome="error")
            for _ in range(2)
        ]
        (root / "model_calls-2026-08-10.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
        )

        surface = tmp_path / "OUT.md"
        code = digest.main(
            ["--dir", str(root), "--since", "24h", "--out", str(surface),
             "--no-heartbeat", "--quiet"]
        )
        assert code == 0
        body = surface.read_text()
        assert "## Trend vs the previous 24h" in body
        # current window = the 4 recent calls; previous = the 2 older ones
        assert "| calls | 2 | 4 | +2" in body

    def test_trend_can_be_switched_off(self, tmp_path):
        root = _store(tmp_path, [_row()])
        surface = tmp_path / "OUT.md"
        digest.main(
            ["--dir", str(root), "--since", "24h", "--out", str(surface),
             "--no-heartbeat", "--quiet", "--no-compare"]
        )
        assert "## Trend" not in surface.read_text()


class TestHeadlineCoverage:
    def test_every_token_class_including_reasoning_is_reported(self, tmp_path):
        summary = digest.summarize(
            [_row(reasoning_tokens=777, cache_write_tokens=888)]
        )
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "777 reasoning" in body
        assert "888 cache-write" in body

    def test_ttft_is_reported_when_present(self, tmp_path):
        summary = digest.summarize([_row(ttft_ms=120), _row(ttft_ms=340)])
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "time to first token" in body
        assert "120" in body

    def test_ttft_absence_is_stated_in_the_headline_not_shown_as_zero(self, tmp_path):
        summary = digest.summarize([_row(ttft_ms=None)])
        body = digest.render_markdown(summary, store=tmp_path, window_label="24h")
        assert "not reported by any call" in body


class TestCaveats:
    def test_run_count_confusion_is_pre_empted(self):
        summary = digest.summarize([_row()])
        assert any("floor on runs" in caveat for caveat in summary["caveats"])

    def test_known_emit_gaps_are_disclosed(self):
        summary = digest.summarize([_row()])
        assert any("emit gaps" in caveat for caveat in summary["caveats"])

    def test_missing_pricing_is_disclosed_rather_than_shown_as_zero(self):
        summary = digest.summarize([_row()], pricing=None)
        assert summary["pricing_available"] is False
        assert any("usage_pricing" in caveat for caveat in summary["caveats"])


class TestSnapshotHistory:
    """The rollup must outlive the raw store it was computed from.

    Trend deltas are recomputed from ``model_calls-*.jsonl`` every run, so
    without a dated copy of the RENDERED markdown, rotating or pruning the
    store destroys every past window irrecoverably.
    """

    def _run(self, tmp_path, extra, rows=None):
        # Inside the 24h window on purpose: the fixture default ts is fixed and
        # would fall out of it, turning every case into the empty-window path.
        now_ms = int(__import__("time").time() * 1000)
        default = [_row(ts_epoch_ms=now_ms - 3600 * 1000)]
        root = _store(tmp_path, rows if rows is not None else default)
        surface = tmp_path / "OUT.md"
        heartbeat = tmp_path / "hb.json"
        code = digest.main(
            ["--dir", str(root), "--since", "24h", "--out", str(surface),
             "--heartbeat", str(heartbeat), "--quiet"] + extra
        )
        return root, surface, heartbeat, code

    def test_no_snapshot_without_the_flag(self, tmp_path):
        """Ad-hoc runs must not silently accumulate an archive."""
        root, _, _, code = self._run(tmp_path, [])
        assert code == 0
        assert not (root / "digests").exists()

    def test_snapshot_is_dated_and_byte_identical_to_the_surface(self, tmp_path):
        snapdir = tmp_path / "archive"
        _, surface, _, code = self._run(tmp_path, ["--snapshot-dir", str(snapdir)])
        assert code == 0

        stamp = datetime.now().strftime("%Y-%m-%d")
        written = snapdir / f"USAGE-DIGEST-{stamp}.md"
        assert written.exists()
        assert written.read_text() == surface.read_text()

    def test_bare_flag_archives_under_the_store(self, tmp_path):
        root, _, _, code = self._run(tmp_path, ["--snapshot-dir"])
        assert code == 0
        assert list((root / "digests").glob("USAGE-DIGEST-*.md"))

    def test_heartbeat_carries_the_snapshot_path(self, tmp_path):
        snapdir = tmp_path / "archive"
        _, _, heartbeat, _ = self._run(tmp_path, ["--snapshot-dir", str(snapdir)])
        payload = json.loads(heartbeat.read_text())
        assert payload["snapshot"].startswith(str(snapdir))

    def test_heartbeat_snapshot_is_null_when_not_archiving(self, tmp_path):
        """Absent, not fabricated — a consumer can tell archiving is off."""
        _, _, heartbeat, _ = self._run(tmp_path, [])
        assert json.loads(heartbeat.read_text())["snapshot"] is None

    def test_snapshot_failure_degrades_loudly_but_does_not_kill_the_run(
        self, tmp_path, capsys
    ):
        """A dead archive must not take the surface down — and must not be
        silent either, since losing history is exactly the quiet degradation
        this surface exists to refuse."""
        blocked = tmp_path / "blocked"
        blocked.write_text("i am a file, not a directory", encoding="utf-8")

        _, surface, heartbeat, code = self._run(
            tmp_path, ["--snapshot-dir", str(blocked)]
        )

        assert code == 0                       # surface still rendered
        assert surface.read_text()             # ...and still written
        assert "snapshot NOT written" in capsys.readouterr().err

        payload = json.loads(heartbeat.read_text())
        assert payload["status"] == "degraded"
        assert "snapshot failed" in payload["detail"]
        assert payload["snapshot"] is None

    def test_json_mode_does_not_archive(self, tmp_path):
        """--json is a machine query, not the scheduled surface render."""
        root, _, _, _ = self._run(tmp_path, ["--snapshot-dir", "--json"])
        assert not (root / "digests").exists()

    def test_launcher_archives_into_the_store_not_hermes_home(self, tmp_path):
        """HERMES_HOME is the PROFILE dir under a Hermes worker session
        (~/.t1000/profiles/<name>), and the store is not under it. Deriving the
        archive path from HERMES_HOME writes history somewhere the digest never
        reads — and the commit step then correctly refuses to commit it, so the
        rollup silently stops accumulating. Pin the resolution rule instead.
        """
        import os
        import subprocess

        store = _store(tmp_path, [_row(ts_epoch_ms=int(__import__("time").time() * 1000))])
        profile_home = tmp_path / "profiles" / "worker"
        profile_home.mkdir(parents=True)

        env = dict(os.environ)
        env.update(
            {
                "T1000_TELEMETRY_DIR": str(store),
                "HERMES_HOME": str(profile_home),   # the trap
                "HOME": str(tmp_path / "fakehome"),
                "T1000_REPO": str(REPO_ROOT),
            }
        )
        env.pop("TELEMETRY_DIGEST_COMMIT", None)
        env.pop("TELEMETRY_DIGEST_SNAPSHOT_DIR", None)

        proc = subprocess.run(
            [str(REPO_ROOT / "deploy" / "telemetry-digest" / "telemetry-digest.sh")],
            capture_output=True, text=True, env=env,
        )

        assert proc.returncode == 0, proc.stderr
        assert list((store / "digests").glob("USAGE-DIGEST-*.md"))
        assert not (profile_home / "telemetry").exists()

        # Delivery contract: stdout IS the message body under a no-agent cron,
        # so operational chatter must never land there.
        assert "# Model-call usage + success surface" in proc.stdout
        assert "# Model-call usage + success surface" not in proc.stderr

    def test_empty_window_still_archives_what_it_rendered(self, tmp_path):
        """An empty digest is itself a finding worth keeping dated."""
        snapdir = tmp_path / "archive"
        root = _store(tmp_path, [_row(ts_epoch_ms=1)])   # far outside 24h
        code = digest.main(
            ["--dir", str(root), "--since", "24h", "--out", str(tmp_path / "O.md"),
             "--no-heartbeat", "--quiet", "--snapshot-dir", str(snapdir)]
        )
        assert code == 1                                  # the empty-window alert
        assert list(snapdir.glob("USAGE-DIGEST-*.md"))
