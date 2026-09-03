#!/usr/bin/env python3
"""Distillery review applier — reads Ryan's kanban-comment decisions and
applies them to a distillery review batch (card C3 successor).

Ryan decides via a kanban card comment on the `HUMAN review: distillery
batch <date>` card `distillery_review_agent.py --card-board` creates,
instead of hand-editing `decision:` fields in reviews/<date>.md (13
batches, 0 hand-edited approvals — nobody ever did it).

Reply grammar, case-insensitive, first non-empty line of the comment only:
  FILE 1,4 / SKIP rest      file rows 1 and 4, skip everything else in the batch
  FILE ALL                  file every row in the batch
  SKIP ALL                  skip every row in the batch
  DEFER                     leave the whole batch pending, comment only
Rows not named in a FILE/SKIP clause stay pending — they are NOT popped
from the pending cache, so they reappear as a candidate in a later batch
(unlike distillery_review_agent.py --apply, which pops the whole batch
regardless of decision). FILE always overrides the judge's own verdict for
that row.

No-agent cron script: empty stdout when there is nothing new to act on.
State (which comment ids have already been processed):
~/.t1000/cache/distillery-review-apply-state.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", "~/.t1000")).expanduser()
BOARD = os.environ.get("DISTILLERY_REVIEW_BOARD", "distillery")
STATE_PATH = HOME / "cache" / "distillery-review-apply-state.json"
TITLE_PREFIX = "HUMAN review: distillery batch "
INTAKE_DIR = Path(
    os.environ.get("DISTILLERY_INTAKE_DIR", "~/.t1000/distillery-intake")
).expanduser()
HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")

SCRIPTS_DIR = Path(__file__).resolve().parent
SWEEP_SCRIPT = SCRIPTS_DIR / "distillery_intake_sweep.py"
REVIEW_AGENT_PATH = SCRIPTS_DIR / "distillery_review_agent.py"

# Author sets — same shape as the remote t1000_human_pr_card_approve.py
# poller this script models itself on. Only RYAN_AUTHORS comments are ever
# acted on; AGENT_AUTHORS is kept explicit so the intent (never let an
# agent's own comment on this card be read as a human decision) is legible
# in the code, even though it's already implied by only matching RYAN_AUTHORS.
AGENT_AUTHORS = {
    "worker",
    "orchestrator",
    "sonnet",
    "grok",
    "flash",
    "nemo",
    "q38",
    "builder",
    "pr-kanban-sync",
    "escalate-sidecar",
}
RYAN_AUTHORS = {
    "default",
    "ryan",
    "telegram",
    "desktop",
    "ryan-desk",
    "ryanmitchellneely",
    "rneely",
}

# First-non-empty-line prefixes that are never a decision — other automation
# writes lines shaped like these onto cards; never mistake them for Ryan.
_NON_DECISION_PREFIXES = ("BLOCKED:", "UNBLOCK:", "WIDTH-CONTROL", "RECLAIM", "AUTO-ESCALATE")

_CLAUSE_RE = re.compile(r"^(FILE|SKIP)\s+(.+)$", re.IGNORECASE)
_NUM_TOKEN_RE = re.compile(r"^(\d+)(?:-(\d+))?$")


def _load_review_agent(path: Path = REVIEW_AGENT_PATH):
    """Import the sibling review-agent module by path (not by package import)
    so the two scripts stay co-located and dual-write independently, while
    tests can still monkeypatch the names re-exported below."""
    spec = importlib.util.spec_from_file_location("distillery_review_agent", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_review_agent = _load_review_agent()
parse_review_rows = _review_agent.parse_review_rows
run_sweep_mark = _review_agent.run_sweep_mark
set_draft_notes = _review_agent.set_draft_notes
append_filed_log = _review_agent.append_filed_log
load_pending = _review_agent.load_pending
save_pending = _review_agent.save_pending

PENDING_CACHE = Path(_review_agent.DEFAULT_PENDING_CACHE).expanduser()


def _parse_nums(text: str) -> set[int]:
    nums: set[int] = set()
    for tok in re.split(r"[,\s]+", text.strip()):
        if not tok:
            continue
        m = _NUM_TOKEN_RE.match(tok)
        if not m:
            raise ValueError(f"bad token {tok!r}")
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if hi < lo:
            raise ValueError(f"bad range {tok!r}")
        nums.update(range(lo, hi + 1))
    return nums


def parse_decision(text: str) -> dict | None:
    """First non-empty line of `text`, parsed against the reply grammar.
    Returns None (never guess) for anything unparseable, including lines
    that are clearly some OTHER automation's status line."""
    if not text:
        return None
    first_line = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break
    if not first_line:
        return None

    upper = first_line.upper()
    if any(upper.startswith(p) for p in _NON_DECISION_PREFIXES):
        return None
    # A trailing note after a spaced dash, colon or parenthesis is Ryan's
    # rationale, not grammar (same shape as the k2 poller's `APPROVE — why`).
    # A bare hyphen inside `2-5` has no surrounding spaces and survives.
    first_line = re.split(r"\s+[—–-]\s+|\s*\(|\s*:\s", first_line, maxsplit=1)[0].strip()
    upper = first_line.upper()

    if upper == "DEFER":
        return {"file": set(), "skip": set(), "defer": True}
    if upper == "FILE ALL":
        return {"file": "ALL", "skip": set(), "defer": False}
    if upper == "SKIP ALL":
        return {"file": set(), "skip": "ALL", "defer": False}

    result: dict = {"file": set(), "skip": set(), "defer": False}
    saw_clause = False
    for clause in re.split(r"[/;]", first_line):
        clause = clause.strip()
        if not clause:
            continue
        m = _CLAUSE_RE.match(clause)
        if not m:
            return None
        verb = m.group(1).upper()
        arg = m.group(2).strip()
        arg_low = arg.lower()
        if arg_low == "rest":
            value: object = "rest"
        elif arg_low == "all":
            value = "ALL"
        else:
            try:
                value = _parse_nums(arg)
            except ValueError:
                return None
            if not value:
                return None
        result["file" if verb == "FILE" else "skip"] = value
        saw_clause = True

    if not saw_clause:
        return None
    return result


