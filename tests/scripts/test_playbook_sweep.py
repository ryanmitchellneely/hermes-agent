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
