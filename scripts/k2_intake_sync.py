#!/usr/bin/env python3
"""K2 health-checker findings → parked kanban cards (t_f3dd22e3).

The k2 board's only automated intake was pr-kanban-sync (GitHub PRs).
K2's own deterministic health checkers emit findings that alert humans on
Telegram and stop — the board never learns, so nothing routes the broken
stuff toward workers. This bridge closes that gap with the same contract
pr-kanban-sync proved:

  - ONE card per checker class (39 stale KB pages = one card carrying the
    count + samples), idempotent by checker key.
  - Cards are born and IMMEDIATELY blocked needs_input — an intake card is
    a notification, and notifications never auto-dispatch (PB-006:
    create-then-block sticky; same rule as playbook repair drafting).
  - Count changes get a comment; a clean checker completes its card.
  - Max 5 new cards per run; internal ~6h throttle (findings move daily,
    the pulse fires half-hourly).

Runs as a rider on the ops-alert pulse. Checkers execute against the
read-only K2 clone — zero K2-repo changes, no lane contact. Stdout is the
Telegram surface via the pulse. Heartbeat: cache/k2-intake-heartbeat.json.

Canonical: T1000 repo scripts/. Deploy copy: ~/.t1000/scripts/.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
_SCRIPT_DESK = Path(__file__).resolve().parent.parent
DESK = _SCRIPT_DESK if (_SCRIPT_DESK / "cache").is_dir() else HOME
CLONE = Path(
    os.environ.get("K2_INTAKE_CLONE", HOME / "src" / "kevin-real-estate-tools")
)
STATE_PATH = DESK / "cache" / "k2-intake-state.json"
HEARTBEAT_PATH = DESK / "cache" / "k2-intake-heartbeat.json"
BOARD = os.environ.get("K2_INTAKE_BOARD", "k2")
HERMES = os.environ.get("K2_INTAKE_HERMES_BIN", str(Path.home() / ".local" / "bin" / "hermes"))
THROTTLE_SECS = int(os.environ.get("K2_INTAKE_THROTTLE_SECS") or 6 * 3600)
MAX_NEW_CARDS_PER_RUN = 5

# Each checker: how to run it and how to read its findings.
#   line_re    — count (and sample) stdout lines matching this regex.
#   summary_re — take the count from this regex's first capture group;
#                samples are the first matching-context lines.
CHECKERS = [
    {
        "key": "wiki-staleness",
        "title": "stale knowledge-base pages (sources changed after page)",
        "argv": ["python3", "scripts/wiki_staleness_check.py"],
        "line_re": r"^\s*STALE\s+\S+",
    },
    {
        "key": "inbox-premise",
        "title": "inbox items with unprotected progress claims (no Premise line)",
        "argv": ["python3", "scripts/inbox_premise_check.py"],
        "line_re": r"warning:",
    },
    {
        "key": "deferred-followups",
        "title": "deferred follow-ups past due",
        "argv": ["python3", "scripts/deferred_followups_check.py"],
        "summary_re": r"deferred-followups:\s*(\d+)\s+due",
        "sample_re": r"^DUE\s",
    },
    {
        "key": "parts-catalog",
        "title": "part-shaped units missing catalog rows",
        "argv": ["python3", "scripts/parts_catalog_check.py"],
        "summary_re": r"(\d+)\s+uncatalogued",
        "sample_re": r"^\s+\S",
    },
]


def run_checker(spec: dict, clone: Path) -> dict | None:
    """Run one checker; return {count, samples} or None on failure."""
    try:
        r = subprocess.run(
            spec["argv"],
            cwd=str(clone),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return None
    out = r.stdout or ""
    lines = out.splitlines()
    if "line_re" in spec:
        matches = [ln for ln in lines if re.search(spec["line_re"], ln)]
        return {"count": len(matches), "samples": [m.strip()[:160] for m in matches[:5]]}
    m = re.search(spec["summary_re"], out)
    if not m:
        return None
    sample_re = spec.get("sample_re")
    samples = (
        [ln.strip()[:160] for ln in lines if sample_re and re.search(sample_re, ln)][:5]
        if sample_re
        else lines[:3]
    )
    return {"count": int(m.group(1)), "samples": samples}


def _hermes(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [HERMES, "kanban", "--board", BOARD, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")


def _create_parked_card(spec: dict, finding: dict) -> str | None:
    title = f"K2 INTAKE ({spec['key']}): {finding['count']} — {spec['title']}"
    body = (
        f"Auto-filed by k2_intake_sync from K2's own checker "
        f"`{' '.join(spec['argv'])}` run against the read-only clone. "
        f"Count: {finding['count']}. Samples:\n"
        + "\n".join(f"- {s}" for s in finding["samples"])
        + "\n\nRe-run in a K2 checkout for the full list. This card is a "
        f"NOTIFICATION: triage it — work it, split it, or archive it. It "
        f"auto-completes when the checker returns clean. Card updates its "
        f"count via comments while the finding persists. FINISH PROTOCOL for "
        f"any worker dispatched on this card: if your deliverable changed code "
        f"or opened a PR, end with `kanban request-review` (NOT `complete`) so "
        f"the board reviewer lane issues an independent verdict."
    )
    create = _hermes(
        [
            "create", title,
            "--body", body,
            "--created-by", "k2-intake-sync",
        ]
    )
    m = re.search(r"Created\s+(t_[0-9a-f]+)", create.stdout or "")
    if create.returncode != 0 or not m:
        return None
    card_id = m.group(1)
    _hermes(
        [
            "block", card_id,
            "intake notification — human triage required; never auto-dispatched",
            "--kind", "needs_input",
        ]
    )
    return card_id


def sync(force: bool = False) -> dict:
    state = _load_state()
    now = time.time()
    if not force and now - state.get("last_run_ts", 0) < THROTTLE_SECS:
        return {"skipped": "throttled"}
    counts = {"checkers": 0, "failed": 0, "new_cards": 0, "updated": 0, "completed": 0}
    cards = state.setdefault("cards", {})
    new_cards_this_run = 0
    for spec in CHECKERS:
        counts["checkers"] += 1
        finding = run_checker(spec, CLONE)
        if finding is None:
            counts["failed"] += 1
            print(f"WARN k2-intake checker failed: {spec['key']}")
            continue
        known = cards.get(spec["key"])
        if finding["count"] > 0 and not known:
            if new_cards_this_run >= MAX_NEW_CARDS_PER_RUN:
                print(f"WARN k2-intake card cap reached; deferring {spec['key']}")
                continue
            card_id = _create_parked_card(spec, finding)
            if card_id:
                cards[spec["key"]] = {"card": card_id, "count": finding["count"]}
                new_cards_this_run += 1
                counts["new_cards"] += 1
                print(
                    f"K2 INTAKE new card {BOARD}/{card_id}: {spec['key']} "
                    f"({finding['count']})"
                )
        elif finding["count"] > 0 and known and finding["count"] != known["count"]:
            _hermes(
                [
                    "comment", known["card"],
                    f"k2-intake update: count {known['count']} -> {finding['count']}",
                ]
            )
            print(
                f"K2 INTAKE {spec['key']}: {known['count']} -> {finding['count']} "
                f"({BOARD}/{known['card']})"
            )
            known["count"] = finding["count"]
            counts["updated"] += 1
        elif finding["count"] == 0 and known:
            _hermes(["unblock", known["card"]])
            _hermes(
                [
                    "complete", known["card"],
                    "--result", f"k2-intake: checker {spec['key']} returned clean",
                ]
            )
            print(f"K2 INTAKE cleared: {spec['key']} ({BOARD}/{known['card']})")
            del cards[spec["key"]]
            counts["completed"] += 1
    state["last_run_ts"] = now
    _save_state(state)
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(
        json.dumps(
            {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **counts}
        ),
        encoding="utf-8",
    )
    return counts


if __name__ == "__main__":
    result = sync(force="--force" in sys.argv)
    print(f"[k2-intake] {result}", file=sys.stderr)
