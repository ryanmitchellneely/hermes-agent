#!/usr/bin/env python3
"""One weekly page answering "how is the fleet's model economy going" (t_da2f74c4).

Ryan's failure mode this closes: "not seeing what is happening, then reacting
later." Today that question needs four separate instruments read by hand —
``telemetry_digest.py``, the kanban escalation tables, the K2 spend pulse (a
Telegram-only push, not a dashboard), and the DevBot sweep ledger. This script
is the fifth thing: one reader over the other four, published as a static page
whose own staleness is what pages (via the freshness table + heartbeat below),
not a fifth thing to remember to check.

Counting only. No caps, no blocks, no judgment calls about what is "too much"
— that policy question belongs elsewhere; this just answers "what happened."

Inputs (each probed independently; a missing/unreadable input degrades to
"unavailable" in its own row rather than crashing the whole page):

  1. T1000 telemetry store (``model_calls-YYYY-MM-DD.jsonl``) — calls/tokens
     by cost class (local/subscription/metered/unknown), reusing the exact
     classification ``telemetry_digest.py`` / ``telemetry_query.py`` already
     use (``classify_provider``, ``iter_records``, ``telemetry_dir``) rather
     than inventing a second one.
  2. Kanban escalations (``task_events`` kind=``model_escalated``) and
     ``task_runs`` resolution, across every board's ``kanban.db``.
  3. K2 hub metered spend (``llm_routing_decisions``) — falls back to
     "unavailable" with a stated reason when ``t1000`` cannot open the DB
     (measured: it cannot — see the freshness note this script emits).
  4. DevBot lane: the sweep ledger + lane PR stats (opened/merged/closed,
     time-to-first-verdict, open PRs with zero verdict) via the GitHub REST
     API, authenticated by minting a short-lived token the same way
     ``k2_intake_sync.py`` already does (borrowed, revoked after use, never
     printed).
  5. Freshness lines for the local-savings ledger and the distillery-intake
     sweep state, so the page can say "the local-savings numbers are 3 days
     stale" instead of silently presenting a number nobody re-checked lately.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import statistics
import sys
import types
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Reused, not reinvented: the store-reading + cost-classification primitives
# telemetry_digest.py / telemetry_query.py already carry. See their own
# docstrings for why local/subscription/metered/unknown is derived from
# provider identity and never guessed.
from telemetry_query import iter_records, telemetry_dir  # noqa: E402
from telemetry_digest import (  # noqa: E402
    classify_provider,
    load_provider_class_map,
    SUMMABLE_TOKEN_FIELDS,
)

UTC = timezone.utc

HEARTBEAT_SYSTEM = "fleet-economics-weekly"

GITHUB_API = "https://api.github.com"
GITHUB_REPO = os.environ.get("FLEET_ECON_GITHUB_REPO", "joinsov/kevin-real-estate-tools")
LANE_APP_AUTHOR = os.environ.get("FLEET_ECON_LANE_AUTHOR", "app/k2-dsh-lane")

DEFAULT_KANBAN_BOARDS_DIR = Path(
    os.environ.get("T1000_KANBAN_BOARDS_DIR", "/opt/t1000/home/kanban/boards")
)
DEFAULT_K2_HUB_DB = Path(
    os.environ.get("K2_HUB_DB", "/opt/k2-hub/k2-hub/k2-hub.db")
)
# k2-hub's own read path for spend (verified live, round 2): GET on this
# localhost port+prefix returns lighthouse_api._spend_summary()'s JSON
# (last_7d_usd, by_model_7d, ...). Gated by a bearer named one of
# K2_HUB_SPEND_TOKEN_ENV_NAMES, sourced from K2_HUB_ENV_PATH — which is
# `-rw-r----- root:k2hub`, unreadable by t1000 (measured; do not chmod it).
K2_HUB_ENV_PATH = Path(os.environ.get("K2_HUB_ENV_PATH", "/etc/k2-hub.env"))
K2_HUB_SPEND_PORT = int(os.environ.get("K2_HUB_PORT", "8000"))
K2_HUB_SPEND_URL_TEMPLATE = os.environ.get(
    "K2_HUB_SPEND_URL", "http://127.0.0.1:{port}/api/v1/llm-spend"
)
K2_HUB_SPEND_TOKEN_ENV_NAMES = ("LIGHTHOUSE_API_TOKEN", "LIGHTHOUSE_ADMIN_API_TOKEN")
DEFAULT_SWEEP_LEDGER = Path(
    os.environ.get(
        "SWEEP_LEDGER_PATH",
        "/opt/t1000/home/src/kevin-real-estate-tools/docs/agent-coordination/devbot/SWEEP-LEDGER.md",
    )
)
# Live desk (HERMES_HOME-rooted) savings series — NOT the
# /opt/t1000/home/telemetry/savings/ tree, which is the frozen pre-fix dir
# (round 2 correction; see _resolve_telemetry_dir below for the same fix
# applied to the telemetry store itself).
DEFAULT_SAVINGS_SERIES = Path(
    os.environ.get(
        "SAVINGS_SERIES_PATH", "/opt/t1000/home/.t1000/telemetry/savings/series.jsonl"
    )
)
DEFAULT_DISTILLERY_STATE = Path(
    os.environ.get(
        "DISTILLERY_STATE_PATH", "/opt/t1000/home/cache/distillery-intake-sweep-state.json"
    )
)
DEFAULT_HEARTBEAT_PATH = Path(
    os.environ.get(
        "FLEET_ECON_HEARTBEAT_PATH",
        "/opt/t1000/home/cache/fleet-economics-weekly-heartbeat.json",
    )
)
DEFAULT_K2_INTAKE_SYNC_PATH = Path(
    os.environ.get("K2_INTAKE_SYNC_PATH", "/opt/t1000/home/scripts/k2_intake_sync.py")
)
# Live-desk (HERMES_HOME-rooted) fleetpage path, per captain's round-2
# instruction — round 1 used /opt/t1000/fleetpage/www/devbot/ (the tree that
# already existed, under bare Path.home()); this is the one under the live
# desk tree, created fresh by this script/captain rather than pre-existing.
DEFAULT_OUT_DIR = Path(
    os.environ.get("FLEET_ECON_OUT_DIR", "/opt/t1000/home/fleetpage/www/devbot/economics")
)

STALE_TELEMETRY_SECONDS = 6 * 3600
STALE_KANBAN_SECONDS = 24 * 3600
STALE_SWEEP_SECONDS = 9 * 86400  # a weekly ledger; one missed week is still ok
STALE_SAVINGS_SECONDS = 2 * 86400
STALE_DISTILLERY_SECONDS = 13 * 3600


# ── ISO week handling ───────────────────────────────────────────────────────


def parse_iso_week(text: Optional[str], *, today: Optional[date] = None) -> tuple[date, date, str]:
    """(week_start_monday, week_end_exclusive, "YYYY-Www") for *text* or the
    current ISO week when *text* is None."""
    today = today or datetime.now(UTC).date()
    if text:
        match = re.match(r"^(\d{4})-W(\d{2})$", text.strip(), re.IGNORECASE)
        if not match:
            raise argparse.ArgumentTypeError(
                f"--week wants YYYY-Www (e.g. 2026-W36), got {text!r}"
            )
        iso_year, iso_week = int(match.group(1)), int(match.group(2))
    else:
        iso_year, iso_week, _ = today.isocalendar()
    week_start = date.fromisocalendar(iso_year, iso_week, 1)
    week_end = week_start + timedelta(days=7)
    return week_start, week_end, f"{iso_year}-W{iso_week:02d}"


def _dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _fmt_ts(value: Optional[datetime]) -> str:
    if value is None:
        return "-"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _status(newest: Optional[datetime], now: datetime, stale_after_seconds: float) -> str:
    if newest is None:
        return "UNAVAILABLE"
    age = (now - newest).total_seconds()
    return "ok" if age <= stale_after_seconds else "STALE"


# ── 1. telemetry store ──────────────────────────────────────────────────────


def _resolve_telemetry_dir() -> Path:
    """The live desk's telemetry root — round-2 fix (captain-caught defect 1).

    ``telemetry_query.telemetry_dir()`` only honors ``T1000_TELEMETRY_DIR``
    then ``HERMES_REAL_HOME``, falling back to ``Path.home()``. This repo's
    own crons (``t1000_ops_alert_pulse.py``) key off ``HERMES_HOME`` instead —
    a DIFFERENT env var name — and ``t1000``'s OS-level home is bare
    ``/opt/t1000`` (confirmed via ``getent passwd t1000``), not
    ``/opt/t1000/home``. Calling the library function directly with only
    ``HERMES_HOME`` set (no ``T1000_TELEMETRY_DIR`` override) therefore
    silently resolved to ``/opt/t1000/.t1000/telemetry`` — a stale/empty path
    — exactly what the captain's verification run hit. Honor ``HERMES_HOME``
    ourselves before falling through to the library's own chain.
    """
    override = os.environ.get("T1000_TELEMETRY_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    home = (os.environ.get("HERMES_REAL_HOME") or os.environ.get("HERMES_HOME") or "").strip()
    if home:
        return Path(home).expanduser() / ".t1000" / "telemetry"
    return telemetry_dir()


def telemetry_summary(
    week_start: datetime, week_end: datetime, *, now: datetime, tel_dir: Optional[Path] = None
) -> tuple[dict, dict]:
    root = tel_dir if tel_dir is not None else _resolve_telemetry_dir()
    class_map = load_provider_class_map(root / "provider_classes.json")

    since_ms = int(week_start.timestamp() * 1000)
    until_ms = int(week_end.timestamp() * 1000)

    calls_by_class: Counter[str] = Counter()
    tokens_by_class: Counter[str] = Counter()
    calls_by_provider: Counter[str] = Counter()
    newest_ms: Optional[int] = None

    for record in iter_records(root, since_ms, until_ms):
        provider = str(record.get("provider") or "")
        cost_class = classify_provider(provider, class_map)
        calls_by_class[cost_class] += 1
        calls_by_provider[provider or "unknown"] += 1
        if record.get("tokens_available") is True:
            total = record.get("total_tokens")
            if isinstance(total, (int, float)):
                tokens_by_class[cost_class] += int(total)
        stamp = record.get("ts_epoch_ms")
        if isinstance(stamp, (int, float)):
            newest_ms = stamp if newest_ms is None else max(newest_ms, int(stamp))

    # Store-wide freshness (not window-limited): the newest record in the
    # store at all, so a page run mid-week still reports "is the pipe alive"
    # rather than "is this week's data complete".
    store_newest_ms = _latest_telemetry_record_ts(root)
    newest_dt = (
        datetime.fromtimestamp(store_newest_ms / 1000, tz=UTC) if store_newest_ms else None
    )

    metrics = {
        "calls_by_class": dict(calls_by_class),
        "tokens_by_class": dict(tokens_by_class),
        "calls_by_provider": dict(calls_by_provider),
    }
    freshness = {
        "ok": newest_dt is not None,
        "newest": _fmt_ts(newest_dt),
        "status": _status(newest_dt, now, STALE_TELEMETRY_SECONDS),
        "note": f"store={root}",
    }
    return metrics, freshness


def _latest_telemetry_record_ts(root: Path) -> Optional[int]:
    """Newest ``ts_epoch_ms`` in the store, cheaply (last line of the newest file)."""
    if not root.is_dir():
        return None
    files = sorted(root.glob("model_calls-*.jsonl"))
    if not files:
        return None
    try:
        with open(files[-1], "r", encoding="utf-8", errors="replace") as handle:
            lines = [line for line in handle if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        stamp = record.get("ts_epoch_ms")
        if isinstance(stamp, (int, float)):
            return int(stamp)
    return None


# ── 2. kanban escalations + task_runs ───────────────────────────────────────


def kanban_summary(
    week_start: datetime, week_end: datetime, *, now: datetime, boards_dir: Optional[Path] = None
) -> tuple[dict, dict]:
    import sqlite3

    boards_dir = boards_dir if boards_dir is not None else DEFAULT_KANBAN_BOARDS_DIR
    start_epoch = int(week_start.timestamp())
    end_epoch = int(week_end.timestamp())

    escalations_by_board: Counter[str] = Counter()
    escalations_to_paid_by_board: Counter[str] = Counter()
    escalations_by_target: Counter[str] = Counter()
    runs_total_by_board: Counter[str] = Counter()
    runs_resolved_by_board: Counter[str] = Counter()
    newest_epoch: Optional[int] = None
    boards_seen = 0

    if boards_dir.is_dir():
        for db_path in sorted(boards_dir.glob("*/kanban.db")):
            board = db_path.parent.name
            # Skip non-board artifacts that happen to live under boards/ (e.g.
            # a hidden .omc/kanban.db that is not a real kanban board and
            # carries none of the expected schema — `ls` without -a hid this
            # from the initial probe; discovered when it 500'd the real run).
            # No real board name starts with '.'.
            if board.startswith("."):
                continue
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            except sqlite3.OperationalError:
                continue
            try:
                cur = conn.execute(
                    "SELECT payload, created_at FROM task_events "
                    "WHERE kind = 'model_escalated' AND created_at >= ? AND created_at < ?",
                    (start_epoch, end_epoch),
                )
                for payload_raw, created_at in cur.fetchall():
                    escalations_by_board[board] += 1
                    newest_epoch = created_at if newest_epoch is None else max(newest_epoch, created_at)
                    try:
                        payload = json.loads(payload_raw or "{}")
                    except ValueError:
                        payload = {}
                    to_provider = str(payload.get("to_provider") or "")
                    to_model = str(payload.get("to_model") or "")
                    cost_class = classify_provider(to_provider)
                    if cost_class in ("subscription", "metered"):
                        escalations_to_paid_by_board[board] += 1
                    escalations_by_target[f"{to_provider}/{to_model}"] += 1

                cur = conn.execute(
                    "SELECT COUNT(*), "
                    "SUM(CASE WHEN resolved_provider IS NOT NULL AND resolved_provider != '' "
                    "THEN 1 ELSE 0 END), MAX(started_at) "
                    "FROM task_runs WHERE started_at >= ? AND started_at < ?",
                    (start_epoch, end_epoch),
                )
                total, resolved, max_started = cur.fetchone()
                runs_total_by_board[board] = total or 0
                runs_resolved_by_board[board] = resolved or 0
                if max_started:
                    newest_epoch = max_started if newest_epoch is None else max(newest_epoch, max_started)
                boards_seen += 1
            except sqlite3.OperationalError:
                # Schema-less/foreign db under boards/ — not a real board.
                continue
            finally:
                conn.close()

    newest_dt = datetime.fromtimestamp(newest_epoch, tz=UTC) if newest_epoch else None
    metrics = {
        "escalations_by_board": dict(escalations_by_board),
        "escalations_to_paid_by_board": dict(escalations_to_paid_by_board),
        "escalations_by_target": dict(escalations_by_target),
        "runs_total_by_board": dict(runs_total_by_board),
        "runs_resolved_by_board": dict(runs_resolved_by_board),
        "boards_seen": boards_seen,
    }
    freshness = {
        "ok": boards_seen > 0,
        "newest": _fmt_ts(newest_dt),
        "status": _status(newest_dt, now, STALE_KANBAN_SECONDS),
        "note": f"{boards_seen} boards under {boards_dir}",
    }
    return metrics, freshness


# ── 3. K2 hub metered spend ─────────────────────────────────────────────────


def _read_env_file_var(path: Path, names: tuple[str, ...]) -> tuple[Optional[str], Optional[str]]:
    """(value, error_reason) for the first of *names* set in the env FILE at
    *path*. Never returns the value in the error branch, and callers must
    never log the value either — only its presence/absence."""
    try:
        text = path.read_text(encoding="utf-8")
    except PermissionError:
        return None, f"{path} unreadable by t1000 (permission denied)"
    except OSError as exc:
        return None, f"{path} unreadable ({type(exc).__name__})"
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    for name in names:
        if values.get(name):
            return values[name], None
    return None, f"none of {names} set in {path}"


def _http_get_json(url: str, token: Optional[str]) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "t1000-fleet-economics-weekly"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def k2_spend_summary(
    week_start: datetime,
    week_end: datetime,
    *,
    now: datetime,
    env_path: Optional[Path] = None,
    port: Optional[int] = None,
    http_get: Optional[Callable[[str, Optional[str]], Any]] = None,
) -> tuple[dict, dict]:
    """K2 metered spend via the hub's OWN read path (round-2 fix, defect 2).

    The production db (``/opt/k2-hub/k2-hub/k2-hub.db``) is ``0600
    k2hub:k2hub`` — unreadable by ``t1000``, and permissions on it are never
    changed to work around that. ``llm_spend_pulse`` has no readable file
    output either (Telegram + the same restricted DB only). What DOES exist:
    ``lighthouse_api.llm_spend()`` — ``GET /api/v1/llm-spend`` on the hub's
    own localhost port, mirroring ``_spend_summary()`` (``last_7d_usd``,
    ``by_model_7d``, ...). It is token-gated by ``LIGHTHOUSE_API_TOKEN`` (or
    the admin token), sourced from ``/etc/k2-hub.env`` — which is ``0640
    root:k2hub``, ALSO unreadable by ``t1000`` (measured). So this is
    genuinely unavailable to this script, and the honest report says so with
    the reason, rather than guessing or leaving the old DB error in place.
    """
    env_path = env_path if env_path is not None else K2_HUB_ENV_PATH
    port = port if port is not None else K2_HUB_SPEND_PORT
    fetch = http_get if http_get is not None else _http_get_json

    token = None
    reason = None
    if http_get is None:
        # Real runs source the bearer from the unit's own env file; tests
        # inject http_get directly and skip this (a fake fetch needs no
        # real token — see test_t1000_fleet_economics_weekly.py).
        token, reason = _read_env_file_var(env_path, K2_HUB_SPEND_TOKEN_ENV_NAMES)
        if token is None:
            return (
                {"available": False, "total_usd": None, "top_models": []},
                {
                    "ok": False,
                    "newest": "-",
                    "status": "UNAVAILABLE",
                    "note": (
                        f"k2-hub's own read path is GET /api/v1/llm-spend "
                        f"(lighthouse_api.llm_spend -> _spend_summary()), gated by a "
                        f"bearer named one of {K2_HUB_SPEND_TOKEN_ENV_NAMES} sourced "
                        f"from {env_path}; {reason}. The production db "
                        f"({DEFAULT_K2_HUB_DB}) is separately unreadable by t1000 too "
                        f"(0600 k2hub:k2hub) — neither path works, and neither's "
                        f"permissions were changed to make it work."
                    ),
                },
            )

    url = K2_HUB_SPEND_URL_TEMPLATE.format(port=port)
    try:
        data = fetch(url, token) or {}
    except Exception as exc:
        return (
            {"available": False, "total_usd": None, "top_models": []},
            {
                "ok": False,
                "newest": "-",
                "status": "UNAVAILABLE",
                "note": f"GET {url} failed: {type(exc).__name__}: {exc}",
            },
        )

    total_usd = data.get("last_7d_usd")
    by_model = sorted(
        (data.get("by_model_7d") or []), key=lambda row: -(row.get("cost") or 0)
    )[:5]
    metrics = {
        "available": total_usd is not None,
        "total_usd": round(total_usd, 4) if isinstance(total_usd, (int, float)) else None,
        "top_models": [
            {
                "model_id": row.get("key"),
                "usd": round(row.get("cost") or 0.0, 4),
                "calls": row.get("calls"),
            }
            for row in by_model
        ],
    }
    freshness = {
        "ok": metrics["available"],
        "newest": _fmt_ts(now) if metrics["available"] else "-",
        "status": "ok" if metrics["available"] else "UNAVAILABLE",
        "note": (
            f"{url} (its own rolling 7d-as-of-call-time window per "
            "_spend_summary(), not this page's Monday-aligned ISO week)"
        ),
    }
    return metrics, freshness


# ── 4. DevBot sweep ledger ──────────────────────────────────────────────────

_SWEEP_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.+)\|\s*$")


def sweep_ledger_summary(
    week_start: datetime, week_end: datetime, *, now: datetime, ledger_path: Optional[Path] = None
) -> tuple[dict, dict]:
    ledger_path = ledger_path if ledger_path is not None else DEFAULT_SWEEP_LEDGER
    rows_in_window = 0
    qualifies_yes = 0
    newest_dt: Optional[datetime] = None

    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _SWEEP_ROW.match(line.strip())
            if not match:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 7:
                continue
            pr, merged_at = cells[0], cells[1]
            qualifies = cells[6].lower()
            try:
                merged_dt = datetime.fromisoformat(merged_at).replace(tzinfo=UTC)
            except ValueError:
                continue
            newest_dt = merged_dt if newest_dt is None else max(newest_dt, merged_dt)
            if week_start <= merged_dt < week_end:
                rows_in_window += 1
                if qualifies == "yes":
                    qualifies_yes += 1

    metrics = {
        "rows_in_window": rows_in_window,
        "qualifies_yes": qualifies_yes,
    }
    freshness = {
        "ok": ledger_path.is_file(),
        "newest": _fmt_ts(newest_dt),
        "status": _status(newest_dt, now, STALE_SWEEP_SECONDS),
        "note": f"{ledger_path}",
    }
    return metrics, freshness


# ── 5. DevBot lane PR stats (GitHub REST, App-token minted like k2_intake_sync) ──


def _load_k2_intake_sync(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("k2_intake_sync_for_econ", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load k2_intake_sync from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mint_lane_token(sync_path: Path) -> tuple[Optional[types.ModuleType], Optional[str]]:
    """Borrow the dsh lane's own installation token, exactly the way
    ``k2_intake_sync._mint_bot_token`` does it. Never logs the token."""
    try:
        module = _load_k2_intake_sync(sync_path)
        wrapper, token = module._mint_bot_token()  # noqa: SLF001
        return wrapper, token
    except Exception:
        return None, None


def _gh_http_get(url: str, token: Optional[str]) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "t1000-fleet-economics-weekly",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _percentile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    import math

    rank = max(1, math.ceil(q * len(ordered)))
    return float(ordered[min(rank, len(ordered)) - 1])


def _fetch_closed_unmerged_count(
    fetch: Callable[[str, Optional[str]], Any],
    repo: str,
    token: Optional[str],
    author: str,
    since_iso: str,
    until_iso: str,
    *,
    max_pages: int = 20,
) -> tuple[int, bool]:
    """(count, fetch_ok) of lane PRs closed WITHOUT a merge, ``closed_at`` in
    [since_iso, until_iso) — via the REST pulls list, not Search.

    Round-3 fix (captain-caught): Search's ``author:app/<slug>`` qualifier
    does not reliably match ``<slug>[bot]``-authored PRs that were closed
    without a merge event (merged ones matched fine, which is why round 2's
    ``is:closed`` minus ``is:merged`` subtraction silently looked internally
    consistent at 35 == 35 while actually missing an entire class of PRs — a
    live REST check of named PRs the captain supplied, e.g. #6131 and #5918,
    confirmed they ARE state=closed/merged_at=null/closed_at-in-window,
    authored by ``k2-dsh-lane[bot]``).

    Sorted by ``updated_at`` descending and paginated until a whole page's
    oldest ``updated_at`` predates the window start — sound because closing
    OR merging a PR always bumps ``updated_at`` to at least that moment, so
    once a full page is entirely older than the window, every later page is
    too. Measured live: 7 pages / 700 PRs covers a 7-day window on this
    repo's actual traffic; ``max_pages=20`` is headroom, not the expected
    depth.
    """
    login_prefix = author.split("/", 1)[-1].lower()  # "app/k2-dsh-lane" -> "k2-dsh-lane"
    count = 0
    any_page_ok = False
    for page in range(1, max_pages + 1):
        url = (
            f"{GITHUB_API}/repos/{repo}/pulls?state=closed&sort=updated"
            f"&direction=desc&per_page=100&page={page}"
        )
        try:
            batch = fetch(url, token) or []
        except Exception:
            batch = []
        if not batch:
            break
        any_page_ok = True
        for pr in batch:
            login = ((pr.get("user") or {}).get("login") or "").lower()
            if not login.startswith(login_prefix):
                continue
            closed_at = pr.get("closed_at") or ""
            if not (since_iso <= closed_at < until_iso):
                continue
            if not pr.get("merged_at"):
                count += 1
        oldest_updated = batch[-1].get("updated_at") or ""
        if len(batch) < 100 or (oldest_updated and oldest_updated < since_iso):
            break
    return count, any_page_ok


def lane_pr_summary(
    week_start: datetime,
    week_end: datetime,
    *,
    now: datetime,
    sync_path: Optional[Path] = None,
    gh_get: Optional[Callable[[str, Optional[str]], Any]] = None,
    repo: str = GITHUB_REPO,
    author: str = LANE_APP_AUTHOR,
) -> tuple[dict, dict]:
    sync_path = sync_path if sync_path is not None else DEFAULT_K2_INTAKE_SYNC_PATH
    fetch = gh_get if gh_get is not None else _gh_http_get

    wrapper = None
    token = None
    minted = False
    if gh_get is None:
        wrapper, token = _mint_lane_token(sync_path)
        minted = token is not None

    try:
        since_iso = week_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        until_iso = week_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        def search(q: str, *, max_pages: int = 1) -> dict:
            """One page (default) or paginated (up to *max_pages*) search,
            merging ``items`` across pages while keeping the server-reported
            ``total_count`` (itself exact regardless of pagination — only
            the ``items`` array is capped per page)."""
            all_items: list[dict] = []
            total_count = 0
            any_page_ok = False
            for page in range(1, max_pages + 1):
                url = (
                    f"{GITHUB_API}/search/issues?per_page=100&page={page}&q="
                    + urllib.request.quote(q, safe="")
                )
                try:
                    result = fetch(url, token) or {}
                except (urllib.error.URLError, urllib.error.HTTPError, Exception):
                    result = {}
                if not result:
                    break
                any_page_ok = True
                total_count = result.get("total_count", total_count)
                page_items = result.get("items") or []
                all_items.extend(page_items)
                if len(page_items) < 100:
                    break
            # Falsy on total failure (mirrors a raw failed fetch: `{}`), even
            # though a REAL zero-hit response (e.g. "0 PRs opened this week")
            # is a truthy {"total_count": 0, ...} — `fetch_ok` below needs to
            # tell those two apart, and an unconditional dict return can't.
            if not any_page_ok:
                return {}
            return {"total_count": total_count, "items": all_items}

        # Pagination cap: per_page=100 x 5 pages = 500 items, comfortably
        # above this lane's weekly volume (~60-190 measured); "opened" and
        # "open" are the two item-level lists this function itemizes (for
        # verdict-latency lookups), so those are the ones that paginate.
        opened = search(
            f"repo:{repo} is:pr author:{author} created:{since_iso}..{until_iso}",
            max_pages=5,
        )
        merged = search(
            f"repo:{repo} is:pr is:merged author:{author} merged:{since_iso}..{until_iso}"
        )
        open_now = search(f"repo:{repo} is:pr is:open author:{author}", max_pages=5)

        opened_items = opened.get("items", []) or []
        open_items = open_now.get("items", []) or []

        # "closed" via the REST pulls list, NOT the Search API (round-3 fix,
        # captain-caught defect: round 2's `is:closed closed:<range>` minus
        # `is:merged merged:<range>` measured 0 for this exact window — but a
        # live REST check of named PRs (#6131, #5918, ...) showed them
        # correctly as state=closed, merged_at=null, closed_at IN the window,
        # authored by k2-dsh-lane[bot]. Search's `author:app/<slug>`
        # qualifier does not reliably match `<slug>[bot]`-authored PRs that
        # were closed WITHOUT a merge event (merged ones matched fine, which
        # is why round 2's number silently looked internally consistent —
        # 35 == 35 — while actually missing an entire class of PRs). The
        # Pulls endpoint has no such gap. Paginated by `updated_at` desc and
        # stopped once a whole page is older than the window start, since
        # closing OR merging a PR always bumps `updated_at` to at least that
        # moment — verified live: 7 pages / 700 PRs to cover this window on
        # this repo's actual traffic.
        closed_unmerged_count, closed_fetch_ok = _fetch_closed_unmerged_count(
            fetch, repo, token, author, since_iso, until_iso
        )

        def has_verdict_comment(number: int, created_at: str) -> Optional[float]:
            """Minutes from PR creation to the first 'Verdict:' comment, or None."""
            try:
                comments = fetch(
                    f"{GITHUB_API}/repos/{repo}/issues/{number}/comments?per_page=100",
                    token,
                ) or []
            except Exception:
                return None
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            earliest = None
            for comment in comments:
                body = comment.get("body") or ""
                if "Verdict:" not in body:
                    continue
                comment_dt = datetime.fromisoformat(
                    (comment.get("created_at") or "").replace("Z", "+00:00")
                )
                if earliest is None or comment_dt < earliest:
                    earliest = comment_dt
            if earliest is None:
                return None
            return (earliest - created_dt).total_seconds() / 60.0

        latencies: list[float] = []
        for item in opened_items:
            number = item.get("number")
            created_at = item.get("created_at")
            if not number or not created_at:
                continue
            minutes = has_verdict_comment(number, created_at)
            if minutes is not None:
                latencies.append(minutes)

        zero_verdict_open = 0
        for item in open_items:
            number = item.get("number")
            created_at = item.get("created_at")
            if not number or not created_at:
                continue
            if has_verdict_comment(number, created_at) is None:
                zero_verdict_open += 1

        fetch_ok = bool(opened) or bool(merged) or bool(open_now) or closed_fetch_ok
        metrics = {
            "opened": opened.get("total_count", len(opened_items)),
            "merged": merged.get("total_count", 0),
            "closed_unmerged": closed_unmerged_count,
            # True (interpolated) median — this is a small-N weekly business
            # metric read by a human, not a latency percentile over thousands
            # of samples, so the nearest-rank convention below (kept for p90,
            # matching telemetry_digest.percentile) would make "median" read
            # as "the smaller of two samples" on a typical light week.
            "ttfv_median_min": statistics.median(latencies) if latencies else None,
            "ttfv_p90_min": _percentile(latencies, 0.9),
            "ttfv_n": len(latencies),
            "open_zero_verdict": zero_verdict_open,
        }
        freshness = {
            "ok": fetch_ok,
            "newest": _fmt_ts(now) if fetch_ok else "-",
            "status": "ok" if fetch_ok else "UNAVAILABLE",
            "note": (
                f"repo={repo} author={author}; token_minted={minted}"
                if gh_get is None
                else "fake gh_get (test)"
            ),
        }
        return metrics, freshness
    finally:
        if minted and wrapper is not None and token:
            try:
                wrapper._revoke_installation_token(token)  # noqa: SLF001
            except Exception:
                pass


# ── freshness-only inputs: local-savings ledger, distillery intake state ───


def savings_series_freshness(*, now: datetime, path: Optional[Path] = None) -> dict:
    path = path if path is not None else DEFAULT_SAVINGS_SERIES
    newest_date: Optional[date] = None
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    raw_date = row.get("date")
                    if not raw_date:
                        continue
                    try:
                        parsed = date.fromisoformat(raw_date)
                    except ValueError:
                        continue
                    newest_date = parsed if newest_date is None else max(newest_date, parsed)
        except OSError:
            pass
    newest_dt = _dt(newest_date) if newest_date else None
    return {
        "ok": newest_dt is not None,
        "newest": _fmt_ts(newest_dt),
        "status": _status(newest_dt, now, STALE_SAVINGS_SECONDS),
        "note": f"{path}",
    }


def distillery_state_freshness(*, now: datetime, path: Optional[Path] = None) -> dict:
    path = path if path is not None else DEFAULT_DISTILLERY_STATE
    newest_dt: Optional[datetime] = None
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            ts = raw.get("ts")
            if ts:
                newest_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (OSError, ValueError):
            pass
    return {
        "ok": newest_dt is not None,
        "newest": _fmt_ts(newest_dt),
        "status": _status(newest_dt, now, STALE_DISTILLERY_SECONDS),
        "note": f"{path}",
    }


# ── page rendering ───────────────────────────────────────────────────────────


def _money(value: Optional[float]) -> str:
    return f"${value:,.2f}" if isinstance(value, (int, float)) else "unavailable"


def _minutes(value: Optional[float]) -> str:
    return f"{value:.0f}m" if isinstance(value, (int, float)) else "n/a"


def _breakdown(counter: dict, limit: int = 6) -> str:
    if not counter:
        return "none"
    items = sorted(counter.items(), key=lambda kv: -kv[1])[:limit]
    return ", ".join(f"{k}: {v}" for k, v in items)


_HEADER_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*$")


def _parse_prior_header_table(text: str) -> dict[str, str]:
    """Best-effort {label: value} out of a previous week's header table."""
    values: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        if line.strip().startswith("## Header"):
            in_table = True
            continue
        if in_table and line.strip().startswith("## "):
            break
        if not in_table:
            continue
        match = _HEADER_ROW_RE.match(line.strip())
        if not match:
            continue
        label, value = match.group(1), match.group(2)
        if label.lower() in ("metric", "---"):
            continue
        values[label] = value
    return values


