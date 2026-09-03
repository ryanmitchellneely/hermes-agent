"""Tests for scripts/t1000_distillery_review_apply.py — the kanban-comment
applier that replaces distillery_review_agent.py's hand-edited decision:
field path (13 batches, 0 human edits ever).

`parse_decision` is pure-text parsing; the `apply_decision` tests below run
end-to-end against a temp intake dir with a real reviews/<date>.md rendered
by distillery_review_agent.render_review_markdown(), with only
`run_sweep_mark` monkeypatched (never shells out to the real sweep here).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import distillery_review_agent as dra  # noqa: E402
import t1000_distillery_review_apply as tdra  # noqa: E402


# ── parse_decision: reply grammar ───────────────────────────────────────


def test_parse_decision_file_and_skip_rest():
    d = tdra.parse_decision("FILE 1,4 / SKIP rest")
    assert d == {"file": {1, 4}, "skip": "rest", "defer": False}


def test_parse_decision_is_case_insensitive_and_tolerates_whitespace():
    d = tdra.parse_decision("  file 1, 2 ; skip 3  ")
    assert d == {"file": {1, 2}, "skip": {3}, "defer": False}


def test_parse_decision_file_all():
    assert tdra.parse_decision("FILE ALL") == {"file": "ALL", "skip": set(), "defer": False}


def test_parse_decision_skip_all():
    assert tdra.parse_decision("SKIP ALL") == {"file": set(), "skip": "ALL", "defer": False}


def test_parse_decision_defer():
    assert tdra.parse_decision("DEFER") == {"file": set(), "skip": set(), "defer": True}
    assert tdra.parse_decision("defer") == {"file": set(), "skip": set(), "defer": True}


def test_parse_decision_ranges_expand_inclusive():
    d = tdra.parse_decision("FILE 2-5")
    assert d == {"file": {2, 3, 4, 5}, "skip": set(), "defer": False}


def test_parse_decision_only_the_first_nonempty_line_matters():
    d = tdra.parse_decision("\n\nFILE 1\nthanks — filing this one")
    assert d == {"file": {1}, "skip": set(), "defer": False}


def test_parse_decision_garbage_returns_none():
    assert tdra.parse_decision("looks good, thanks!") is None
    assert tdra.parse_decision("FILE") is None
    assert tdra.parse_decision("FILE banana") is None


def test_parse_decision_blocked_prefix_returns_none():
    assert tdra.parse_decision("BLOCKED: waiting on Kevin") is None


def test_parse_decision_unblock_prefix_returns_none():
    assert tdra.parse_decision("UNBLOCK: resuming") is None


def test_parse_decision_other_automation_prefixes_return_none():
    assert tdra.parse_decision("WIDTH-CONTROL: ncols=160") is None
    assert tdra.parse_decision("RECLAIM: stale claim released") is None
    assert tdra.parse_decision("AUTO-ESCALATE (timeout): sonnet -> opus") is None


def test_parse_decision_empty_or_blank_text_returns_none():
    assert tdra.parse_decision("") is None
    assert tdra.parse_decision("   \n   \n") is None


# ── apply_decision: end-to-end against a fabricated review file ────────


def _index_row(rid, title, board=None):
    return {
        "id": rid,
        "source_kind": "mesh_done_card" if rid.startswith("mesh_done_card:") else "plan",
        "source_path": f"~/.hermes/plans/{rid}.md",
        "source_ref": "deadbeef",
        "title": title,
        "captured_at": "2026-08-09T03:15:16Z",
        "status": "draft",
        "status_changed_at": "2026-08-09T03:15:16Z",
        "summary": "a summary",
        "board": board,
        "superseded_by": None,
        "notes": "",
    }


def _write_index(intake_dir: Path, rows: list[dict]) -> None:
    intake_dir.mkdir(parents=True, exist_ok=True)
    (intake_dir / "index.json").write_text(
        json.dumps({"schema": 1, "generated_at": "2026-08-10T00:00:00Z", "rows": rows}, indent=2),
        encoding="utf-8",
    )


def _write_review(intake_dir: Path, date_str: str, rows, clusters, verdicts) -> Path:
    text = dra.render_review_markdown(date_str, rows, clusters, verdicts)
    path = intake_dir / "reviews" / f"{date_str}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_apply_decision_files_and_skips_by_row_number_and_writes_lessons_ledger(tmp_path, monkeypatch):
    intake = tmp_path / "intake"
    rows = [
        _index_row("mesh_done_card:t_aaa@1", "Card A", board="k2"),
        _index_row("plan:xyz", "Plan B"),
        _index_row("plan:zzz", "Plan C"),
    ]
    _write_index(intake, rows)

    clusters = [{"label": "C", "row_ids": [r["id"] for r in rows]}]
    verdicts = {
        "mesh_done_card:t_aaa@1": {
            "cluster": "C", "verdict": "file", "rationale": "worth filing", "supersede_of": None
        },
        "plan:xyz": {"cluster": "C", "verdict": "skip", "rationale": "too narrow", "supersede_of": None},
        "plan:zzz": {"cluster": "C", "verdict": "skip", "rationale": "still deciding", "supersede_of": None},
    }
    date_str = "2026-08-10"
    _write_review(intake, date_str, rows, clusters, verdicts)

    pending_cache = tmp_path / "pending.json"
    dra.save_pending(
        pending_cache,
        {r["id"]: {"review_date": date_str, "review_file": f"reviews/{date_str}.md"} for r in rows},
    )

    recorded_marks: list[str] = []
    monkeypatch.setattr(
        tdra, "run_sweep_mark", lambda sweep_script, intake_dir, marks: recorded_marks.extend(marks)
    )

    # Row 1 = Card A, row 2 = Plan B, row 3 = Plan C (document order).
    decision = {"file": {1}, "skip": {2}, "defer": False}
    result = tdra.apply_decision(date_str, decision, intake, pending_cache)

    assert result == {"filed": 1, "skipped": 1, "pending": 1, "defer": False}
    assert sorted(recorded_marks) == sorted(
        ["mesh_done_card:t_aaa@1=filed", "plan:xyz=skipped"]
    )

    filed_log = (intake / "FILED-LOG.md").read_text()
    assert "mesh_done_card:t_aaa@1 | Card A" in filed_log
    assert "worth filing" in filed_log
    assert "Plan B" not in filed_log  # skip verdict never gets a FILED-LOG line

    lessons = (intake / "LESSONS-LEDGER.md").read_text()
    assert "k2:t_aaa" in lessons
    assert "Card A" in lessons
    assert "worth filing" in lessons
    assert "Plan B" not in lessons  # only mesh_done_card: ids get a lessons line

    pending = dra.load_pending(pending_cache)
    assert set(pending.keys()) == {"plan:zzz"}  # row 3 never named -> stays pending


def test_apply_decision_file_all_and_skip_rest_leave_nothing_pending(tmp_path, monkeypatch):
    intake = tmp_path / "intake"
    rows = [_index_row("a", "Row A"), _index_row("b", "Row B")]
    _write_index(intake, rows)
    clusters = [{"label": "C", "row_ids": ["a", "b"]}]
    verdicts = {
        "a": {"cluster": "C", "verdict": "file", "rationale": "keep", "supersede_of": None},
        "b": {"cluster": "C", "verdict": "skip", "rationale": "narrow", "supersede_of": None},
    }
    date_str = "2026-08-10"
    _write_review(intake, date_str, rows, clusters, verdicts)
    pending_cache = tmp_path / "pending.json"
    dra.save_pending(
        pending_cache,
        {r["id"]: {"review_date": date_str, "review_file": f"reviews/{date_str}.md"} for r in rows},
    )
    monkeypatch.setattr(tdra, "run_sweep_mark", lambda *a, **k: None)

    result = tdra.apply_decision(
        date_str, {"file": "ALL", "skip": set(), "defer": False}, intake, pending_cache
    )
    assert result == {"filed": 2, "skipped": 0, "pending": 0, "defer": False}
    assert dra.load_pending(pending_cache) == {}


def test_apply_decision_supersede_writes_dup_note_on_draft_file(tmp_path, monkeypatch):
    intake = tmp_path / "intake"
    rows = [_index_row("a", "Row A"), _index_row("b", "Row B")]
    _write_index(intake, rows)
    clusters = [{"label": "C", "row_ids": ["a", "b"]}]
    verdicts = {
        "a": {"cluster": "C", "verdict": "file", "rationale": "keep", "supersede_of": None},
        "b": {"cluster": "C", "verdict": "supersede", "rationale": "dup of a", "supersede_of": "a"},
    }
    date_str = "2026-08-10"
    _write_review(intake, date_str, rows, clusters, verdicts)

    drafts_dir = intake / "drafts"
    drafts_dir.mkdir(parents=True)
    (drafts_dir / "b.md").write_text("# draft\n\n## notes\n\n(none)\n", encoding="utf-8")

    pending_cache = tmp_path / "pending.json"
    dra.save_pending(
        pending_cache,
        {r["id"]: {"review_date": date_str, "review_file": f"reviews/{date_str}.md"} for r in rows},
    )
    monkeypatch.setattr(tdra, "run_sweep_mark", lambda *a, **k: None)

    result = tdra.apply_decision(
        date_str, {"file": {1}, "skip": {2}, "defer": False}, intake, pending_cache
    )
    assert result == {"filed": 1, "skipped": 1, "pending": 0, "defer": False}

    draft_text = (drafts_dir / "b.md").read_text()
    assert "dup of a" in draft_text.split("## notes")[-1]


def test_apply_decision_defer_leaves_pending_cache_untouched(tmp_path, monkeypatch):
    intake = tmp_path / "intake"
    rows = [_index_row("a", "Row A")]
    _write_index(intake, rows)
    clusters = [{"label": "C", "row_ids": ["a"]}]
    verdicts = {"a": {"cluster": "C", "verdict": "file", "rationale": "keep", "supersede_of": None}}
    date_str = "2026-08-10"
    _write_review(intake, date_str, rows, clusters, verdicts)

    pending_cache = tmp_path / "pending.json"
    dra.save_pending(
        pending_cache, {"a": {"review_date": date_str, "review_file": f"reviews/{date_str}.md"}}
    )

    def boom(*a, **k):
        raise AssertionError("run_sweep_mark must not be called on DEFER")

    monkeypatch.setattr(tdra, "run_sweep_mark", boom)

    result = tdra.apply_decision(
        date_str, {"file": set(), "skip": set(), "defer": True}, intake, pending_cache
    )
    assert result == {"filed": 0, "skipped": 0, "pending": 1, "defer": True}
    assert dra.load_pending(pending_cache) == {"a": {"review_date": date_str, "review_file": f"reviews/{date_str}.md"}}


def test_apply_decision_missing_review_file_raises(tmp_path):
    intake = tmp_path / "intake"
    intake.mkdir()
    pending_cache = tmp_path / "pending.json"
    try:
        tdra.apply_decision("2026-08-10", {"file": "ALL", "skip": set(), "defer": False}, intake, pending_cache)
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert "no review file" in str(e)


def test_trailing_note_after_dash_colon_or_paren_is_ignored():
    from t1000_distillery_review_apply import parse_decision

    assert parse_decision("DEFER — applier smoke test (ryan-claude); still owed")["defer"] is True
    assert parse_decision("FILE ALL: these are all keepers")["file"] == "ALL"
    assert parse_decision("SKIP ALL (nothing durable here)")["skip"] == "ALL"
    d = parse_decision("FILE 1,4 / SKIP rest — the rest are bookkeeping")
    assert d["file"] == {1, 4} and d["skip"] == "rest"
    d = parse_decision("FILE 2-5 - keep the plans")
    assert d["file"] == {2, 3, 4, 5}
