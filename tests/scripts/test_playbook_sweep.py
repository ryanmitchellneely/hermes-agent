"""Playbook sweep (t_c3a4b01d v0): retrieval must fire on the real failures.

The corpus was seeded from the 2026-08-17..19 dsh-lane arc, so the strongest
test is replaying those runs' ACTUAL failure text and asserting the right
entry hits — the card's own success criterion, executed retroactively.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
PLAYBOOK = REPO / "docs" / "playbook"


@pytest.fixture()
def sweep_mod(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYBOOK_DIR", str(PLAYBOOK))
    monkeypatch.setenv("PLAYBOOK_BOARDS_DIR", str(tmp_path / "boards"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "cache").mkdir()
    spec = importlib.util.spec_from_file_location(
        "playbook_sweep", REPO / "scripts" / "playbook_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# Verbatim failure text from the runs that seeded the corpus.
RUN_934 = (
    "dsh headless ok in 34.7s. ... | DSH_BOT_APP_KEY_PATH does not point at a "
    "file: $HOME/.t1000/secrets/dsh-bot-app.pem"
)
RUN_935 = (
    "dsh headless ok in 62.9s. ... | git/PR failed: failed to create branch "
    "'ryan/dsh/t_da63b06a' from 'origin/main': error: Your local changes to "
    "the following files would be overwritten by checkout"
)
RUN_929 = (
    "worker exited cleanly (rc=0) without calling kanban_complete or "
    "kanban_block — protocol violation."
)


def test_corpus_parses_with_patterns(sweep_mod):
    entries = sweep_mod.parse_entries(PLAYBOOK)
    assert len(entries) >= 8
    for e in entries:
        assert e["patterns"], f"{e['id']} has no patterns"
        assert e["fix_line"] != "(see entry)", f"{e['id']} fix line not extracted"


@pytest.mark.parametrize(
    "text,expected",
    [(RUN_934, "PB-001"), (RUN_935, "PB-002"), (RUN_929, "PB-007")],
)
def test_real_historical_failures_hit_the_right_entry(sweep_mod, text, expected):
    entries = sweep_mod.parse_entries(PLAYBOOK)
    hits = [e["id"] for e in sweep_mod.match_entries(entries, text)]
    assert expected in hits, f"expected {expected} in {hits}"


def test_literal_matching_not_regex(sweep_mod):
    """`$HOME` must match itself — a regex engine would read `$` as an anchor."""
    entries = [{"id": "X", "patterns": ["file: $HOME"], "fix_line": "f", "path": "x"}]
    assert sweep_mod.match_entries(entries, "no file: $HOME/y here")
    assert not sweep_mod.match_entries(entries, "file HOME without the sigil")


def test_clean_text_hits_nothing(sweep_mod):
    entries = sweep_mod.parse_entries(PLAYBOOK)
    assert sweep_mod.match_entries(entries, "dsh headless ok in 31.6s, all good") == []


def _mk_board(tmp_path, name, rows):
    db_dir = tmp_path / "boards" / name
    db_dir.mkdir(parents=True)
    conn = sqlite3.connect(db_dir / "kanban.db")
    conn.execute(
        "CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, "
        "outcome TEXT, summary TEXT, error TEXT, ended_at INTEGER)"
    )
    conn.executemany(
        "INSERT INTO task_runs (task_id, outcome, summary, error, ended_at) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_sweep_dry_run_finds_and_dedupes(sweep_mod, tmp_path, capsys):
    now = int(time.time())
    _mk_board(
        tmp_path,
        "mesh",
        [
            ("t_aaa", "blocked", RUN_934, None, now - 60),
            ("t_bbb", "completed", "fine", None, now - 60),
            ("t_old", "blocked", RUN_934, None, now - 10 * 86400),
        ],
    )
    counts = sweep_mod.sweep(dry_run=True)
    out = capsys.readouterr().out
    assert counts["hits"] == 1
    assert "t_aaa" in out and "PB-001" in out
    assert "t_old" not in out  # outside the window
    assert "t_bbb" not in out  # not a failure


def test_state_dedupe_prevents_recomment(sweep_mod, tmp_path):
    now = int(time.time())
    _mk_board(tmp_path, "mesh", [("t_aaa", "blocked", RUN_934, None, now - 60)])
    calls = []
    sweep_mod.comment_hit = lambda b, t, e, d: calls.append((b, t, e["id"])) or True
    c1 = sweep_mod.sweep(dry_run=False)
    c2 = sweep_mod.sweep(dry_run=False)
    assert c1["hits"] == 1 and c2["hits"] == 0
    assert len(calls) == 1


def test_heartbeat_written(sweep_mod, tmp_path):
    _mk_board(tmp_path, "mesh", [])
    sweep_mod.comment_hit = lambda *a: True
    sweep_mod.sweep(dry_run=False)
    hb = sweep_mod.HEARTBEAT_PATH.read_text(encoding="utf-8")
    assert '"boards": 1' in hb and '"ts"' in hb


def test_unmatched_failure_surfaces_as_miss_candidate(sweep_mod, tmp_path, capsys):
    """Corpus growth: a failure no entry matches must nominate itself —
    once. Deduped per (board, task) so the nudge doesn't repeat every 30m."""
    now = int(time.time())
    _mk_board(
        tmp_path, "mesh",
        [("t_novel", "crashed", "some entirely novel failure mode xyzzy", None, now - 60)],
    )
    sweep_mod.comment_hit = lambda *a: True
    c1 = sweep_mod.sweep(dry_run=False)
    out1 = capsys.readouterr().out
    assert c1["misses"] == 1
    assert "PLAYBOOK MISS candidate: mesh/t_novel" in out1
    c2 = sweep_mod.sweep(dry_run=False)
    out2 = capsys.readouterr().out
    assert c2["misses"] == 0
    assert "t_novel" not in out2


