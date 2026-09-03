"""steals_signal_crosscheck.py: each finding type fires, and a consistent
fixture yields empty stdout (cron no-agent contract) + a written state file.

Second pass (coordinator follow-up, live-run false-alarm fixes):
  - CARD-NO-SIG must check comments too, and skip terminal (done/archived)
    cards, not just archived ones.
  - ROLLUP-DEAD-CARD must look across every board under --boards-dir, not
    just the steals board.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def mod():
    spec = importlib.util.spec_from_file_location(
        "steals_signal_crosscheck", REPO / "scripts" / "steals_signal_crosscheck.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _entry(entries_dir: Path, sig: str, title: str, posture: str, rank: str) -> None:
    text = (
        f"# {sig} — {title}\n\n"
        "```yaml\n"
        f"id: {sig}\n"
        "date: 2026-09-01\n"
        f'title: "{title}"\n'
        "bucket: harness\n"
        f"posture: {posture}\n"
        f"steal_rank: {rank}\n"
        "confidence: high\n"
        "status: open\n"
        "distill: none\n"
        "```\n"
    )
    (entries_dir / f"{sig}_slug.md").write_text(text)


def _make_board_db(path: Path, tasks: list[tuple], comments: list[tuple] | None = None) -> None:
    """tasks: [(id, title, body, status)]. comments: [(task_id, body)]."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, body TEXT, status TEXT)"
    )
    conn.executemany("INSERT INTO tasks (id, title, body, status) VALUES (?, ?, ?, ?)", tasks)
    conn.execute("CREATE TABLE task_comments (task_id TEXT, body TEXT)")
    if comments:
        conn.executemany("INSERT INTO task_comments (task_id, body) VALUES (?, ?)", comments)
    conn.commit()
    conn.close()


STEALS_HEADER = (
    "# Open steals rollup (P0 / P1 only)\n\n"
    "| Steal | From | Rank | T1000-shaped action | Wire status |\n"
    "|-------|------|------|---------------------|-------------|\n"
)


@pytest.fixture()
def repo(tmp_path):
    entries_dir = tmp_path / "docs" / "research" / "signal-log" / "entries"
    entries_dir.mkdir(parents=True)
    return tmp_path


def _write_steals(root: Path, rows: str) -> None:
    (root / "docs" / "research" / "signal-log" / "STEALS.md").write_text(
        STEALS_HEADER + rows
    )


def _entries_dir(root: Path) -> Path:
    return root / "docs" / "research" / "signal-log" / "entries"


# ── exit(2) when required inputs are missing ────────────────────────────────


def test_missing_entries_dir_exits_2(mod, tmp_path):
    with pytest.raises(SystemExit) as exc:
        mod.crosscheck(tmp_path, tmp_path / "nonexistent.db", tmp_path / "boards")
    assert exc.value.code == 2


def test_missing_steals_md_exits_2(mod, repo):
    with pytest.raises(SystemExit) as exc:
        mod.crosscheck(repo, repo / "nonexistent.db", repo / "boards")
    assert exc.value.code == 2


# ── MISSING-ROLLUP ───────────────────────────────────────────────────────────


def test_missing_rollup_fires(mod, repo):
    _entry(_entries_dir(repo), "SIG-20260901-01", "A P1 steal never rolled up", "steal", "P1")
    _write_steals(repo, "")  # rollup never mentions the entry

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    hits = [f for f in state["findings"] if f.startswith("MISSING-ROLLUP")]
    assert hits == ["MISSING-ROLLUP SIG-20260901-01 A P1 steal never rolled up"]


def test_missing_rollup_does_not_fire_for_watch_posture(mod, repo):
    _entry(_entries_dir(repo), "SIG-20260901-01", "Just a watch", "watch", "P1")
    _write_steals(repo, "")

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    assert not [f for f in state["findings"] if f.startswith("MISSING-ROLLUP")]


def test_missing_rollup_does_not_fire_for_p2(mod, repo):
    _entry(_entries_dir(repo), "SIG-20260901-01", "P2 steal", "steal", "P2")
    _write_steals(repo, "")

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    assert not [f for f in state["findings"] if f.startswith("MISSING-ROLLUP")]


# ── ROW-NO-SIG ────────────────────────────────────────────────────────────


def test_row_no_sig_fires(mod, repo):
    row = "| **A steal with no source cite** | mystery | **P1** | do the thing | open |\n"
    _write_steals(repo, row)

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    hits = [f for f in state["findings"] if f.startswith("ROW-NO-SIG")]
    assert hits == ["ROW-NO-SIG **A steal with no source cite**"]


def test_row_no_sig_skips_struck_rows(mod, repo):
    row = "| ~~**Superseded, no SIG cite**~~ | mystery | ~~P1~~ | n/a | superseded |\n"
    _write_steals(repo, row)

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    assert not [f for f in state["findings"] if f.startswith("ROW-NO-SIG")]


