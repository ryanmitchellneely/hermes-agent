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
import re
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
# Distillery intake sweep runs every 6h (hermes cron 534f64030bae); two missed
# ticks is the page threshold.
DISTILLERY_INTAKE_STALE_SECS = int(os.environ.get("DISTILLERY_INTAKE_STALE_SECS") or 13 * 3600)
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
# dsh verdict-waste threshold (harness t_70595c66). DEVBOT-2-PLAN §5's rule —
# keep iterating while PRs clear; producing unstampable PRs is the waste — was
# a memory until now: 8 dsh-lane PRs sat unverdicted >72h before the 09-01
# routing ruling and zero instruments said so.
DSH_WASTE_CACHE = DESK / "cache" / "k2-dsh-waste.json"
# How GitHub REST spells the lane's App identity. `gh` prints the PR author as
# `app/k2-dsh-lane`; the REST API returns `k2-dsh-lane[bot]` with
# user.type == "Bot" — MEASURED 2026-09-01 with one read-only GET on
# /repos/joinsov/kevin-real-estate-tools/pulls/5878, run on k2vps as t1000
# against the lane's own installation token. Both spellings are matched so a
# future REST change does not silently empty the lane.
DSH_LANE_LOGINS = ("k2-dsh-lane[bot]", "app/k2-dsh-lane")
# A verdict only counts when a NON-author, non-automation login stamped it.
# github-actions[bot] is excluded on purpose: the automated lane posts
# INCONCLUSIVE notices, and on #5834 it posted a fabricated objection — an
# unreviewed PR must not look reviewed because CI talked to itself.
DSH_VERDICT_RE = re.compile(
    r"Verdict:\s*\**\s*(APPROVE-WITH-NITS|APPROVE|REQUEST-CHANGES|BLOCK)"
)
DSH_VERDICT_IGNORE_LOGINS = ("github-actions[bot]",)
ALERTS = [
    ("model_failover", DESK / "failover" / "sustained-failover-alert.json"),
    ("reconciler", DESK / "reconciler" / "last-alert.json"),
]
# DS4 (deepseek-v4-flash) liveness pulse (models-board t_c765b8f4, 2026-09-02):
# the on-box kevin-spark watchdog only ever sees the container from its own
# loopback, so a dead tailnet path or a dead model-proxy would be invisible
# from here without a second, independent leg. From k2vps, DS4 is reachable
# ONLY as http://100.125.80.66:11435 with Host: model.local:11435 and a
# bearer token — the tailnet ACL admits no other port. MEASURED live
# 2026-09-02: a real completion against this exact URL/header/model returns
# choices with no error key; an unauthenticated request returns 401.
DS4_LIVENESS_URL = os.environ.get(
    "DS4_LIVENESS_URL", "http://100.125.80.66:11435/v1/chat/completions"
)
DS4_LIVENESS_HOST_HEADER = os.environ.get("DS4_LIVENESS_HOST_HEADER", "model.local:11435")
DS4_LIVENESS_MODEL = os.environ.get("DS4_LIVENESS_MODEL", "deepseek-v4-flash")
DS4_LIVENESS_TIMEOUT_S = float(os.environ.get("DS4_LIVENESS_TIMEOUT_S", "25"))
DS4_LIVENESS_TOKEN_ENV = Path(
    os.environ.get("DS4_LIVENESS_TOKEN_ENV") or (DESK / "secrets" / "model-proxy.env")
)
DS4_LIVENESS_TOKEN_KEY = "K2_LOCAL_API_KEY"
# flash-next pilot (t_37efebbb, 2026-09-06): Qwen3.8-Flash-Next served by llama.cpp on
# ryan-spark :8898, reached from k2vps ONLY through the sparklink reverse tunnel :11439.
# It is provider `spark` for the whole T1000 engine, so if this is down every local
# kanban card is down. :11435 is the small-model ollama (hermes3 aux) on the same box.
FLASH_HEALTH_URL = os.environ.get("FLASH_HEALTH_URL", "http://127.0.0.1:11439/health")
FLASH_METRICS_URL = os.environ.get("FLASH_METRICS_URL", "http://127.0.0.1:11439/metrics")
FLASH_MODELS_URL = os.environ.get("FLASH_MODELS_URL", "http://127.0.0.1:11439/v1/models")
SPARK_OLLAMA_URL = os.environ.get("SPARK_OLLAMA_URL", "http://127.0.0.1:11435/api/version")
FLASH_TIMEOUT_S = float(os.environ.get("FLASH_TIMEOUT_S", "10"))
# flash-next completion liveness (harness t_83348309, 2026-09-06): the
# _flash_next_liveness() leg above only proves /health and /v1/models answer
# -- it does not prove a real completion works. This leg mirrors
# _ds4_liveness(): one tiny real chat completion through the same :11439
# tunnel. No auth token: the tunnel is local-only and unauthenticated
# (measured live 2026-09-06 with a bare curl POST).
FLASHNEXT_LIVENESS_URL = os.environ.get(
    "FLASHNEXT_LIVENESS_URL", "http://127.0.0.1:11439/v1/chat/completions"
)
FLASHNEXT_LIVENESS_MODEL = os.environ.get("FLASHNEXT_LIVENESS_MODEL", "qwen3.8-flash-next")
FLASHNEXT_LIVENESS_TIMEOUT_S = float(os.environ.get("FLASHNEXT_LIVENESS_TIMEOUT_S", "25"))
FLASHNEXT_LIVENESS_MAX_TOKENS = int(os.environ.get("FLASHNEXT_LIVENESS_MAX_TOKENS", "8"))


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


