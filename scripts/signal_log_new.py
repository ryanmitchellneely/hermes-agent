#!/usr/bin/env python3
"""Scaffold a signal-log entry + INDEX row. Does not fetch URLs.

Usage:
  python3 scripts/signal_log_new.py \\
    --title "Oh-My-Hermes multi-model orchestration" \\
    --url "https://x.com/rlaope/status/2085581549484073099" \\
    --bucket router \\
    --posture steal \\
    --rank P1 \\
    --slug omh-orchestration

Optional: --repo --docs --confidence --dry-run

Remote minting (Ryan ruling 2026-09-03): the canonical signal-log library is
the VPS checkout k2vps:/opt/t1000/src, not whichever machine happens to run
this script. Minting IDs against a LOCAL entries/ glob on two hosts on the
same day produced colliding SIG-YYYYMMDD-NN ids. By default this script now
mints against the VPS over ssh (--remote); pass --local only when you must
work offline from the VPS, and reconcile the resulting suffixed id by hand.
"""
from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "research" / "signal-log"
ENTRIES = LOG / "entries"
TEMPLATE = LOG / "TEMPLATE.md"
GENERATOR = Path(__file__).with_name("signal_log_index.py")

CANONICAL_ENTRIES_DIR = Path("/opt/t1000/src/docs/research/signal-log/entries")


def is_canonical_host() -> bool:
    """True when this process is running on the VPS canonical checkout itself."""
    return CANONICAL_ENTRIES_DIR.is_dir()


def next_id(day: str) -> str:
    """SIG-YYYYMMDD-NN"""
    prefix = f"SIG-{day.replace('-', '')}-"
    n = 0
    if ENTRIES.exists():
        for p in ENTRIES.glob(f"{prefix}*.md"):
            m = re.search(r"-(\d{2})(?:_|$)", p.stem)
            # stem like SIG-20260807-01_slug
            m = re.match(rf"SIG-{day.replace('-', '')}-(\d{{2}})_", p.name)
            if m:
                n = max(n, int(m.group(1)))
    return f"SIG-{day.replace('-', '')}-{n + 1:02d}"


def local_host_suffix() -> str:
    """First letter of the short hostname — tags an offline-minted local id."""
    host = socket.gethostname().split(".")[0]
    return (host[:1] or "x").lower()


def remote_next_id(day: str, host: str, root: str, user: str, run=subprocess.run) -> str:
    """SIG-YYYYMMDD-NN minted against the remote entries/ dir over ssh (one call)."""
    prefix = f"SIG-{day.replace('-', '')}-"
    remote_dir = f"{root}/docs/research/signal-log/entries"
    result = run(
        ["ssh", host, f"sudo -u {user} ls {remote_dir}"],
        capture_output=True,
        text=True,
    )
    n = 0
    if result.returncode == 0:
        for name in (result.stdout or "").splitlines():
            m = re.match(rf"SIG-{day.replace('-', '')}-(\d{{2}})_", name.strip())
            if m:
                n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:02d}"