def test_row_with_sig_does_not_fire(mod, repo):
    row = "| **Good row** | SIG-20260901-01 | **P1** | do the thing | `t_deadbeef` |\n"
    _write_steals(repo, row)

    state = mod.crosscheck(repo, repo / "nonexistent.db", repo / "nonexistent-boards")
    assert not [f for f in state["findings"] if f.startswith("ROW-NO-SIG")]


# ── CARD-NO-SIG ──────────────────────────────────────────────────────────


def test_card_no_sig_fires_for_live_task_without_cite(mod, repo):
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(steals_db, [("t_deadbeef", "No sig here", "body text", "blocked")])

    state = mod.crosscheck(repo, steals_db, boards_dir)
    hits = [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]
    assert hits == ["CARD-NO-SIG t_deadbeef No sig here"]


def test_card_no_sig_skips_archived(mod, repo):
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(steals_db, [("t_deadbeef", "No sig here", "", "archived")])

    state = mod.crosscheck(repo, steals_db, boards_dir)
    assert not [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]


def test_card_no_sig_skips_done(mod, repo):
    """Done lab/bench cards (LAB:, Nemotron, Solver) are not signal-derived."""
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(steals_db, [("t_deadbeef", "LAB: q38 protocol run", "", "done")])

    state = mod.crosscheck(repo, steals_db, boards_dir)
    assert not [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]


def test_card_no_sig_skips_when_cited(mod, repo):
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(steals_db, [("t_deadbeef", "Has SIG-20260901-01 cite", "", "scheduled")])

    state = mod.crosscheck(repo, steals_db, boards_dir)
    assert not [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]


def test_card_no_sig_skips_when_cited_only_in_a_comment(mod, repo):
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(
        steals_db,
        [("t_deadbeef", "No cite in title or body", "plain body text", "scheduled")],
        comments=[("t_deadbeef", "Filed from SIG-20260901-01, see the entry")],
    )

    state = mod.crosscheck(repo, steals_db, boards_dir)
    assert not [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]


# ── ROLLUP-DEAD-CARD ─────────────────────────────────────────────────────


def test_rollup_dead_card_fires_for_unknown_tid(mod, repo):
    row = "| **Steal** | SIG-20260901-01 | **P1** | action | `t_deadbeef` card |\n"
    _write_steals(repo, row)
    boards_dir = repo / "boards"
    _make_board_db(
        boards_dir / "steals" / "kanban.db",
        [("t_11111111", "Something else", "", "scheduled")],
    )

    state = mod.crosscheck(repo, boards_dir / "steals" / "kanban.db", boards_dir)
    hits = [f for f in state["findings"] if f.startswith("ROLLUP-DEAD-CARD")]
    assert hits == ["ROLLUP-DEAD-CARD t_deadbeef"]


def test_rollup_dead_card_ok_when_card_exists_any_status(mod, repo):
    row = "| **Steal** | SIG-20260901-01 | **P1** | action | `t_deadbeef` card |\n"
    _write_steals(repo, row)
    boards_dir = repo / "boards"
    _make_board_db(
        boards_dir / "steals" / "kanban.db",
        [("t_deadbeef", "Archived but real", "", "archived")],
    )

    state = mod.crosscheck(repo, boards_dir / "steals" / "kanban.db", boards_dir)
    assert not [f for f in state["findings"] if f.startswith("ROLLUP-DEAD-CARD")]


def test_rollup_dead_card_ok_when_card_exists_on_sibling_board(mod, repo):
    """STEALS.md legitimately cites mesh/k2/etc cards, not just the steals board."""
    row = "| **Steal** | SIG-20260901-01 | **P1** | action | `t_deadbeef` on mesh |\n"
    _write_steals(repo, row)
    boards_dir = repo / "boards"
    # Steals board itself has no matching task...
    _make_board_db(
        boards_dir / "steals" / "kanban.db",
        [("t_00000000", "Unrelated steals-board task", "", "scheduled")],
    )
    # ...but a sibling board does.
    _make_board_db(
        boards_dir / "mesh" / "kanban.db",
        [("t_deadbeef", "Lives on the mesh board", "", "scheduled")],
    )

    state = mod.crosscheck(repo, boards_dir / "steals" / "kanban.db", boards_dir)
    assert not [f for f in state["findings"] if f.startswith("ROLLUP-DEAD-CARD")]