def _distillery_intake() -> list[str]:
    """Distillery intake sweep heartbeat (mesh t_a4d3ea5b, 2026-09-03).

    The sweep ran for three weeks with every source path resolving to a
    nonexistent directory and reported "silent (empty output)" — indistinguishable
    from a clean tick. The sweep now writes per-source counts into its state
    file; this leg pages when the file is stale (sweep not running) or when an
    enabled source has reported zero artifacts on two consecutive sweeps.
    """
    warns: list[str] = []
    state_path = DESK / "cache" / "distillery-intake-sweep-state.json"
    if not state_path.is_file():
        return [f"WARN distillery-intake state missing at {state_path} — sweep never ran here"]
    try:
        st = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"WARN distillery-intake state unreadable: {type(exc).__name__}: {exc}"]
    ts = st.get("ts")
    try:
        age = time.time() - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except Exception:  # noqa: BLE001
        return [f"WARN distillery-intake state has no parseable ts ({ts!r})"]
    if age > DISTILLERY_INTAKE_STALE_SECS:
        warns.append(
            f"WARN distillery-intake sweep STALE age={int(age // 3600)}h "
            f"(threshold {DISTILLERY_INTAKE_STALE_SECS // 3600}h) — cron 534f64030bae not landing"
        )
    sources = st.get("sources") or {}
    if not sources:
        warns.append(
            "WARN distillery-intake state carries no per-source counts — "
            "pre-2026-09-03 sweep build still running"
        )
        return warns
    zero_now = sorted(k for k, v in sources.items() if isinstance(v, dict) and not v.get("count"))
    missing = sorted(k for k, v in sources.items() if isinstance(v, dict) and v.get("exists") is False)
    if missing:
        warns.append(f"WARN distillery-intake source path MISSING: {', '.join(missing)}")
    prev_zero = set((st.get("prev_zero_sources") or []))
    persistent = [k for k in zero_now if k in prev_zero and k not in missing]
    if persistent:
        warns.append(
            f"WARN distillery-intake source reported 0 artifacts on two consecutive sweeps: "
            f"{', '.join(persistent)}"
        )
    try:
        st["prev_zero_sources"] = zero_now
        state_path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
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



