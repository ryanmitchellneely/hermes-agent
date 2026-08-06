#!/usr/bin/env python3
"""T1000 daily build-hygiene sweep — no-agent cron script.

Reports only when something needs human/agent attention:
  - dirty working trees
  - unpushed commits (ahead of upstream)
  - behind upstream
  - no upstream set on a tracked branch
  - T1000 doctor/reconciler red flags (light)
  - session DB size tripwire
  - Pulp auth days-left if status file reachable via last known local cache

Empty stdout = silent (cron no_agent stays quiet).
State: ~/.t1000/cache/build-hygiene-sweep-state.json (optional fingerprint de-dupe)

Never auto-push. Never commit. Report only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
STATE_PATH = HOME / "cache" / "build-hygiene-sweep-state.json"

# Repos Ryan actually ships from. Order = report priority.
REPOS: list[tuple[str, Path]] = [
    ("T1000", Path.home() / "Documents" / "T1000"),
    ("sovereign-advisory", Path.home() / "Documents" / "sovereign-advisory"),
    ("sovereign-consulting", Path.home() / "Documents" / "sovereign-consulting"),
    ("kevin-real-estate-tools", Path.home() / "Documents" / "kevin-real-estate-tools"),
    ("investing", Path.home() / "Documents" / "investing"),
    ("proofmark", Path.home() / "Documents" / "proofmark"),
    ("career", Path.home() / "Documents" / "career"),
    ("HermesDesktop", Path.home() / "Documents" / "HermesDesktop"),
]

# Skip dirty noise under these path prefixes (relative to repo root).
DIRTY_IGNORE_PREFIXES = (
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "dist/",
    "build/",
    ".DS_Store",
    # local-only runtime noise often present in desk repos
    "desk/HEARTBEATS.md",  # may be live-written; still flag if only this? keep visible
)

# Cap porcelain lines shown per repo
MAX_DIRTY_LINES = 8

# Session DB tripwire (MB)
SESSION_DB_WARN_MB = 200


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return p.returncode, out.strip()
    except Exception as e:
        return 99, f"{type(e).__name__}: {e}"


def _git(repo: Path, *args: str, timeout: int = 20) -> tuple[int, str]:
    return _run(["git", "-C", str(repo), *args], timeout=timeout)


def _filter_dirty(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for ln in lines:
        path = ln[3:].strip() if len(ln) >= 4 else ln
        # rename lines: "R  old -> new"
        if " -> " in path:
            path = path.split(" -> ", 1)[-1].strip()
        if any(path.startswith(pfx) or f"/{pfx}" in f"/{path}" for pfx in DIRTY_IGNORE_PREFIXES if pfx.endswith("/")):
            continue
        if path in DIRTY_IGNORE_PREFIXES or path.endswith("/.DS_Store"):
            continue
        kept.append(ln)
    return kept


def scan_repo(name: str, path: Path) -> dict | None:
    if not (path / ".git").exists() and not path.is_dir():
        return None
    # worktree / normal repo
    code, _ = _git(path, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return None

    _, branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch or "?"

    code_sb, sb = _git(path, "status", "-sb")
    sb_line = (sb.splitlines()[0] if sb else "").strip()

    code_p, porcelain = _git(path, "status", "--porcelain")
    dirty_raw = [ln for ln in (porcelain.splitlines() if porcelain else []) if ln.strip()]
    dirty = _filter_dirty(dirty_raw)

    ahead = behind = None
    upstream_missing = False
    code_u, _ = _git(path, "rev-parse", "--abbrev-ref", "@{u}")
    if code_u != 0:
        upstream_missing = branch not in ("HEAD",) and not branch.startswith("(")
    else:
        _, a = _git(path, "rev-list", "--count", "@{u}..HEAD")
        _, b = _git(path, "rev-list", "--count", "HEAD..@{u}")
        try:
            ahead = int(a or "0")
        except ValueError:
            ahead = None
        try:
            behind = int(b or "0")
        except ValueError:
            behind = None

    # uncommitted stash count (info only if >0 and we already noisy)
    _, stash_list = _git(path, "stash", "list")
    stash_n = len([x for x in stash_list.splitlines() if x.strip()]) if stash_list else 0

    issues: list[str] = []
    if dirty:
        issues.append(f"dirty={len(dirty)}")
    if ahead and ahead > 0:
        issues.append(f"unpushed={ahead}")
    if behind and behind > 0:
        issues.append(f"behind={behind}")
    if upstream_missing and (dirty or (ahead and ahead > 0) or branch not in ("main", "master")):
        # only flag no-upstream when there's something to lose or non-default branch work
        if dirty or branch not in ("main", "master"):
            issues.append("no-upstream")

    if not issues:
        return None

    return {
        "name": name,
        "path": str(path),
        "branch": branch,
        "status_line": sb_line,
        "dirty_n": len(dirty),
        "dirty_sample": dirty[:MAX_DIRTY_LINES],
        "ahead": ahead,
        "behind": behind,
        "upstream_missing": upstream_missing,
        "stash_n": stash_n,
        "issues": issues,
    }


def t1000_ops_flags() -> list[str]:
    flags: list[str] = []
    juice = Path.home() / "Documents" / "T1000" / "scripts" / "juice-doctor"
    if juice.exists():
        code, out = _run(
            [str(juice), "--reconcile-only"],
            timeout=60,
        )
        if code != 0 or "drifted=" in out and "drifted=0" not in out.replace("drifted=0", ""):
            # crude: flag non-zero exit
            if code != 0:
                flags.append(f"juice-doctor exit={code}")
            if "refused=" in out:
                for ln in out.splitlines():
                    if "reconciler:" in ln or "refused=" in ln or "drifted=" in ln:
                        if "OK fixed=0 drifted=0 refused=0" not in ln:
                            flags.append(ln.strip()[:160])
                            break

    # failover alert file present?
    alert = HOME / "failover" / "sustained-failover-alert.json"
    if alert.is_file() and alert.stat().st_size > 2:
        flags.append(f"model-failover alert file present: {alert}")

    rec_alert = HOME / "reconciler" / "last-alert.json"
    if rec_alert.is_file() and rec_alert.stat().st_size > 2:
        flags.append(f"reconciler alert file present: {rec_alert}")

    # session DB size
    db = HOME / "state.db"
    if db.is_file():
        mb = db.stat().st_size / (1024 * 1024)
        if mb >= SESSION_DB_WARN_MB:
            flags.append(f"session state.db ~{mb:.0f}MB (≥{SESSION_DB_WARN_MB} — consider hermes-session-hygiene)")

    # gateway heartbeat age via launchctl presence (soft)
    code, out = _run(["launchctl", "list", "ai.hermes.gateway"], timeout=10)
    if code != 0 or "ai.hermes.gateway" not in (out or ""):
        # list format may just be PID status label
        pass

    return flags


def pulp_auth_flag() -> str | None:
    """Best-effort Pulp auth days-left via short SSH, else local cache."""
    code, out = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=6",
            "k2vps",
            "cat /var/lib/pulp/auth_readiness_status.json 2>/dev/null || true",
        ],
        timeout=12,
    )
    raw = out.strip() if code == 0 else ""
    if raw.startswith("{"):
        try:
            cache = HOME / "cache" / "pulp-auth-status.json"
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(raw + "\n", encoding="utf-8")
            d = json.loads(raw)
            days = d.get("days_left")
            exp = d.get("expires_at")
            if isinstance(days, (int, float)) and days <= 14:
                return f"Pulp auth ~{days:.1f}d left (expires {exp}) — renew before cliff"
            return None
        except Exception:
            pass
    for p in (
        HOME / "cache" / "pulp-auth-status.json",
        Path("/tmp/pulp-auth-status.json"),
    ):
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                days = d.get("days_left")
                exp = d.get("expires_at")
                if isinstance(days, (int, float)) and days <= 14:
                    return f"Pulp auth ~{days:.1f}d left (expires {exp}) — renew before cliff"
            except Exception:
                pass
    return None


def format_report(repos: list[dict], flags: list[str]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "T1000 build hygiene sweep",
        f"{now}",
        "",
        "Auto-push: NEVER. Commit/push only with your OK.",
        "",
    ]
    if repos:
        lines.append("## Git")
        for r in repos:
            bits = ", ".join(r["issues"])
            lines.append(f"• {r['name']} [{r['branch']}] — {bits}")
            if r.get("status_line"):
                lines.append(f"    {r['status_line']}")
            if r.get("ahead"):
                lines.append(f"    → push: cd {r['path']} && git push")
            if r.get("behind"):
                lines.append(f"    → pull/rebase before new work (behind {r['behind']})")
            if r.get("upstream_missing"):
                lines.append("    → no upstream — set tracking or open PR branch")
            if r.get("dirty_sample"):
                lines.append(f"    dirty sample ({r['dirty_n']}):")
                for d in r["dirty_sample"]:
                    lines.append(f"      {d}")
                if r["dirty_n"] > len(r["dirty_sample"]):
                    lines.append(f"      … +{r['dirty_n'] - len(r['dirty_sample'])} more")
            if r.get("stash_n"):
                lines.append(f"    stashes: {r['stash_n']}")
            lines.append("")
    if flags:
        lines.append("## Ops flags")
        for f in flags:
            lines.append(f"• {f}")
        lines.append("")

    lines.append("## Suggested daily habit")
    lines.append("1. Commit finished work with a why-message")
    lines.append("2. git push (or PR) same day — don't leave ahead>0 overnight")
    lines.append("3. Leave WIP on a named branch, not silent dirty main")
    lines.append("4. Say 'hygiene sweep' anytime for an on-demand run")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    findings: list[dict] = []
    for name, path in REPOS:
        if not path.exists():
            continue
        hit = scan_repo(name, path)
        if hit:
            findings.append(hit)

    flags = t1000_ops_flags()
    pa = pulp_auth_flag()
    if pa:
        flags.append(pa)

    if not findings and not flags:
        # fully clean — silent
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "clean": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0

    report = format_report(findings, flags)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "clean": False,
                "repos": [r["name"] for r in findings],
                "flags": flags,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
