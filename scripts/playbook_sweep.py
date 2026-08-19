#!/usr/bin/env python3
"""Failure-playbook retrieval sweep (t_c3a4b01d v0).

The playbook (docs/playbook/PB-*.md) only closes the loop if a lookup happens
AT FAILURE TIME without anyone remembering to do it. This sweep is that hook:
it scans recent blocked/crashed kanban runs across every board, greps their
failure text against each entry's `match` patterns, and comments the hit onto
the card — so the known diagnosis lands on the failure itself, minutes after
it happens.

Runs as a rider on the ops-alert pulse (Track C pattern per that script's
docstring: ride the proven 30m cadence, never author a naked new cron).
Stdout is the alert surface: the pulse delivers non-empty stdout to Telegram,
so printed hits reach a human unprompted. Heartbeat:
~/.t1000/cache/playbook-sweep-heartbeat.json.

Patterns are matched as case-insensitive LITERAL substrings, not regexes —
entries contain strings like `$HOME` that must mean themselves.

Canonical: T1000 repo scripts/playbook_sweep.py. Deploy copy: ~/.t1000/scripts/.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
_SCRIPT_DESK = Path(__file__).resolve().parent.parent
DESK = _SCRIPT_DESK if (_SCRIPT_DESK / "cache").is_dir() else HOME
PLAYBOOK_DIR = Path(
    os.environ.get("PLAYBOOK_DIR", Path.home() / "Documents" / "T1000" / "docs" / "playbook")
)
BOARDS_DIR = Path(os.environ.get("PLAYBOOK_BOARDS_DIR", HOME / "kanban" / "boards"))
STATE_PATH = DESK / "cache" / "playbook-sweep-state.json"
HEARTBEAT_PATH = DESK / "cache" / "playbook-sweep-heartbeat.json"
WINDOW_SECS = int(os.environ.get("PLAYBOOK_WINDOW_SECS") or 24 * 3600)
STALE_DAYS = int(os.environ.get("PLAYBOOK_STALE_DAYS") or 90)
HERMES = os.environ.get("PLAYBOOK_HERMES_BIN", str(Path.home() / ".local" / "bin" / "hermes"))


def parse_entries(playbook_dir: Path) -> list[dict]:
    """PB-*.md frontmatter -> [{id, patterns, fix_line, verified, path}]."""
    entries = []
    for path in sorted(playbook_dir.glob("PB-*.md")):
        text = path.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if not fm:
            continue
        head, body = fm.groups()
        pid = re.search(r"^id:\s*(\S+)", head, re.M)
        patterns = re.findall(r'^\s+- "(.*)"$', head, re.M)
        verified = re.search(r"^verified:\s*(\S+)", head, re.M)
        fix = re.search(r"\*\*Fix[^:]*:\*\*\s*(.+?)(?:\n\n|\Z)", body, re.S)
        fix_line = " ".join(fix.group(1).split())[:300] if fix else "(see entry)"
        repair = re.search(r'^repair:\s*"(.*)"\s*$', head, re.M)
        repair_assignee = re.search(r"^repair_assignee:\s*(\S+)", head, re.M)
        repair_auto = re.search(r"^repair_auto:\s*true\s*$", head, re.M)
        if pid and patterns:
            entries.append(
                {
                    "id": pid.group(1),
                    "patterns": patterns,
                    "fix_line": fix_line,
                    "verified": verified.group(1) if verified else None,
                    "path": str(path),
                    # Detect->Diagnose->REPAIR: an entry may carry a card-able
                    # repair instruction. Without repair_auto: true the drafted
                    # card is parked blocked/needs_input (human arms it) — the
                    # machinery ships dormant and earns trust per entry.
                    "repair": repair.group(1) if repair else None,
                    "repair_assignee": (
                        repair_assignee.group(1) if repair_assignee else "worker"
                    ),
                    "repair_auto": bool(repair_auto),
                }
            )
    return entries


def match_entries(entries: list[dict], failure_text: str) -> list[dict]:
    """Entries whose ANY pattern occurs in failure_text (literal, case-insensitive)."""
    hay = (failure_text or "").lower()
    return [e for e in entries if any(p.lower() in hay for p in e["patterns"])]


def stale_entries(entries: list[dict], now: float | None = None) -> list[dict]:
    now = now if now is not None else time.time()
    out = []
    for e in entries:
        v = e.get("verified")
        if not v:
            out.append(e)
            continue
        try:
            ts = time.mktime(time.strptime(v, "%Y-%m-%d"))
        except ValueError:
            out.append(e)
            continue
        if now - ts > STALE_DAYS * 86400:
            out.append(e)
    return out


def recent_failures(db_path: Path, since: float) -> list[dict]:
    """Recent blocked/crashed runs: [{task_id, run_id, text, ended_at}]."""
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, task_id, outcome, summary, error, ended_at FROM task_runs "
            "WHERE ended_at IS NOT NULL AND ended_at > ? "
            "AND outcome IN ('blocked', 'crashed') ORDER BY ended_at",
            (since,),
        ).fetchall()
        return [
            {
                "task_id": r["task_id"],
                "run_id": int(r["id"]),
                "text": " ".join(filter(None, [r["summary"], r["error"]])),
                "ended_at": r["ended_at"],
            }
            for r in rows
        ]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"commented": []}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Cap growth: keep the newest 2000 dedupe keys.
    state["commented"] = state["commented"][-2000:]
    state["misses"] = state.get("misses", [])[-2000:]
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")


def comment_hit(board: str, task_id: str, entry: dict, dry_run: bool) -> bool:
    msg = (
        f"PLAYBOOK HIT {entry['id']}: known failure class. Fix: {entry['fix_line']} "
        f"(full entry: {Path(entry['path']).name} in docs/playbook/)"
    )
    if dry_run:
        print(f"[dry-run] would comment on {board}/{task_id}: {entry['id']}")
        return True
    r = subprocess.run(
        [HERMES, "kanban", "--board", board, "comment", task_id, msg],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.returncode == 0


def sweep(dry_run: bool = False) -> dict:
    entries = parse_entries(PLAYBOOK_DIR)
    state = _load_state()
    seen = set(tuple(x) for x in state["commented"])
    since = time.time() - WINDOW_SECS
    counts = {"boards": 0, "failures": 0, "hits": 0, "misses": 0, "entries": len(entries)}
    miss_seen = set(tuple(x) for x in state.get("misses", []))
    new_misses: list[str] = []
    for db_path in sorted(BOARDS_DIR.glob("*/kanban.db")):
        board = db_path.parent.name
        counts["boards"] += 1
        for failure in recent_failures(db_path, since):
            counts["failures"] += 1
            matched = match_entries(entries, failure["text"])
            if not matched:
                # Corpus growth: an unmatched failure is a candidate entry.
                # Deduped per (board, task) in state; surfaced max 3 per run
                # so the Telegram line stays a nudge, not a firehose.
                mkey = (board, failure["task_id"])
                if mkey not in miss_seen:
                    miss_seen.add(mkey)
                    state.setdefault("misses", []).append(list(mkey))
                    counts["misses"] += 1
                    if len(new_misses) < 3:
                        snippet = " ".join((failure["text"] or "").split())[:110]
                        new_misses.append(
                            f"PLAYBOOK MISS candidate: {board}/{failure['task_id']} — {snippet}"
                        )
                continue
            for entry in matched:
                key = (board, failure["task_id"], entry["id"])
                if key in seen:
                    continue
                if comment_hit(board, failure["task_id"], entry, dry_run):
                    counts["hits"] += 1
                    seen.add(key)
                    state["commented"].append(list(key))
                    print(
                        f"PLAYBOOK HIT {entry['id']} -> {board}/{failure['task_id']}"
                    )
    for line in new_misses:
        print(line)
    for e in stale_entries(entries):
        print(f"WARN playbook entry {e['id']} unverified >{STALE_DAYS}d — re-verify or retire")
    if not dry_run:
        _save_state(state)
        HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_PATH.write_text(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    **counts,
                }
            ),
            encoding="utf-8",
        )
    return counts


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    c = sweep(dry_run=dry)
    print(
        f"[playbook-sweep] entries={c['entries']} boards={c['boards']} "
        f"failures={c['failures']} hits={c['hits']}",
        file=sys.stderr,
    )
