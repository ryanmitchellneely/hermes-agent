#!/usr/bin/env python3
"""T1000 ops alert pulse — no-agent cron script.

Watches human-visible Distillery residuals:
  - ~/.t1000/failover/sustained-failover-alert.json  (P2 model failover)
  - ~/.t1000/reconciler/last-alert.json              (P0 unrepaired drift)

Also piggybacks read-only clone freshness (Track C pattern — ride this proven
30m cadence; do not author a naked new cron):
  - runs ~/.t1000/scripts/refresh_readonly_clones.py
  - surfaces its WARN stdout + a stale-heartbeat check

Prints a short Telegram message only when something NEW or CHANGED is present.
Empty stdout = silent (cron no_agent delivery stays quiet).

State: ~/.t1000/cache/ops-alert-pulse-state.json
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
# Desk-rooted paths: this script lives at <desk>/scripts/; clone refresh and
# heartbeats must hit the desk even when a profile sets HERMES_HOME to
# ~/.t1000/profiles/<name>.
_SCRIPT_DESK = Path(__file__).resolve().parent.parent
DESK = _SCRIPT_DESK if (_SCRIPT_DESK / "scripts").is_dir() else HOME
STATE_PATH = DESK / "cache" / "ops-alert-pulse-state.json"
READONLY_CLONE_SCRIPT = DESK / "scripts" / "refresh_readonly_clones.py"
READONLY_CLONE_HB = DESK / "cache" / "readonly-clones-heartbeat.json"
# If the clone heartbeat is older than this after a refresh attempt, WARN.
READONLY_CLONE_STALE_SECS = int(os.environ.get("READONLY_CLONE_STALE_SECS") or 2 * 3600)
# Failure-playbook retrieval sweep (t_c3a4b01d) — same Track C piggyback:
# comments known-failure diagnoses onto blocked/crashed cards; its stdout
# (hits + stale-entry warns) is a Telegram-worthy surface.
PLAYBOOK_SWEEP_SCRIPT = DESK / "scripts" / "playbook_sweep.py"
# Checkout-flipper guard (t_7f340677 / PB-003): the T1000 checkout has been
# silently flipped to main at least once, degrading the running gateway on
# its next restart (dsh seam absent, wrong dispatcher). The flipper is still
# unidentified — until it is, verify the branch mechanically every pulse
# instead of relying on the "check before/after restarts" human habit.
T1000_CHECKOUT = Path(
    os.environ.get("T1000_CHECKOUT", Path.home() / "Documents" / "T1000")
)
T1000_EXPECTED_BRANCH = os.environ.get("T1000_EXPECTED_BRANCH", "ryan/herald-0.20-cutover")
T1000_SEAM_FILE = "hermes_cli/kanban_db.py"
T1000_SEAM_MARKER = "_profile_worker_command"
ALERTS = [
    ("model_failover", DESK / "failover" / "sustained-failover-alert.json"),
    ("reconciler", DESK / "reconciler" / "last-alert.json"),
]


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fp(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw.strip():
        return None
    return hashlib.sha256(raw).hexdigest()[:16]


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"raw": data}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "path": str(path)}


def _summarize(kind: str, path: Path) -> str:
    d = _load_json(path)
    if kind == "model_failover":
        pref = d.get("preferred_provider") or "?"
        active = d.get("active_provider") or "?"
        elapsed = d.get("elapsed_sec")
        msg = d.get("message") or "sustained model failover"
        mins = f"{float(elapsed)/60:.0f}m" if isinstance(elapsed, (int, float)) else "?"
        return (
            f"🔴 MODEL FAILOVER sustained\n"
            f"preferred={pref} active={active} elapsed≈{mins}\n"
            f"{msg}\n"
            f"file: {path}"
        )
    # reconciler
    status = d.get("status") or d.get("message") or "reconciler alert"
    refused = d.get("refused")
    drifted = d.get("drifted")
    detail = d.get("message") or d.get("reason") or json.dumps(
        {k: d.get(k) for k in list(d)[:8]}, default=str
    )[:400]
    return (
        f"🟠 RECONCILER alert\n"
        f"status={status} refused={refused} drifted={drifted}\n"
        f"{detail}\n"
        f"file: {path}"
    )


def _refresh_readonly_clones() -> list[str]:
    """Best-effort Track C piggyback. Never raises. Returns WARN lines."""
    warns: list[str] = []
    if not READONLY_CLONE_SCRIPT.is_file():
        return warns
    try:
        r = subprocess.run(
            [sys.executable, str(READONLY_CLONE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        out = (r.stdout or "").strip()
        if out:
            warns.append(out)
        if r.returncode not in (0, None) and not out:
            warns.append(
                f"WARN readonly-clone refresh rc={r.returncode}: "
                f"{(r.stderr or '')[-300:]}"
            )
    except Exception as exc:  # noqa: BLE001 — ops pulse must still run
        warns.append(f"WARN readonly-clone refresh error: {type(exc).__name__}: {exc}")

    # Stale heartbeat surface: silently-never-running defeats the check.
    try:
        if not READONLY_CLONE_HB.is_file():
            warns.append(
                f"WARN readonly-clone heartbeat missing at {READONLY_CLONE_HB} "
                f"— refresh did not write a heartbeat"
            )
        else:
            age = time.time() - READONLY_CLONE_HB.stat().st_mtime
            if age > READONLY_CLONE_STALE_SECS:
                warns.append(
                    f"WARN readonly-clone heartbeat STALE age={int(age)}s "
                    f"(limit {READONLY_CLONE_STALE_SECS}s) at {READONLY_CLONE_HB}"
                )
            hb = _load_json(READONLY_CLONE_HB)
            status = hb.get("status")
            if status in ("fail", "degraded"):
                # Dedup against identical content via fps below when possible;
                # always include status transition text here if refresh was quiet.
                if not any("readonly-clone" in w or "dsh deploy" in w for w in warns):
                    warns.append(
                        f"WARN readonly-clone heartbeat status={status} ts={hb.get('ts')}"
                    )
    except Exception as exc:  # noqa: BLE001
        warns.append(f"WARN readonly-clone heartbeat read error: {exc}")
    return warns


def _playbook_sweep() -> list[str]:
    """Failure-playbook retrieval sweep (t_c3a4b01d). Best-effort, never raises.

    The sweep comments PLAYBOOK HITs onto blocked/crashed cards itself and
    dedupes internally (its own state file), so lines returned here are only
    NEW hits and stale-entry warns — exactly what deserves a Telegram line.
    """
    warns: list[str] = []
    if not PLAYBOOK_SWEEP_SCRIPT.is_file():
        return warns
    try:
        r = subprocess.run(
            [sys.executable, str(PLAYBOOK_SWEEP_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        out = (r.stdout or "").strip()
        if out:
            warns.append(out)
        if r.returncode not in (0, None) and not out:
            warns.append(
                f"WARN playbook sweep rc={r.returncode}: {(r.stderr or '')[-300:]}"
            )
    except Exception as exc:  # noqa: BLE001 — ops pulse must still run
        warns.append(f"WARN playbook sweep error: {type(exc).__name__}: {exc}")
    return warns


def _k2_intake() -> list[str]:
    """K2 health-checker findings → parked kanban cards (t_f3dd22e3).

    The script self-throttles to ~6h internally, so riding the 30m pulse
    costs nothing between real runs. Its stdout (new cards, count changes,
    cleared findings) is the Telegram surface.
    """
    warns: list[str] = []
    script = DESK / "scripts" / "k2_intake_sync.py"
    if not script.is_file():
        return warns
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        out = (r.stdout or "").strip()
        if out:
            warns.append(out)
        if r.returncode not in (0, None) and not out:
            warns.append(f"WARN k2-intake rc={r.returncode}: {(r.stderr or '')[-300:]}")
    except Exception as exc:  # noqa: BLE001 — ops pulse must still run
        warns.append(f"WARN k2-intake error: {type(exc).__name__}: {exc}")
    return warns


def _checkout_guard() -> list[str]:
    """Detect the still-unidentified checkout-flipper mechanically (PB-003)."""
    warns: list[str] = []
    try:
        r = subprocess.run(
            ["git", "-C", str(T1000_CHECKOUT), "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        branch = (r.stdout or "").strip()
        if r.returncode != 0:
            warns.append(f"WARN checkout guard: git failed rc={r.returncode}")
        elif branch != T1000_EXPECTED_BRANCH:
            warns.append(
                f"WARN T1000 CHECKOUT FLIPPED: on {branch!r}, expected "
                f"{T1000_EXPECTED_BRANCH!r} — the running gateway degrades on its "
                f"next restart (PB-003 / t_7f340677). Do NOT restart before "
                f"restoring; check for uncommitted work first."
            )
        seam = T1000_CHECKOUT / T1000_SEAM_FILE
        if seam.is_file() and T1000_SEAM_MARKER not in seam.read_text(
            encoding="utf-8", errors="replace"
        ):
            warns.append(
                f"WARN T1000 checkout lacks {T1000_SEAM_MARKER} in "
                f"{T1000_SEAM_FILE} — dsh worker_command seam absent on disk"
            )
    except Exception as exc:  # noqa: BLE001 — ops pulse must still run
        warns.append(f"WARN checkout guard error: {type(exc).__name__}: {exc}")
    return warns


def _fleet_liveness() -> list[str]:
    """Alert on silently-broken automation: erroring active crons and stale
    always-fresh surfaces. Every threshold is ~2.5x the expected cadence so a
    single slow run never pages.
    """
    warns: list[str] = []
    now = time.time()
    # (a) enabled cron jobs whose most recent run failed
    try:
        jobs = json.loads((HOME / "cron" / "jobs.json").read_text(encoding="utf-8"))
        for j in jobs.get("jobs") or []:
            if not j.get("enabled"):
                continue
            status = (j.get("last_status") or "").lower()
            if status and status not in ("ok", "success", "completed"):
                err = (j.get("last_error") or "").strip().splitlines()[:1]
                warns.append(
                    f"WARN cron '{j.get('name')}' last run {status}"
                    + (f": {err[0][:120]}" if err else "")
                )
    except Exception as exc:
        warns.append(f"WARN cron-registry read error: {type(exc).__name__}: {exc}")
    # (b) fleet status page must regenerate every 60s (t1000-fleetpage.timer)
    try:
        page = Path("/opt/t1000/fleetpage/www/index.html")
        if page.exists():
            age = now - page.stat().st_mtime
            if age > 300:
                warns.append(f"WARN fleet page STALE: last generated {age/60:.0f}m ago (expect 1m)")
        else:
            warns.append("WARN fleet page missing: /opt/t1000/fleetpage/www/index.html")
    except Exception as exc:
        warns.append(f"WARN fleet-page check error: {type(exc).__name__}: {exc}")
    # (c) gateway heartbeat file (written by the gateway itself)
    try:
        hb = HOME / "state" / "gateway.heartbeat"
        if hb.exists() and now - hb.stat().st_mtime > 900:
            warns.append(
                f"WARN gateway heartbeat stale: {(now - hb.stat().st_mtime)/60:.0f}m "
                "(if you are reading this the cron scheduler still runs — check dispatcher/telegram)"
            )
    except Exception as exc:
        warns.append(f"WARN gateway-heartbeat check error: {type(exc).__name__}: {exc}")
    return warns


def main() -> int:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev: dict = {}
    if STATE_PATH.exists():
        try:
            prev = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    lines: list[str] = []
    new_state: dict = {"ts": _iso(), "fps": {}}

    # Track C piggyback: refresh ~/.t1000/src/* before residual checks.
    clone_warns = _refresh_readonly_clones()
    clone_blob = "\n".join(clone_warns).strip()
    clone_fp = (
        hashlib.sha256(clone_blob.encode()).hexdigest()[:16] if clone_blob else None
    )
    new_state["fps"]["readonly_clones"] = clone_fp
    old_clone_fp = (prev.get("fps") or {}).get("readonly_clones")
    if clone_fp and clone_fp != old_clone_fp:
        lines.append(clone_blob)

    # Playbook retrieval sweep (t_c3a4b01d): same fingerprint dedup so a
    # persistent stale-entry WARN notifies once per content, not every 30m.
    pb_warns = _playbook_sweep()
    pb_blob = "\n".join(pb_warns).strip()
    pb_fp = hashlib.sha256(pb_blob.encode()).hexdigest()[:16] if pb_blob else None
    new_state["fps"]["playbook_sweep"] = pb_fp
    old_pb_fp = (prev.get("fps") or {}).get("playbook_sweep")
    if pb_fp and pb_fp != old_pb_fp:
        lines.append(pb_blob)

    # K2 intake bridge (t_f3dd22e3): same fp dedup; the script also
    # self-throttles internally so most pulses are a no-op.
    ki_warns = _k2_intake()
    ki_blob = "\n".join(ki_warns).strip()
    ki_fp = hashlib.sha256(ki_blob.encode()).hexdigest()[:16] if ki_blob else None
    new_state["fps"]["k2_intake"] = ki_fp
    old_ki_fp = (prev.get("fps") or {}).get("k2_intake")
    if ki_fp and ki_fp != old_ki_fp:
        lines.append(ki_blob)

    # Checkout-flipper guard (PB-003): a flip is urgent — same fp dedup so a
    # sustained flip notifies once per content, not every 30m.
    guard_warns = _checkout_guard()
    guard_blob = "\n".join(guard_warns).strip()
    guard_fp = (
        hashlib.sha256(guard_blob.encode()).hexdigest()[:16] if guard_blob else None
    )
    new_state["fps"]["checkout_guard"] = guard_fp
    old_guard_fp = (prev.get("fps") or {}).get("checkout_guard")
    if guard_fp and guard_fp != old_guard_fp:
        lines.append(guard_blob)

    # Fleet liveness (Ryan directive 2026-08-20: "make this so it doesn't stop
    # working and alerts us if it does"): erroring crons + stale surfaces were
    # invisible unless someone ran `hermes cron list`. Same fp dedup.
    fl_warns = _fleet_liveness()
    fl_blob = "\n".join(fl_warns).strip()
    fl_fp = hashlib.sha256(fl_blob.encode()).hexdigest()[:16] if fl_blob else None
    new_state["fps"]["fleet_liveness"] = fl_fp
    old_fl_fp = (prev.get("fps") or {}).get("fleet_liveness")
    if fl_fp and fl_fp != old_fl_fp:
        lines.append(fl_blob)

    for kind, path in ALERTS:
        fp = _fp(path)
        new_state["fps"][kind] = fp
        old_fp = (prev.get("fps") or {}).get(kind)
        if fp is None:
            continue  # clear / missing — silent
        if fp == old_fp:
            continue  # already notified this content
        lines.append(_summarize(kind, path))

    STATE_PATH.write_text(json.dumps(new_state, indent=2) + "\n", encoding="utf-8")

    if not lines:
        return 0  # silent

    body = "T1000 ops alert pulse\n\n" + "\n\n".join(lines)
    body += "\n\n(clear the json file or fix root cause; next change re-notifies)"
    sys.stdout.write(body + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
