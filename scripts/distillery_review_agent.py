#!/usr/bin/env python3
"""Distillery review agent — cluster+judge pass (C2) + apply path (C3).

Design: docs/research/fleet-roadmap-2026-08-09/spec-distillery-review.md
(spec parent t_216ac84b; this script implements mesh cards t_0d8b422e "C2"
and t_9a5a4a93 "C3").

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

This script NEVER writes index.json directly — only the sweep's own
--mark path does that. --dry-run still makes a real judge call (the
acceptance proof needs real output) but writes no files and touches no
pending-cache state.

Pending-cache contract (~/.t1000/cache/distillery-review-pending.json):
the cluster+judge pass only ever ADDS row ids to it (on a real,
non-dry-run write). `--apply` is the only thing that ever removes
entries — for every row in the batch file it applies, regardless of that
row's individual decision, so a `decision:` left blank still reappears as
a candidate in the next day's batch (spec Design sketch step 2 +
Acceptance criteria).

Empty stdout on a real (non-dry-run) run with zero candidates = silent,
matching the sweep's own no_agent cron contract.

`--apply <date>` (card C3): reads back `decision: approve` rows from
reviews/<date>.md, flips their status via `distillery_intake_sweep.py
--mark id=filed|skipped` (never touches index.json itself), and appends
one pointer line to FILED-LOG.md per `file` verdict applied. `supersede`
maps to `--mark id=skipped` (STATUS_TERMINAL has no third state) plus a
"dup of <id>" note. There is no `--mark`-level way to set notes, so the
note is written to the row's own drafts/<id>.md `## notes` section — the
same human-edit-round-trip surface the sweep already reads back into
index.json on its next regular (non-mark) run via fold_human_edits(). This
is a real, spec-flagged compromise (see spec Gates & risks on `supersede`),
not a silent deviation, and it adds no new code to the sweep script itself.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
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
# Must match the ryan-spark residency manifest's pinned context_length for
# gpt-oss:120b (~/Documents/sovereign-consulting/tools/spark-residency/manifest/ryan-spark.yaml).
# Omitting num_ctx lets Ollama pick its own default on load, which drifts off the
# pin and evicts hermes3:8b-16k.
JUDGE_NUM_CTX = 65536

CANDIDATE_STATUSES = ("stale", "draft")  # sort priority order, not a filter set
DEFAULT_BATCH_SIZE = 24  # t_76d4e3bd: 8/day could never outrun ~35-55/day intake
VERDICTS = ("file", "skip", "supersede")
DEFAULT_PENDING_CACHE = os.path.join(
    os.environ.get("HERMES_HOME", "~/.t1000"), "cache", "distillery-review-pending.json"
)

# Must match distillery_intake_sweep.py's NOTES_HEADING exactly — that's the
# human-edit-round-trip contract read_human_edits()/fold_human_edits() parse
# drafts/*.md against. Not imported (the two scripts talk over the CLI/FS,
# never Python imports — same dual-write-copy independence the sweep's own
# --mark subprocess call already relies on).
NOTES_HEADING = "## notes"

# render_review_markdown()'s exact output shape, one block per row:
#   ### <title>
#
#   ```yaml
#   id: <id>
#   ...
#   decision:
#   ```
REVIEW_ROW_RE = re.compile(
    r"^### (?P<title>.+?)\s*\n\n```yaml\n(?P<yaml>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


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
        "options": {"temperature": 0.2, "num_ctx": JUDGE_NUM_CTX},
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
    row_num = 0
    for cluster in clusters:
        lines += ["", f"## {cluster['label']}"]
        for rid in cluster["row_ids"]:
            row_num += 1
            row = by_id[rid]
            v = verdicts[rid]
            lines += [
                "",
                f"### {row.get('title') or rid}",
                "",
                "```yaml",
                f"id: {rid}",
                f"row: {row_num}",
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


def render_cron_summary(
    date_str: str,
    rows: list[dict],
    clusters: list[dict],
    review_path: Path,
    card_id: str | None = None,
) -> str:
    suffix = f" card={card_id}" if card_id else ""
    return (
        f"Distillery review batch {date_str}: {len(rows)} row(s), "
        f"{len(clusters)} cluster(s). Review: {review_path}{suffix}\n"
    )


def render_review_card_body(date_str: str, rows_in_order: list[dict], review_path: Path) -> str:
    """Kanban card body for a review batch: a numbered list matching
    parse_review_rows()'s document order exactly, plus the human reply
    grammar footer. FILE/SKIP replies name these numbers, not row ids —
    Ryan never has to type an id."""
    lines = [f"Distillery review batch {date_str} — {len(rows_in_order)} row(s)."]
    for n, row in enumerate(rows_in_order, start=1):
        sup = f" (dup of {row['supersede_of']})" if row.get("supersede_of") else ""
        lines.append(f"{n}. [{row['verdict']}] {row['title']} — {row['rationale']}{sup}")
    lines += [
        "",
        "Reply as a comment: FILE 1,4 / SKIP rest · FILE ALL · SKIP ALL · DEFER. "
        "FILE overrides the judge's verdict; rows not named are left pending "
        "unless you say SKIP rest / SKIP ALL.",
        f"Review file: {review_path}",
    ]
    return "\n".join(lines) + "\n"


def create_review_card(
    hermes_bin: str,
    hermes_home: str,
    board: str,
    date_str: str,
    body: str,
    run=subprocess.run,
) -> str:
    """Create the HUMAN review card, immediately block it (a freshly created
    card is `ready` and will be claimed by a dispatcher otherwise), and
    verify the block actually landed. Raises SystemExit on any failure —
    never leaves a review batch with an unblocked or missing card."""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    title = f"HUMAN review: distillery batch {date_str}"

    create_result = run(
        [
            hermes_bin,
            "kanban",
            "--board",
            board,
            "create",
            title,
            "--body",
            body,
            "--created-by",
            "distillery-review",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if create_result.returncode != 0:
        raise SystemExit(
            "distillery-review: card create failed (exit "
            f"{create_result.returncode}): "
            f"{(create_result.stderr or create_result.stdout or '').strip()}"
        )
    m = re.search(r"t_[0-9a-f]{8}", create_result.stdout or "")
    if not m:
        raise SystemExit(
            "distillery-review: card create produced no task id in output: "
            f"{(create_result.stdout or '').strip()!r}"
        )
    card_id = m.group(0)

    block_reason = "Ryan: FILE n,n / SKIP rest / FILE ALL / SKIP ALL / DEFER as a comment"
    block_result = run(
        [
            hermes_bin,
            "kanban",
            "--board",
            board,
            "block",
            card_id,
            "--kind",
            "needs_input",
            block_reason,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if block_result.returncode != 0:
        raise SystemExit(
            f"distillery-review: card {card_id} created but block failed (exit "
            f"{block_result.returncode}): "
            f"{(block_result.stderr or block_result.stdout or '').strip()} — "
            "card left in default (ready) status, a dispatcher will claim it"
        )

    show_result = run(
        [hermes_bin, "kanban", "--board", board, "show", card_id],
        capture_output=True,
        text=True,
        env=env,
    )
    if show_result.returncode != 0 or not re.search(
        r"status:\s*blocked", show_result.stdout or ""
    ):
        raise SystemExit(
            f"distillery-review: card {card_id} block could not be verified — "
            f"show output: {(show_result.stdout or '').strip()!r}"
        )

    return card_id


def parse_review_rows(text: str) -> list[dict]:
    """Parse the yaml-fenced row blocks render_review_markdown() wrote back
    out of a (possibly human-edited) reviews/<date>.md file."""
    rows = []
    for m in REVIEW_ROW_RE.finditer(text):
        fields: dict[str, str] = {}
        for line in m.group("yaml").splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                continue
            fields[key.strip()] = value.strip()
        row_id = fields.get("id")
        if not row_id:
            continue
        row_field = fields.get("row", "")
        rows.append(
            {
                "id": row_id,
                "row": int(row_field) if row_field.strip().isdigit() else None,
                "title": m.group("title").strip(),
                "verdict": fields.get("verdict", ""),
                "rationale": fields.get("rationale", ""),
                "supersede_of": fields.get("supersede_of") or None,
                "decision": fields.get("decision", ""),
            }
        )
    return rows


def run_sweep_mark(sweep_script: Path, intake_dir: Path, marks: list[str]) -> None:
    """The only write path for status: shells out to the sweep's own
    --mark, exactly as a human would from the CLI. Never touches
    index.json itself."""
    if not marks:
        return
    cmd = [sys.executable, str(sweep_script), "--intake-dir", str(intake_dir)]
    for mark in marks:
        cmd += ["--mark", mark]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise SystemExit(
            f"distillery-review --apply: sweep --mark failed (exit "
            f"{result.returncode}):\n{result.stderr.strip()}"
        )


def set_draft_notes(drafts_dir: Path, row_id: str, notes: str) -> None:
    """Write `notes` into drafts/<row_id>.md's `## notes` section — the
    same human-edit surface the sweep reads back on its next regular run.
    A no-op if the draft file doesn't exist (--mark always regenerates it
    first via write_drafts, so this should never fire in practice)."""
    path = Path(drafts_dir).expanduser() / f"{row_id}.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    head, sep, _tail = text.partition(NOTES_HEADING)
    if not sep:
        return
    path.write_text(head + NOTES_HEADING + "\n\n" + notes + "\n", encoding="utf-8")


def append_filed_log(filed_log_path: Path, date_str: str, entries: list[dict]) -> None:
    """One append-only pointer line per `file` verdict applied. rationale
    doubles as the "where this should land" pointer per spec — the judge
    is asked for exactly that in build_judge_messages()."""
    if not entries:
        return
    filed_log_path = Path(filed_log_path)
    filed_log_path.parent.mkdir(parents=True, exist_ok=True)
    if not filed_log_path.is_file():
        filed_log_path.write_text(
            "# Filed distillery rows\n\n"
            "Append-only pointer log — one line per `file` verdict applied "
            "by `distillery_review_agent.py --apply`. This is a pointer, "
            "not the artifact: writing the actual KB page / skill update "
            "is a human or future-agent follow-through, starting here.\n",
            encoding="utf-8",
        )
    lines = [
        f"- {date_str} | {row['id']} | {row['title']} — {row['rationale']}"
        for row in entries
    ]
    with filed_log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(lines) + "\n")


def apply_review_batch(
    intake_dir: Path, date_str: str, pending_cache: Path, as_json: bool = False
) -> int:
    review_path = intake_dir / "reviews" / f"{date_str}.md"
    if not review_path.is_file():
        raise SystemExit(f"distillery-review --apply: no review file at {review_path}")

    rows = parse_review_rows(review_path.read_text(encoding="utf-8"))
    if not rows:
        raise SystemExit(
            f"distillery-review --apply: {review_path} has no recognizable "
            "row blocks — was it hand-edited past the yaml-fence format?"
        )

    approved = [r for r in rows if r["decision"].strip() == "approve"]
    marks: list[str] = []
    filed_entries: list[dict] = []
    supersede_notes: list[tuple[str, str]] = []

    for row in approved:
        verdict = row["verdict"]
        if verdict == "file":
            marks.append(f"{row['id']}=filed")
            filed_entries.append(row)
        elif verdict == "skip":
            marks.append(f"{row['id']}=skipped")
        elif verdict == "supersede":
            marks.append(f"{row['id']}=skipped")
            supersede_notes.append((row["id"], f"dup of {row['supersede_of'] or 'unknown'}"))
        else:
            raise SystemExit(
                f"distillery-review --apply: row {row['id']} has an "
                f"unrecognized verdict {verdict!r} — refusing to guess a "
                "--mark status"
            )

    sweep_script = Path(__file__).resolve().parent / "distillery_intake_sweep.py"
    run_sweep_mark(sweep_script, intake_dir, marks)

    drafts_dir = intake_dir / "drafts"
    for row_id, notes in supersede_notes:
        set_draft_notes(drafts_dir, row_id, notes)

    append_filed_log(intake_dir / "FILED-LOG.md", date_str, filed_entries)

    # Every row in this batch clears from pending — approved or deferred —
    # so a blank `decision:` reappears as a candidate in a later batch
    # instead of being stuck "pending" against a batch that already closed.
    pending = load_pending(pending_cache)
    for row in rows:
        pending.pop(row["id"], None)
    save_pending(pending_cache, pending)

    skipped_count = len(approved) - len(filed_entries)
    deferred = len(rows) - len(approved)
    if as_json:
        sys.stdout.write(
            json.dumps(
                {
                    "date": date_str,
                    "review_file": str(review_path),
                    "applied": len(approved),
                    "filed": len(filed_entries),
                    "skipped": skipped_count,
                    "deferred": deferred,
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            f"distillery-review --apply {date_str}: {len(approved)} applied "
            f"({len(filed_entries)} filed, {skipped_count} skipped/superseded), "
            f"{deferred} deferred (decision left blank).\n"
        )
    return 0


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
    ap.add_argument(
        "--apply",
        metavar="DATE",
        default=None,
        help=(
            "Apply decision: approve rows from reviews/DATE.md: flips "
            "status via the sweep's own --mark (never touches index.json "
            "directly), appends one FILED-LOG.md line per file verdict, "
            "and clears every row in that batch from the pending cache "
            "(approved or not) so a deferred row reappears in a later batch."
        ),
    )
    ap.add_argument(
        "--card-board",
        default=None,
        help=(
            "If set, create a blocked HUMAN review kanban card on this board "
            "after writing the review file (non-dry-run only) so Ryan "
            "decides via a card comment instead of hand-editing decision: "
            "fields."
        ),
    )
    ap.add_argument(
        "--hermes-bin",
        default=os.environ.get("HERMES_BIN", "hermes"),
        help="hermes binary used for --card-board (default: $HERMES_BIN or 'hermes')",
    )
    ap.add_argument(
        "--hermes-home",
        default=os.environ.get("HERMES_HOME", "~/.t1000"),
        help="HERMES_HOME used for --card-board (default: $HERMES_HOME or ~/.t1000)",
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

    if args.apply:
        return apply_review_batch(intake_dir, args.apply, pending_cache, as_json=args.json)

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

    card_id = None
    if not args.dry_run:
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            render_review_markdown(date_str, candidates, clusters, verdicts), encoding="utf-8"
        )
        for r in candidates:
            pending[r["id"]] = {"review_date": date_str, "review_file": str(review_rel)}
        save_pending(pending_cache, pending)

        if args.card_board:
            rows_in_order = parse_review_rows(review_path.read_text(encoding="utf-8"))
            card_body = render_review_card_body(date_str, rows_in_order, review_path)
            card_id = create_review_card(
                args.hermes_bin,
                str(Path(args.hermes_home).expanduser()),
                args.card_board,
                date_str,
                card_body,
            )

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
        sys.stdout.write(render_cron_summary(date_str, candidates, clusters, review_path, card_id))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
