#!/usr/bin/env python3
"""Distillery review agent — cluster + judge pass (v1, card C2 scope).

Design: docs/research/fleet-roadmap-2026-08-09/spec-distillery-review.md
(spec parent t_216ac84b; this script implements mesh card t_0d8b422e, "C2").

Reads docs/research/distillery-intake/index.json, selects up to
--batch-size candidate rows (status draft/stale, stale-oldest-first then
draft-oldest-first, skipping rows already sitting in an undecided prior
batch), sends title/summary/source_kind/source_path/notes to the
house-pinned local judge (gpt-oss:120b on Ryan Spark, keep_alive <=30m, no
other model touched) for cluster groupings plus a file/skip/supersede
verdict and one-line rationale per row, and renders
docs/research/distillery-intake/reviews/<date>.md with a human-editable
`decision:` field per row.

Endpoint note: the spec names 127.0.0.1:11435/v1/chat/completions, but
Ollama's OpenAI-compat layer is known to silently ignore `keep_alive` in
that request body — it falls back to the server default instead of the
value sent (ollama/ollama#11458). This script calls the native /api/chat
endpoint instead (same host:port, same pinned model) because that is the
endpoint that actually honors a per-request keep_alive, which is the
safety-critical half of the requirement (never leave an un-TTL'd load
pinned on Ryan Spark — the exact landmine already hit once on this box).
Flagged for the C5 arm-gate reviewer; not a silent deviation.

This script NEVER writes index.json — only the sweep's own --mark path
does that (see C3, --apply, not implemented here). --dry-run still makes a
real judge call (the acceptance proof needs real output) but writes no
files and touches no pending-cache state.

Pending-cache contract (~/.t1000/cache/distillery-review-pending.json):
this script only ever ADDS row ids to it (on a real, non-dry-run write).
C3's --apply is the only thing that should ever remove entries — for every
row in the batch file it applies, regardless of that row's individual
decision, so a `decision:` left blank still reappears as a candidate in
the next day's batch (spec Design sketch step 2 + Acceptance criteria).

Empty stdout on a real (non-dry-run) run with zero candidates = silent,
matching the sweep's own no_agent cron contract.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

# Hard-pinned — never make these CLI flags. Spec Non-goals: "No new model,
# no second Spark tenant." Every judge call must hit this exact model with
# a bounded keep_alive; that discipline isn't something a caller should be
# able to override by accident.
JUDGE_BASE = "http://127.0.0.1:11435"
JUDGE_MODEL = "gpt-oss:120b"
JUDGE_KEEP_ALIVE = "30m"
JUDGE_TIMEOUT_S = 300.0

CANDIDATE_STATUSES = ("stale", "draft")  # sort priority order, not a filter set
DEFAULT_BATCH_SIZE = 8
VERDICTS = ("file", "skip", "supersede")
DEFAULT_PENDING_CACHE = "~/.t1000/cache/distillery-review-pending.json"


def fmt_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(TS_FMT)


def load_index(intake_dir: Path) -> list[dict]:
    path = Path(intake_dir).expanduser() / "index.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    return payload.get("rows", [])


def load_pending(cache_path: Path) -> dict[str, dict]:
    cache_path = Path(cache_path).expanduser()
    if not cache_path.is_file():
        return {}
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return payload.get("rows", {})


def save_pending(cache_path: Path, rows: dict[str, dict]) -> None:
    cache_path = Path(cache_path).expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "updated_at": fmt_ts(datetime.now(timezone.utc)),
        "rows": rows,
    }
    cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def select_candidates(rows: list[dict], pending_ids: set[str], batch_size: int) -> list[dict]:
    """Stale-oldest-first, then draft-oldest-first; skip pending rows."""
    open_rows = [
        r
        for r in rows
        if r.get("status") in CANDIDATE_STATUSES and r["id"] not in pending_ids
    ]

    def sort_key(row: dict) -> tuple[int, str]:
        status_rank = CANDIDATE_STATUSES.index(row["status"])
        return (status_rank, row.get("captured_at", ""))

    open_rows.sort(key=sort_key)
    return open_rows[:batch_size]


def build_judge_messages(rows: list[dict]) -> list[dict]:
    row_payload = [
        {
            "id": r["id"],
            "title": r.get("title", ""),
            "summary": r.get("summary") or "",
            "source_kind": r.get("source_kind", ""),
            "source_path": r.get("source_path", ""),
            "notes": r.get("notes") or "",
        }
        for r in rows
    ]
    system = (
        "You are the review judge for the T1000 Distillery intake queue. "
        "Given a batch of candidate rows (durable artifacts awaiting a "
        "file/skip decision), do two things: (1) group related rows into "
        "clusters by theme — every row must land in exactly one cluster; "
        "(2) propose a verdict per row: `file` (worth filing into a KB "
        "page or skill reference), `skip` (not worth filing — already "
        "covered, too narrow, or stale history), or `supersede` (a "
        "near-duplicate of another row in THIS batch — set supersede_of "
        "to that row's id). Every verdict needs a one-line rationale. You "
        "are a recommendation only — nothing you say changes any file; a "
        "human approves or defers every row. Respond with ONLY a JSON "
        "object, no prose, matching exactly this shape: "
        '{"clusters": [{"label": "<short theme>", "row_ids": ["<id>", ...]}], '
        '"verdicts": {"<id>": {"verdict": "file|skip|supersede", '
        '"rationale": "<one line>", "supersede_of": "<id or null>"}}} '
        "Every row id in the input must appear in exactly one cluster and "
        "have exactly one verdicts entry."
    )
    user = json.dumps({"rows": row_payload}, indent=2)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_judge(rows: list[dict]) -> dict:
    url = JUDGE_BASE.rstrip("/") + "/api/chat"
    payload = {
        "model": JUDGE_MODEL,
        "messages": build_judge_messages(rows),
        "stream": False,
        "keep_alive": JUDGE_KEEP_ALIVE,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=JUDGE_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(
            f"distillery-review: judge call to {url} failed: {e}\n"
            f"  ({JUDGE_MODEL} at {JUDGE_BASE} unreachable — check the tunnel; "
            "nothing was written.)"
        )

    content = ((body.get("message") or {}).get("content") or "").strip()
    if not content:
        content = ((body.get("message") or {}).get("thinking") or "").strip()
    if not content:
        raise SystemExit(
            "distillery-review: judge returned no content — raw response: "
            f"{json.dumps(body)[:500]}"
        )
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"distillery-review: judge response was not valid JSON ({e}): {content[:500]}"
        )


def normalize_judge_output(rows: list[dict], raw: dict) -> tuple[list[dict], dict[str, dict]]:
    """Defensive fold: every row gets exactly one cluster + one verdict,
    even if the judge's JSON is incomplete. Safe by construction — nothing
    here ever touches index.json, so the worst case is a bad rationale a
    human skims past and defers, never a bad file/skip landing silently.
    """
    row_ids = {r["id"] for r in rows}
    clusters_raw = raw.get("clusters") or []
    verdicts_raw = raw.get("verdicts") or {}

    assigned: dict[str, str] = {}
    clusters: list[dict] = []
    for c in clusters_raw:
        label = str(c.get("label") or "Uncategorized").strip() or "Uncategorized"
        ids = [rid for rid in (c.get("row_ids") or []) if rid in row_ids and rid not in assigned]
        if not ids:
            continue
        clusters.append({"label": label, "row_ids": ids})
        for rid in ids:
            assigned[rid] = label

    leftover = [r["id"] for r in rows if r["id"] not in assigned]
    if leftover:
        clusters.append({"label": "Uncategorized", "row_ids": leftover})
        for rid in leftover:
            assigned[rid] = "Uncategorized"

    verdicts: dict[str, dict] = {}
    for r in rows:
        rid = r["id"]
        v = verdicts_raw.get(rid) or {}
        verdict = v.get("verdict")
        if verdict not in VERDICTS:
            verdict = "skip"
            rationale = (
                "judge returned no usable verdict for this row "
                "(defaulted to skip — needs a human look)"
            )
            supersede_of = None
        else:
            rationale = str(v.get("rationale") or "").strip() or "(no rationale given)"
            supersede_of = v.get("supersede_of")
            if verdict == "supersede":
                if supersede_of not in row_ids or supersede_of == rid:
                    bad = supersede_of
                    verdict = "skip"
                    rationale = (
                        f"judge flagged supersede but named no valid duplicate "
                        f"in this batch (was {bad!r}) — coerced to skip"
                    )
                    supersede_of = None
            else:
                supersede_of = None
        verdicts[rid] = {
            "cluster": assigned[rid],
            "verdict": verdict,
            "rationale": rationale,
            "supersede_of": supersede_of,
        }

    return clusters, verdicts


def render_review_markdown(
    date_str: str, rows: list[dict], clusters: list[dict], verdicts: dict[str, dict]
) -> str:
    by_id = {r["id"]: r for r in rows}
    lines = [
        f"# Distillery review batch — {date_str}",
        "",
        f"{len(rows)} candidate row(s), {len(clusters)} cluster(s). "
        f"Judge: {JUDGE_MODEL} @ {JUDGE_BASE} (keep_alive {JUDGE_KEEP_ALIVE}).",
        "",
        "Edit `decision:` to `approve` on any row below to accept its "
        "proposed verdict on the next `--apply` run. Leave blank (or "
        "anything else) to defer — the row reappears in a later batch.",
    ]
    for cluster in clusters:
        lines += ["", f"## {cluster['label']}"]
        for rid in cluster["row_ids"]:
            row = by_id[rid]
            v = verdicts[rid]
            lines += [
                "",
                f"### {row.get('title') or rid}",
                "",
                "```yaml",
                f"id: {rid}",
                f"cluster: {cluster['label']}",
                f"verdict: {v['verdict']}",
                f"rationale: {v['rationale']}",
            ]
            if v["supersede_of"]:
                lines.append(f"supersede_of: {v['supersede_of']}")
            lines += ["decision:", "```"]
            if row.get("summary"):
                lines += ["", row["summary"]]
            lines += ["", f"source: [{row.get('source_kind')}] {row.get('source_path')}"]
    return "\n".join(lines).rstrip() + "\n"


def render_dry_run_report(rows: list[dict], clusters: list[dict], verdicts: dict[str, dict]) -> str:
    by_id = {r["id"]: r for r in rows}
    lines = [
        f"distillery-review --dry-run: {len(rows)} candidate row(s), "
        f"{len(clusters)} cluster(s) (nothing written)"
    ]
    for cluster in clusters:
        lines.append(f"\n## {cluster['label']}")
        for rid in cluster["row_ids"]:
            row = by_id[rid]
            v = verdicts[rid]
            sup = f" (dup of {v['supersede_of']})" if v["supersede_of"] else ""
            lines.append(f"- [{v['verdict']}{sup}] {row.get('title') or rid} — {v['rationale']}")
    return "\n".join(lines) + "\n"


def render_cron_summary(date_str: str, rows: list[dict], clusters: list[dict], review_path: Path) -> str:
    return (
        f"Distillery review batch {date_str}: {len(rows)} row(s), "
        f"{len(clusters)} cluster(s). Review: {review_path}\n"
    )


def main(argv: list[str] | None = None) -> int:
    repo_root_default = Path(__file__).resolve().parents[1]
    intake_default = repo_root_default / "docs" / "research" / "distillery-intake"

    ap = argparse.ArgumentParser(
        prog="distillery_review_agent.py",
        description=(
            "Cluster + judge pass over the distillery intake queue "
            "(report-only; never touches index.json)."
        ),
    )
    ap.add_argument(
        "--intake-dir",
        default=None,
        help=(
            "Required in practice: this script is dual-written to "
            "~/.t1000/scripts/ for cron, where __file__-derived defaults "
            "resolve to the wrong tree (same fragility distillery_intake_sweep.py "
            "carries, made safe there only because its cron wrapper always "
            "passes --intake-dir explicitly — see distillery_sweep_cron.sh). "
            "No default here on purpose: silently writing a review nobody can "
            "find is worse than refusing to run."
        ),
    )
    ap.add_argument("--repo-root", default=str(repo_root_default))
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--pending-cache", default=DEFAULT_PENDING_CACHE)
    ap.add_argument("--dry-run", action="store_true", help="judge for real, write nothing")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--date", default=None, help="override batch date (testing only; default today UTC)"
    )
    args = ap.parse_args(argv)

    if args.intake_dir is None:
        ap.error(
            "--intake-dir is required. This script runs from two copies "
            f"(repo canonical + ~/.t1000/scripts/ dual-write); the __file__-"
            f"derived guess would be {intake_default} from wherever it's "
            "invoked, which is silently wrong from the dual-write copy. "
            "Pass the real repo path explicitly, matching "
            "distillery_sweep_cron.sh's pattern for its sibling script."
        )

    intake_dir = Path(args.intake_dir).expanduser()
    pending_cache = Path(args.pending_cache).expanduser()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows = load_index(intake_dir)
    pending = load_pending(pending_cache)
    candidates = select_candidates(rows, set(pending.keys()), args.batch_size)

    if not candidates:
        if args.json:
            sys.stdout.write(json.dumps({"date": date_str, "candidates": 0, "written": False}) + "\n")
        elif args.dry_run:
            sys.stdout.write(
                "distillery-review --dry-run: no candidate rows (draft/stale, not already pending)\n"
            )
        # else: real cron run, zero candidates -> silent (matches sweep contract)
        return 0

    raw = call_judge(candidates)
    clusters, verdicts = normalize_judge_output(candidates, raw)

    review_rel = Path("reviews") / f"{date_str}.md"
    review_path = intake_dir / review_rel

    if not args.dry_run:
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            render_review_markdown(date_str, candidates, clusters, verdicts), encoding="utf-8"
        )
        for r in candidates:
            pending[r["id"]] = {"review_date": date_str, "review_file": str(review_rel)}
        save_pending(pending_cache, pending)

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "date": date_str,
                    "candidates": len(candidates),
                    "clusters": clusters,
                    "verdicts": verdicts,
                    "written": not args.dry_run,
                    "review_file": str(review_path) if not args.dry_run else None,
                },
                indent=2,
            )
            + "\n"
        )
    elif args.dry_run:
        sys.stdout.write(render_dry_run_report(candidates, clusters, verdicts))
    else:
        sys.stdout.write(render_cron_summary(date_str, candidates, clusters, review_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
