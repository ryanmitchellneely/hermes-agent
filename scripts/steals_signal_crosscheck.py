#!/usr/bin/env python3
"""Cross-check docs/research/signal-log/STEALS.md against entries + the kanban boards.

Report-only. Exits 0 whenever it could read its inputs — even when it found
findings — and exits 2 only if the signal-log entries dir or STEALS.md itself
can't be read (the two required inputs). Stdout is EMPTY when everything is
consistent (cron no-agent contract: empty stdout = silent); non-empty stdout
is the alert.

Checks:
  1. MISSING-ROLLUP   — a P0/P1 steal|spike|adopt entry not cited in STEALS.md
  2. ROW-NO-SIG       — a live STEALS.md row that cites no SIG-YYYYMMDD-NN
  3. CARD-NO-SIG      — a non-terminal (not done/archived) steals-board task
                        that cites no SIG-YYYYMMDD-NN in its title, body, OR
                        any of its comments
  4. ROLLUP-DEAD-CARD — a t_xxxxxxxx in a wire-status cell with no matching
                        task ANYWHERE across every board (STEALS.md legitimately
                        cites mesh/k2/etc cards, not just the steals board)

Check 3 needs the steals board sqlite db (--board-db); if it's missing, the
check is skipped and a single WARN line stands in for it. Check 4 needs every
board db under --boards-dir; if that dir is missing, the check is skipped and
a single WARN line stands in for it.

  python3 scripts/steals_signal_crosscheck.py
  python3 scripts/steals_signal_crosscheck.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
HOME = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".t1000")).expanduser()
BOARDS_DIR_DEFAULT = HOME / "kanban" / "boards"
BOARD_DB_DEFAULT = BOARDS_DIR_DEFAULT / "steals" / "kanban.db"
STATE_DEFAULT = HOME / "cache" / "steals-signal-crosscheck-state.json"

SIG_RE = re.compile(r"SIG-\d{8}-\d{2}(?!\d)")
TID_RE = re.compile(r"t_[0-9a-f]{8}(?![0-9a-f])")
_YAML_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)

ROLLUP_POSTURES = {"steal", "spike", "adopt"}
ROLLUP_RANKS = {"P0", "P1"}
# Terminal cards are done being worked — a done/archived lab or bench card
# (LAB:, Nemotron, Solver, ...) is not signal-derived and must not nag weekly.
TERMINAL_STATUSES = {"done", "archived"}


def parse_signal_frontmatter(text: str) -> dict:
    """Pull the fenced ```yaml block a signal-log entry carries (scalars only).

    Standalone copy of distillery_intake_sweep.parse_signal_frontmatter — kept
    duplicated on purpose so this script has no import dependency on it.
    """
    m = _YAML_FENCE_RE.search(text)
    if not m:
        return {}
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#", "-")):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def collect_entries(entries_dir: Path) -> list[dict]:
    out = []
    for p in sorted(entries_dir.glob("SIG-*.md")):
        meta = parse_signal_frontmatter(p.read_text(encoding="utf-8"))
        if meta.get("id"):
            out.append(meta)
    return out


def split_row_cells(line: str) -> list[str]:
    """Markdown table row -> cell texts, respecting backslash-escaped pipes."""
    parts = re.split(r"(?<!\\)\|", line)
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def table_rows(steals_text: str) -> list[str]:
    """Data rows of the STEALS.md table — header + separator + '~~'-struck rows dropped."""
    lines = steals_text.splitlines()
    pipe_idx = [i for i, l in enumerate(lines) if l.strip().startswith("|")]
    sep_idx = None
    for i in pipe_idx:
        if re.fullmatch(r"[|:\-\s]+", lines[i].strip()):
            sep_idx = i
            break
    rows = []
    for i in pipe_idx:
        if sep_idx is not None and i <= sep_idx:
            continue  # header row + separator row
        line = lines[i]
        cells = split_row_cells(line)
        if cells and cells[0].startswith("~~"):
            continue
        rows.append(line)
    return rows


def check_missing_rollup(entries: list[dict], steals_text: str) -> list[str]:
    findings = []
    for meta in entries:
        posture = (meta.get("posture") or "").lower()
        rank = (meta.get("steal_rank") or "").upper()
        if posture in ROLLUP_POSTURES and rank in ROLLUP_RANKS:
            sig_id = meta.get("id", "")
            if sig_id and sig_id not in steals_text:
                title = (meta.get("title") or "")[:80]
                findings.append(f"MISSING-ROLLUP {sig_id} {title}")
    return findings


def check_row_no_sig(rows: list[str]) -> list[str]:
    findings = []
    for row in rows:
        if not SIG_RE.search(row):
            cells = split_row_cells(row)
            steal_cell = cells[0] if cells else row.strip()
            findings.append(f"ROW-NO-SIG {steal_cell[:60]}")
    return findings


def check_card_no_sig(tasks: list[dict]) -> list[str]:
    """A non-terminal task must cite a SIG id in its title, body, or a comment."""
    findings = []
    for t in tasks:
        if (t.get("status") or "") in TERMINAL_STATUSES:
            continue
        haystack = " ".join(
            [t.get("title") or "", t.get("body") or "", *(t.get("comments") or [])]
        )
        if not SIG_RE.search(haystack):
            findings.append(f"CARD-NO-SIG {t.get('id')} {(t.get('title') or '')[:60]}")
    return findings


def check_rollup_dead_card(rows: list[str], card_ids: set[str]) -> list[str]:
    findings = []
    seen: set[str] = set()
    for row in rows:
        cells = split_row_cells(row)
        if not cells:
            continue
        wire_cell = cells[-1]
        for m in TID_RE.finditer(wire_cell):
            tid = m.group(0)
            if tid in seen:
                continue
            seen.add(tid)
            if tid not in card_ids:
                findings.append(f"ROLLUP-DEAD-CARD {tid}")
    return findings


def read_board_tasks(db_path: Path) -> list[dict] | None:
    """[{id, title, body, status, comments}] for every task on one board, or None if unreadable."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return None
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, title, body, status FROM tasks").fetchall()
        tasks = [dict(r) for r in rows]
        comments_by_task: dict[str, list[str]] = {}
        try:
            crows = conn.execute("SELECT task_id, body FROM task_comments").fetchall()
            for c in crows:
                comments_by_task.setdefault(c["task_id"], []).append(c["body"] or "")
        except sqlite3.Error:
            pass  # a board without a task_comments table just has no comments
        for t in tasks:
            t["comments"] = comments_by_task.get(t["id"], [])
        return tasks
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def read_all_card_ids(boards_dir: Path) -> set[str] | None:
    """Every tasks.id across every <boards_dir>/*/kanban.db, or None if boards_dir is missing."""
    if not boards_dir.is_dir():
        return None
    ids: set[str] = set()
    for db_path in sorted(boards_dir.glob("*/kanban.db")):
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        except sqlite3.Error:
            continue
        try:
            conn.row_factory = sqlite3.Row
            for r in conn.execute("SELECT id FROM tasks").fetchall():
                ids.add(r["id"])
        except sqlite3.Error:
            continue
        finally:
            conn.close()
    return ids


def crosscheck(repo_root: Path, board_db: Path, boards_dir: Path) -> dict:
    """Run all checks; exits the process (code 2) if the required inputs can't be read."""
    entries_dir = repo_root / "docs" / "research" / "signal-log" / "entries"
    steals_path = repo_root / "docs" / "research" / "signal-log" / "STEALS.md"

    if not entries_dir.is_dir():
        print(f"ERROR: signal-log entries dir not found: {entries_dir}", file=sys.stderr)
        sys.exit(2)
    if not steals_path.is_file():
        print(f"ERROR: STEALS.md not found: {steals_path}", file=sys.stderr)
        sys.exit(2)

    entries = collect_entries(entries_dir)
    steals_text = steals_path.read_text(encoding="utf-8")
    rows = table_rows(steals_text)

    findings: list[str] = []
    findings += check_missing_rollup(entries, steals_text)
    findings += check_row_no_sig(rows)

    tasks = read_board_tasks(board_db)
    if tasks is None:
        findings.append(f"WARN board db not found at {board_db}")
    else:
        findings += check_card_no_sig(tasks)

    all_card_ids = read_all_card_ids(boards_dir)
    if all_card_ids is None:
        findings.append(f"WARN boards dir not found at {boards_dir}")
    else:
        findings += check_rollup_dead_card(rows, all_card_ids)

    counts = {
        "entries": len(entries),
        "rows": len(rows),
        "board_tasks": len(tasks) if tasks is not None else 0,
        "boards_scanned": len(list(boards_dir.glob("*/kanban.db"))) if boards_dir.is_dir() else 0,
        "findings": len(findings),
    }
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": counts,
        "findings": findings,
    }


def write_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    ap.add_argument("--board-db", default=str(BOARD_DB_DEFAULT))
    ap.add_argument("--boards-dir", default=str(BOARDS_DIR_DEFAULT))
    ap.add_argument("--state", default=str(STATE_DEFAULT))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    state = crosscheck(Path(args.repo_root), Path(args.board_db), Path(args.boards_dir))
    write_state(Path(args.state), state)

    if args.json:
        print(json.dumps(state))
        return

    findings = state["findings"]
    if findings:
        print(f"Steals ↔ signal-log cross-check: {len(findings)} finding(s)")
        for f in findings:
            print(f)


if __name__ == "__main__":
    main()