def remote_write(path_rel: str, body: str, host: str, root: str, user: str, run=subprocess.run) -> None:
    """Write ``body`` to ``<root>/<path_rel>`` on the remote, then refresh INDEX.md.

    Refuses (SystemExit) if the remote file already exists. A failed remote
    index regen is a NOTE, not a fatal error — the entry is already written.
    """
    full = f"{root}/{path_rel}"
    check = run(
        ["ssh", host, f"sudo -u {user} test -e {full}"],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        raise SystemExit(f"exists: {host}:{full}")
    write = run(
        ["ssh", host, f"sudo -u {user} tee {full} > /dev/null"],
        input=body,
        capture_output=True,
        text=True,
    )
    if write.returncode != 0:
        raise SystemExit(f"remote write failed: {(write.stderr or '').strip()}")
    index = run(
        [
            "ssh",
            host,
            f"cd {root} && sudo -u {user} /opt/t1000/venv/bin/python scripts/signal_log_index.py --write",
        ],
        capture_output=True,
        text=True,
    )
    if index.returncode != 0:
        print(
            f"NOTE: remote index regen failed — run it by hand: "
            f"ssh {host} 'cd {root} && sudo -u {user} /opt/t1000/venv/bin/python "
            f"scripts/signal_log_index.py --write' ({(index.stderr or '').strip()})",
            file=sys.stderr,
        )
    else:
        print("indexed (remote)")


def build_entry(template_text: str, sig: str, day: str, args: argparse.Namespace) -> str:
    """Pure substitution of the scaffolded entry body from the template text."""
    body = template_text
    body = body.replace("SIG-YYYYMMDD-NN", sig)
    body = body.replace("date: YYYY-MM-DD", f"date: {day}")
    body = body.replace('title: ""', f'title: "{args.title}"')
    body = body.replace('source_url: ""', f'source_url: "{args.url}"')
    body = body.replace('canonical_repo: ""', f'canonical_repo: "{args.repo}"')
    body = body.replace('canonical_docs: ""', f'canonical_docs: "{args.docs}"')
    # first enum defaults in template — replace bucket/posture lines carefully
    body = re.sub(
        r"^bucket:.*$",
        f"bucket: {args.bucket}",
        body,
        count=1,
        flags=re.M,
    )
    body = re.sub(
        r"^posture:.*$",
        f"posture: {args.posture}",
        body,
        count=1,
        flags=re.M,
    )
    body = re.sub(
        r"^steal_rank:.*$",
        f"steal_rank: {args.steal_rank}",
        body,
        count=1,
        flags=re.M,
    )
    body = re.sub(
        r"^confidence:.*$",
        f"confidence: {args.confidence}",
        body,
        count=1,
        flags=re.M,
    )
    # The template ships enum literals on these two lines; without substituting
    # them every scaffolded entry landed with `status: open|wired|done|wont`
    # (caught 2026-08-09 by signal_log_index.py's enum warning).
    body = re.sub(r"^status:.*$", "status: open", body, count=1, flags=re.M)
    body = re.sub(r"^distill:.*$", "distill: none", body, count=1, flags=re.M)
    body = body.replace("# SIG-YYYYMMDD-NN — <short title>", f"# {sig} — {args.title}")
    return body


def _template_text() -> str:
    return TEMPLATE.read_text() if TEMPLATE.exists() else "# entry\n"


def run_remote(args: argparse.Namespace, day: str, slug: str) -> None:
    if args.dry_run:
        # Fetching the real NN requires an ssh round-trip; --dry-run performs
        # no ssh, so the sequence number is shown as a placeholder.
        placeholder = f"SIG-{day.replace('-', '')}-NN_{slug}.md"
        print(f"{args.remote_host}:{args.remote_root}/docs/research/signal-log/entries/{placeholder}")
        return

    sig = remote_next_id(day, args.remote_host, args.remote_root, args.remote_user)
    path_rel = f"docs/research/signal-log/entries/{sig}_{slug}.md"
    target = f"{args.remote_host}:{args.remote_root}/{path_rel}"
    body = build_entry(_template_text(), sig, day, args)
    remote_write(path_rel, body, args.remote_host, args.remote_root, args.remote_user)
    print(f"wrote {target}")


def run_local(args: argparse.Namespace, day: str, slug: str) -> None:
    sig = f"{next_id(day)}{local_host_suffix()}"
    path = ENTRIES / f"{sig}_{slug}.md"
    print(
        f"WARNING: local id {sig} was minted offline from the VPS canonical "
        f"library ({args.remote_host}:{args.remote_root}) — reconcile it there "
        f"before it collides with another host's entry for the same day.",
        file=sys.stderr,
    )

    if args.dry_run:
        print(path)
        return

    body = build_entry(_template_text(), sig, day, args)

    ENTRIES.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"exists: {path}")
    path.write_text(body)
    print(f"wrote {path}")

    # INDEX.md is GENERATED from entry frontmatter — never hand-insert a row here.
    # This script used to write its own row, which made two writers for one file;
    # that is how the ledger drifted (5 rows listed for 12 entries, 2026-08-09).
    if subprocess.run([sys.executable, str(GENERATOR), "--write"]).returncode == 0:
        print(f"indexed {sig}")
    else:
        print(f"NOTE: run `python3 {GENERATOR} --write` to refresh INDEX.md", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--posture", default="watch")
    ap.add_argument("--rank", default="—", dest="steal_rank")
    ap.add_argument("--slug", required=True, help="kebab-case file slug")
    ap.add_argument("--repo", default="")
    ap.add_argument("--docs", default="")
    ap.add_argument("--confidence", default="medium")
    ap.add_argument("--day", default=None, help="YYYY-MM-DD (default today local)")
    ap.add_argument("--dry-run", action="store_true")

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--remote", action="store_true",
        help="mint against the VPS canonical library over ssh (default off-VPS)",
    )
    mode.add_argument(
        "--local", action="store_true",
        help="mint locally with a host-suffixed id (default on the VPS itself)",
    )
    ap.add_argument("--remote-host", default="k2vps")
    ap.add_argument("--remote-root", default="/opt/t1000/src")
    ap.add_argument("--remote-user", default="t1000")
    args = ap.parse_args()

    day = args.day or date.today().isoformat()
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")

    use_remote = args.remote or (not args.local and not is_canonical_host())
    if use_remote:
        run_remote(args, day, slug)
    else:
        run_local(args, day, slug)


if __name__ == "__main__":
    main()
