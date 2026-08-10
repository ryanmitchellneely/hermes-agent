"""Tests for the Distillery review agent (scripts/distillery_review_agent.py).

Card C2 scope only: cluster + judge pass (load index.json, select a
prioritized batch, judge, render reviews/<date>.md). --apply is a separate
follow-on card (C3) and is not implemented or tested here.

All fixtures are synthetic and local — no live network call to the judge;
`call_judge` is monkeypatched everywhere it would otherwise fire.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import distillery_review_agent as dra  # noqa: E402


def _row(rid, status="draft", captured_at="2026-08-09T03:15:16Z", title=None, **kw):
    row = {
        "id": rid,
        "source_kind": "plan",
        "source_path": f"~/.hermes/plans/{rid}.md",
        "source_ref": "deadbeef",
        "title": title or rid,
        "captured_at": captured_at,
        "status": status,
        "status_changed_at": captured_at,
        "summary": "a summary",
        "board": None,
        "superseded_by": None,
        "notes": "",
    }
    row.update(kw)
    return row


def _write_index(intake_dir: Path, rows: list[dict]) -> None:
    intake_dir.mkdir(parents=True, exist_ok=True)
    (intake_dir / "index.json").write_text(
        json.dumps({"schema": 1, "generated_at": "2026-08-10T00:00:00Z", "rows": rows}, indent=2),
        encoding="utf-8",
    )


def _stub_judge(monkeypatch, verdict="file"):
    """Deterministic one-cluster-per-row stub — no network call."""

    def fake_call_judge(rows):
        return {
            "clusters": [{"label": "Test cluster", "row_ids": [r["id"] for r in rows]}],
            "verdicts": {
                r["id"]: {"verdict": verdict, "rationale": "stub rationale", "supersede_of": None}
                for r in rows
            },
        }

    monkeypatch.setattr(dra, "call_judge", fake_call_judge)


# ── select_candidates: priority order + pending exclusion ─────────────


def test_stale_rows_sort_before_draft_rows():
    rows = [
        _row("d1", status="draft", captured_at="2026-08-01T00:00:00Z"),
        _row("s1", status="stale", captured_at="2026-08-09T00:00:00Z"),
    ]
    selected = dra.select_candidates(rows, pending_ids=set(), batch_size=10)
    assert [r["id"] for r in selected] == ["s1", "d1"]


def test_within_same_status_oldest_captured_at_first():
    rows = [
        _row("d2", status="draft", captured_at="2026-08-05T00:00:00Z"),
        _row("d1", status="draft", captured_at="2026-08-01T00:00:00Z"),
    ]
    selected = dra.select_candidates(rows, pending_ids=set(), batch_size=10)
    assert [r["id"] for r in selected] == ["d1", "d2"]


def test_batch_size_caps_selection():
    rows = [_row(f"d{i}") for i in range(20)]
    selected = dra.select_candidates(rows, pending_ids=set(), batch_size=8)
    assert len(selected) == 8


def test_pending_rows_are_excluded():
    rows = [_row("a"), _row("b")]
    selected = dra.select_candidates(rows, pending_ids={"a"}, batch_size=10)
    assert [r["id"] for r in selected] == ["b"]


def test_filed_and_skipped_rows_are_never_candidates():
    rows = [_row("a", status="filed"), _row("b", status="skipped"), _row("c", status="draft")]
    selected = dra.select_candidates(rows, pending_ids=set(), batch_size=10)
    assert [r["id"] for r in selected] == ["c"]


# ── normalize_judge_output: defensive fold ─────────────────────────────


def test_valid_supersede_passes_through():
    rows = [_row("a"), _row("b")]
    raw = {
        "clusters": [{"label": "C", "row_ids": ["a", "b"]}],
        "verdicts": {
            "a": {"verdict": "file", "rationale": "keep"},
            "b": {"verdict": "supersede", "rationale": "dup", "supersede_of": "a"},
        },
    }
    _, verdicts = dra.normalize_judge_output(rows, raw)
    assert verdicts["b"]["verdict"] == "supersede"
    assert verdicts["b"]["supersede_of"] == "a"


def test_supersede_of_outside_batch_is_coerced_to_skip():
    rows = [_row("a")]
    raw = {"clusters": [], "verdicts": {"a": {"verdict": "supersede", "supersede_of": "ghost"}}}
    _, verdicts = dra.normalize_judge_output(rows, raw)
    assert verdicts["a"]["verdict"] == "skip"
    assert verdicts["a"]["supersede_of"] is None
    assert "coerced to skip" in verdicts["a"]["rationale"]


def test_self_supersede_is_coerced_to_skip():
    rows = [_row("a")]
    raw = {"clusters": [], "verdicts": {"a": {"verdict": "supersede", "supersede_of": "a"}}}
    _, verdicts = dra.normalize_judge_output(rows, raw)
    assert verdicts["a"]["verdict"] == "skip"


def test_missing_verdict_defaults_to_skip_with_explanatory_rationale():
    rows = [_row("a")]
    raw = {"clusters": [], "verdicts": {}}
    _, verdicts = dra.normalize_judge_output(rows, raw)
    assert verdicts["a"]["verdict"] == "skip"
    assert "no usable verdict" in verdicts["a"]["rationale"]


def test_invalid_verdict_string_defaults_to_skip():
    rows = [_row("a")]
    raw = {"clusters": [], "verdicts": {"a": {"verdict": "delete", "rationale": "x"}}}
    _, verdicts = dra.normalize_judge_output(rows, raw)
    assert verdicts["a"]["verdict"] == "skip"


def test_row_missing_from_every_cluster_lands_in_uncategorized():
    rows = [_row("a"), _row("b")]
    raw = {"clusters": [{"label": "C", "row_ids": ["a"]}], "verdicts": {}}
    clusters, _ = dra.normalize_judge_output(rows, raw)
    uncategorized = next(c for c in clusters if c["label"] == "Uncategorized")
    assert uncategorized["row_ids"] == ["b"]


def test_every_row_appears_in_exactly_one_cluster_even_with_duplicate_claims():
    rows = [_row("a"), _row("b")]
    raw = {
        "clusters": [
            {"label": "First", "row_ids": ["a", "b"]},
            {"label": "Second", "row_ids": ["a"]},  # judge double-claimed "a"
        ],
        "verdicts": {},
    }
    clusters, _ = dra.normalize_judge_output(rows, raw)
    seen = [rid for c in clusters for rid in c["row_ids"]]
    assert sorted(seen) == ["a", "b"]
    assert len(seen) == len(set(seen))


# ── rendering ───────────────────────────────────────────────────────────


def test_review_markdown_has_editable_decision_field():
    rows = [_row("a", title="Row A")]
    clusters = [{"label": "C", "row_ids": ["a"]}]
    verdicts = {"a": {"cluster": "C", "verdict": "file", "rationale": "r", "supersede_of": None}}
    md = dra.render_review_markdown("2026-08-10", rows, clusters, verdicts)
    assert "id: a" in md
    assert "verdict: file" in md
    assert "rationale: r" in md
    assert "decision:" in md
    assert "supersede_of" not in md  # only present when applicable


def test_review_markdown_includes_supersede_of_only_when_set():
    rows = [_row("a", title="Row A")]
    clusters = [{"label": "C", "row_ids": ["a"]}]
    verdicts = {
        "a": {"cluster": "C", "verdict": "supersede", "rationale": "r", "supersede_of": "b"}
    }
    md = dra.render_review_markdown("2026-08-10", rows, clusters, verdicts)
    assert "supersede_of: b" in md


# ── pending cache round trip ────────────────────────────────────────────


def test_pending_cache_round_trips(tmp_path):
    cache = tmp_path / "pending.json"
    assert dra.load_pending(cache) == {}
    dra.save_pending(cache, {"a": {"review_date": "2026-08-10", "review_file": "reviews/2026-08-10.md"}})
    assert dra.load_pending(cache) == {"a": {"review_date": "2026-08-10", "review_file": "reviews/2026-08-10.md"}}


def test_pending_cache_missing_file_is_empty(tmp_path):
    assert dra.load_pending(tmp_path / "nope.json") == {}


# ── CLI / main(): dry-run writes nothing, real run writes + updates pending ──


def test_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    _stub_judge(monkeypatch)
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a"), _row("b")])
    pending_cache = tmp_path / "pending.json"

    rc = dra.main(
        [
            "--intake-dir", str(intake),
            "--pending-cache", str(pending_cache),
            "--dry-run",
            "--date", "2026-08-10",
        ]
    )
    assert rc == 0
    assert not (intake / "reviews").exists()
    assert not pending_cache.exists()
    out = capsys.readouterr().out
    assert "nothing written" in out


def test_real_run_writes_review_file_and_pending_cache(tmp_path, monkeypatch):
    _stub_judge(monkeypatch)
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a"), _row("b")])
    pending_cache = tmp_path / "pending.json"

    rc = dra.main(
        ["--intake-dir", str(intake), "--pending-cache", str(pending_cache), "--date", "2026-08-10"]
    )
    assert rc == 0
    review_file = intake / "reviews" / "2026-08-10.md"
    assert review_file.is_file()
    assert "decision:" in review_file.read_text()

    pending = dra.load_pending(pending_cache)
    assert set(pending.keys()) == {"a", "b"}
    assert pending["a"]["review_file"] == "reviews/2026-08-10.md"


def test_second_run_skips_rows_still_pending_from_first_batch(tmp_path, monkeypatch):
    _stub_judge(monkeypatch)
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a"), _row("b"), _row("c")])
    pending_cache = tmp_path / "pending.json"

    dra.main(
        [
            "--intake-dir", str(intake),
            "--pending-cache", str(pending_cache),
            "--batch-size", "2",
            "--date", "2026-08-10",
        ]
    )
    first_pending = set(dra.load_pending(pending_cache).keys())
    assert len(first_pending) == 2

    rc = dra.main(
        [
            "--intake-dir", str(intake),
            "--pending-cache", str(pending_cache),
            "--batch-size", "2",
            "--date", "2026-08-11",
        ]
    )
    assert rc == 0
    second_pending = set(dra.load_pending(pending_cache).keys()) - first_pending
    assert second_pending == {"c"}


def test_real_run_is_silent_when_no_candidates(tmp_path, monkeypatch, capsys):
    _stub_judge(monkeypatch)
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a", status="filed")])
    pending_cache = tmp_path / "pending.json"

    rc = dra.main(
        ["--intake-dir", str(intake), "--pending-cache", str(pending_cache), "--date", "2026-08-10"]
    )
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_json_output_is_machine_readable(tmp_path, monkeypatch):
    _stub_judge(monkeypatch)
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a")])
    pending_cache = tmp_path / "pending.json"

    rc = dra.main(
        [
            "--intake-dir", str(intake),
            "--pending-cache", str(pending_cache),
            "--dry-run",
            "--json",
            "--date", "2026-08-10",
        ]
    )
    assert rc == 0


def test_judge_never_invoked_when_all_rows_already_pending(tmp_path, monkeypatch):
    intake = tmp_path / "intake"
    _write_index(intake, [_row("a")])
    pending_cache = tmp_path / "pending.json"
    dra.save_pending(pending_cache, {"a": {"review_date": "2026-08-09", "review_file": "x"}})

    def boom(rows):
        raise AssertionError("call_judge should not be invoked with zero candidates")

    monkeypatch.setattr(dra, "call_judge", boom)

    rc = dra.main(
        ["--intake-dir", str(intake), "--pending-cache", str(pending_cache), "--date", "2026-08-10"]
    )
    assert rc == 0
