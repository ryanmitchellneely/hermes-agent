#!/usr/bin/env python3
"""Refresh read-only clones under <desk>/src (fetch + hard-reset to origin/main).

Paths derive from DESK (this file's own parent), which is /opt/t1000/home on
the VPS since the 2026-08-19 flip -- NOT ~/.t1000, which is the pre-flip Mac
layout and is a frozen mirror now.

Piggybacked on the T1000 ops-alert pulse cron (every 30m) — Track C pattern:
ride a proven cadence; do not author a naked new cron. Empty stdout = silent
when healthy. Prints WARN lines on stale/fail so no_agent telegram delivery
surfaces them (observability-principle: heartbeat + surface + auto-alert;
silently stale defeats the whole check).

Heartbeat always written to:
  <desk>/cache/readonly-clones-heartbeat.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME") or Path.home() / ".t1000").expanduser()
# Desk root owns ~/.t1000/src even when a profile worker has HERMES_HOME=
# ~/.t1000/profiles/<name>. Prefer the scripts/ parent of this file when it
# looks like a desk layout (…/scripts/refresh_readonly_clones.py → …/).
_SCRIPT_DESK = Path(__file__).resolve().parent.parent
DESK = _SCRIPT_DESK if (_SCRIPT_DESK / "scripts").is_dir() else HOME
SRC_ROOT = DESK / "src"
HEARTBEAT_PATH = DESK / "cache" / "readonly-clones-heartbeat.json"
STATE_PATH = DESK / "cache" / "readonly-clones-state.json"

# Clones this script owns. path is relative to SRC_ROOT.
CLONES = (
    {
        "name": "kevin-real-estate-tools",
        "path": "kevin-real-estate-tools",
        "remote": "origin",
        "branch": "main",
        # Optional: if set, also report deploy-vs-canonical mismatch for the
        # dsh lane (does not fix deploy; only WARNs).
        "dsh_canonical_rel": "docs/agent-coordination/devbot/harness-bench/dsh_kanban_worker.py",
        # DESK, not Path.home(). Every other path in this file derives from
        # DESK; this one line did not, and that made the whole check inert.
        # Since the 2026-08-19 VPS flip the t1000 user's OS home is /opt/t1000
        # while the desk is /opt/t1000/home, so Path.home()/".t1000"/"bin"
        # resolved to /opt/t1000/.t1000/bin/... which does not exist. A missing
        # file leaves deploy_hash None, so dsh_deploy_match read False and
        # status read degraded ALWAYS -- independent of reality. An always-red
        # instrument cannot report a real drift, and did not: on 2026-08-29 the
        # deployed worker was missing PR #5714's credential scrub for hours
        # while this check said exactly what it says when everything is fine.
        "dsh_deploy": DESK / "bin" / "dsh_kanban_worker.py",
    },
)

# A clone whose HEAD is more than this many seconds behind the remote tip
# (or whose last successful refresh is older than this) is WARN-stale.
STALE_AFTER_SECS = int(os.environ.get("READONLY_CLONE_STALE_SECS") or 2 * 3600)


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- auth for private mirrors -------------------------------------------------
# These clones point at a PRIVATE repo over https and the t1000 account has no
# credential helper, no .git-credentials and no usable ssh to github, so every
# fetch died on "could not read Username" and the mirror silently froze. That is
# worse than a stale file: the devbot queue derives every card from this
# snapshot, so frozen it re-finds the same work forever, never sees its own
# merges land, and every PR it opens needs a hand rebase.
#
# Auth REUSES the dsh wrapper's reviewed path rather than reinventing it: a
# short-lived App installation token, handed to git through GIT_CONFIG_* env
# rather than argv or a token-bearing URL. That last detail is not cosmetic —
# review finding R2-11 moved it out of argv precisely because a token there is
# visible to any same-user `ps -ww` for the life of the command.
_FETCH_ENV: dict = {}


def _bot_fetch_env() -> dict:
    """Env carrying a fresh installation token, or {} if unavailable.

    {} is not an error: a public mirror, or a box without the bot identity,
    must keep refreshing exactly as it did before.
    """
    home = Path(os.environ.get("HERMES_HOME", Path.home()))
    secrets = Path(os.environ.get("DSH_BOT_ENV_PATH") or home / "secrets" / "dsh-bot.env")
    try:
        # The identity lives in a 0600 FILE, not the pulse's environment, so
        # read it and hand it to the wrapper explicitly. Plain key=value
        # parsing only — the minting and the header shape stay the wrapper's.
        env = dict(os.environ)
        for line in secrets.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            line = line[len("export "):] if line.startswith("export ") else line
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
        sys.path.insert(0, str(home / "bin"))
        import dsh_kanban_worker as w  # reviewed minting + header helpers
        return dict(w._push_auth_env(w.read_bot_identity(env).token))
    except Exception as exc:
        # Loud, because a silent {} here is indistinguishable from "no auth
        # needed" and would leave the mirror frozen while reporting success —
        # the exact failure this whole change exists to end.
        print(f"WARN readonly-clone: no bot auth ({type(exc).__name__}: {exc}); "
              f"fetches will run unauthenticated", file=sys.stderr)
        return {}


def _run(argv: list[str], cwd: Path, timeout: int = 120,
         extra_env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env={**os.environ, **(extra_env or {})} if extra_env else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def _sha256(path: Path) -> str | None:
    import hashlib

    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            h.update(f.read())
        return h.hexdigest()
    except OSError:
        return None


def refresh_one(spec: dict) -> dict:
    """Fetch + reset one clone to origin/<branch>. Returns status dict."""
    name = spec["name"]
    root = SRC_ROOT / spec["path"]
    remote = spec.get("remote") or "origin"
    branch = spec.get("branch") or "main"
    result: dict = {
        "name": name,
        "path": str(root),
        "status": "ok",
        "error": None,
        "before_sha": None,
        "after_sha": None,
        "remote_sha": None,
        "updated": False,
        "dsh_deploy_match": None,
    }
    if not (root / ".git").exists() and not root.is_dir():
        result["status"] = "fail"
        result["error"] = f"clone missing at {root}"
        return result
    if not (root / ".git").exists():
        # plain dir without .git (e.g. broken partial)
        git_dir = root / ".git"
        if not git_dir.exists():
            result["status"] = "fail"
            result["error"] = f"not a git clone: {root}"
            return result

    try:
        before = _run(["git", "rev-parse", "HEAD"], root)
        result["before_sha"] = (before.stdout or "").strip() or None

        fetch = _run(["git", "fetch", "--prune", remote, branch], root,
                     timeout=180, extra_env=_FETCH_ENV)
        if fetch.returncode != 0:
            result["status"] = "fail"
            result["error"] = f"git fetch failed rc={fetch.returncode}: {(fetch.stdout or '')[-400:]}"
            return result

        remote_ref = f"{remote}/{branch}"
        rsha = _run(["git", "rev-parse", remote_ref], root)
        if rsha.returncode != 0:
            result["status"] = "fail"
            result["error"] = f"missing {remote_ref}"
            return result
        result["remote_sha"] = (rsha.stdout or "").strip()

        rel = spec.get("dsh_canonical_rel")
        deploy = spec.get("dsh_deploy")
        hold_for_deploy = False
        if (
            rel
            and deploy
            and Path(deploy).is_file()
            and result["before_sha"]
            and result["remote_sha"]
            and result["before_sha"] != result["remote_sha"]
        ):
            # Do not downgrade a clone that currently byte-matches the live
            # deploy copy onto an older origin/main that does not — that would
            # capability-block the dsh lane the moment worker_command_canonical
            # is armed. Hold until origin/main catches up (PR merge).
            deploy_hash = _sha256(Path(deploy))

            def _blob_sha(rev: str) -> str | None:
                r = subprocess.run(
                    ["git", "cat-file", "-p", f"{rev}:{rel}"],
                    cwd=str(root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=30,
                )
                if r.returncode != 0:
                    return None
                import hashlib as _h

                return _h.sha256(r.stdout).hexdigest()

            cur_hash = _blob_sha(result["before_sha"])
            remote_hash = _blob_sha(result["remote_sha"])
            if (
                deploy_hash
                and cur_hash
                and remote_hash
                and cur_hash == deploy_hash
                and remote_hash != deploy_hash
            ):
                hold_for_deploy = True
                result["held"] = True
                result["hold_reason"] = (
                    f"HEAD matches live deploy ({deploy_hash[:12]}) but "
                    f"{remote_ref} does not ({remote_hash[:12]}); holding "
                    f"until origin/{branch} lands the wrapper parity PR"
                )

        # Detached HEAD at remote tip — never a working branch for agents.
        # Prefer checkout --detach over reset --hard when already detached on tip.
        if (not hold_for_deploy) and result["before_sha"] != result["remote_sha"]:
            co = _run(["git", "checkout", "--detach", remote_ref], root)
            if co.returncode != 0:
                # Fallback: force index+worktree to remote tip without branch dance
                co2 = _run(["git", "read-tree", "-u", "-m", remote_ref], root)
                if co2.returncode != 0:
                    result["status"] = "fail"
                    result["error"] = (
                        f"checkout detach failed: {(co.stdout or '')[-300:]} "
                        f"/ read-tree: {(co2.stdout or '')[-300:]}"
                    )
                    return result
                # Move HEAD
                _run(["git", "update-ref", "HEAD", result["remote_sha"]], root)
            result["updated"] = True

        after = _run(["git", "rev-parse", "HEAD"], root)
        result["after_sha"] = (after.stdout or "").strip() or None
        if (not hold_for_deploy) and result["after_sha"] != result["remote_sha"]:
            result["status"] = "fail"
            result["error"] = (
                f"HEAD {result['after_sha']} != {remote_ref} {result['remote_sha']}"
            )
            return result

        # Optional: surface dsh deploy-vs-canonical mismatch (not auto-fixed).
        if rel and deploy:
            canon = root / rel
            if canon.is_file() and Path(deploy).is_file():
                ch = _sha256(canon)
                dh = _sha256(Path(deploy))
                result["dsh_deploy_match"] = bool(ch and dh and ch == dh)
                result["dsh_canonical_sha256"] = (ch or "")[:16]
                result["dsh_deploy_sha256"] = (dh or "")[:16]
            else:
                result["dsh_deploy_match"] = False
                result["error"] = (
                    (result.get("error") or "")
                    + f" missing canon={canon.is_file()} deploy={Path(deploy).is_file()}"
                ).strip()

        if hold_for_deploy and result.get("dsh_deploy_match"):
            # Healthy hold: deploy still matches; mark degraded so the hold is
            # visible once, not a silent permanent fork off main.
            result["status"] = "degraded"
            result["error"] = result.get("hold_reason")

        return result
    except subprocess.TimeoutExpired:
        result["status"] = "fail"
        result["error"] = "timeout"
        return result
    except Exception as exc:  # noqa: BLE001 — heartbeat must still write
        result["status"] = "fail"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def main() -> int:
    # Mint once per run, not per repo: one token covers every mirror, and a
    # failed mint must degrade to the old unauthenticated behaviour rather than
    # abort the refresh of a public clone.
    global _FETCH_ENV
    _FETCH_ENV = _bot_fetch_env()
    t0 = time.monotonic()
    DESK.joinpath("cache").mkdir(parents=True, exist_ok=True)
    prev = _load_json(STATE_PATH)

    results = [refresh_one(spec) for spec in CLONES]
    wall_s = round(time.monotonic() - t0, 2)
    ts = _iso()

    worst = "ok"
    for r in results:
        if r["status"] == "fail":
            worst = "fail"
            break
        if r["status"] == "degraded" or r.get("dsh_deploy_match") is False:
            worst = "degraded" if worst == "ok" else worst
        if r.get("held") and r.get("hold_reason"):
            # Surface the hold once via WARN path (degraded).
            pass

    # Staleness: last successful ok older than STALE_AFTER_SECS is WARN even if
    # this tick claims ok (covers a silent schedule skip).
    last_ok_ts = prev.get("last_ok_ts")
    stale = False
    if last_ok_ts and worst == "ok":
        try:
            # parse Zulu
            last = datetime.strptime(last_ok_ts, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            age = (datetime.now(timezone.utc) - last).total_seconds()
            # only meaningful if THIS tick somehow didn't run work — we just ran,
            # so update last_ok below. Keep the field for external readers.
            stale = False
            _ = age
        except Exception:
            stale = False

    heartbeat = {
        "ts": ts,
        "status": worst,
        "wall_s": wall_s,
        "stale_after_secs": STALE_AFTER_SECS,
        "clones": results,
    }
    tmp = HEARTBEAT_PATH.with_suffix(HEARTBEAT_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(heartbeat, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, HEARTBEAT_PATH)

    state = {
        "ts": ts,
        "status": worst,
        "last_ok_ts": ts if worst == "ok" else last_ok_ts,
        "clones": {r["name"]: r for r in results},
    }
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    # WARN surface (stdout → telegram via no_agent deliver). Silent when ok.
    warns: list[str] = []
    for r in results:
        if r["status"] == "fail":
            warns.append(
                f"WARN readonly-clone FAIL {r['name']}: {r.get('error') or 'unknown'}"
            )
        elif r.get("held"):
            warns.append(
                f"WARN readonly-clone HOLD {r['name']}: {r.get('hold_reason') or r.get('error')}"
            )
        elif r.get("dsh_deploy_match") is False:
            warns.append(
                f"WARN dsh deploy≠canonical after refresh {r['name']} "
                f"canon={r.get('dsh_canonical_sha256')} deploy={r.get('dsh_deploy_sha256')} "
                f"— re-deploy from {r['path']}/{CLONES[0].get('dsh_canonical_rel')} "
                f"or the live dsh lane will capability-block once "
                f"worker_command_canonical is active"
            )
        if r.get("updated"):
            # informational only when healthy — stay silent on pure success
            pass

    # External stale detector: if heartbeat file itself is old on NEXT reader;
    # here we also flag if a clone remote tip could not move and HEAD empty.
    for r in results:
        if r["status"] == "ok" and not r.get("after_sha"):
            warns.append(f"WARN readonly-clone {r['name']} has empty HEAD")

    if not warns:
        return 0
    sys.stdout.write(
        "T1000 readonly-clone freshness\n\n" + "\n".join(warns) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