_LEADING_NUMBER_RE = re.compile(r"-?\$?[\d,]+(?:\.\d+)?")


def _leading_number(text: str) -> Optional[float]:
    match = _LEADING_NUMBER_RE.match(text.strip())
    if not match:
        return None
    try:
        return float(match.group(0).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def render_page(
    *,
    week_label: str,
    week_start: date,
    week_end_inclusive: date,
    generated_at: datetime,
    telemetry: tuple[dict, dict],
    kanban: tuple[dict, dict],
    k2_spend: tuple[dict, dict],
    sweep: tuple[dict, dict],
    lane_prs: tuple[dict, dict],
    savings_fresh: dict,
    distillery_fresh: dict,
    prior_page_text: Optional[str],
) -> str:
    tel_m, tel_f = telemetry
    kan_m, kan_f = kanban
    spend_m, spend_f = k2_spend
    sweep_m, sweep_f = sweep
    pr_m, pr_f = lane_prs

    local_calls = tel_m["calls_by_class"].get("local", 0)
    sub_calls_total = tel_m["calls_by_class"].get("subscription", 0)
    sub_by_provider = {
        p: n
        for p, n in tel_m["calls_by_provider"].items()
        if classify_provider(p) == "subscription"
    }

    header_rows = [
        ("Local calls (7d)", str(local_calls)),
        (
            "Subscription calls (7d) by provider",
            f"{sub_calls_total} total — {_breakdown(sub_by_provider)}",
        ),
        (
            "Escalations to paid seats (7d)",
            f"{sum(kan_m['escalations_to_paid_by_board'].values())} total — "
            f"{_breakdown(kan_m['escalations_to_paid_by_board'])}",
        ),
        ("K2 metered spend (7d)", _money(spend_m.get("total_usd")) if spend_m.get("available") else "unavailable"),
        (
            "Lane PRs opened / merged / closed (7d)",
            f"{pr_m['opened']} / {pr_m['merged']} / {pr_m['closed_unmerged']}",
        ),
        (
            "Time to first verdict (median / p90)",
            f"{_minutes(pr_m['ttfv_median_min'])} / {_minutes(pr_m['ttfv_p90_min'])} (n={pr_m['ttfv_n']})",
        ),
        ("Open lane PRs with zero verdict", str(pr_m["open_zero_verdict"])),
        (
            "DevBot sweep qualifies (7d)",
            f"{sweep_m['qualifies_yes']} of {sweep_m['rows_in_window']} rows",
        ),
    ]

    lines: list[str] = []
    lines.append(f"# Fleet economics — {week_label}")
    lines.append("")
    lines.append(
        f"Week: {week_start.isoformat()} .. {week_end_inclusive.isoformat()} "
        f"(generated {_fmt_ts(generated_at)})"
    )
    lines.append("")
    lines.append(
        "One reader over the four instruments (telemetry digest, kanban "
        "escalations, K2 spend, DevBot sweep ledger) — counting only, no "
        "caps, no blocks. See the freshness table below before trusting a "
        "number here; a page whose own inputs are stale says so."
    )
    lines.append("")
    lines.append("## Header")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    for label, value in header_rows:
        lines.append(f"| {label} | {value} |")
    lines.append("")

    lines.append("## Freshness")
    lines.append("")
    lines.append("| Input | Newest | Status |")
    lines.append("|---|---|---|")
    fresh_rows = [
        ("Telemetry store", tel_f),
        ("Kanban boards (escalations/runs)", kan_f),
        ("K2 spend (llm_routing_decisions)", spend_f),
        ("DevBot sweep ledger", sweep_f),
        ("GitHub lane PRs", pr_f),
        ("Local-savings ledger (series.jsonl)", savings_fresh),
        ("Distillery intake sweep state", distillery_fresh),
    ]
    for label, fresh in fresh_rows:
        lines.append(f"| {label} | {fresh['newest']} | {fresh['status']} |")
    lines.append("")
    for label, fresh in fresh_rows:
        if fresh.get("note"):
            lines.append(f"- {label}: {fresh['note']}")
    lines.append("")

    lines.append("## What changed vs last week")
    lines.append("")
    if prior_page_text:
        prior = _parse_prior_header_table(prior_page_text)
        any_delta = False
        for label, value in header_rows:
            prior_value = prior.get(label)
            if prior_value is None:
                continue
            cur_num = _leading_number(value)
            prior_num = _leading_number(prior_value)
            if cur_num is None or prior_num is None:
                continue
            delta = cur_num - prior_num
            arrow = "+" if delta >= 0 else ""
            lines.append(f"- {label}: {prior_num:g} -> {cur_num:g} ({arrow}{delta:g})")
            any_delta = True
        if not any_delta:
            lines.append("- prior week file found but no comparable numeric rows.")
    else:
        lines.append("- no prior week file found — this is the first run.")
    lines.append("")

    return "\n".join(lines)


# ── heartbeat + main ────────────────────────────────────────────────────────


def write_heartbeat(
    path: Path,
    *,
    week_label: str,
    now: datetime,
    inputs: dict[str, dict],
) -> None:
    payload = {
        "ts": _fmt_ts(now),
        "week": week_label,
        "inputs": {
            name: {"ok": info["ok"], "newest": info["newest"], "note": info.get("note", "")}
            for name, info in inputs.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_page(week_arg: Optional[str], *, now: Optional[datetime] = None, out_dir: Optional[Path] = None):
    now = now or datetime.now(UTC)
    week_start_date, week_end_date, week_label = parse_iso_week(week_arg, today=now.date())
    week_start = _dt(week_start_date)
    week_end = _dt(week_end_date)
    effective_end = min(week_end, now)

    telemetry = telemetry_summary(week_start, effective_end, now=now)
    kanban = kanban_summary(week_start, effective_end, now=now)
    k2_spend = k2_spend_summary(week_start, effective_end, now=now)
    sweep = sweep_ledger_summary(week_start, effective_end, now=now)
    lane_prs = lane_pr_summary(week_start, effective_end, now=now)
    savings_fresh = savings_series_freshness(now=now)
    distillery_fresh = distillery_state_freshness(now=now)

    out_dir = out_dir if out_dir is not None else DEFAULT_OUT_DIR
    prior_text = None
    prior_start, _, _ = parse_iso_week(None, today=week_start_date - timedelta(days=1))
    prior_label = f"{prior_start.isocalendar()[0]}-W{prior_start.isocalendar()[1]:02d}"
    prior_path = out_dir / f"{prior_label}.md"
    if prior_path.is_file():
        try:
            prior_text = prior_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            prior_text = None

    page = render_page(
        week_label=week_label,
        week_start=week_start_date,
        week_end_inclusive=week_end_date - timedelta(days=1),
        generated_at=now,
        telemetry=telemetry,
        kanban=kanban,
        k2_spend=k2_spend,
        sweep=sweep,
        lane_prs=lane_prs,
        savings_fresh=savings_fresh,
        distillery_fresh=distillery_fresh,
        prior_page_text=prior_text,
    )

    inputs = {
        "telemetry": telemetry[1],
        "kanban": kanban[1],
        "k2_spend": k2_spend[1],
        "sweep_ledger": sweep[1],
        "lane_prs": lane_prs[1],
        "savings_series": savings_fresh,
        "distillery_state": distillery_fresh,
    }
    return page, week_label, out_dir, now, inputs, telemetry, kanban, k2_spend, sweep, lane_prs


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", default=None, help="YYYY-Www (default: current ISO week)")
    parser.add_argument("--dry-run", action="store_true", help="print the page, write nothing")
    parser.add_argument("--out-dir", default=None, help="override the page output directory")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir) if args.out_dir else None
    (
        page,
        week_label,
        resolved_out_dir,
        now,
        inputs,
        telemetry,
        kanban,
        k2_spend,
        sweep,
        lane_prs,
    ) = build_page(args.week, out_dir=out_dir)

    if args.dry_run:
        print(page)
        return 0

    resolved_out_dir.mkdir(parents=True, exist_ok=True)
    week_path = resolved_out_dir / f"{week_label}.md"
    latest_path = resolved_out_dir / "latest.md"
    week_path.write_text(page, encoding="utf-8")
    latest_path.write_text(page, encoding="utf-8")

    write_heartbeat(DEFAULT_HEARTBEAT_PATH, week_label=week_label, now=now, inputs=inputs)

    local_calls = telemetry[0]["calls_by_class"].get("local", 0)
    k2_usd = k2_spend[0].get("total_usd")
    k2_usd_str = _money(k2_usd) if k2_spend[0].get("available") else "unavailable"
    pr_m = lane_prs[0]
    print(
        f"Fleet economics {week_label}: local={local_calls} calls, "
        f"K2={k2_usd_str}, lane PRs {pr_m['opened']}/{pr_m['merged']}/{pr_m['closed_unmerged']} "
        f"(o/m/c), sweep {sweep[0]['qualifies_yes']}/{sweep[0]['rows_in_window']} qualify; "
        f"page {week_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