def test_miss_lines_capped_at_three_per_run(sweep_mod, tmp_path, capsys):
    now = int(time.time())
    _mk_board(
        tmp_path, "mesh",
        [(f"t_m{i}", "blocked", f"novel failure number {i} qwerty", None, now - 60)
         for i in range(6)],
    )
    sweep_mod.comment_hit = lambda *a: True
    counts = sweep_mod.sweep(dry_run=False)
    out = capsys.readouterr().out
    assert counts["misses"] == 6  # all tracked in state
    assert out.count("PLAYBOOK MISS candidate") == 3  # only 3 surfaced


def test_repair_fields_parse_when_present(sweep_mod, tmp_path):
    """The repair seam (Detect->Diagnose->Repair) parses; consumption of it
    is a separate, human-sanctioned step — see t_c3a4b01d follow-up."""
    pb = tmp_path / "pb"
    pb.mkdir()
    (pb / "PB-900-test.md").write_text(
        '---\nid: PB-900\nclass: t\nmatch:\n  - "boom"\nverified: 2026-08-19\n'
        'sources:\n  - "x"\nrepair: "run the fixer"\nrepair_assignee: worker\n'
        "---\n\n**Fix:** f\n",
        encoding="utf-8",
    )
    entries = sweep_mod.parse_entries(pb)
    assert entries[0]["repair"] == "run the fixer"
    assert entries[0]["repair_assignee"] == "worker"
    assert entries[0]["repair_auto"] is False


RUN_935_SHORT = "git/PR failed: failed to create branch 'ryan/dsh/t_x' from 'origin/main'"


def test_repair_draft_seeded_from_hit_and_budgeted(sweep_mod, tmp_path, capsys):
    """Scoped Detect->Diagnose->Repair: a hit on a repair-carrying entry
    drafts exactly one card, dedupes on rerun, and the total is budgeted."""
    now = int(time.time())
    _mk_board(tmp_path, "mesh", [("t_hit", "blocked", RUN_935_SHORT, None, now - 60)])
    drafted = []
    sweep_mod.comment_hit = lambda *a: True
    sweep_mod.draft_repair_card = (
        lambda b, t, e, d: drafted.append((b, t, e["id"])) or "t_new"
    )
    c1 = sweep_mod.sweep(dry_run=False)
    c2 = sweep_mod.sweep(dry_run=False)
    assert c1["repairs"] == 1 and c2["repairs"] == 0
    assert drafted == [("mesh", "t_hit", "PB-002")]


def test_repair_budget_is_a_hard_stop(sweep_mod, tmp_path, capsys):
    now = int(time.time())
    _mk_board(
        tmp_path, "mesh",
        [(f"t_h{i}", "blocked", RUN_935_SHORT, None, now - 60) for i in range(5)],
    )
    sweep_mod.comment_hit = lambda *a: True
    sweep_mod.draft_repair_card = lambda *a: "t_new"
    counts = sweep_mod.sweep(dry_run=False)
    out = capsys.readouterr().out
    assert counts["repairs"] == sweep_mod.REPAIR_BUDGET == 3
    assert "repair budget spent" in out


def test_deliberate_parks_never_nominate_as_misses(sweep_mod, tmp_path, capsys):
    """A run blocked by design (human gate) is not a failure — the first
    live run surfaced 3 review-holds as 'candidates', hence this filter."""
    now = int(time.time())
    _mk_board(
        tmp_path, "mesh",
        [
            ("t_gate", "blocked", "HUMAN PR review — do not free-fire. Sticky.", None, now - 60),
            ("t_real", "crashed", "novel genuine failure zzz", None, now - 60),
        ],
    )
    sweep_mod.comment_hit = lambda *a: True
    counts = sweep_mod.sweep(dry_run=False)
    out = capsys.readouterr().out
    assert counts["misses"] == 1
    assert "t_real" in out and "t_gate" not in out


