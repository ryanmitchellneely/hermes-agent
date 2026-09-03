#!/usr/bin/env python3
"""Distillery intake sweep — PULL durable artifacts into draft review rows.

Design: docs/research/distillery-intake-sweep-design.md (mesh card t_216ac84b).

Reads systems of record (plans, signal-log entries, mesh done cards, skill
references), fingerprints each durable artifact, and drafts one review row per
new fingerprint. Drafts are for a HUMAN to file — this script never files
anything into K2, PATTERN-LEDGER, or Buzz.

Empty stdout = silent (cron no_agent stays quiet).

Never writes outside the intake dir + its own dedup state.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

STATUS_TERMINAL = ("filed", "skipped")
DRAFT_STATUSES = ("draft", "filed", "skipped", "stale", "superseded")
NOTES_HEADING = "## notes"

_HEADING_RE = re.compile(r"^#{1,2}\s+(.+?)\s*$")
_YAML_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)


def parse_ts(value: str) -> datetime:
    """Parse an ISO8601 UTC timestamp (the only form this sweep writes)."""
    return datetime.strptime(value, TS_FMT).replace(tzinfo=timezone.utc)


def fmt_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(TS_FMT)


DEFAULT_CONFIG: dict = {
    # Board source list — mesh-only today. Adding a board here is the *entire*
    # mechanism for scope expansion; nothing else in the sweep changes.
    "boards": ["mesh"],
    "sources": {
        "plans": {"enabled": True, "path": "~/.hermes/plans"},
        "signal_log": {
            "enabled": True,
            "path": "docs/research/signal-log/entries",
        },
        "mesh_done_cards": {
            "enabled": True,
            "db_template": "~/.t1000/kanban/boards/{board}/kanban.db",
            "title_exclude_patterns": ["^HUMAN review: PR #"],
            "require_result_boards": [],
        },
        "skill_references": {
            "enabled": True,
            "trees": [
                "~/.t1000/profiles/worker/skills/software-development"
                "/local-inference-fleet/references"
            ],
        },
    },
    "filters": {
        "signal_log": {"exclude_posture": ["ignore"], "exclude_bucket": ["noise"]},
    },
    "staleness_days": 5,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: Path) -> dict:
    """Config file merged over defaults; absent file means pure defaults."""
    path = Path(path).expanduser()
    if not path.is_file():
        return _deep_merge(DEFAULT_CONFIG, {})
    import yaml

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise SystemExit(f"distillery-intake: {path} must contain a YAML mapping")
    return _deep_merge(DEFAULT_CONFIG, loaded)


def render_draft(row: dict) -> str:
    """Human-readable rendering of one row. Regenerated every run."""
    lines = [
        f"# {row['title']}",
        "",
        "```yaml",
        f"id: {row['id']}",
        f"source_kind: {row['source_kind']}",
        f"source_path: {row['source_path']}",
        f"source_ref: {row['source_ref']}",
        f"board: {row['board'] if row['board'] else 'null'}",
        f"captured_at: {row['captured_at']}",
        f"status: {row['status']}",
        f"status_changed_at: {row['status_changed_at']}",
        f"superseded_by: {row['superseded_by'] if row['superseded_by'] else 'null'}",
        "```",
        "",
    ]
    if row.get("summary"):
        lines += [row["summary"], ""]
    lines += [
        f"Set `status:` above to `filed` or `skipped` once reviewed "
        f"(the sweep reads your edit back and never re-drafts {row['source_kind']} "
        "rows it has already seen).",
        "",
        NOTES_HEADING,
        "",
        row.get("notes", ""),
    ]
    return "\n".join(lines).rstrip() + "\n"


def read_human_edits(drafts_dir: Path, row_id: str) -> dict:
    """Read back the two fields a human may edit in a draft file."""
    path = Path(drafts_dir).expanduser() / f"{row_id}.md"
    if not path.is_file():
        return {}

    text = path.read_text(encoding="utf-8")
    out: dict = {}

    meta = parse_signal_frontmatter(text)
    status = meta.get("status")
    if status in DRAFT_STATUSES:
        out["status"] = status

    head, sep, tail = text.partition(NOTES_HEADING)
    if sep:
        out["notes"] = tail.strip()
    return out


def format_report(result: SweepResult, max_per_section: int = 8) -> str:
    """Report only when the sweep actually found something (silent otherwise)."""
    if not result.new and not result.newly_stale:
        return ""

    lines = ["# Distillery intake sweep"]
    lines.append(
        f"{len(result.new)} new draft(s), {len(result.newly_stale)} stale, "
        f"{len(result.superseded)} superseded"
    )

    if result.new:
        lines += ["", "## New drafts"]
        for row in result.new[:max_per_section]:
            lines.append(f"- [{row['source_kind']}] {row['title']}")
        if len(result.new) > max_per_section:
            lines.append(f"- … +{len(result.new) - max_per_section} more")

    if result.newly_stale:
        lines += ["", f"## Stale — unreviewed past threshold ({len(result.newly_stale)})"]
        for row in result.newly_stale[:max_per_section]:
            lines.append(f"- [{row['source_kind']}] {row['title']} (since {row['captured_at']})")
        if len(result.newly_stale) > max_per_section:
            lines.append(f"- … +{len(result.newly_stale) - max_per_section} more")

    lines += ["", "Review: docs/research/distillery-intake/drafts/"]
    return "\n".join(lines).rstrip() + "\n"


def file_row_id(source_kind: str, relpath: str, content_sha: str) -> str:
    """Stable idempotency key for a file artifact (design §3).

    Content-hashed, never mtime — a fresh `git clone` resets mtimes without
    changing content and would otherwise re-draft every file.
    """
    key = hashlib.sha256(f"{source_kind}:{relpath}:{content_sha}".encode()).hexdigest()[:16]
    return f"{source_kind}:{key}"


def derive_title_and_summary(text: str, fallback: str) -> tuple[str, str | None]:
    """First H1/H2 as title; first non-heading, non-fence paragraph as summary."""
    title = None
    summary = None
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        m = _HEADING_RE.match(stripped)
        if m:
            if title is None:
                title = m.group(1)
            continue
        if stripped.startswith("#"):
            continue
        if summary is None:
            summary = stripped
        if title is not None and summary is not None:
            break
    return title or fallback, summary


def collect_file_fingerprints(
    source_kind: str,
    root: Path,
    pattern: str = "*.md",
    relative_to: Path | None = None,
) -> list[dict]:
    """Fingerprint every file matching `pattern` under `root`."""
    root = Path(root).expanduser()
    if not root.is_dir():
        return []

    base = Path(relative_to).expanduser() if relative_to else root
    out: list[dict] = []
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        content_sha = hashlib.sha256(raw).hexdigest()
        try:
            relpath = str(path.relative_to(base))
        except ValueError:
            relpath = str(path)
        text = raw.decode("utf-8", errors="replace")
        title, summary = derive_title_and_summary(text, path.name)
        out.append(
            {
                "id": file_row_id(source_kind, relpath, content_sha),
                "source_kind": source_kind,
                "source_path": _display_path(path),
                "source_ref": content_sha[:16],
                "title": title,
                "summary": summary,
                "board": None,
            }
        )
    return out


def parse_signal_frontmatter(text: str) -> dict:
    """Pull the fenced ```yaml block a signal-log entry carries (scalars only)."""
    m = _YAML_FENCE_RE.search(text)
    if not m:
        return {}
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#", "-")):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def collect_signal_fingerprints(root: Path, filters: dict | None = None) -> list[dict]:
    """Signal-log entries, minus configured posture/bucket exclusions (design §2)."""
    filters = filters or {}
    exclude_posture = {p.lower() for p in filters.get("exclude_posture", [])}
    exclude_bucket = {b.lower() for b in filters.get("exclude_bucket", [])}

    out = []
    for fp in collect_file_fingerprints("signal_log_entry", root, "SIG-*.md"):
        meta = parse_signal_frontmatter(
            Path(fp["source_path"]).expanduser().read_text(encoding="utf-8")
        )
        if meta.get("posture", "").lower() in exclude_posture:
            continue
        if meta.get("bucket", "").lower() in exclude_bucket:
            continue
        if meta.get("title"):
            fp["title"] = meta["title"]
        out.append(fp)
    return out


def collect_board_fingerprints(
    board: str,
    db_path: Path,
    title_exclude_patterns: list[str] | None = None,
    since_epoch: int | None = None,
    require_result: bool = False,
) -> list[dict]:
    """Done cards on one kanban board, keyed by task_id@completion_generation.

    `completion_generation` (not `completed_at`) is the re-completion signal:
    it advances on every successful completion including manual ones, so a
    card that is reopened and re-`done`d yields a fresh fingerprint.
    """
    db_path = Path(db_path).expanduser()
    if not db_path.is_file():
        return []

    patterns = [re.compile(p) for p in (title_exclude_patterns or [])]

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        con.row_factory = sqlite3.Row
        # Boards created after mid-August 2026 (steals, harness, models, infra)
        # have no completion_generation column; on those, completed_at is the
        # re-completion signal. A query error here is fatal on purpose — it
        # used to return [] and read as "board has nothing", which is exactly
        # the silent zero this sweep exists to refuse.
        cols = {r[1] for r in con.execute("PRAGMA table_info(tasks)")}
        gen_expr = (
            "completion_generation"
            if "completion_generation" in cols
            else "COALESCE(completed_at, 0)"
        )
        sql = (
            f"SELECT id, title, body, completed_at, {gen_expr} AS completion_generation"
            " FROM tasks WHERE status = 'done'"
        )
        params: list = []
        if require_result:
            sql += " AND result IS NOT NULL AND TRIM(result) != ''"
        if since_epoch is not None:
            sql += " AND COALESCE(completed_at, 0) > ?"
            params.append(int(since_epoch))
        sql += " ORDER BY COALESCE(completed_at, 0), id"
        cards = con.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        raise SystemExit(f"distillery-intake: board {board!r} query failed at {db_path}: {exc}")
    finally:
        con.close()

    out = []
    for card in cards:
        title = card["title"] or card["id"]
        if any(p.search(title) for p in patterns):
            continue
        generation = card["completion_generation"] or 0
        _, summary = derive_title_and_summary(card["body"] or "", title)
        out.append(
            {
                "id": f"mesh_done_card:{card['id']}@{generation}",
                "source_kind": "mesh_done_card",
                "source_path": card["id"],
                "source_ref": f"{card['id']}@{generation}",
                "title": title,
                "summary": summary,
                "board": board,
            }
        )
    return out


def _display_path(path: Path) -> str:
    """Absolute path, home-collapsed for readable rows."""
    p = str(path)
    home = str(Path.home())
    return f"~{p[len(home):]}" if p.startswith(home + "/") else p


@dataclass
class SweepResult:
    rows: list[dict] = field(default_factory=list)
    new: list[dict] = field(default_factory=list)
    newly_stale: list[dict] = field(default_factory=list)
    superseded: list[dict] = field(default_factory=list)
    sources: dict = field(default_factory=dict)


def reconcile(
    rows: list[dict],
    fingerprints: list[dict],
    now: datetime,
    staleness_days: int,
) -> SweepResult:
    """Fold current fingerprints into existing rows.

    - fingerprint already known (any status) -> no-op
    - fingerprint unseen -> new draft row; an open (draft/stale) row for the
      same source is transitioned to superseded and points at the new row
    - a row a human already resolved (filed/skipped) is never touched
    - any row still `draft` past staleness_days from captured_at -> stale
    """
    rows = [dict(r) for r in rows]
    by_id = {r["id"]: r for r in rows}
    result = SweepResult(rows=rows)
    stamp = fmt_ts(now)

    for fp in fingerprints:
        if fp["id"] in by_id:
            continue

        row = {
            "id": fp["id"],
            "source_kind": fp["source_kind"],
            "source_path": fp["source_path"],
            "source_ref": fp["source_ref"],
            "title": fp.get("title") or fp["source_path"],
            "captured_at": stamp,
            "status": "draft",
            "status_changed_at": stamp,
            "summary": fp.get("summary"),
            "board": fp.get("board"),
            "superseded_by": None,
            "notes": "",
        }

        for old in rows:
            same_source = (
                old["source_kind"] == row["source_kind"]
                and old["source_path"] == row["source_path"]
            )
            if same_source and old["status"] in ("draft", "stale"):
                old["status"] = "superseded"
                old["status_changed_at"] = stamp
                old["superseded_by"] = row["id"]
                result.superseded.append(old)

        rows.append(row)
        by_id[row["id"]] = row
        result.new.append(row)

    cutoff = now - timedelta(days=staleness_days)
    for row in rows:
        if row["status"] != "draft":
            continue
        if parse_ts(row["captured_at"]) < cutoff:
            row["status"] = "stale"
            row["status_changed_at"] = stamp
            result.newly_stale.append(row)

    return result


# ── store ─────────────────────────────────────────────────────────────


def load_index(intake_dir: Path) -> list[dict]:
    path = Path(intake_dir).expanduser() / "index.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    return payload.get("rows", [])


def save_index(intake_dir: Path, rows: list[dict]) -> None:
    intake_dir = Path(intake_dir).expanduser()
    intake_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "generated_at": fmt_ts(datetime.now(timezone.utc)),
        "rows": rows,
    }
    (intake_dir / "index.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def write_drafts(intake_dir: Path, rows: list[dict]) -> None:
    drafts = Path(intake_dir).expanduser() / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (drafts / f"{row['id']}.md").write_text(render_draft(row), encoding="utf-8")


def fold_human_edits(intake_dir: Path, rows: list[dict]) -> list[dict]:
    """Fold `status:`/notes a human edited in drafts/*.md back into the index."""
    drafts = Path(intake_dir).expanduser() / "drafts"
    if not drafts.is_dir():
        return rows

    out = []
    for row in rows:
        row = dict(row)
        edits = read_human_edits(drafts, row["id"])
        if edits.get("status") and edits["status"] != row["status"]:
            row["status"] = edits["status"]
            row["status_changed_at"] = fmt_ts(datetime.now(timezone.utc))
        if "notes" in edits:
            row["notes"] = edits["notes"]
        out.append(row)
    return out


# ── sweep runner ──────────────────────────────────────────────────────

SOURCE_KINDS = ("plan", "signal_log_entry", "mesh_done_card", "skill_reference")


def _resolve(path_str: str, repo_root: Path) -> Path:
    path = Path(path_str).expanduser()
    return path if path.is_absolute() else (Path(repo_root).expanduser() / path)


def collect_fingerprints(
    config: dict,
    repo_root: Path,
    sources: list[str] | None = None,
    since_epoch: int | None = None,
) -> tuple[list[dict], dict[str, dict]]:
    """Enumerate current fingerprints across every enabled, requested source.

    Returns `(fingerprints, sources_report)` — the report covers every
    enabled, requested source with its resolved path, whether that path
    exists, and how many fingerprints it yielded. `run_sweep()` uses it to
    fail closed instead of reading a missing source as "nothing to draft".
    """
    wanted = set(sources or SOURCE_KINDS)
    src = config.get("sources", {})
    out: list[dict] = []
    sources_report: dict[str, dict] = {}

    plans = src.get("plans", {})
    if plans.get("enabled") and "plan" in wanted:
        plans_path = _resolve(plans["path"], repo_root)
        fps = collect_file_fingerprints("plan", plans_path, "*.md")
        out += fps
        sources_report["plan"] = {
            "path": str(plans_path),
            "exists": plans_path.is_dir(),
            "count": len(fps),
        }

    signal = src.get("signal_log", {})
    if signal.get("enabled") and "signal_log_entry" in wanted:
        signal_path = _resolve(signal["path"], repo_root)
        fps = collect_signal_fingerprints(
            signal_path,
            config.get("filters", {}).get("signal_log", {}),
        )
        out += fps
        sources_report["signal_log_entry"] = {
            "path": str(signal_path),
            "exists": signal_path.is_dir(),
            "count": len(fps),
        }

    cards = src.get("mesh_done_cards", {})
    if cards.get("enabled") and "mesh_done_card" in wanted:
        template = cards.get(
            "db_template",
            DEFAULT_CONFIG["sources"]["mesh_done_cards"]["db_template"],
        )
        require_result_boards = cards.get("require_result_boards", [])
        for board in config.get("boards", []):
            db_path = Path(template.format(board=board)).expanduser()
            fps = collect_board_fingerprints(
                board,
                db_path,
                cards.get("title_exclude_patterns", []),
                since_epoch=since_epoch,
                require_result=board in require_result_boards,
            )
            out += fps
            sources_report[f"mesh_done_card:{board}"] = {
                "path": str(db_path),
                "exists": db_path.is_file(),
                "count": len(fps),
            }

    refs = src.get("skill_references", {})
    if refs.get("enabled") and "skill_reference" in wanted:
        for i, tree in enumerate(refs.get("trees", [])):
            tree_path = _resolve(tree, repo_root)
            fps = collect_file_fingerprints("skill_reference", tree_path, "*.md")
            out += fps
            sources_report[f"skill_reference:{i}"] = {
                "path": str(tree_path),
                "exists": tree_path.is_dir(),
                "count": len(fps),
            }

    if since_epoch is not None:
        out = [fp for fp in out if _fingerprint_epoch(fp, since_epoch)]
    return out, sources_report


def _fingerprint_epoch(fp: dict, since_epoch: int) -> bool:
    """`--since` for file sources: keep files modified after the cutoff.

    Board rows are already filtered in SQL (their fingerprint carries no
    filesystem mtime), so they pass through untouched.
    """
    if fp["source_kind"] == "mesh_done_card":
        return True
    path = Path(fp["source_path"]).expanduser()
    try:
        return path.stat().st_mtime > since_epoch
    except OSError:
        return True


def run_sweep(
    config: dict,
    intake_dir: Path,
    repo_root: Path,
    now: datetime | None = None,
    sources: list[str] | None = None,
    since_epoch: int | None = None,
    dry_run: bool = False,
    strict_sources: bool = True,
) -> SweepResult:
    """One sweep tick: collect → reconcile → age → persist.

    Fails closed by default: a missing configured source path reads as an
    error, not as "nothing to draft" (a `--dry-run` against a dead path used
    to report 0 new and look clean). `strict_sources=False` opts back into
    the old silent-skip behavior.
    """
    now = now or datetime.now(timezone.utc)
    intake_dir = Path(intake_dir).expanduser()

    rows = fold_human_edits(intake_dir, load_index(intake_dir))
    fingerprints, sources_report = collect_fingerprints(config, repo_root, sources, since_epoch)

    if strict_sources:
        missing = [
            f"{kind}={info['path']}" for kind, info in sources_report.items() if not info["exists"]
        ]
        if missing:
            sys.stderr.write(f"distillery-intake: missing source paths: {', '.join(missing)}\n")
            raise SystemExit(2)

    result = reconcile(
        rows=rows,
        fingerprints=fingerprints,
        now=now,
        staleness_days=int(config.get("staleness_days", 5)),
    )
    result.sources = sources_report

    if not dry_run:
        save_index(intake_dir, result.rows)
        changed = {r["id"]: r for r in result.new + result.newly_stale + result.superseded}
        # Rows whose human-edited status was folded back in also need a redraw,
        # otherwise the file and the index disagree on the next read.
        for row in result.rows:
            if row["id"] not in changed and not (
                Path(intake_dir / "drafts" / f"{row['id']}.md").is_file()
            ):
                changed[row["id"]] = row
        write_drafts(intake_dir, list(changed.values()))

    return result


# ── CLI ───────────────────────────────────────────────────────────────


def _parse_since(value: str) -> int:
    """`--since` accepts `7d` / `12h` or an ISO8601 UTC timestamp."""
    value = value.strip()
    m = re.fullmatch(r"(\d+)([dh])", value)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        delta = timedelta(days=amount) if unit == "d" else timedelta(hours=amount)
        return int((datetime.now(timezone.utc) - delta).timestamp())
    for fmt in (TS_FMT, "%Y-%m-%d"):
        try:
            return int(datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    raise SystemExit(f"distillery-intake: cannot parse --since {value!r} (use 7d, 12h, or ISO8601)")


def main(argv: list[str] | None = None) -> int:
    import argparse

    repo_root_default = Path(__file__).resolve().parents[1]
    intake_default = repo_root_default / "docs" / "research" / "distillery-intake"

    ap = argparse.ArgumentParser(
        prog="distillery_intake_sweep.py",
        description="PULL durable artifacts into draft intake rows (report only).",
    )
    ap.add_argument("--intake-dir", default=str(intake_default))
    ap.add_argument("--config", default=None, help="defaults to <intake-dir>/config.yaml")
    ap.add_argument("--repo-root", default=str(repo_root_default))
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--since", default=None, help="only artifacts newer than 7d / 12h / ISO8601")
    ap.add_argument(
        "--source",
        action="append",
        choices=list(SOURCE_KINDS),
        help="restrict to one source kind (repeatable, for debug)",
    )
    ap.add_argument(
        "--mark",
        action="append",
        metavar="ID=STATUS",
        help="human verdict: flip a row to filed|skipped (repeatable)",
    )
    ap.add_argument(
        "--allow-missing-source",
        action="store_true",
        help="do not fail closed when a configured source path is missing",
    )
    args = ap.parse_args(argv)

    intake_dir = Path(args.intake_dir).expanduser()
    config_path = Path(args.config).expanduser() if args.config else intake_dir / "config.yaml"

    # Fail closed on an unconfigured intake dir. The dual-write copy at
    # ~/.t1000/scripts/ resolves its default repo root to ~/.t1000, so running
    # it flagless would otherwise seed a second store against the wrong tree —
    # silently, and looking like a successful first sweep.
    if not config_path.is_file():
        sys.stderr.write(
            f"distillery-intake: no config.yaml at {config_path}\n"
            "  Point --intake-dir at the configured store (repo: "
            "docs/research/distillery-intake), or pass --config explicitly.\n"
        )
        return 2

    config = load_config(config_path)

    if args.mark:
        return _apply_marks(intake_dir, args.mark, as_json=args.json)

    result = run_sweep(
        config,
        intake_dir,
        repo_root=Path(args.repo_root).expanduser(),
        sources=args.source,
        since_epoch=_parse_since(args.since) if args.since else None,
        dry_run=args.dry_run,
        strict_sources=not args.allow_missing_source,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "counts": {
                        "new": len(result.new),
                        "stale": len(result.newly_stale),
                        "superseded": len(result.superseded),
                        "total_rows": len(result.rows),
                    },
                    "new": [
                        {k: r[k] for k in ("id", "source_kind", "source_path", "title")}
                        for r in result.new
                    ],
                    "newly_stale": [
                        {k: r[k] for k in ("id", "source_kind", "source_path", "title")}
                        for r in result.newly_stale
                    ],
                    "sources": result.sources,
                },
                indent=2,
            )
        )
        return 0

    report = format_report(result)
    if not args.dry_run:
        _write_state(result)
    if report:
        sys.stdout.write(report)
    return 0


def _apply_marks(intake_dir: Path, marks: list[str], as_json: bool = False) -> int:
    rows = load_index(intake_dir)
    by_id = {r["id"]: r for r in rows}
    stamp = fmt_ts(datetime.now(timezone.utc))
    changed = []

    for mark in marks:
        row_id, sep, status = mark.partition("=")
        if not sep or status not in STATUS_TERMINAL:
            raise SystemExit(
                f"distillery-intake: --mark expects ID={'|'.join(STATUS_TERMINAL)}, got {mark!r}"
            )
        row = by_id.get(row_id)
        if row is None:
            raise SystemExit(f"distillery-intake: no such row {row_id!r}")
        row["status"] = status
        row["status_changed_at"] = stamp
        changed.append(row)

    save_index(intake_dir, rows)
    write_drafts(intake_dir, changed)
    if as_json:
        print(json.dumps({"marked": [{"id": r["id"], "status": r["status"]} for r in changed]}))
    return 0


def _write_state(result: SweepResult) -> None:
    """Audit breadcrumb for the cron, mirroring the hygiene sweep's state file."""
    state_path = (
        Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
        / "cache"
        / "distillery-intake-sweep-state.json"
    )
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "ts": fmt_ts(datetime.now(timezone.utc)),
                    "new": len(result.new),
                    "stale": len(result.newly_stale),
                    "superseded": len(result.superseded),
                    "total_rows": len(result.rows),
                    "sources": result.sources,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        # State is a breadcrumb, never the product — a read-only cache dir
        # must not fail the sweep.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