def _load_index_rows(intake_dir: Path) -> list[dict]:
    path = Path(intake_dir) / "index.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    return payload.get("rows", [])


def apply_decision(date_str: str, decision: dict, intake_dir: Path, pending_cache: Path) -> dict:
    """Apply one parsed decision to reviews/<date_str>.md.

    Unlike distillery_review_agent.py's apply_review_batch(), rows named in
    neither FILE nor SKIP are left pending on purpose — their ids are NOT
    popped from the pending cache, so they reappear as a candidate in a
    later batch instead of vanishing into a closed batch.
    """
    intake_dir = Path(intake_dir)
    review_path = intake_dir / "reviews" / f"{date_str}.md"
    if not review_path.is_file():
        raise SystemExit(f"distillery-review-apply: no review file at {review_path}")

    rows = parse_review_rows(review_path.read_text(encoding="utf-8"))
    if not rows:
        raise SystemExit(
            f"distillery-review-apply: {review_path} has no recognizable row blocks"
        )

    by_row_num = {r["row"]: r for r in rows if r.get("row") is not None}
    all_nums = set(by_row_num.keys())

    if decision.get("defer"):
        return {"filed": 0, "skipped": 0, "pending": len(rows), "defer": True}

    file_spec = decision.get("file", set())
    skip_spec = decision.get("skip", set())

    if file_spec == "ALL":
        file_nums = set(all_nums)
    elif isinstance(file_spec, set):
        file_nums = file_spec & all_nums
    else:
        file_nums = set()

    remaining = all_nums - file_nums
    if skip_spec in ("ALL", "rest"):
        skip_nums = set(remaining)
    elif isinstance(skip_spec, set):
        skip_nums = skip_spec & remaining
    else:
        skip_nums = set()

    filed_rows = [by_row_num[n] for n in sorted(file_nums)]
    skipped_rows = [by_row_num[n] for n in sorted(skip_nums)]
    pending_nums = all_nums - file_nums - skip_nums

    marks = [f"{r['id']}=filed" for r in filed_rows] + [f"{r['id']}=skipped" for r in skipped_rows]
    run_sweep_mark(SWEEP_SCRIPT, intake_dir, marks)

    append_filed_log(intake_dir / "FILED-LOG.md", date_str, filed_rows)

    index_rows_by_id = {r["id"]: r for r in _load_index_rows(intake_dir)}
    lessons_entries = []
    for row in filed_rows:
        if row["id"].startswith("mesh_done_card:"):
            board = index_rows_by_id.get(row["id"], {}).get("board") or "?"
            card_id = row["id"].split(":", 1)[1].split("@", 1)[0]
            lessons_entries.append(
                f"- {date_str} | {board}:{card_id} | {row['title']} — {row['rationale']}"
            )
    if lessons_entries:
        lessons_path = intake_dir / "LESSONS-LEDGER.md"
        lessons_path.parent.mkdir(parents=True, exist_ok=True)
        if not lessons_path.is_file():
            lessons_path.write_text("# Distillery lessons ledger\n\n", encoding="utf-8")
        with lessons_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lessons_entries) + "\n")

    drafts_dir = intake_dir / "drafts"
    for row in skipped_rows:
        if row["verdict"] == "supersede":
            set_draft_notes(drafts_dir, row["id"], f"dup of {row['supersede_of'] or 'unknown'}")

    pending = load_pending(pending_cache)
    for row in filed_rows + skipped_rows:
        pending.pop(row["id"], None)
    save_pending(pending_cache, pending)

    return {
        "filed": len(filed_rows),
        "skipped": len(skipped_rows),
        "pending": len(pending_nums),
        "defer": False,
    }


