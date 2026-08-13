#!/usr/bin/env python3
"""ST-13 Phase 1 — per-turn stage-router signals, OBSERVER ONLY (t_95bb6eb2).

Ports the *signal shape* from NVIDIA NeMo Switchyard's ``stage_router``
(SIG-20260811-06, docs/research/signal-log/entries/SIG-20260811-06_nemo-switchyard-stage-router.md)
as a read-only observer over telemetry we already emit. This module changes
no routing, writes no config, restarts nothing, and requires no new
dependency (stdlib only) or Rust toolchain.

SIGNAL SOURCES (honest enumeration — item 1 of the card's Phase 1 ask)
------------------------------------------------------------------------
Kanban ``task_events`` (``<board>/kanban.db``) is a coarse, per-RUN
lifecycle stream: created/promoted/claimed/spawned/heartbeat(~60s,
empty payload)/blocked/unblocked/completed/crashed/timed_out/gave_up/
protocol_violation/block_loop_detected/model_escalated/... There is
NO per-tool-call or per-turn event in this table today — heartbeats
carry no signal beyond "still alive". So:

  * severity (windowed error severity)
      SOURCE: EXISTS, but split across two places —
        (a) run-terminal task_events kinds {crashed, timed_out, gave_up,
            protocol_violation, block_loop_detected} plus the tasks.
            consecutive_failures counter (kanban DB), and
        (b) inline fatal/warning markers in the plain-text worker log
            (``<board>/logs/<task_id>.log``): "API call failed",
            "Non-retryable error", "authentication failed",
            "BadRequestError", "[... not found]", leading "⚠️"/"❌".
      Neither source is windowed/structured today — this module does
      the windowing.

  * spinning (deep churn, no reads or writes)
      SOURCE: EXISTS only in the worker log's tool-call transcript
      (icon-tagged action lines rendered by agent/display.py — see
      _ACTION_CLASS below). NOT present in kanban task_events at all.

  * exploring (reading/planning without producing)
      SOURCE: same as spinning — worker log tool-call transcript only.

  * recent_production_intensity (writes/edits landing)
      SOURCE: same as spinning — worker log tool-call transcript only
      (✍️ write / 🔧 patch action lines).

Net: 3 of 4 signals have NO source in the structured kanban DB at all
today — they exist only by parsing the human-readable CLI transcript
log, which is not a stable, versioned schema (it is a terminal-render
convenience, agent/display.py, subject to change without notice). That
fragility is itself a Phase-1 finding, not swept under the rug.

SCORING SHAPE (item 2 — pure function, no I/O)
------------------------------------------------------------------------
Switchyard's docs (as paraphrased in SIG-20260811-06) state the score is
"signed, tanh-squashed to [0,1]", and that "one full signal scores ~0.46
— just under the 0.5 threshold". We do not have their source, so we
reconstruct the simplest formula that reproduces that documented
reference point exactly: each of the three escalate axes (severity,
spinning, exploring) contributes AXIS_WEIGHT=0.5 to a nonnegative raw
sum; production_intensity subtracts at the same weight; the raw sum is
floored at 0 and passed through tanh (whose output is already in
[0, 1) for nonnegative input, so no further rescale is needed):

    tanh(1 * 0.5) = 0.4621...  ≈ "~0.46" for one fully-triggered axis
    tanh(2 * 0.5) = 0.7616...  for two corroborating axes (crosses 0.5)

Per HARD RULES on the card: we do NOT carry over Switchyard's 0.5
threshold as our decision boundary (that number is calibrated on
SWE-Bench Pro Python-75, not our kanban mix) — Phase 1 logs the raw
score at several candidate thresholds for comparison; it does not pick
one. Phase 2 (RESCUE/LOSS calibration) is gated separately and is not
started here.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

HOME = Path(os.environ.get("HERMES_HOME") or Path.home() / ".t1000").expanduser()
# The kanban mesh lives at a single shared location (~/.t1000/kanban/boards/*)
# regardless of which profile's HERMES_HOME a worker happens to run under —
# do not derive this from HERMES_HOME (worker profiles redirect it to
# ~/.t1000/profiles/<name>, which has no kanban/ subtree of its own).
KANBAN_ROOT = Path(os.environ.get("KANBAN_ROOT") or Path.home() / ".t1000" / "kanban" / "boards").expanduser()

AXIS_WEIGHT = 0.5  # see SCORING SHAPE docstring above

# Run-terminal task_events kinds that count as a hard failure outcome.
FAIL_KINDS = {"crashed", "timed_out", "gave_up", "protocol_violation", "block_loop_detected"}
PASS_KINDS = {"completed"}

# ---------------------------------------------------------------------------
# Pure scorer — no I/O below this line down to OFFLINE PARSING
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnSignals:
    """One windowed observation. Every field is a float in [0, 1] except
    critical_error. Callers (the offline parser, or in principle a live
    hook) are responsible for producing these from raw telemetry — this
    dataclass and score_window() below do no I/O."""

    severity: float = 0.0
    spinning: float = 0.0
    exploring: float = 0.0
    production_intensity: float = 0.0
    critical_error: bool = False

    def __post_init__(self) -> None:
        for name in ("severity", "spinning", "exploring", "production_intensity"):
            v = getattr(self, name)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"{name}={v!r} out of [0, 1]")


@dataclass(frozen=True)
class ObserverVerdict:
    score: float  # tanh-squashed, in [0, 1]
    hard_override: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def would_escalate(self, threshold: float) -> bool:
        """Would the observer have voted to escalate at this threshold?
        Phase 1 uses this only to LOG a verdict — see module docstring
        HARD RULES; it never feeds routing."""
        return self.hard_override or self.score >= threshold


def score_window(signals: TurnSignals) -> ObserverVerdict:
    """Pure function: TurnSignals -> ObserverVerdict. No I/O, deterministic.

    A critical_error is a hard override — escalates on its own at score
    1.0 regardless of the other three axes, matching Switchyard's
    documented "critical-error severity is a hard override" rule.
    """
    if signals.critical_error:
        return ObserverVerdict(score=1.0, hard_override=True, reasons=("critical_error_hard_override",))

    raw = (
        signals.severity * AXIS_WEIGHT
        + signals.spinning * AXIS_WEIGHT
        + signals.exploring * AXIS_WEIGHT
        - signals.production_intensity * AXIS_WEIGHT
    )
    raw = max(0.0, raw)
    score = math.tanh(raw)

    reasons = []
    if signals.severity > 0:
        reasons.append(f"severity={signals.severity:.2f}")
    if signals.spinning > 0:
        reasons.append(f"spinning={signals.spinning:.2f}")
    if signals.exploring > 0:
        reasons.append(f"exploring={signals.exploring:.2f}")
    if signals.production_intensity > 0:
        reasons.append(f"production_intensity={signals.production_intensity:.2f}")

    return ObserverVerdict(score=score, hard_override=False, reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# OFFLINE PARSING — everything below this line does I/O (sqlite3, files).
# ---------------------------------------------------------------------------

# agent/display.py tool-call render vocabulary (verified against source,
# see module docstring). Classification is ours; the icon set is theirs.
_READ_ICONS = {"📖"}
_WRITE_ICONS = {"✍️", "🔧"}
_EXPLORE_ICONS = {"🔎", "🔍", "📄", "👁️", "📚", "📋"}
_SHELL_ICONS = {"💻", "🐍", "⚙️", "⏰"}

_ACTION_LINE_RE = re.compile(r"┊\s*(\S+)\s")
_ERROR_MARKER_RE = re.compile(
    r"(⚠️|❌|\[.*not found.*\]|API call failed|Non-retryable error|"
    r"authentication failed|BadRequestError|OAuth session expired)",
    re.IGNORECASE,
)


def _action_class(icon: str) -> str:
    if icon in _READ_ICONS:
        return "read"
    if icon in _WRITE_ICONS:
        return "write"
    if icon in _EXPLORE_ICONS:
        return "explore"
    if icon in _SHELL_ICONS:
        return "shell"
    return "other"


@dataclass
class LogEvent:
    line_no: int
    action_class: str  # read | write | explore | shell | other | error
    is_error: bool


def parse_worker_log(path: Path) -> list[LogEvent]:
    """Parse a plain-text worker log into an ordered tool-call/error
    sequence. Best-effort regex over a render format we do not control
    (agent/display.py) — see module docstring on this fragility."""
    events: list[LogEvent] = []
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return events
    for i, line in enumerate(text.splitlines()):
        is_error = bool(_ERROR_MARKER_RE.search(line))
        m = _ACTION_LINE_RE.search(line)
        if m:
            events.append(LogEvent(line_no=i, action_class=_action_class(m.group(1)), is_error=is_error))
        elif is_error:
            events.append(LogEvent(line_no=i, action_class="other", is_error=True))
    return events


def windows(events: list[LogEvent], size: int = 8) -> Iterator[tuple[int, list[LogEvent]]]:
    """Sliding window over tool-call events, stepping by 1. Yields
    (end_index, window_slice). This is our operational stand-in for
    "per turn" — the worker log has no explicit turn-boundary marker
    (verified: only 6 divider lines in a 296-line, 90-iteration run),
    so a tool-call window is the finest-grained honest proxy available.

    Only FULL windows (len == size) are yielded. A ramp-up window (size
    1, 2, 3, ...) was tried first and rejected: at n=1 a single non-
    read/write event trivially satisfies "no reads or writes" and
    signals_from_window() reports spinning=1.0 from one data point —
    every task in the offline run flagged at window 1 regardless of
    outcome, which is small-n noise, not a real signal. If the whole
    log is shorter than `size`, the entire log is yielded once as a
    single partial window so short runs still produce one verdict."""
    if not events:
        return
    if len(events) < size:
        yield len(events), events
        return
    for end in range(size, len(events) + 1):
        yield end, events[end - size:end]


def signals_from_window(win: list[LogEvent]) -> TurnSignals:
    if not win:
        return TurnSignals()
    n = len(win)
    reads = sum(1 for e in win if e.action_class == "read")
    writes = sum(1 for e in win if e.action_class == "write")
    explores = sum(1 for e in win if e.action_class == "explore")
    errors = sum(1 for e in win if e.is_error)

    severity = min(1.0, (errors / n) * 3.0)
    spinning = max(0.0, 1.0 - (reads + writes) / 2.0) if (reads + writes) < 2 else 0.0
    exploring = 0.0 if writes > 0 else min(1.0, (reads + explores) / n)
    production_intensity = min(1.0, (writes / n) * 2.0)

    return TurnSignals(
        severity=severity,
        spinning=spinning,
        exploring=exploring,
        production_intensity=production_intensity,
        critical_error=False,  # filled in by the caller from task_events
    )


def board_dbs(board: Optional[str] = None) -> list[Path]:
    if board:
        p = KANBAN_ROOT / board / "kanban.db"
        return [p] if p.exists() else []
    return sorted(KANBAN_ROOT.glob("*/kanban.db"))


def load_task_outcomes(db_path: Path) -> dict[str, dict]:
    """One row per task: terminal kind (fail kind, or 'completed'), and
    the run_id the terminal event landed on (to align with the log)."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    out: dict[str, dict] = {}
    try:
        rows = con.execute(
            "SELECT task_id, kind, run_id, payload, created_at FROM task_events "
            "WHERE kind IN ({}) ORDER BY task_id, created_at".format(
                ",".join("?" * (len(FAIL_KINDS) + len(PASS_KINDS)))
            ),
            tuple(FAIL_KINDS | PASS_KINDS),
        ).fetchall()
    finally:
        con.close()
    for r in rows:
        # Last terminal event wins (a card can crash, get re-dispatched,
        # then complete — we want the FINAL outcome).
        out[r["task_id"]] = {"kind": r["kind"], "run_id": r["run_id"], "payload": r["payload"]}
    return out