def _pb_entry(tmp_path, extra_fm=""):
    pb = tmp_path / "pbg"
    pb.mkdir(exist_ok=True)
    (pb / "PB-901-gate.md").write_text(
        '---\nid: PB-901\nclass: t\nmatch:\n  - "gateboom"\nverified: 2026-08-19\n'
        'sources:\n  - "x"\nrepair: "patch something"\nrepair_assignee: worker\n'
        f"repair_auto: true\n{extra_fm}---\n\n**Fix:** f\n",
        encoding="utf-8",
    )
    return pb


def test_gauntlet_gate_fail_closed_undeclared_repair_never_arms(sweep_mod, tmp_path):
    """t_18792526 rule: no repair_class declaration => patch-class => parked,
    even with repair_auto: true. Arming a patch requires the ADR-073
    promotion-record path, which does not exist yet."""
    entries = sweep_mod.parse_entries(_pb_entry(tmp_path))
    assert entries[0]["repair_class"] == "patch"
    blocks = []
    real_run = sweep_mod.subprocess.run

    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "Created t_9999beef\n"
        if "block" in cmd:
            blocks.append(cmd)
        return R()

    sweep_mod.subprocess.run = fake_run
    try:
        new_id = sweep_mod.draft_repair_card("mesh", "t_src", entries[0], dry_run=False)
    finally:
        sweep_mod.subprocess.run = real_run
    assert new_id == "t_9999beef"
    assert len(blocks) == 1 and "GAUNTLET GATE" in blocks[0][6]


def test_report_class_with_auto_still_arms(sweep_mod, tmp_path):
    entries = sweep_mod.parse_entries(_pb_entry(tmp_path, "repair_class: report\n"))
    assert entries[0]["repair_class"] == "report"
    blocks = []
    real_run = sweep_mod.subprocess.run

    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "Created t_8888beef\n"
        if "block" in cmd:
            blocks.append(cmd)
        return R()

    sweep_mod.subprocess.run = fake_run
    try:
        new_id = sweep_mod.draft_repair_card("mesh", "t_src", entries[0], dry_run=False)
    finally:
        sweep_mod.subprocess.run = real_run
    assert new_id == "t_8888beef"
    assert blocks == []  # armed: no block call


def test_drafted_body_carries_repair_class_marker(sweep_mod, tmp_path):
    """Wrapper contract (t_18792526): the drafted card body carries a
    machine-readable repair-class line the dsh wrapper's gauntlet gate
    reads. Without the stamp, a patch-class card is indistinguishable from
    an ordinary card at PR time."""
    entries = sweep_mod.parse_entries(_pb_entry(tmp_path))
    assert entries[0]["repair_class"] == "patch"
    creates = []
    real_run = sweep_mod.subprocess.run

    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "Created t_7777beef\n"
        if "create" in cmd:
            creates.append(cmd)
        return R()

    sweep_mod.subprocess.run = fake_run
    try:
        sweep_mod.draft_repair_card("mesh", "t_src", entries[0], dry_run=False)
    finally:
        sweep_mod.subprocess.run = real_run
    assert len(creates) == 1
    body = creates[0][creates[0].index("--body") + 1]
    assert body.rstrip().endswith("repair-class: patch")


def test_actionable_counts_only_live_nondeliberate_cards(sweep_mod, tmp_path):
    """`failures` counts rows; `actionable` counts distinct live cards that
    are neither deliberate parks nor already-resolved — the residue that is
    actually waiting on someone (Ryan, 2026-08-20)."""
    now = int(time.time())
    db_dir = tmp_path / "boards" / "mesh"
    db_dir.mkdir(parents=True)
    conn = sqlite3.connect(db_dir / "kanban.db")
    conn.execute(
        "CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, "
        "outcome TEXT, summary TEXT, error TEXT, ended_at INTEGER)"
    )
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT)")
    rows = [
        ("t_gate0000", "blocked", "HUMAN PR review — do not free-fire", "blocked"),
        ("t_done0000", "blocked", "novel failure alpha", "done"),
        ("t_live0000", "blocked", "novel failure beta", "blocked"),
        ("t_live0000", "crashed", "novel failure beta again", "blocked"),  # same card twice
        ("t_live0001", "crashed", "novel failure gamma", "ready"),
    ]
    for tid, out, summ, tstat in rows:
        conn.execute(
            "INSERT INTO task_runs (task_id, outcome, summary, error, ended_at) VALUES (?,?,?,?,?)",
            (tid, out, summ, None, now - 60),
        )
        conn.execute("INSERT OR IGNORE INTO tasks (id, status) VALUES (?,?)", (tid, tstat))
    conn.commit(); conn.close()
    sweep_mod.comment_hit = lambda *a: True
    counts = sweep_mod.sweep(dry_run=True)
    assert counts["failures"] == 5      # every row
    assert counts["actionable"] == 2    # t_live0000 (deduped) + t_live0001
