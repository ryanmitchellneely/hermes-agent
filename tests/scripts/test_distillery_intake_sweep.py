"""Tests for the Distillery intake sweep (scripts/distillery_intake_sweep.py).

The sweep PULLs durable artifacts from systems of record (plans, signal-log
entries, mesh done cards, skill references) and drafts review rows. Design:
docs/research/distillery-intake-sweep-design.md (card t_216ac84b).

All fixtures are synthetic and local — no live network, no K2, no writes
outside tmp_path.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import distillery_intake_sweep as sweep  # noqa: E402


# ── reconcile core: draft / no-op / supersede / stale ──────────────────


def _fp(source_kind="plan", path="a.md", ref="deadbeef", title="A"):
    return {
        "id": f"{source_kind}:{ref}",
        "source_kind": source_kind,
        "source_path": path,
        "source_ref": ref,
        "title": title,
        "summary": None,
        "board": None,
    }


def test_new_fingerprint_creates_draft_row():
    result = sweep.reconcile(
        rows=[],
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        staleness_days=5,
    )

    assert [r["id"] for r in result.new] == ["plan:deadbeef"]
    row = result.rows[0]
    assert row["status"] == "draft"
    assert row["captured_at"] == "2026-08-08T00:00:00Z"
    assert row["superseded_by"] is None
    assert row["notes"] == ""


def test_second_run_on_unchanged_source_produces_zero_new_rows():
    now = sweep.parse_ts("2026-08-08T00:00:00Z")
    first = sweep.reconcile(rows=[], fingerprints=[_fp()], now=now, staleness_days=5)

    second = sweep.reconcile(
        rows=first.rows,
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-08T06:00:00Z"),
        staleness_days=5,
    )

    assert second.new == []
    assert second.superseded == []
    assert len(second.rows) == 1
    assert second.rows[0]["status"] == "draft"


def test_already_filed_row_is_not_redrafted():
    now = sweep.parse_ts("2026-08-08T00:00:00Z")
    first = sweep.reconcile(rows=[], fingerprints=[_fp()], now=now, staleness_days=5)
    first.rows[0]["status"] = "filed"

    second = sweep.reconcile(
        rows=first.rows,
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-09T00:00:00Z"),
        staleness_days=5,
    )

    assert second.new == []
    assert second.rows[0]["status"] == "filed"


def test_changed_fingerprint_supersedes_old_draft_and_creates_new():
    first = sweep.reconcile(
        rows=[],
        fingerprints=[_fp(ref="aaaa")],
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        staleness_days=5,
    )

    second = sweep.reconcile(
        rows=first.rows,
        fingerprints=[_fp(ref="bbbb")],
        now=sweep.parse_ts("2026-08-09T00:00:00Z"),
        staleness_days=5,
    )

    by_id = {r["id"]: r for r in second.rows}
    assert by_id["plan:aaaa"]["status"] == "superseded"
    assert by_id["plan:aaaa"]["superseded_by"] == "plan:bbbb"
    assert by_id["plan:bbbb"]["status"] == "draft"
    assert [r["id"] for r in second.new] == ["plan:bbbb"]


def test_filed_row_is_not_superseded_when_source_changes():
    # A human decision (filed/skipped) is terminal — a later edit of the same
    # source drafts a fresh row but must not rewrite the human's verdict.
    first = sweep.reconcile(
        rows=[],
        fingerprints=[_fp(ref="aaaa")],
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        staleness_days=5,
    )
    first.rows[0]["status"] = "filed"

    second = sweep.reconcile(
        rows=first.rows,
        fingerprints=[_fp(ref="bbbb")],
        now=sweep.parse_ts("2026-08-09T00:00:00Z"),
        staleness_days=5,
    )

    by_id = {r["id"]: r for r in second.rows}
    assert by_id["plan:aaaa"]["status"] == "filed"
    assert by_id["plan:aaaa"]["superseded_by"] is None
    assert by_id["plan:bbbb"]["status"] == "draft"


def test_aged_unswept_draft_flips_to_stale():
    first = sweep.reconcile(
        rows=[],
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-01T00:00:00Z"),
        staleness_days=5,
    )

    second = sweep.reconcile(
        rows=first.rows,
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        staleness_days=5,
    )

    assert [r["id"] for r in second.newly_stale] == ["plan:deadbeef"]
    assert second.rows[0]["status"] == "stale"
    assert second.rows[0]["status_changed_at"] == "2026-08-08T00:00:00Z"


def test_stale_row_is_reported_once_not_every_run():
    rows = sweep.reconcile(
        rows=[], fingerprints=[_fp()], now=sweep.parse_ts("2026-08-01T00:00:00Z"), staleness_days=5
    ).rows
    aged = sweep.reconcile(
        rows=rows, fingerprints=[_fp()], now=sweep.parse_ts("2026-08-08T00:00:00Z"), staleness_days=5
    )
    again = sweep.reconcile(
        rows=aged.rows,
        fingerprints=[_fp()],
        now=sweep.parse_ts("2026-08-09T00:00:00Z"),
        staleness_days=5,
    )

    assert again.newly_stale == []
    assert again.rows[0]["status"] == "stale"


def test_draft_within_threshold_stays_draft():
    rows = sweep.reconcile(
        rows=[], fingerprints=[_fp()], now=sweep.parse_ts("2026-08-01T00:00:00Z"), staleness_days=5
    ).rows
    later = sweep.reconcile(
        rows=rows, fingerprints=[_fp()], now=sweep.parse_ts("2026-08-04T00:00:00Z"), staleness_days=5
    )

    assert later.newly_stale == []
    assert later.rows[0]["status"] == "draft"


def test_disappearing_source_leaves_existing_rows_untouched():
    # Deleting a plan file must not delete its review row — the artifact
    # existed and the human still owes it a verdict.
    rows = sweep.reconcile(
        rows=[], fingerprints=[_fp()], now=sweep.parse_ts("2026-08-08T00:00:00Z"), staleness_days=5
    ).rows

    result = sweep.reconcile(
        rows=rows, fingerprints=[], now=sweep.parse_ts("2026-08-08T01:00:00Z"), staleness_days=5
    )

    assert len(result.rows) == 1
    assert result.rows[0]["status"] == "draft"


# ── file sources: content-hash fingerprints ───────────────────────────


def test_file_fingerprint_is_content_hashed_not_mtime_based(tmp_path):
    # git checkout resets mtimes without changing content; the sweep must not
    # flood with false "new artifact" drafts on a fresh clone.
    plans = tmp_path / "plans"
    plans.mkdir()
    f = plans / "p.md"
    f.write_text("# Plan One\n\nbody\n")

    before = sweep.collect_file_fingerprints("plan", plans, "*.md")
    f.touch()
    import os
    import time

    os.utime(f, (time.time() + 500, time.time() + 500))
    after = sweep.collect_file_fingerprints("plan", plans, "*.md")

    assert [x["id"] for x in before] == [x["id"] for x in after]


def test_file_fingerprint_changes_when_content_changes(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    f = plans / "p.md"
    f.write_text("# Plan One\n")
    before = sweep.collect_file_fingerprints("plan", plans, "*.md")
    f.write_text("# Plan One\n\nnow with a decision\n")
    after = sweep.collect_file_fingerprints("plan", plans, "*.md")

    assert before[0]["id"] != after[0]["id"]
    assert before[0]["source_path"] == after[0]["source_path"]


def test_file_fingerprint_derives_title_from_first_heading(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "p.md").write_text("# Mesh efficiency pack\n\nFirst paragraph here.\n")

    fp = sweep.collect_file_fingerprints("plan", plans, "*.md")[0]

    assert fp["title"] == "Mesh efficiency pack"
    assert fp["summary"] == "First paragraph here."
    assert fp["source_kind"] == "plan"


def test_file_fingerprint_falls_back_to_filename_without_heading(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "no-heading.md").write_text("just text\n")

    fp = sweep.collect_file_fingerprints("plan", plans, "*.md")[0]

    assert fp["title"] == "no-heading.md"


def test_missing_source_dir_yields_no_fingerprints(tmp_path):
    assert sweep.collect_file_fingerprints("plan", tmp_path / "nope", "*.md") == []


# ── signal-log posture/bucket filters ─────────────────────────────────


def _sig(posture="steal", bucket="inference"):
    return (
        "# SIG-20260808-09 — thing\n\n"
        "```yaml\n"
        "id: SIG-20260808-09\n"
        'title: "A thing"\n'
        f"bucket: {bucket}\n"
        f"posture: {posture}\n"
        "steal_rank: P1\n"
        "```\n\nBody text.\n"
    )


def test_signal_log_frontmatter_parsed_from_fenced_yaml_block():
    meta = sweep.parse_signal_frontmatter(_sig(posture="watch", bucket="ops"))

    assert meta["posture"] == "watch"
    assert meta["bucket"] == "ops"


def test_signal_posture_ignore_is_excluded(tmp_path):
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "SIG-1.md").write_text(_sig(posture="ignore"))

    fps = sweep.collect_signal_fingerprints(
        entries, {"exclude_posture": ["ignore"], "exclude_bucket": ["noise"]}
    )

    assert fps == []


def test_signal_bucket_noise_is_excluded(tmp_path):
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "SIG-1.md").write_text(_sig(bucket="noise"))

    fps = sweep.collect_signal_fingerprints(
        entries, {"exclude_posture": ["ignore"], "exclude_bucket": ["noise"]}
    )

    assert fps == []


def test_signal_posture_watch_is_included(tmp_path):
    # watch is still citation-worthy per design §2 — excluding it would be a
    # false negative, the failure mode this design deliberately avoids.
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "SIG-1.md").write_text(_sig(posture="watch"))

    fps = sweep.collect_signal_fingerprints(
        entries, {"exclude_posture": ["ignore"], "exclude_bucket": ["noise"]}
    )

    assert len(fps) == 1
    assert fps[0]["source_kind"] == "signal_log_entry"


# ── mesh done cards ───────────────────────────────────────────────────


def _make_board_db(tmp_path, rows):
    import sqlite3

    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "kanban.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, body TEXT, status TEXT,"
        " completed_at INTEGER, completion_generation INTEGER NOT NULL DEFAULT 0)"
    )
    con.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return db


def test_done_cards_become_fingerprints(tmp_path):
    db = _make_board_db(
        tmp_path, [("t_aaa", "Ship the thing", "why it matters", "done", 1786000000, 1)]
    )

    fps = sweep.collect_board_fingerprints("mesh", db, [])

    assert len(fps) == 1
    assert fps[0]["id"] == "mesh_done_card:t_aaa@1"
    assert fps[0]["source_path"] == "t_aaa"
    assert fps[0]["title"] == "Ship the thing"
    assert fps[0]["board"] == "mesh"


def test_non_done_cards_are_ignored(tmp_path):
    db = _make_board_db(
        tmp_path,
        [
            ("t_aaa", "Running", None, "running", None, 0),
            ("t_bbb", "Blocked", None, "blocked", None, 0),
        ],
    )

    assert sweep.collect_board_fingerprints("mesh", db, []) == []


def test_pr_review_wrapper_cards_are_excluded_by_config_pattern(tmp_path):
    db = _make_board_db(
        tmp_path,
        [
            ("t_aaa", "HUMAN review: PR #4352", None, "done", 1786000000, 1),
            ("t_bbb", "Real artifact card", None, "done", 1786000000, 1),
        ],
    )

    fps = sweep.collect_board_fingerprints("mesh", db, ["^HUMAN review: PR #"])

    assert [f["source_path"] for f in fps] == ["t_bbb"]


def test_recompleted_card_produces_a_new_fingerprint(tmp_path):
    db1 = _make_board_db(tmp_path / "a", [("t_aaa", "Card", None, "done", 1786000000, 1)])
    db2 = _make_board_db(tmp_path / "b", [("t_aaa", "Card", None, "done", 1786100000, 2)])

    first = sweep.collect_board_fingerprints("mesh", db1, [])
    second = sweep.collect_board_fingerprints("mesh", db2, [])

    assert first[0]["id"] == "mesh_done_card:t_aaa@1"
    assert second[0]["id"] == "mesh_done_card:t_aaa@2"


def test_since_filters_board_cards_by_completion_time(tmp_path):
    db = _make_board_db(
        tmp_path,
        [
            ("t_old", "Old", None, "done", 1785000000, 1),
            ("t_new", "New", None, "done", 1786000000, 1),
        ],
    )

    fps = sweep.collect_board_fingerprints("mesh", db, [], since_epoch=1785500000)

    assert [f["source_path"] for f in fps] == ["t_new"]


def test_missing_board_db_is_not_fatal(tmp_path):
    assert sweep.collect_board_fingerprints("mesh", tmp_path / "nope.db", []) == []


def _make_board_db_with_result(tmp_path, rows):
    import sqlite3

    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "kanban.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, body TEXT, status TEXT,"
        " completed_at INTEGER, completion_generation INTEGER NOT NULL DEFAULT 0,"
        " result TEXT)"
    )
    con.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return db


def test_require_result_filters_cards_without_a_result(tmp_path):
    db = _make_board_db_with_result(
        tmp_path,
        [
            ("t_aaa", "Has a result", None, "done", 1786000000, 1, "wrote the fix"),
            ("t_bbb", "No result", None, "done", 1786000000, 1, None),
            ("t_ccc", "Blank result", None, "done", 1786000000, 1, "   "),
        ],
    )

    strict = sweep.collect_board_fingerprints("mesh", db, [], require_result=True)
    lenient = sweep.collect_board_fingerprints("mesh", db, [], require_result=False)

    assert [f["source_path"] for f in strict] == ["t_aaa"]
    assert [f["source_path"] for f in lenient] == ["t_aaa", "t_bbb", "t_ccc"]


# ── config: mesh-only default, board list is config not schema ────────


def test_default_config_is_mesh_only(tmp_path):
    cfg = sweep.load_config(tmp_path / "absent.yaml")

    assert cfg["boards"] == ["mesh"]
    assert cfg["staleness_days"] == 5


def test_adding_a_board_is_a_config_edit_only(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("boards:\n  - mesh\n  - k2\nstaleness_days: 9\n")

    cfg = sweep.load_config(p)

    assert cfg["boards"] == ["mesh", "k2"]
    assert cfg["staleness_days"] == 9
    # unspecified keys still fall back to defaults
    assert cfg["sources"]["plans"]["enabled"] is True


def test_config_can_disable_a_source(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("sources:\n  plans:\n    enabled: false\n")

    cfg = sweep.load_config(p)

    assert cfg["sources"]["plans"]["enabled"] is False
    assert cfg["sources"]["signal_log"]["enabled"] is True


def test_require_result_boards_honored_per_board_via_collect_fingerprints(tmp_path):
    board_a = tmp_path / "boards" / "a"
    board_b = tmp_path / "boards" / "b"
    _make_board_db_with_result(
        board_a,
        [
            ("t_a1", "A with result", None, "done", 1786000000, 1, "done note"),
            ("t_a2", "A without result", None, "done", 1786000000, 1, None),
        ],
    )
    _make_board_db_with_result(
        board_b,
        [
            ("t_b1", "B with result", None, "done", 1786000000, 1, "done note"),
            ("t_b2", "B without result", None, "done", 1786000000, 1, None),
        ],
    )

    config = {
        "boards": ["a", "b"],
        "sources": {
            "plans": {"enabled": False, "path": "unused"},
            "signal_log": {"enabled": False, "path": "unused"},
            "mesh_done_cards": {
                "enabled": True,
                "db_template": str(tmp_path / "boards" / "{board}" / "kanban.db"),
                "title_exclude_patterns": [],
                "require_result_boards": ["a"],
            },
            "skill_references": {"enabled": False, "trees": []},
        },
        "filters": {},
        "staleness_days": 5,
    }

    fps, _ = sweep.collect_fingerprints(config, repo_root=tmp_path)

    by_path = {fp["source_path"]: fp for fp in fps}
    assert "t_a1" in by_path and "t_a2" not in by_path
    assert "t_b1" in by_path and "t_b2" in by_path


# ── draft rendering + human round-trip ────────────────────────────────


def _row(**kw):
    row = {
        "id": "plan:abc123",
        "source_kind": "plan",
        "source_path": "~/.hermes/plans/x.md",
        "source_ref": "abc123",
        "title": "A plan",
        "captured_at": "2026-08-08T00:00:00Z",
        "status": "draft",
        "status_changed_at": "2026-08-08T00:00:00Z",
        "summary": "Short excerpt.",
        "board": None,
        "superseded_by": None,
        "notes": "",
    }
    row.update(kw)
    return row


def test_draft_markdown_contains_row_fields():
    md = sweep.render_draft(_row())

    assert "A plan" in md
    assert "id: plan:abc123" in md
    assert "status: draft" in md
    assert "Short excerpt." in md


def test_human_edited_notes_survive_regeneration(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    row = _row()
    (drafts / "plan:abc123.md").write_text(sweep.render_draft(row))

    path = drafts / "plan:abc123.md"
    path.write_text(path.read_text() + "\nRyan: file this under router work.\n")
    carried = sweep.read_human_edits(drafts, row["id"])

    assert "file this under router work" in carried["notes"]
    regenerated = sweep.render_draft({**row, "notes": carried["notes"]})
    assert "file this under router work" in regenerated


def test_human_status_edit_in_draft_file_is_read_back(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    row = _row()
    path = drafts / "plan:abc123.md"
    path.write_text(sweep.render_draft(row).replace("status: draft", "status: filed"))

    carried = sweep.read_human_edits(drafts, row["id"])

    assert carried["status"] == "filed"


def test_read_human_edits_on_missing_file_returns_empty(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()

    assert sweep.read_human_edits(drafts, "plan:nope") == {}


# ── report: silent when clean ─────────────────────────────────────────


def test_report_is_empty_when_nothing_new_or_stale():
    result = sweep.SweepResult(rows=[_row()])

    assert sweep.format_report(result) == ""


def test_report_lists_new_and_stale_counts():
    result = sweep.SweepResult(
        rows=[],
        new=[_row(title="Fresh plan")],
        newly_stale=[_row(id="plan:old", title="Aged plan", status="stale")],
    )

    report = sweep.format_report(result)

    assert "Fresh plan" in report
    assert "Aged plan" in report
    assert "1 new" in report
    assert "1 stale" in report


# ── end-to-end sweep over synthetic systems of record ─────────────────


def _fixture_world(tmp_path):
    """A synthetic desk: plans dir, signal-log entries, mesh board, skill refs."""
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "2026-08-08_plan.md").write_text("# Mesh efficiency pack\n\nDo the thing.\n")

    entries = tmp_path / "repo" / "docs" / "research" / "signal-log" / "entries"
    entries.mkdir(parents=True)
    (entries / "SIG-20260808-01_thing.md").write_text(_sig())
    (entries / "SIG-20260808-02_hype.md").write_text(_sig(bucket="noise"))

    refs = tmp_path / "skill" / "references"
    refs.mkdir(parents=True)
    (refs / "router-policies.md").write_text("# Router policies\n\nPrefer local.\n")

    board_dir = tmp_path / "boards" / "mesh"
    board_dir.mkdir(parents=True)
    _make_board_db(
        board_dir,
        [
            ("t_done", "Shipped a fix", "why", "done", 1786000000, 1),
            ("t_pr", "HUMAN review: PR #4352", None, "done", 1786000000, 1),
            ("t_open", "Still running", None, "running", None, 0),
        ],
    )

    intake = tmp_path / "intake"
    config = {
        "boards": ["mesh"],
        "sources": {
            "plans": {"enabled": True, "path": str(plans)},
            "signal_log": {"enabled": True, "path": str(entries)},
            "mesh_done_cards": {
                "enabled": True,
                "db_template": str(tmp_path / "boards" / "{board}" / "kanban.db"),
                "title_exclude_patterns": ["^HUMAN review: PR #"],
            },
            "skill_references": {"enabled": True, "trees": [str(refs)]},
        },
        "filters": {"signal_log": {"exclude_posture": ["ignore"], "exclude_bucket": ["noise"]}},
        "staleness_days": 5,
    }
    return config, intake, {"plans": plans, "entries": entries, "refs": refs}


def test_sweep_drafts_one_row_per_durable_artifact(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)

    result = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T00:00:00Z")
    )

    kinds = sorted(r["source_kind"] for r in result.new)
    # plan + 1 signal (noise filtered) + 1 done card (PR wrapper filtered) + 1 skill ref
    assert kinds == ["mesh_done_card", "plan", "signal_log_entry", "skill_reference"]
    assert (intake / "index.json").is_file()
    assert len(list((intake / "drafts").glob("*.md"))) == 4


def test_second_sweep_produces_zero_new_drafts(tmp_path):
    # Card acceptance: re-running must not duplicate drafts.
    config, intake, _ = _fixture_world(tmp_path)
    sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T00:00:00Z")
    )

    second = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T06:00:00Z")
    )

    assert second.new == []
    assert second.newly_stale == []
    assert sweep.format_report(second) == ""
    assert len(second.rows) == 4


def test_changed_artifact_on_second_sweep_drafts_again(tmp_path):
    config, intake, paths = _fixture_world(tmp_path)
    sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T00:00:00Z")
    )

    (paths["plans"] / "2026-08-08_plan.md").write_text("# Mesh efficiency pack\n\nRevised.\n")
    second = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-09T00:00:00Z")
    )

    assert [r["source_kind"] for r in second.new] == ["plan"]
    assert [r["source_kind"] for r in second.superseded] == ["plan"]


def test_aged_unswept_artifact_is_flagged_stale_by_the_sweep_itself(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)
    sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-01T00:00:00Z")
    )

    later = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-10T00:00:00Z")
    )

    assert len(later.newly_stale) == 4
    assert "stale" in sweep.format_report(later)


def test_human_filed_verdict_survives_the_next_sweep(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)
    first = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-01T00:00:00Z")
    )
    target = first.new[0]["id"]
    p = intake / "drafts" / f"{target}.md"
    p.write_text(p.read_text().replace("status: draft", "status: filed"))

    later = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-10T00:00:00Z")
    )

    by_id = {r["id"]: r for r in later.rows}
    assert by_id[target]["status"] == "filed"
    assert target not in [r["id"] for r in later.newly_stale]


def test_dry_run_writes_nothing(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)

    result = sweep.run_sweep(
        config,
        intake,
        repo_root=tmp_path / "repo",
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        dry_run=True,
    )

    assert len(result.new) == 4
    assert not intake.exists()


def test_source_filter_restricts_the_sweep(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)

    result = sweep.run_sweep(
        config,
        intake,
        repo_root=tmp_path / "repo",
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        sources=["plan"],
        dry_run=True,
    )

    assert [r["source_kind"] for r in result.new] == ["plan"]


def test_disabled_source_is_not_swept(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)
    config["sources"]["skill_references"]["enabled"] = False

    result = sweep.run_sweep(
        config,
        intake,
        repo_root=tmp_path / "repo",
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        dry_run=True,
    )

    assert "skill_reference" not in [r["source_kind"] for r in result.new]


# ── fail-closed source paths + per-source counts ──────────────────────


def test_missing_source_path_fails_closed_by_default(tmp_path, capsys):
    config, intake, _ = _fixture_world(tmp_path)
    config["sources"]["plans"]["path"] = str(tmp_path / "no-such-plans-dir")

    raised = False
    try:
        sweep.run_sweep(
            config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T00:00:00Z")
        )
    except SystemExit as exc:
        raised = True
        assert exc.code == 2

    assert raised
    assert "plan=" in capsys.readouterr().err
    assert not intake.exists()


def test_dry_run_also_fails_closed_on_missing_source(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)
    config["sources"]["plans"]["path"] = str(tmp_path / "no-such-plans-dir")

    raised = False
    try:
        sweep.run_sweep(
            config,
            intake,
            repo_root=tmp_path / "repo",
            now=sweep.parse_ts("2026-08-08T00:00:00Z"),
            dry_run=True,
        )
    except SystemExit as exc:
        raised = True
        assert exc.code == 2

    assert raised


def test_strict_sources_false_completes_and_reports_missing_path(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)
    config["sources"]["plans"]["path"] = str(tmp_path / "no-such-plans-dir")

    result = sweep.run_sweep(
        config,
        intake,
        repo_root=tmp_path / "repo",
        now=sweep.parse_ts("2026-08-08T00:00:00Z"),
        strict_sources=False,
    )

    assert result.sources["plan"]["exists"] is False
    assert result.sources["plan"]["count"] == 0


def test_sources_report_counts_match_fingerprints_on_a_good_config(tmp_path):
    config, intake, _ = _fixture_world(tmp_path)

    result = sweep.run_sweep(
        config, intake, repo_root=tmp_path / "repo", now=sweep.parse_ts("2026-08-08T00:00:00Z")
    )

    assert result.sources["plan"]["exists"] is True
    assert result.sources["plan"]["count"] == 1
    assert result.sources["signal_log_entry"]["count"] == 1
    assert result.sources["mesh_done_card:mesh"]["count"] == 1
    assert result.sources["skill_reference:0"]["count"] == 1


# ── CLI ───────────────────────────────────────────────────────────────


def _write_cli_config(tmp_path, config):
    import json

    intake = tmp_path / "intake"
    intake.mkdir(parents=True, exist_ok=True)
    # config.yaml is YAML, but JSON is a valid YAML subset — keeps the test
    # free of a yaml-dump dependency while exercising the real loader.
    (intake / "config.yaml").write_text(json.dumps(config))
    return intake


def _run_cli(tmp_path, intake, *args):
    import subprocess

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "distillery_intake_sweep.py"),
            "--intake-dir",
            str(intake),
            "--repo-root",
            str(tmp_path / "repo"),
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_dry_run_reports_without_writing(tmp_path):
    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run")

    assert proc.returncode == 0, proc.stderr
    assert "Distillery intake sweep" in proc.stdout
    assert not (intake / "index.json").exists()


def test_cli_json_output_is_machine_readable(tmp_path):
    import json

    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["counts"]["new"] == 4
    assert payload["counts"]["stale"] == 0


def test_cli_is_silent_on_a_clean_second_run(tmp_path):
    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    first = _run_cli(tmp_path, intake)
    second = _run_cli(tmp_path, intake)

    assert first.returncode == 0, first.stderr
    assert first.stdout.strip() != ""
    assert second.returncode == 0, second.stderr
    assert second.stdout == ""


def test_cli_source_filter_flag(tmp_path):
    import json

    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run", "--json", "--source", "plan")

    payload = json.loads(proc.stdout)
    assert payload["counts"]["new"] == 1


def test_cli_rejects_unknown_source(tmp_path):
    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run", "--source", "bogus")

    assert proc.returncode != 0
    assert "bogus" in (proc.stderr + proc.stdout)


def test_cli_refuses_an_unconfigured_intake_dir_instead_of_seeding_a_second_store(tmp_path):
    # The dual-write copy at ~/.t1000/scripts/ resolves its default repo root
    # to ~/.t1000. Run with no flags it would silently create a SECOND intake
    # store against the wrong tree. Fail closed instead.
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "distillery_intake_sweep.py"),
            "--intake-dir",
            str(tmp_path / "unconfigured"),
            "--repo-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert proc.returncode != 0
    assert "config.yaml" in (proc.stderr + proc.stdout)
    assert not (tmp_path / "unconfigured").exists()


def test_cli_json_output_includes_sources(tmp_path):
    import json

    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "sources" in payload
    assert payload["sources"]["plan"]["count"] == 1


def test_cli_allow_missing_source_flag_avoids_fail_closed(tmp_path):
    config, _, _ = _fixture_world(tmp_path)
    config["sources"]["plans"]["path"] = str(tmp_path / "no-such-plans-dir")
    intake = _write_cli_config(tmp_path, config)

    proc = _run_cli(tmp_path, intake, "--dry-run", "--allow-missing-source")

    assert proc.returncode == 0, proc.stderr


def test_cli_mark_flips_a_row_status(tmp_path):
    import json

    config, _, _ = _fixture_world(tmp_path)
    intake = _write_cli_config(tmp_path, config)
    _run_cli(tmp_path, intake)
    rows = json.loads((intake / "index.json").read_text())["rows"]
    target = rows[0]["id"]

    proc = _run_cli(tmp_path, intake, "--mark", f"{target}=filed")

    assert proc.returncode == 0, proc.stderr
    after = json.loads((intake / "index.json").read_text())["rows"]
    assert {r["id"]: r["status"] for r in after}[target] == "filed"


def test_board_without_completion_generation_column_still_yields_rows(tmp_path):
    """Boards created after mid-Aug 2026 lack completion_generation; the sweep
    must key on completed_at instead of silently returning nothing."""
    import sqlite3

    from distillery_intake_sweep import collect_board_fingerprints

    db = tmp_path / "kanban.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE tasks (id TEXT, title TEXT, body TEXT, status TEXT, "
        "completed_at INTEGER, result TEXT)"
    )
    con.execute(
        "INSERT INTO tasks VALUES ('t_aaaaaaaa', 'ST-01 thing', 'body', 'done', 1700000000, 'measured')"
    )
    con.execute(
        "INSERT INTO tasks VALUES ('t_bbbbbbbb', 'ST-02 empty', 'body', 'done', 1700000001, NULL)"
    )
    con.commit()
    con.close()

    rows = collect_board_fingerprints("steals", db)
    assert {r["id"] for r in rows} == {
        "mesh_done_card:t_aaaaaaaa@1700000000",
        "mesh_done_card:t_bbbbbbbb@1700000001",
    }
    only_evidence = collect_board_fingerprints("steals", db, require_result=True)
    assert [r["source_path"] for r in only_evidence] == ["t_aaaaaaaa"]


def test_board_query_error_is_fatal_not_empty(tmp_path):
    import sqlite3

    import pytest

    from distillery_intake_sweep import collect_board_fingerprints

    db = tmp_path / "kanban.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE tasks (id TEXT, status TEXT)")  # no completed_at/title/body
    con.commit()
    con.close()
    with pytest.raises(SystemExit):
        collect_board_fingerprints("harness", db)