def _hermes(args: list[str]) -> subprocess.CompletedProcess:
    """The only hermes call path — every kanban write goes through this so
    tests can monkeypatch it wholesale."""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(HOME)
    return subprocess.run([HERMES_BIN, *args], capture_output=True, text=True, env=env)


def _comment(task_id: str, board: str, text: str) -> subprocess.CompletedProcess:
    return _hermes(["kanban", "--board", board, "comment", task_id, text])


def _unblock(task_id: str, board: str, reason: str) -> subprocess.CompletedProcess:
    return _hermes(["kanban", "--board", board, "unblock", task_id, "--reason", reason])


def _archive(task_id: str, board: str) -> subprocess.CompletedProcess:
    return _hermes(["kanban", "--board", board, "archive", task_id])


def _block(task_id: str, board: str, reason: str) -> subprocess.CompletedProcess:
    return _hermes(["kanban", "--board", board, "block", task_id, "--kind", "needs_input", reason])


def _err_text(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout or "").strip()


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_pending(state: dict) -> list[dict]:
    """New, unprocessed, Ryan-authored, decision-shaped comments on open
    `HUMAN review: distillery batch <date>` cards."""
    db = HOME / "kanban" / "boards" / BOARD / "kanban.db"
    if not db.is_file():
        return []
    processed = set(state.get("processed_comment_ids") or [])

    items: list[dict] = []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        cards = con.execute(
            "SELECT id, title, status FROM tasks "
            "WHERE title LIKE ? AND status NOT IN ('done', 'archived')",
            (TITLE_PREFIX + "%",),
        ).fetchall()
        for card in cards:
            date_str = card["title"][len(TITLE_PREFIX):].strip()
            comments = con.execute(
                "SELECT id, author, body, created_at FROM task_comments "
                "WHERE task_id = ? ORDER BY created_at ASC, id ASC",
                (card["id"],),
            ).fetchall()
            for c in comments:
                if c["id"] in processed:
                    continue
                if (c["author"] or "") not in RYAN_AUTHORS:
                    continue
                decision = parse_decision(c["body"] or "")
                if decision is None:
                    continue
                items.append(
                    {
                        "comment_id": c["id"],
                        "task_id": card["id"],
                        "board": BOARD,
                        "date_str": date_str,
                        "decision": decision,
                        "author": c["author"],
                        "created_at": c["created_at"],
                    }
                )
    finally:
        con.close()
    return items


def _apply_one(item: dict, state: dict) -> str:
    task_id = item["task_id"]
    board = item["board"]
    date_str = item["date_str"]
    decision = item["decision"]

    try:
        if decision.get("defer"):
            _comment(task_id, board, "DEFER recorded")
            summary = f"DEFER {date_str} {task_id}"
        else:
            counts = apply_decision(date_str, decision, INTAKE_DIR, PENDING_CACHE)
            receipt = (
                f"Applied: {counts['filed']} filed, {counts['skipped']} skipped, "
                f"{counts['pending']} left pending. FILED-LOG updated."
            )
            comment_result = _comment(task_id, board, receipt)
            if comment_result.returncode != 0:
                summary = f"APPLY {date_str} {task_id}: {receipt} (comment failed: {_err_text(comment_result)})"
            else:
                summary = f"APPLY {date_str} {task_id}: {receipt}"

            if counts["pending"] == 0:
                unblock_result = _unblock(
                    task_id, board, "distillery-review-apply: batch fully resolved"
                )
                if unblock_result.returncode == 0:
                    archive_result = _archive(task_id, board)
                    if archive_result.returncode != 0:
                        _comment(
                            task_id,
                            board,
                            f"Archiver error: {_err_text(archive_result)}",
                        )
                        # Never leave a fully-unblocked card sitting `ready` —
                        # re-block it so a dispatcher can't claim it.
                        _block(
                            task_id,
                            board,
                            "distillery-review-apply: archive failed after "
                            "unblock — re-blocked to avoid a stray ready card",
                        )
                else:
                    _comment(
                        task_id,
                        board,
                        f"Unblock error: {_err_text(unblock_result)}",
                    )
    except (Exception, SystemExit) as e:
        _comment(task_id, board, f"Applier error: {e}")
        summary = f"ERROR {date_str} {task_id}: {e}"

    processed = state.setdefault("processed_comment_ids", [])
    if item["comment_id"] not in processed:
        processed.append(item["comment_id"])
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="t1000_distillery_review_apply.py",
        description=(
            "Apply Ryan's kanban-comment FILE/SKIP/DEFER decisions to pending "
            "distillery review batches (no-agent cron)."
        ),
    )
    ap.add_argument("--dry-run", action="store_true", help="print what would happen; write nothing")
    args = ap.parse_args(argv)

    state = _load_state()
    pending = collect_pending(state)
    if not pending:
        return 0

    if args.dry_run:
        for item in pending:
            print(f"DRY {item['date_str']} {item['decision']}")
        return 0

    lines = [_apply_one(item, state) for item in pending]
    _save_state(state)

    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
