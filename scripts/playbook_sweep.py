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
# A blocked run carrying one of these is a deliberate human gate, not a
# failure — never a miss candidate (lowercase; matched as substrings).
DELIBERATE_PARK_MARKERS = [
    "do not free-fire",
    "human pr review",
    "not for unattended dispatch",
    "waits on",
    # k2-intake's own parked notifications (first live sweep after the
    # bridge shipped nominated all 4 of them as "unknown failures").
    "intake notification",
    "human triage",
]
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
        repair_class = re.search(r"^repair_class:\s*(\S+)", head, re.M)
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
                    # Gauntlet gate (t_18792526, Ryan approved 2026-08-19):
                    # FAIL CLOSED — an entry that does not explicitly declare
                    # repair_class: report is treated as patch-class, and
                    # patch-class repairs can never arm from here: they park
                    # until a Gauntlet promotion record exists (ADR-073
                    # packet-1 schema) and Kevin's K2-side half is ruled.
                    "repair_class": (
                        repair_class.group(1) if repair_class else "patch"
                    ),
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
        out = []
        for r in rows:
            try:
                st = conn.execute(
                    "SELECT status FROM tasks WHERE id = ?", (r["task_id"],)
                ).fetchone()
                task_status = st["status"] if st else None
            except sqlite3.Error:
                task_status = None
            out.append(
                {
                    "task_id": r["task_id"],
                    "run_id": int(r["id"]),
                    "text": " ".join(filter(None, [r["summary"], r["error"]])),
                    "ended_at": r["ended_at"],
                    "task_status": task_status,
                }
            )
        return out
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


# Scoped repair-drafting (Ryan sanction 2026-08-19: "test it making legit
# work on its own. We can scope it to a few runs"). The TOTAL number of
# cards this machinery may ever draft is budgeted in state; when the budget
# is spent it warns once and stops. Raising PLAYBOOK_REPAIR_BUDGET is a
# deliberate human act, not something the sweep can do to itself.
REPAIR_BUDGET = int(os.environ.get("PLAYBOOK_REPAIR_BUDGET") or 3)

# Option A (Kevin's K2 inbox-5251 ruling, 2026-08-23): a patch class may arm
# when the K2 repo carries, AT origin/main, BOTH a registry row with a real
# enumerated scope AND a promoted record for that class. This check is
# deliberately shallow — registry row + scope shape + record verdict — because
# the dsh wrapper's gate re-validates everything fail-closed at PR time (deep
# record validation, base-loaded registry, per-path scope enforcement). The
# sweep's copy exists only to decide born-armed vs parked; a false positive
# here still cannot push code past the wrapper.
_K2_REPO_CANDIDATES = (
    HOME / "src" / "kevin-real-estate-tools",              # VPS shape
    Path.home() / "Documents" / "kevin-real-estate-tools", # Mac shape
)
K2_REPO = Path(
    os.environ.get("PLAYBOOK_K2_REPO")
    or next((str(p) for p in _K2_REPO_CANDIDATES if p.is_dir()), str(_K2_REPO_CANDIDATES[0]))
)
_K2_REGISTRY = "docs/gauntlets/candidate-class-registry.json"
_K2_PROMOTIONS = "docs/promotions"


def _k2_show(rel: str, repo: Path) -> str | None:
    """K2 file content at origin/main — never the working tree (may be stale/dirty)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "show", f"origin/main:{rel}"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _scope_is_real(scope: object) -> bool:
    """Mirrors the wrapper's rider check: real path list + positive int cap."""
    if not isinstance(scope, dict):
        return False
    allowed = scope.get("allowed_paths")
    cap = scope.get("max_files")
    return (
        isinstance(allowed, list)
        and bool(allowed)
        and all(isinstance(a, str) and a.strip() and a.strip() != "/" for a in allowed)
        and isinstance(cap, int)
        and not isinstance(cap, bool)
        and cap >= 1
    )