def _night_dequeue_heartbeat() -> list[str]:
    """DevBot night-dequeue heartbeat, read over the spark reverse tunnel.

    Closes the atlas R3 owed item (Ryan-approved 2026-08-31): the nightly
    unattended executor on kevin-spark had zero off-box heartbeat rows, so a
    dead crontab and a healthy quiet night were indistinguishable from here.
    kevin-spark serves ~/devbot/logs on 127.0.0.1:8899, reverse-tunneled to
    local :11440 (moved off 11439 on 2026-09-01: that port is
    allocated to deepseek-v4-flash per dsh-flashnext.yml) via the pre-authorized permitlisten key (no new creds).

    Rule 4 wording: an unreachable channel is told as CHANNEL (spark down,
    tunnel dead, or server stopped), never as "the cron did not run" — and a
    stale receipt is told as the cron's silence. Thresholds ~2.5x cadence:
    the job fires daily 06:30Z, so stale > 60h pages; unreachable pages
    immediately (the tunnel is supervised by a 10-min keeper, so a dead
    channel is itself a real fault, and the fp dedup means one page per
    distinct state, not one per pulse).
    """
    import urllib.request
    warns: list[str] = []
    max_age_h = float(os.environ.get("T1000_NIGHT_HB_MAX_AGE_H", "60"))
    try:
        with urllib.request.urlopen("http://127.0.0.1:11440/night-last.json", timeout=6) as r:
            hb = json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return [
            "WARN night-dequeue heartbeat UNREACHABLE via :11440 tunnel "
            f"({type(exc).__name__}) — spark down, tunnel dead, or the logs "
            "server stopped; the cron's own state is UNKNOWN, not bad"
        ]
    try:
        ts = datetime.strptime(hb.get("ts", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    except Exception:
        return [f"WARN night-dequeue receipt unparseable: {str(hb)[:120]}"]
    if age_h > max_age_h:
        warns.append(
            f"WARN night-dequeue receipt STALE: last ran {hb.get('ts')} "
            f"({age_h:.0f}h ago; expected daily ~06:30Z) — the cron on "
            "kevin-spark has gone quiet"
        )
    rc = hb.get("rc")
    # rc is the PROCESS exit, not the outcome: on 2026-09-02 db-0020 exited rc=0
    # with its only deliverable refused by the path fence, and this checker
    # stayed silent. The receipt now carries apply_ok/apply_fail (night_dequeue.sh);
    # a failed apply is a warning even when rc is 0.
    af = hb.get("apply_fail")
    if af in (-1, -2):
        # No countable outcome is itself a warning: -1 the run wrote no
        # code.json at all, -2 it wrote one that cannot be parsed. Neither is
        # "healthy", and rc=0 says nothing either way.
        why = "never wrote its code.json" if af == -1 else "wrote an unparseable code.json"
        return ("warn", f"night dequeue ran {hb.get('job')} rc={hb.get('rc')} but {why} (apply_fail={af}) — no countable outcome; read night.log on kevin-spark")
    ao = hb.get("apply_ok")
    if hb.get("job") and af == 0 and ao == 0:
        # Grok residual risk on #5923: an empty results list counts 0/0 and
        # looked healthy. A job that ran, exited rc=0, and applied NOTHING is
        # not a delivered job — the model returned no fences, or every fence
        # was dropped before the apply loop. Warn.
        return ("warn", f"night dequeue ran {hb.get('job')} rc={hb.get('rc')} but applied nothing (apply_ok=0, apply_fail=0) — no deliverable; read night.log on kevin-spark")
    if isinstance(af, int) and af > 0:
        return ("warn", f"night dequeue ran {hb.get('job')} rc={hb.get('rc')} but apply_fail={af} (apply_ok={hb.get('apply_ok')}): the deliverable did not land — read night.log on kevin-spark")
    if rc not in (0, -1):
        warns.append(
            f"WARN night-dequeue last run FAILED rc={rc} note={str(hb.get('note'))[:100]}"
        )
    return warns


def _gh_get(path: str, token: str) -> list | dict:
    """One read-only GitHub REST GET. The single network seam in this module.

    Kept module-level and parameterised so the tests stub exactly one thing;
    raises on anything that is not a clean 200 so the caller reports
    UNMEASURED rather than a short count.
    """
    import urllib.request

    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "t1000-ops-alert-pulse",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # fixed github.com host
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def _read_env_value(path: Path, key: str) -> str | None:
    """Parse one KEY=VALUE line from a simple .env file. Never logs the value."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


def _ds4_completion_request(token: str) -> dict:
    """The single network seam for the DS4 liveness check — kept module-level
    and parameterised so tests stub exactly one thing (same pattern as
    `_gh_get`). Raises on connection failure, timeout, or any non-2xx
    (urllib raises HTTPError for those natively).
    """
    import urllib.request

    req = urllib.request.Request(
        DS4_LIVENESS_URL,
        data=json.dumps(
            {
                "model": DS4_LIVENESS_MODEL,
                "messages": [{"role": "user", "content": "reply with OK"}],
                "max_tokens": 16,
            }
        ).encode("utf-8"),
        headers={
            "Host": DS4_LIVENESS_HOST_HEADER,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=DS4_LIVENESS_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ds4_liveness() -> list[str]:
    """DS4 flash liveness, read from k2vps through the model-proxy tailnet
    leg (t_c765b8f4). Success is silent; failure is a WARN with the failure
    told honestly rather than folded into a generic message (rule 4: an
    unreachable channel is told as CHANNEL, not confused with "down").
    """
    import urllib.error

    token = _read_env_value(DS4_LIVENESS_TOKEN_ENV, DS4_LIVENESS_TOKEN_KEY)
    if not token:
        return [
            f"WARN ds4 flash: token unreadable from {DS4_LIVENESS_TOKEN_ENV} "
            f"(missing {DS4_LIVENESS_TOKEN_KEY}) — liveness check cannot run"
        ]

    try:
        body = _ds4_completion_request(token)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return [
                "WARN ds4 flash: auth rejected (401) against the model-proxy — "
                "the K2_LOCAL_API_KEY token is wrong or rotated"
            ]
        return [f"WARN ds4 flash: model-proxy returned HTTP {exc.code}"]
    except Exception as exc:  # noqa: BLE001 — connection refused/timeout/DNS/etc.
        return [
            "WARN ds4 flash: CHANNEL unreachable via the k2vps model-proxy "
            f"({type(exc).__name__}) — tailnet path down, proxy down, or the "
            "DS4 container itself down; state is UNKNOWN, not bad"
        ]

    if "error" in body:
        return [
            f"WARN ds4 flash: completion returned an error: {str(body.get('error'))[:160]}"
        ]
    if not body.get("choices"):
        return [
            "WARN ds4 flash: completion returned no choices — real inference "
            "path is not working"
        ]
    return []


def _http_get(url: str, timeout: float) -> tuple[int, str]:
    import urllib.request
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.status, resp.read().decode("utf-8", "replace")


def _flash_next_liveness() -> list[str]:
    """flash-next pilot liveness through the :11439 tunnel. Silent when healthy.
    Tells CHANNEL (tunnel/box unreachable) apart from SERVER (answers but not ok)
    apart from MODEL (health ok but the served model list is wrong)."""
    warns: list[str] = []
    try:
        code, body = _http_get(FLASH_HEALTH_URL, FLASH_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        warns.append(
            "WARN flash-next (provider spark, ALL local kanban cards): CHANNEL unreachable at "
            f"{FLASH_HEALTH_URL} ({type(exc).__name__}) — sparklink tunnel :11439 down, ryan-spark "
            "down, or llama-server not listening on :8898. Spark cron relaunches both within 2 min; "
            "if this persists, look at ~/models/flash-next/flash-next.service.log on the Spark."
        )
    else:
        if code != 200 or '"ok"' not in body:
            warns.append(f"WARN flash-next: /health answered HTTP {code} {body[:120]!r} — server up but not healthy")
        else:
            try:
                _, models = _http_get(FLASH_MODELS_URL, FLASH_TIMEOUT_S)
                if "qwen3.8-flash-next" not in models:
                    warns.append(
                        f"WARN flash-next: :11439 healthy but serves {models[:120]!r}, not qwen3.8-flash-next — "
                        "the tunnel points at the wrong server (bench window left open?)"
                    )
            except Exception as exc:  # noqa: BLE001
                warns.append(f"WARN flash-next: /health ok but /v1/models failed ({type(exc).__name__})")
    try:
        code, _ = _http_get(SPARK_OLLAMA_URL, FLASH_TIMEOUT_S)
        if code != 200:
            warns.append(f"WARN spark ollama (:11435, hermes3 aux): HTTP {code}")
    except Exception as exc:  # noqa: BLE001
        warns.append(
            f"WARN spark ollama (:11435, hermes3 aux for kanban estimator/titles): unreachable ({type(exc).__name__})"
        )
    return warns


def _flashnext_completion_request() -> dict:
    """The single network seam for the flash-next completion liveness check --
    kept module-level and parameterised so tests stub exactly one thing (same
    pattern as `_ds4_completion_request`). Raises on connection failure,
    timeout, or any non-2xx (urllib raises HTTPError for those natively). No
    auth token: the :11439 tunnel is local-only and unauthenticated.
    """
    import json
    import urllib.request

    req = urllib.request.Request(
        FLASHNEXT_LIVENESS_URL,
        data=json.dumps(
            {
                "model": FLASHNEXT_LIVENESS_MODEL,
                "messages": [{"role": "user", "content": "reply with OK"}],
                "max_tokens": FLASHNEXT_LIVENESS_MAX_TOKENS,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=FLASHNEXT_LIVENESS_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _flashnext_liveness() -> list[str]:
    """flash-next real-inference liveness (t_83348309, 2026-09-06): a tiny
    chat completion through the :11439 tunnel, mirroring `_ds4_liveness()`.
    Success is silent; failure is told honestly -- CHANNEL when the tunnel or
    box itself is unreachable, MODEL when the endpoint answers but the
    completion failed (rule 4: an unreachable channel is never confused with
    a broken model).
    """
    import urllib.error

    try:
        body = _flashnext_completion_request()
    except urllib.error.HTTPError as exc:
        return [
            f"WARN flash-next completion: MODEL endpoint returned HTTP {exc.code} "
            "-- server up but the completion path errored"
        ]
    except Exception as exc:  # noqa: BLE001 -- connection refused/timeout/DNS/etc.
        return [
            "WARN flash-next completion: CHANNEL unreachable via :11439 tunnel "
            f"({type(exc).__name__}) -- sparklink tunnel down, ryan-spark down, "
            "or llama-server not listening on :8898; state is UNKNOWN, not bad"
        ]

    if "error" in body:
        return [
            f"WARN flash-next completion: MODEL returned an error: {str(body.get('error'))[:160]}"
        ]
    if not body.get("choices"):
        return [
            "WARN flash-next completion: MODEL returned no choices -- real "
            "inference path is not working"
        ]
    return []


def _dsh_verdict_waste() -> list[str]:
    """Page when N+ dsh-lane PRs have sat unverdicted for longer than the age.

    The waste this measures is not a slow review — it is the loop producing
    PRs nobody can stamp. Read with the lane's OWN App identity via
    `k2_intake_sync._mint_bot_token()` (no second credential to rotate), and
    revoked in `finally`.

    Observability rule 4: a checker that cannot measure SAYS so. Every failure
    path — missing sibling module, unmintable token, any failed GET — returns
    one UNMEASURED warn and writes `measured: false`. Reporting 0 when the API
    was unreachable would be the exact lie this instrument exists to prevent.
    """
    threshold = int(os.environ.get("T1000_DSH_WASTE_MIN") or 5)
    age_h = float(os.environ.get("T1000_DSH_WASTE_AGE_H") or 72)
    repo = os.environ.get("T1000_DSH_WASTE_REPO") or "joinsov/kevin-real-estate-tools"

    def _write(measured: bool, open_lane_prs: int, stale: list[dict], error) -> None:
        # Written on EVERY path (clean, warn, unmeasured) so the Pulse artifact
        # can show the number even when the checker is silent.
        payload = {
            "ts": _iso(),
            "measured": measured,
            "open_lane_prs": open_lane_prs,
            "unverdicted_over_age": stale,
            "threshold": threshold,
            "age_h": age_h,
            "error": error,
        }
        try:
            DSH_WASTE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            DSH_WASTE_CACHE.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass

    def _unmeasured(why: str) -> list[str]:
        _write(False, 0, [], why)
        return [
            f"WARN dsh waste threshold UNMEASURED ({why}) — count unknown, not zero"
        ]

    try:
        import k2_intake_sync as KI  # sibling in <desk>/scripts/
    except Exception as exc:  # noqa: BLE001 — the pulse must still run
        return _unmeasured(f"k2_intake_sync unimportable: {type(exc).__name__}")

    try:
        wrapper, token = KI._mint_bot_token()
    except Exception as exc:  # noqa: BLE001
        return _unmeasured(f"token mint failed: {type(exc).__name__}")

    now = datetime.now(timezone.utc)
    try:
        lane: list[dict] = []
        page = 1
        while True:
            batch = _gh_get(
                f"/repos/{repo}/pulls?state=open&per_page=100&page={page}", token
            )
            if not isinstance(batch, list):
                raise RuntimeError("pulls payload not a list")
            for pr in batch:
                login = ((pr.get("user") or {}).get("login")) or ""
                if login in DSH_LANE_LOGINS:
                    lane.append(pr)
            if len(batch) < 100:
                break
            page += 1

        stale: list[dict] = []
        for pr in lane:
            try:
                created = datetime.strptime(
                    pr.get("created_at") or "", "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                raise RuntimeError(f"PR #{pr.get('number')} created_at unparseable")
            pr_age_h = (now - created).total_seconds() / 3600
            if pr_age_h <= age_h:
                continue
            author = ((pr.get("user") or {}).get("login")) or ""
            number = pr.get("number")
            verdicted = False
            cpage = 1
            while not verdicted:
                comments = _gh_get(
                    f"/repos/{repo}/issues/{number}/comments?per_page=100&page={cpage}",
                    token,
                )
                if not isinstance(comments, list):
                    raise RuntimeError(f"comments payload for #{number} not a list")
                for c in comments:
                    clogin = ((c.get("user") or {}).get("login")) or ""
                    if clogin == author or clogin in DSH_VERDICT_IGNORE_LOGINS:
                        continue
                    if DSH_VERDICT_RE.search(c.get("body") or ""):
                        verdicted = True
                        break
                if verdicted or len(comments) < 100:
                    break
                cpage += 1
            if not verdicted:
                stale.append(
                    {
                        "number": number,
                        "age_h": round(pr_age_h, 1),
                        "title": (pr.get("title") or "")[:120],
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return _unmeasured(f"{type(exc).__name__}: {str(exc)[:120]}")
    finally:
        try:
            wrapper._revoke_installation_token(token)
        except Exception:  # noqa: BLE001
            pass

    _write(True, len(lane), stale, None)
    if len(stale) < threshold:
        return []
    named = "\n".join(
        f"  #{s['number']} age={s['age_h']:.0f}h {s['title']}" for s in stale
    )
    return [
        f"WARN dsh verdict waste: {len(stale)} lane PRs open >{age_h:.0f}h with no "
        f"non-author verdict (threshold {threshold}) — the loop is producing "
        f"PRs nobody is stamping:\n{named}"
    ]


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

    # Night-dequeue heartbeat (atlas R3, 2026-08-31): fp dedup — one page
    # per distinct state (unreachable / stale / failed), not one per pulse.
    nh_warns = _night_dequeue_heartbeat()
    nh_blob = "\n".join(nh_warns).strip()
    nh_fp = hashlib.sha256(nh_blob.encode()).hexdigest()[:16] if nh_blob else None
    new_state["fps"]["night_dequeue"] = nh_fp
    old_nh_fp = (prev.get("fps") or {}).get("night_dequeue")
    if nh_fp and nh_fp != old_nh_fp:
        lines.append(nh_blob)

    # K2 intake bridge (t_f3dd22e3): same fp dedup; the script also
    # self-throttles internally so most pulses are a no-op.
    ki_warns = _k2_intake()
    ki_blob = "\n".join(ki_warns).strip()
    ki_fp = hashlib.sha256(ki_blob.encode()).hexdigest()[:16] if ki_blob else None
    new_state["fps"]["k2_intake"] = ki_fp
    old_ki_fp = (prev.get("fps") or {}).get("k2_intake")
    if ki_fp and ki_fp != old_ki_fp:
        lines.append(ki_blob)

    # Distillery intake sweep heartbeat (t_a4d3ea5b): same fp dedup — a
    # sustained stale/zero-source state pages once per distinct content.
    di_warns = _distillery_intake()
    di_blob = "\n".join(di_warns).strip()
    di_fp = hashlib.sha256(di_blob.encode()).hexdigest()[:16] if di_blob else None
    new_state["fps"]["distillery_intake"] = di_fp
    old_di_fp = (prev.get("fps") or {}).get("distillery_intake")
    if di_fp and di_fp != old_di_fp:
        lines.append(di_blob)

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

    # dsh verdict-waste threshold (t_70595c66): same fp dedup — one page per
    # distinct set of stalled PRs, not one per pulse. Silent when clean; the
    # count is always readable in cache/k2-dsh-waste.json.
    dw_warns = _dsh_verdict_waste()
    dw_blob = "\n".join(dw_warns).strip()
    dw_fp = hashlib.sha256(dw_blob.encode()).hexdigest()[:16] if dw_blob else None
    new_state["fps"]["dsh_waste"] = dw_fp
    old_dw_fp = (prev.get("fps") or {}).get("dsh_waste")
    if dw_fp and dw_fp != old_dw_fp:
        lines.append(dw_blob)

    # DS4 flash liveness (t_c765b8f4, 2026-09-02): a second, independent read
    # of the flash lane through the k2vps model-proxy leg — same fp dedup so
    # a sustained outage pages once per distinct state, not every 30m. The
    # timestamp is written every run regardless (register + heartbeat), even
    # on the silent/clean path.
    ds4_warns = _ds4_liveness()
    ds4_blob = "\n".join(ds4_warns).strip()
    ds4_fp = hashlib.sha256(ds4_blob.encode()).hexdigest()[:16] if ds4_blob else None
    new_state["fps"]["ds4_liveness"] = ds4_fp
    new_state["ds4_liveness_checked_at"] = _iso()
    old_ds4_fp = (prev.get("fps") or {}).get("ds4_liveness")
    if ds4_fp and ds4_fp != old_ds4_fp:
        lines.append(ds4_blob)

    # flash-next pilot liveness (t_37efebbb, 2026-09-06): provider `spark` for the whole
    # engine now lives behind :11439. Same fp dedup; plus an explicit recovery line,
    # because "it came back" is the one message the DS4 pattern never sends.
    fn_warns = _flash_next_liveness()
    fn_blob = "\n".join(fn_warns).strip()
    fn_fp = hashlib.sha256(fn_blob.encode()).hexdigest()[:16] if fn_blob else None
    new_state["fps"]["flash_next"] = fn_fp
    new_state["flash_next_checked_at"] = _iso()
    old_fn_fp = (prev.get("fps") or {}).get("flash_next")
    if fn_fp and fn_fp != old_fn_fp:
        lines.append(fn_blob)
    elif not fn_fp and old_fn_fp:
        lines.append("🟢 flash-next: :11439 healthy again (provider spark restored)")

    # flash-next completion liveness (t_83348309, 2026-09-06): a second,
    # independent leg proving real inference (not just health/models) through
    # the same :11439 tunnel -- same fp dedup pattern as ds4_liveness.
    fnx_warns = _flashnext_liveness()
    fnx_blob = "\n".join(fnx_warns).strip()
    fnx_fp = hashlib.sha256(fnx_blob.encode()).hexdigest()[:16] if fnx_blob else None
    new_state["fps"]["flashnext_liveness"] = fnx_fp
    new_state["flashnext_liveness_checked_at"] = _iso()
    old_fnx_fp = (prev.get("fps") or {}).get("flashnext_liveness")
    if fnx_fp and fnx_fp != old_fnx_fp:
        lines.append(fnx_blob)

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