@dataclass
class TaskVerdictTrace:
    task_id: str
    board: str
    outcome: str  # one of FAIL_KINDS or 'completed'
    total_windows: int
    first_flag_window: dict[float, Optional[int]]  # threshold -> window index or None
    had_critical_override: bool


def evaluate_task(board: str, task_id: str, outcome_kind: str, log_path: Path, thresholds: Iterable[float]) -> Optional[TaskVerdictTrace]:
    events = parse_worker_log(log_path)
    if not events:
        return None
    thresholds = list(thresholds)
    first_flag: dict[float, Optional[int]] = {t: None for t in thresholds}
    had_override = False
    total = 0
    for end, win in windows(events, size=8):
        total = end
        sig = signals_from_window(win)
        # Critical-error hard override: the LAST window of a run that
        # ends in a fail kind is where the fatal marker (if any) or the
        # run-terminal condition itself lives. We treat the final window
        # of a FAIL-outcome task as critical_error=True — this is the
        # honest per-run analogue of "the run just crashed/gave up/timed
        # out here"; Phase 1 has no per-window fail signal finer than
        # that (see SIGNAL SOURCES: no per-turn kanban event exists).
        is_last = end == len(events)
        critical = is_last and outcome_kind in FAIL_KINDS
        if critical:
            had_override = True
        sig = TurnSignals(
            severity=sig.severity,
            spinning=sig.spinning,
            exploring=sig.exploring,
            production_intensity=sig.production_intensity,
            critical_error=critical,
        )
        verdict = score_window(sig)
        for t in thresholds:
            if first_flag[t] is None and verdict.would_escalate(t):
                first_flag[t] = end
    return TaskVerdictTrace(
        task_id=task_id,
        board=board,
        outcome=outcome_kind,
        total_windows=total,
        first_flag_window=first_flag,
        had_critical_override=had_override,
    )