def test_rollup_dead_card_fires_when_absent_from_every_board(mod, repo):
    row = "| **Steal** | SIG-20260901-01 | **P1** | action | `t_deadbeef` nowhere |\n"
    _write_steals(repo, row)
    boards_dir = repo / "boards"
    _make_board_db(
        boards_dir / "steals" / "kanban.db",
        [("t_00000000", "Unrelated steals-board task", "", "scheduled")],
    )
    _make_board_db(
        boards_dir / "mesh" / "kanban.db",
        [("t_11111111", "Unrelated mesh task", "", "scheduled")],
    )

    state = mod.crosscheck(repo, boards_dir / "steals" / "kanban.db", boards_dir)
    hits = [f for f in state["findings"] if f.startswith("ROLLUP-DEAD-CARD")]
    assert hits == ["ROLLUP-DEAD-CARD t_deadbeef"]


# ── missing board db / boards dir: independent WARN lines ──────────────────


def test_missing_board_db_warns_and_skips_check3_only(mod, repo):
    _write_steals(repo, "")
    boards_dir = repo / "boards"
    # boards_dir exists (for check 4) but the steals board db itself is absent.
    _make_board_db(boards_dir / "mesh" / "kanban.db", [("t_11111111", "x", "", "scheduled")])
    missing_steals_db = boards_dir / "steals" / "kanban.db"

    state = mod.crosscheck(repo, missing_steals_db, boards_dir)
    warns = [f for f in state["findings"] if f.startswith("WARN board db not found")]
    assert len(warns) == 1
    assert str(missing_steals_db) in warns[0]
    assert state["counts"]["board_tasks"] == 0
    assert not [f for f in state["findings"] if f.startswith("CARD-NO-SIG")]


def test_missing_boards_dir_warns_and_skips_check4_only(mod, repo):
    _write_steals(repo, "")
    missing_boards_dir = repo / "nope-boards"
    steals_db = missing_boards_dir / "steals" / "kanban.db"  # also absent

    state = mod.crosscheck(repo, steals_db, missing_boards_dir)
    warns = [f for f in state["findings"] if f.startswith("WARN boards dir not found")]
    assert len(warns) == 1
    assert str(missing_boards_dir) in warns[0]
    assert not [f for f in state["findings"] if f.startswith("ROLLUP-DEAD-CARD")]


# ── consistent fixture: empty stdout, state file written ───────────────────


def test_consistent_fixture_yields_empty_stdout_and_state_written(mod, repo):
    _entry(_entries_dir(repo), "SIG-20260901-01", "A clean P1 steal", "steal", "P1")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(
        steals_db,
        [
            ("t_deadbeef", "Card citing SIG-20260901-01", "", "scheduled"),
            ("t_stale0000", "Old archived card, no cite needed", "", "archived"),
            ("t_donecard0", "LAB: done, no cite needed", "", "done"),
        ],
    )
    row = (
        "| **A clean P1 steal** | SIG-20260901-01 | **P1** | do the thing | "
        "`t_deadbeef` card |\n"
    )
    _write_steals(repo, row)

    state_path = repo / "cache" / "state.json"
    state = mod.crosscheck(repo, steals_db, boards_dir)
    mod.write_state(state_path, state)

    assert state["findings"] == []
    assert state_path.is_file()
    written = json.loads(state_path.read_text())
    assert written["findings"] == []
    assert "ts" in written
    assert written["counts"]["entries"] == 1


def test_main_prints_nothing_when_consistent(mod, repo, monkeypatch, capsys, tmp_path):
    _entry(_entries_dir(repo), "SIG-20260901-01", "A clean P1 steal", "steal", "P1")
    boards_dir = repo / "boards"
    steals_db = boards_dir / "steals" / "kanban.db"
    _make_board_db(steals_db, [("t_deadbeef", "Card citing SIG-20260901-01", "", "scheduled")])
    row = (
        "| **A clean P1 steal** | SIG-20260901-01 | **P1** | do the thing | "
        "`t_deadbeef` card |\n"
    )
    _write_steals(repo, row)

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "steals_signal_crosscheck.py",
            "--repo-root", str(repo),
            "--board-db", str(steals_db),
            "--boards-dir", str(boards_dir),
            "--state", str(state_path),
        ],
    )
    mod.main()
    out = capsys.readouterr().out
    assert out == ""
    assert state_path.is_file()


def test_main_prints_header_and_findings_when_inconsistent(mod, repo, monkeypatch, capsys, tmp_path):
    _entry(_entries_dir(repo), "SIG-20260901-01", "An uncited P1 steal", "steal", "P1")
    _write_steals(repo, "")
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "steals_signal_crosscheck.py",
            "--repo-root", str(repo),
            "--board-db", str(tmp_path / "nonexistent.db"),
            "--boards-dir", str(tmp_path / "nonexistent-boards"),
            "--state", str(state_path),
        ],
    )
    mod.main()
    out = capsys.readouterr().out
    assert out.startswith("Steals ↔ signal-log cross-check: ")
    assert "MISSING-ROLLUP SIG-20260901-01" in out
    assert "WARN board db not found" in out
    assert "WARN boards dir not found" in out
