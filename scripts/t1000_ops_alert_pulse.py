#!/usr/bin/env python3
"""T1000 ops alert pulse — no-agent cron script.

Watches human-visible Distillery residuals:
  - ~/.t1000/failover/sustained-failover-alert.json  (P2 model failover)
  - ~/.t1000/reconciler/last-alert.json              (P0 unrepaired drift)

Prints a short Telegram message only when something NEW or CHANGED is present.
Empty stdout = silent (cron no_agent delivery stays quiet).

State: ~/.t1000/cache/ops-alert-pulse-state.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
STATE_PATH = HOME / "cache" / "ops-alert-pulse-state.json"
ALERTS = [
    ("model_failover", HOME / "failover" / "sustained-failover-alert.json"),
    ("reconciler", HOME / "reconciler" / "last-alert.json"),
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