def run_offline(board: Optional[str], thresholds: list[float]) -> list[TaskVerdictTrace]:
    results: list[TaskVerdictTrace] = []
    for db_path in board_dbs(board):
        b = db_path.parent.name
        logs_dir = db_path.parent / "logs"
        if not logs_dir.exists():
            continue
        outcomes = load_task_outcomes(db_path)
        for task_id, info in outcomes.items():
            log_path = logs_dir / f"{task_id}.log"
            if not log_path.exists():
                continue
            trace = evaluate_task(b, task_id, info["kind"], log_path, thresholds)
            if trace is not None:
                results.append(trace)
    return results


def format_report(results: list[TaskVerdictTrace], thresholds: list[float]) -> str:
    lines = []
    lines.append("# ST-13 Phase 1 — stage-router observer, offline run (read-only, no routing changed)")
    lines.append("")
    lines.append(f"Cards evaluated: {len(results)} (must have a worker log AND a terminal task_event)")
    lines.append("")
    header = "| task | board | outcome | tool-call windows | " + " | ".join(f"flag@{t:.2f}" for t in thresholds) + " |"
    sep = "|---" * (3 + len(thresholds)) + "|"
    lines.append(header)
    lines.append(sep)
    fail_rows = [r for r in results if r.outcome in FAIL_KINDS]
    pass_rows = [r for r in results if r.outcome in PASS_KINDS]
    for r in sorted(results, key=lambda r: (r.outcome not in FAIL_KINDS, r.task_id)):
        flags = []
        for t in thresholds:
            fw = r.first_flag_window.get(t)
            if fw is None:
                flags.append("never")
            else:
                lead = r.total_windows - fw
                flags.append(f"w{fw} ({lead} before end)")
        lines.append(f"| {r.task_id} | {r.board} | {r.outcome} | {r.total_windows} | " + " | ".join(flags) + " |")

    lines.append("")
    lines.append("## Summary")
    lines.append(f"- FAIL-outcome cards (crashed/timed_out/gave_up/protocol_violation/block_loop_detected): {len(fail_rows)}")
    lines.append(f"- PASS-outcome cards (completed): {len(pass_rows)}")
    for t in thresholds:
        fail_flagged = sum(1 for r in fail_rows if r.first_flag_window.get(t) is not None)
        pass_flagged = sum(1 for r in pass_rows if r.first_flag_window.get(t) is not None)
        lines.append(
            f"- threshold {t:.2f}: flagged {fail_flagged}/{len(fail_rows)} FAIL cards, "
            f"{pass_flagged}/{len(pass_rows)} PASS cards (false-positive rate on this sample)"
        )
    lines.append("")
    lines.append(
        "NOTE: 'critical_error' is asserted only on the FINAL window of a FAIL-outcome "
        "task in this offline replay (see evaluate_task docstring) — every FAIL card "
        "is flagged at its own last window by construction. The number that matters is "
        "how much EARLIER (lead columns above) a non-override signal (severity/spinning/"
        "exploring outweighing production_intensity) would have flagged it, since a "
        "same-window flag carries no warning value."
    )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--board", default=None, help="Restrict to one board (default: all boards)")
    ap.add_argument(
        "--thresholds", default="0.46,0.5,0.76",
        help="Comma-separated candidate thresholds to LOG verdicts at (not a routing decision — see HARD RULES)",
    )
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the markdown report")
    ap.add_argument("--out", default=None, help="Write report to this path instead of stdout")
    args = ap.parse_args()

    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    results = run_offline(args.board, thresholds)

    if args.json:
        payload = [
            {
                "task_id": r.task_id,
                "board": r.board,
                "outcome": r.outcome,
                "total_windows": r.total_windows,
                "first_flag_window": {str(t): w for t, w in r.first_flag_window.items()},
                "had_critical_override": r.had_critical_override,
            }
            for r in results
        ]
        out = json.dumps(payload, indent=2)
    else:
        out = format_report(results, thresholds)

    if args.out:
        Path(args.out).write_text(out + "\n")
    else:
        print(out)


if __name__ == "__main__":
    main()
