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
"""
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "research" / "signal-log"
ENTRIES = LOG / "entries"
INDEX = LOG / "INDEX.md"
TEMPLATE = LOG / "TEMPLATE.md"


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
    args = ap.parse_args()

    day = args.day or date.today().isoformat()
    sig = next_id(day)
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    path = ENTRIES / f"{sig}_{slug}.md"

    body = TEMPLATE.read_text() if TEMPLATE.exists() else "# entry\n"
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
    body = body.replace("# SIG-YYYYMMDD-NN — <short title>", f"# {sig} — {args.title}")

    rank = args.steal_rank
    index_row = (
        f"| {sig} | {day} | {args.title} | `{args.bucket}` | `{args.posture}` | "
        f"`{rank}` | [entry](entries/{path.name}) | [src]({args.url}) | open |\n"
    )

    if args.dry_run:
        print(path)
        print(index_row)
        return

    ENTRIES.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"exists: {path}")
    path.write_text(body)

    if not INDEX.exists():
        INDEX.write_text(
            "# Signal log index\n\n"
            "| ID | Date | Title | Bucket | Posture | Rank | Entry | Source | Status |\n"
            "|----|------|-------|--------|---------|------|-------|--------|--------|\n"
        )
    text = INDEX.read_text()
    lines = text.splitlines(keepends=True)
    # insert after header separator line
    out: list[str] = []
    inserted = False
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and line.startswith("|----"):
            out.append(index_row)
            inserted = True
    if not inserted:
        out.append(index_row)
    INDEX.write_text("".join(out))
    print(f"wrote {path}")
    print(f"indexed {sig}")


if __name__ == "__main__":
    main()