def validated_patch_classes(repo: Path | None = None) -> set[str]:
    """Classes that may arm patch drafting. FAIL-CLOSED: any error -> empty.

    A class qualifies only when K2 origin/main carries a registry row with a
    real enumerated scope AND at least one promotions record for it with
    verdict:promoted. Best-effort fetch first so origin/main means today.
    """
    repo = repo or K2_REPO
    if not (repo / ".git").exists() and not (repo / "HEAD").exists():
        return set()
    try:
        subprocess.run(
            ["git", "-C", str(repo), "fetch", "--quiet", "origin", "main"],
            timeout=60, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass  # stale origin/main is still origin/main; the wrapper re-checks
    reg_text = _k2_show(_K2_REGISTRY, repo)
    if reg_text is None:
        return set()
    try:
        rows = json.loads(reg_text).get("classes", [])
    except ValueError:
        return set()
    scoped = {
        r.get("id") for r in rows
        if isinstance(r, dict) and r.get("id") and _scope_is_real(r.get("scope"))
    }
    if not scoped:
        return set()
    promoted: set[str] = set()
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "--name-only",
             "origin/main", _K2_PROMOTIONS + "/"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=30, check=False,
        )
        names = [l.strip() for l in (proc.stdout or "").splitlines() if l.strip().endswith(".json")]
    except (OSError, subprocess.TimeoutExpired):
        return set()
    for rel in names:
        blob = _k2_show(rel, repo)
        if blob is None:
            continue
        try:
            doc = json.loads(blob)
        except ValueError:
            continue
        cls = doc.get("candidate_class")
        if cls in scoped and doc.get("verdict") == "promoted":
            promoted.add(cls)
    return promoted


def draft_repair_card(
    board: str,
    task_id: str,
    entry: dict,
    dry_run: bool,
    validated: frozenset[str] | set[str] = frozenset(),
) -> str | None:
    """Draft the repair card for a hit entry carrying a repair: instruction.

    Returns the new card id (or a dry-run marker), None on failure. Cards
    are born armed only when the entry says ``repair_auto: true`` AND the
    class may arm: report-class always may; a patch class only when it is in
    ``validated`` (Option A — a scoped registry row plus a promoted record at
    K2 origin/main; see validated_patch_classes). Otherwise create-then-block
    sticky (PB-006: --initial-status alone does not hold).

    A validated patch-class card is created project-linked (``--project k2
    --workspace worktree``, assignee dsh) so it dispatches into a real K2
    worktree and the wrapper's PR flow — where the gate re-validates the
    class, record, and scope fail-closed before any push.
    """
    title = f"AUTO-REPAIR ({entry['id']}): follow-up to {task_id}"
    body = (
        f"Auto-drafted by playbook_sweep: {board}/{task_id} hit {entry['id']}. "
        f"REPAIR INSTRUCTION: {entry['repair']} "
        f"Context: the PLAYBOOK HIT comment on {task_id}, and "
        f"docs/playbook/{Path(entry['path']).name}. "
        "FINISH PROTOCOL: if your deliverable changed code or opened a PR, end "
        "the run with `kanban request-review` (NOT `complete`) so the board "
        "reviewer lane issues an independent verdict; report-only deliverables "
        "may `complete` directly."
    )
    # Machine marker for the dsh wrapper's gauntlet gate (t_18792526 wrapper
    # half): the wrapper treats any non-"report" class as promotion-record-
    # required, restrictive direction only. Stamped by the sweep so the
    # wrapper reads the sweep's own line, not card prose.
    body += f"\n\nrepair-class: {entry['repair_class']}"
    is_report = entry["repair_class"] == "report"
    class_validated = entry["repair_class"] in validated
    if dry_run:
        print(f"[dry-run] would draft repair card on {board} for {entry['id']}")
        return "dry-run"
    create_args = [
        HERMES, "kanban", "--board", board, "create", title,
        "--body", body,
        "--assignee", "dsh" if class_validated else entry["repair_assignee"],
        "--created-by", "playbook-sweep",
    ]
    if class_validated:
        create_args += ["--project", "k2", "--workspace", "worktree"]
    create = subprocess.run(
        create_args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    m = re.search(r"Created\s+(t_[0-9a-f]+)", create.stdout or "")
    if create.returncode != 0 or not m:
        return None
    new_id = m.group(1)
    # repair_auto means "armed" for report-class repairs, and — since Kevin's
    # Option-A ruling (K2 inbox-5251, 2026-08-23) — for patch classes whose
    # registry row carries a real scope and whose promoted record stands at
    # K2 origin/main. Everything else parks sticky.
    armed = entry["repair_auto"] and (is_report or class_validated)
    if not armed:
        if not is_report:
            reason = (
                f"GAUNTLET GATE ({entry['id']} is {entry['repair_class']}-class): "
                f"this class is not validated at K2 origin/main (needs a "
                f"registry row with an enumerated scope AND a promoted "
                f"ADR-073 record — Option A per inbox-5251). Human may still "
                f"run this attended, or mint the class via the live-fire path."
            )
        else:
            reason = (
                f"auto-drafted repair for {entry['id']} — human: unblock to arm, "
                f"archive if the hit was noise"
            )
        subprocess.run(
            [
                HERMES, "kanban", "--board", board, "block", new_id,
                reason,
                "--kind", "needs_input",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    print(
        f"PLAYBOOK REPAIR drafted: {board}/{new_id} ({entry['id']}, "
        f"{'ARMED' if armed else 'parked needs_input'})"
    )
    return new_id


def sweep(dry_run: bool = False) -> dict:
    entries = parse_entries(PLAYBOOK_DIR)
    # Option-A class check costs a K2 fetch — only pay it when some entry
    # could actually use it (armed patch-class repair instruction present).
    validated: frozenset[str] = frozenset()
    if any(
        e.get("repair") and e["repair_auto"] and e["repair_class"] != "report"
        for e in entries
    ):
        validated = frozenset(validated_patch_classes())
    state = _load_state()
    seen = set(tuple(x) for x in state["commented"])
    since = time.time() - WINDOW_SECS
    counts = {
        "boards": 0, "failures": 0, "hits": 0, "misses": 0,
        "repairs": 0, "entries": len(entries),
    }
    # The honest metric (Ryan, 2026-08-20): `failures` counts every
    # blocked/crashed run-row in the window — deliberate parks, resolved
    # cards' historical rows, everything. `actionable` counts only DISTINCT
    # cards that are still live (not done/archived) and not a deliberate
    # human gate: the residue actually waiting on someone.
    actionable_cards = set()
    state.setdefault("repairs", [])
    drafted = set(tuple(x) for x in state["repairs"])
    miss_seen = set(tuple(x) for x in state.get("misses", []))
    new_misses: list[str] = []
    for db_path in sorted(BOARDS_DIR.glob("*/kanban.db")):
        board = db_path.parent.name
        counts["boards"] += 1
        for failure in recent_failures(db_path, since):
            counts["failures"] += 1
            hay_a = (failure["text"] or "").lower()
            if (
                failure.get("task_status") not in ("done", "archived")
                and not any(m in hay_a for m in DELIBERATE_PARK_MARKERS)
            ):
                actionable_cards.add((board, failure["task_id"]))
            matched = match_entries(entries, failure["text"])
            if not matched:
                # Deliberate parks are not failures: a run blocked by design
                # (human gates, pr-kanban-sync holds) must not nominate
                # itself as a missing playbook entry. First live run proved
                # the need — 3 of 3 surfaced "candidates" were review holds.
                hay = (failure["text"] or "").lower()
                if any(m in hay for m in DELIBERATE_PARK_MARKERS):
                    continue
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
                if key not in seen:
                    if comment_hit(board, failure["task_id"], entry, dry_run):
                        counts["hits"] += 1
                        seen.add(key)
                        state["commented"].append(list(key))
                        print(
                            f"PLAYBOOK HIT {entry['id']} -> {board}/{failure['task_id']}"
                        )
                # Detect->Diagnose->Repair, scoped: drafting is deduped
                # separately from commenting so a pre-existing hit can still
                # seed its repair card once the entry gains a repair: field.
                if entry.get("repair"):
                    rkey = (board, failure["task_id"], entry["id"], "repair")
                    if rkey in drafted:
                        continue
                    if len(drafted) >= REPAIR_BUDGET:
                        if not state.get("repair_budget_warned"):
                            print(
                                f"WARN playbook repair budget spent "
                                f"({REPAIR_BUDGET} drafts) — raising "
                                f"PLAYBOOK_REPAIR_BUDGET is a human decision"
                            )
                            state["repair_budget_warned"] = True
                        continue
                    if draft_repair_card(
                        board, failure["task_id"], entry, dry_run,
                        validated=validated,
                    ):
                        counts["repairs"] += 1
                        drafted.add(rkey)
                        state["repairs"].append(list(rkey))
    counts["actionable"] = len(actionable_cards)
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
