#!/usr/bin/env python3
"""K2 health-checker findings → parked kanban cards (t_f3dd22e3).

The k2 board's only automated intake was pr-kanban-sync (GitHub PRs).
K2's own deterministic health checkers emit findings that alert humans on
Telegram and stop — the board never learns, so nothing routes the broken
stuff toward workers. This bridge closes that gap with the same contract
pr-kanban-sync proved:

  - ONE card per checker class (39 stale KB pages = one card carrying the
    count + samples), idempotent by checker key.
  - Cards are born and IMMEDIATELY blocked needs_input — an intake card is
    a notification, and notifications never auto-dispatch (PB-006:
    create-then-block sticky; same rule as playbook repair drafting).
  - Count changes get a comment; a clean checker completes its card.
  - Max 5 new cards per run; internal ~6h throttle (findings move daily,
    the pulse fires half-hourly).

Since ADR-087 a checker may ALSO carry a "split" block, and then it does two
different things at once — the distinction is the whole design:

  - The BUCKET card above is unchanged and still born-then-blocked. It is a
    notification ("60 stale KB pages"), not a unit of work, and dispatching one
    hands a worker a bucket. PB-006 stands.
  - The SPLITTER mints one ROUTED card per artifact, born `ready` and assigned
    to the lane, each naming one artifact and the receipt that proves it done.
    These are what may run without a human.

A checker with no "split" block can never mint a routed card, so eligibility is
data rather than a code path. Of the four checkers only two qualify today:
wiki-staleness (one KB page per STALE line) and parts-catalog (one uncatalogued
unit). inbox-premise writes coordination files in both lanes and needs judgment
about which pathspec protects a claim; deferred-followups rows are arbitrary
deferred work, mostly owned by the other lane. Both stay bucket-only.

Routed cards are capped two ways (per run and in flight) so one 76-item bucket
cannot mint 76 dispatchable cards, are checked against a deny list of
human-review paths, and are never parented to their bucket — a child of a
not-done parent is demoted to todo, and the bucket is sticky-blocked forever.

Runs as a rider on the ops-alert pulse. Checkers execute against the
read-only K2 clone — zero K2-repo changes, no lane contact. Stdout is the
Telegram surface via the pulse. Heartbeat: cache/k2-intake-heartbeat.json.

Canonical: T1000 repo scripts/. Deploy copy: ~/.t1000/scripts/.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".t1000")).expanduser()
_SCRIPT_DESK = Path(__file__).resolve().parent.parent
DESK = _SCRIPT_DESK if (_SCRIPT_DESK / "cache").is_dir() else HOME
CLONE = Path(
    os.environ.get("K2_INTAKE_CLONE", HOME / "src" / "kevin-real-estate-tools")
)
STATE_PATH = DESK / "cache" / "k2-intake-state.json"
HEARTBEAT_PATH = DESK / "cache" / "k2-intake-heartbeat.json"
# devbot, not k2, since ADR-087 ruled the dsh lane its own board. Deliberately
# the DEFAULT rather than an env var in the runner's environment: the pulse
# invokes this with no env= and inherits whatever the cron runner has, so an
# environment-set board silently reverts to k2 on any restart or re-provision
# and nothing reports it. K2_INTAKE_BOARD still overrides for a one-off.
BOARD = os.environ.get("K2_INTAKE_BOARD", "devbot")
HERMES = os.environ.get("K2_INTAKE_HERMES_BIN", str(Path.home() / ".local" / "bin" / "hermes"))
THROTTLE_SECS = int(os.environ.get("K2_INTAKE_THROTTLE_SECS") or 6 * 3600)
MAX_NEW_CARDS_PER_RUN = 5

# --- Auto-route (ADR-087, harness t_89dc4076) ------------------------------
# A bucket card ("60 stale KB pages") is a NOTIFICATION and stays sticky-blocked
# forever (PB-006). What may be dispatched without a human is what the SPLITTER
# produces from it: one card per artifact, each naming its receipt. A checker
# without a "split" block is bucket-only and can never mint a routed card.
ROUTED_ASSIGNEE = os.environ.get("K2_INTAKE_ROUTED_ASSIGNEE", "dsh")
MAX_NEW_ROUTED_PER_RUN = int(os.environ.get("K2_INTAKE_MAX_ROUTED_PER_RUN") or 3)
MAX_ROUTED_IN_FLIGHT = int(os.environ.get("K2_INTAKE_MAX_ROUTED_IN_FLIGHT") or 6)
# After this many terminal-but-artifact-still-live outcomes, an artifact is
# parked VISIBLY instead of re-carded forever (t_9de2917f).
MAX_ROUTE_ATTEMPTS = int(os.environ.get("K2_INTAKE_MAX_ROUTE_ATTEMPTS") or 2)

# Human-gated regardless of class (ADR-087 decision 3). Checked against the
# repo-relative artifact path; prefix match, so a directory covers its subtree.
DENIED_PREFIXES = (
    "docs/decisions/",
    ".github/workflows/",
    ".claude/hooks/",
    "docs/agent-coordination/inbox-for-",
    "docs/agent-coordination/outbox-from-",
    "docs/agent-coordination/devbot/harness-bench/",  # the wrapper gates itself
    "kevin-lab/",
    "k2-hub/src/k2_hub/arctic/",
    "k2-hub/src/k2_hub/handlers/arctic_api.py",
    "k2-hub/src/k2_hub/sierra_client.py",
    "k2-hub/src/k2_hub/sierra_sandbox.py",
    "k2-hub/src/k2_hub/sendgrid_client.py",
)
DENIED_EXACT = ("CLAUDE.md", "AGENTS.md")


def is_denied(artifact: str) -> bool:
    """True when this artifact may never be auto-routed.

    Evaluates the EDIT TARGET. For a `page::source` pair that is the page —
    the source is only read, and reading CLAUDE.md or a file in the other
    lane to check a claim against it is legitimate. Splitting explicitly
    rather than testing the raw string, because the exact-match entries
    (`CLAUDE.md`, `AGENTS.md`) silently stop matching once a `::source` is
    appended: prefix entries kept working only because the page happens to
    come first, which is luck, not a boundary.
    """
    artifact = (artifact or "").partition("::")[0]
    # NOT lstrip("./") — that strips a character SET, so ".github/workflows/"
    # would become "github/workflows/" and slip the deny list entirely. Caught
    # by test_is_denied_covers_the_adr_087_set_and_traversal.
    a = artifact or ""
    while a.startswith("./"):
        a = a[2:]
    a = a.lstrip("/")
    if not a or ".." in a.split("/"):
        return True
    return a in DENIED_EXACT or a.startswith(DENIED_PREFIXES)

# Each checker: how to run it and how to read its findings.
#   line_re    — count (and sample) stdout lines matching this regex.
#   summary_re — take the count from this regex's first capture group;
#                samples are the first matching-context lines.
CHECKERS = [
    {
        "key": "wiki-staleness",
        "title": "stale knowledge-base pages (sources changed after page)",
        "argv": ["python3", "scripts/wiki_staleness_check.py"],
        "line_re": r"^\s*STALE\s+\S+",
        "split": {
            "cls": 1,
            "page_re": r"^\s*STALE\s+(\S+)",
            "source_re": r"source changed after page:\s+(\S+)",
            "artifact_prefix": "docs/knowledge-base/",
            "title": "KB verify: {page} ({n_sources} drifted source(s))",
            "receipt": (
                "SCOPE — READ THIS FIRST, IT IS NARROWER THAN IT LOOKS. The "
                "page is `{page}`, but you are NOT verifying the whole page. "
                "Verify ONLY the claims that rest on the {n_sources} source(s) "
                "that changed after the page was last committed: {sources}. "
                "Every other source the page lists is out of scope — leave "
                "those claims alone and do not mention them.\n"
                "ARTIFACT: {page} — the claims deriving from those sources.\n"
                "RECEIPT, both halves required:\n"
                "  1. EDIT THE YAML FRONTMATTER at the top of the file (between "
                "the opening and closing `---`): set `updated:` to now and "
                "`last_verified:` to today, changing the existing lines IN "
                "PLACE. Do not add a second copy and do not append these keys "
                "to the document body — they are frontmatter fields and a "
                "duplicate in the body is just noise a human has to clean up.\n"
                "  2. A per-claim table WRITTEN INTO THE DOCUMENT ITSELF, as a "
                "`## Verification` section at the end of the file. Not in your "
                "reply, not in a kanban comment, not in the PR description — "
                "those are not the artifact and do not survive into the repo. "
                "ONE ROW PER CLAIM, each row naming the claim, the source file "
                "AND line number you checked it against, and the verdict "
                "(verified / corrected / removed). A summary such as 'all "
                "claims checked, no discrepancies' is NOT a receipt — it "
                "asserts the check without evidence anyone can re-run, and "
                "will be rejected. If a `## Verification` section already "
                "exists, REPLACE it rather than stacking a second one - and when replacing, CARRY EVERY EXISTING ROW FORWARD. A row you cannot re-confirm gets its verdict cell changed to `stale` or `human`, NEVER silently deleted: evidence that shrinks while last_verified advances is quiet evidence-loss (measured 2026-08-31, two PRs in one run deleted rows whose cited code was unchanged at the cited lines). Delete a row ONLY when its cited target no longer exists, and say so in the verdict cell: removed - target gone.\n"
                "  3. CHANGE NOTHING ELSE. Add your section and edit the two "
                "frontmatter dates; leave every other byte of the document "
                "exactly as you found it. Do not reflow, retitle, or 'tidy' "
                "prose, and do not drop trailing markup — a real run dropped a "
                "closing `**` off the last sentence and left the page with an "
                "unclosed bold marker.\n"
                "READ THIS BEFORE YOU DECIDE THE TABLE IS OPTIONAL. "
                "`scripts/wiki_staleness_check.py` does NOT read `updated:` — it "
                "compares GIT COMMIT TIMES, flagging a page whose sources were "
                "committed after the page itself. So ANY commit touching this "
                "file clears the STALE flag, including a worthless one. The flag "
                "going green therefore proves NOTHING about whether you did the "
                "work, and the per-claim table is the ONLY artifact that carries "
                "evidence. A date bump plus a green checker with no table is "
                "indistinguishable from a whitespace commit — it silences the "
                "detector instead of doing the job.\n"
                "If you cannot produce both halves honestly, `kanban block` and "
                "say why. Silencing the checker without the evidence is the one "
                "unrecoverable failure here."
            ),
        },
    },
    {
        "key": "inbox-premise",
        "title": "inbox items with unprotected progress claims (no Premise line)",
        "argv": ["python3", "scripts/inbox_premise_check.py"],
        "line_re": r"warning:",
    },
    {
        "key": "deferred-followups",
        "title": "deferred follow-ups past due",
        "argv": ["python3", "scripts/deferred_followups_check.py"],
        "summary_re": r"deferred-followups:\s*(\d+)\s+due",
        "sample_re": r"^DUE\s",
    },
    {
        "key": "parts-catalog",
        "title": "part-shaped units missing catalog rows",
        "argv": ["python3", "scripts/parts_catalog_check.py"],
        "summary_re": r"(\d+)\s+uncatalogued",
        "sample_re": r"^\s+\S",
        # PAUSED 2026-08-27 — renamed from "split" so this class cannot mint.
        # Record of why, because the spec below is CORRECT as far as it goes and
        # the next reader will be tempted to just switch it back on:
        #
        # Cataloguing a part takes THREE edits, not two. The TSV row and the
        # PARTS-CATALOG.md section are both necessary and still not sufficient —
        # scripts/test_foundry_genome.py additionally requires a FROZEN ID MINT
        # ("name matches no frozen id and no alias — commit a new id mint"), and
        # that test runs in root-tests. #5662 had a clean TSV row, a matching MD
        # section, a correct header count bump, and passed parts_catalog_check
        # with exit 0 — and root-tests still refused it.
        #
        # Class record: 5 cards, 0 merges. Three corrupted the TSV, one was
        # incomplete because my own "+1/-0" bound forbade the MD half, and the
        # last was defeated by this third gate. Each fix revealed one more
        # requirement, which is the signal to stop minting and go read the
        # whole contract instead of discovering it one red check at a time.
        #
        # To re-enable: teach the card the id-mint step, verify against
        # test_foundry_genome (NOT just parts_catalog_check — that is the check
        # that lulled me twice), then rename this key back to "split".
        "split_PAUSED_needs_id_mint": {
            "cls": 2,
            "artifact_re": r"^\s{2,}(\S+\.py)\s*$",
            "title": "parts catalog: add the row for {artifact}",
            "receipt": (
                "ARTIFACT: TWO edits, and one without the other FAILS the "
                "check. `parts_catalog_check.py` enforces MD PARITY and calls a "
                "mismatch fatal.\n"
                "  (a) ONE new tab-separated row for {artifact}, APPENDED to "
                "`docs/sovereign/parts-catalog.tsv`.\n"
                "  (b) A matching `### <same name>` section in "
                "`docs/sovereign/PARTS-CATALOG.md`, following the shape of the "
                "entries already there (grade/effort/Sierra line, one-paragraph "
                "description, then Proof / Copy when / Depends on / Paths / "
                "Last verified bullets). The NAME must match the TSV row's first "
                "column exactly — that is the key the parity check joins on.\n"
                "SIZE OF THE CHANGE — a hard bound, not a style note. You ADD to "
                "both files. Do NOT rewrite, re-sort, reformat, re-align, or "
                "reproduce existing rows or sections in either. Removing or "
                "altering any existing line is a failure; if your diff shows "
                "deletions outside your own new content, STOP.\n"
                "DISPLAY ARTIFACTS ARE NOT CONTENT. If your tooling shows the "
                "file with line numbers (`1: name...`), or wrapped in tags such "
                "as `<path>`/`<content>`, those come from how the file was READ "
                "and must NEVER be written into it. Two real runs committed "
                "exactly that and destroyed all 415 rows.\n"
                "RECEIPT: run `python3 scripts/parts_catalog_check.py` after your "
                "edit and PASTE ITS VERBATIM OUTPUT, showing {artifact} no longer "
                "listed under COVERAGE. Saying it passes is not the receipt — the "
                "pasted output is. If the unit is genuinely not a reusable part, "
                "the correct deliverable is a COVERAGE_IGNORE entry with the "
                "reason, not a row."
            ),
        },
    },
]


def run_checker(spec: dict, clone: Path) -> dict | None:
    """Run one checker; return {count, samples} or None on failure."""
    try:
        r = subprocess.run(
            spec["argv"],
            cwd=str(clone),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return None
    out = r.stdout or ""
    lines = out.splitlines()
    if "line_re" in spec:
        matches = [ln for ln in lines if re.search(spec["line_re"], ln)]
        return {
            "count": len(matches),
            "samples": [m.strip()[:160] for m in matches[:5]],
            "artifacts": _artifacts(spec, lines),
            "sources_by_artifact": (
                _sources_by_page(spec, lines)
                if "page_re" in (spec.get("split") or {}) else {}
            ),
        }
    m = re.search(spec["summary_re"], out)
    if not m:
        return None
    sample_re = spec.get("sample_re")
    samples = (
        [ln.strip()[:160] for ln in lines if sample_re and re.search(sample_re, ln)][:5]
        if sample_re
        else lines[:3]
    )
    return {
        "count": int(m.group(1)),
        "samples": samples,
        "artifacts": _artifacts(spec, lines),
        "sources_by_artifact": (
            _sources_by_page(spec, lines)
            if "page_re" in (spec.get("split") or {}) else {}
        ),
    }


def _sources_by_page(spec: dict, lines: list[str]) -> dict[str, list[str]]:
    """{page: [sources that drifted]} for a checker reporting drift per source.

    wiki_staleness_check prints a STALE page followed by one indented line per
    source that moved after it. The card is per PAGE, but its SCOPE is these
    sources — measured 2026-08-26, that is a mean of 2.1 rather than "every
    claim on the page", which is what the two refusals were actually about.

    Per-SOURCE cards were tried first (Ryan's initial ruling) and reverted: they
    worked — 3/3 completed, including a page that had refused twice — but two
    cards for one page produce PRs editing identical hunks, proven to conflict,
    and 54% of stale pages have 2+ drifted sources. Serialising per page instead
    would let the first merge clear the page's STALE flag and silently strip the
    remaining sources. Scoping one card is the version with neither cost.
    """
    page_re, src_re = spec["split"]["page_re"], spec["split"]["source_re"]
    prefix = spec["split"].get("artifact_prefix", "")
    out: dict[str, list[str]] = {}
    page = None
    for ln in lines:
        m = re.search(page_re, ln)
        if m:
            page = prefix + m.group(1).strip()
            out.setdefault(page, [])
            continue
        m = re.search(src_re, ln)
        if m and page:
            src = m.group(1).strip()
            if src not in out[page]:
                out[page].append(src)
    return out


def _artifacts(spec: dict, lines: list[str]) -> list[str]:
    """Full repo-relative artifact list for a splittable checker ([] otherwise).

    Deliberately NOT capped the way `samples` is: samples are for a human
    reading a notification, artifacts are the work items. Order-preserving and
    de-duplicated so a checker that reports a path twice mints one card.
    """
    split = spec.get("split")
    if not split:
        return []
    if "page_re" in split:
        return list(_sources_by_page(spec, lines))
    prefix = split.get("artifact_prefix", "")
    out, seen = [], set()
    for ln in lines:
        m = re.search(split["artifact_re"], ln)
        if not m:
            continue
        art = prefix + m.group(1).strip()
        if art not in seen:
            seen.add(art)
            out.append(art)
    return out


def _hermes(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [HERMES, "kanban", "--board", BOARD, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")


def _create_parked_card(spec: dict, finding: dict) -> str | None:
    title = f"K2 INTAKE ({spec['key']}): {finding['count']} — {spec['title']}"
    body = (
        f"Auto-filed by k2_intake_sync from K2's own checker "
        f"`{' '.join(spec['argv'])}` run against the read-only clone. "
        f"Count: {finding['count']}. Samples:\n"
        + "\n".join(f"- {s}" for s in finding["samples"])
        + "\n\nRe-run in a K2 checkout for the full list. This card is a "
        f"NOTIFICATION: triage it — work it, split it, or archive it. It "
        f"auto-completes when the checker returns clean. Card updates its "
        f"count via comments while the finding persists. FINISH PROTOCOL for "
        f"any worker dispatched on this card: if your deliverable changed code "
        f"or opened a PR, end with `kanban request-review` (NOT `complete`) so "
        f"the board reviewer lane issues an independent verdict."
    )
    create = _hermes(
        [
            "create", title,
            "--body", body,
            "--created-by", "k2-intake-sync",
        ]
    )
    m = re.search(r"Created\s+(t_[0-9a-f]+)", create.stdout or "")
    if create.returncode != 0 or not m:
        return None
    card_id = m.group(1)
    _hermes(
        [
            "block", card_id,
            "intake notification — human triage required; never auto-dispatched",
            "--kind", "needs_input",
        ]
    )
    return card_id


def _routed_key(checker_key: str, artifact: str) -> str:
    return f"{checker_key}::{artifact}"


def _card_status(card_id: str) -> str | None:
    """Card status via a read-only peek at the board db; None on any failure.

    None must behave like the old semantics (hold the slot): a broken peek
    that read as terminal would refree slots and re-mint cards — the same
    class of quiet lie this helper exists to end, pointed the other way.
    """
    try:
        import sqlite3
        db = DESK / "kanban" / "boards" / BOARD / "kanban.db"
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = conn.execute("select status from tasks where id = ?", (card_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _board_has_workdir() -> bool:
    """True when this board binds tasks to a repo checkout.

    Read straight off the board's own board.json rather than asked of the CLI:
    it is the file the engine itself resolves, and one cheap read per mint beats
    a subprocess. A missing/unreadable file is treated as unbound — fail closed,
    because the cost of being wrong is a queue full of cards that cannot work.
    """
    try:
        cfg = HOME / "kanban" / "boards" / BOARD / "board.json"
        return bool(json.loads(cfg.read_text(encoding="utf-8")).get("default_workdir"))
    except Exception:
        return False


def _create_routed_card(spec: dict, artifact: str, sources: list[str] | None = None) -> str | None:
    """Mint ONE dispatchable card for ONE artifact.

    Born `ready` and assigned explicitly — no `block` call follows, and that
    asymmetry with `_create_parked_card` is the whole auto-route mechanism.

    Two deliberate non-obvious choices:

    * **Assignee is set here, not inferred.** Nothing in the engine routes to
      the dsh lane: `kanban_estimate.py` has no such preference and the live
      config's only `dsh` reference is a concurrency cap. Verified 2026-08-26;
      mesh card t_3781a500 claims otherwise and is wrong. So assignment is a
      property of the card's class, which is what we wanted anyway.
    * **No `--parent`.** Parenting these to the bucket would look right and
      would strand them: linking a child to a not-done parent demotes it to
      `todo`, and the bucket is sticky-blocked forever by design. The
      relationship is recorded in prose instead.
    """
    # Pre-flight: a routed card is repo work, so a board with no default_workdir
    # mints cards into a scratch dir where EVERY one of them fails identically —
    # the worker cannot see the artifact and blocks. Caught in production on the
    # first live card (t_7418d489, "Unable to locate the file ... in the
    # workspace"). Refuse to mint rather than manufacture guaranteed failures.
    if not _board_has_workdir():
        print(
            f"WARN k2-intake board '{BOARD}' has no default_workdir; refusing to "
            f"mint routed cards (they would run in a scratch dir with no checkout). "
            f"Fix: hermes kanban boards set-default-workdir {BOARD} <repo path>"
        )
        return None

    split = spec["split"]
    # A pair artifact is "page::source"; a plain one is just the path. Both are
    # offered to format() so a checker can use whichever placeholders it wants.
    srcs = sources or []
    fmt = {
        "artifact": artifact,
        "page": artifact,
        "sources": ", ".join(f"`{x}`" for x in srcs) or "(none reported)",
        "n_sources": len(srcs),
    }
    title = split["title"].format(**fmt)
    body = (
        f"Auto-routed by k2_intake_sync from checker `{spec['key']}` "
        f"(class {split['cls']}, ADR-087). This card is ONE unit of work with a "
        f"receipt — not a notification. The bucket card for this checker stays "
        f"blocked and is not yours to touch.\n\n"
        + split["receipt"].format(**fmt)
        + "\n\nIf the deliverable turns out to be larger than this card says, "
        "STOP and `kanban block` with what you found — do not widen the scope "
        "yourself.\n\nFINISH PROTOCOL — unconditional for this card: you WILL "
        "edit a file and the wrapper WILL open a PR, so end with "
        "`kanban request-review`, NEVER `complete`. Do not reason about whether "
        "your change counts as code; it does not matter here. Completing leaves "
        "the card reading done with an unreviewed PR open, which is the orphan "
        "state the reviewer lane exists to prevent."
    )
    create = _hermes(
        [
            "create", title,
            "--body", body,
            "--assignee", ROUTED_ASSIGNEE,
            "--created-by", "k2-intake-sync",
        ]
    )
    m = re.search(r"Created\s+(t_[0-9a-f]+)", create.stdout or "")
    if create.returncode != 0 or not m:
        return None
    return m.group(1)


def sync(force: bool = False) -> dict:
    state = _load_state()
    now = time.time()
    if not force and now - state.get("last_run_ts", 0) < THROTTLE_SECS:
        return {"skipped": "throttled"}
    counts = {
        "checkers": 0, "failed": 0, "new_cards": 0, "updated": 0, "completed": 0,
        "routed_new": 0, "routed_cleared": 0, "routed_denied": 0,
        "slots_refreed": 0, "held_blocked": 0, "parked_failing": 0, "parked_skipped": 0,
    }
    cards = state.setdefault("cards", {})
    routed = state.setdefault("routed", {})
    new_cards_this_run = 0
    routed_this_run = 0
    attempts = state.setdefault("route_attempts", {})
    parked = state.setdefault("parked_artifacts", {})
    for spec in CHECKERS:
        counts["checkers"] += 1
        finding = run_checker(spec, CLONE)
        if finding is None:
            counts["failed"] += 1
            print(f"WARN k2-intake checker failed: {spec['key']}")
            continue
        known = cards.get(spec["key"])
        if finding["count"] > 0 and not known:
            if new_cards_this_run >= MAX_NEW_CARDS_PER_RUN:
                print(f"WARN k2-intake card cap reached; deferring {spec['key']}")
                continue
            card_id = _create_parked_card(spec, finding)
            if card_id:
                cards[spec["key"]] = {"card": card_id, "count": finding["count"]}
                new_cards_this_run += 1
                counts["new_cards"] += 1
                print(
                    f"K2 INTAKE new card {BOARD}/{card_id}: {spec['key']} "
                    f"({finding['count']})"
                )
        elif finding["count"] > 0 and known and finding["count"] != known["count"]:
            _hermes(
                [
                    "comment", known["card"],
                    f"k2-intake update: count {known['count']} -> {finding['count']}",
                ]
            )
            print(
                f"K2 INTAKE {spec['key']}: {known['count']} -> {finding['count']} "
                f"({BOARD}/{known['card']})"
            )
            known["count"] = finding["count"]
            counts["updated"] += 1
        elif finding["count"] == 0 and known:
            _hermes(["unblock", known["card"]])
            _hermes(
                [
                    "complete", known["card"],
                    "--result", f"k2-intake: checker {spec['key']} returned clean",
                ]
            )
            print(f"K2 INTAKE cleared: {spec['key']} ({BOARD}/{known['card']})")
            del cards[spec["key"]]
            counts["completed"] += 1

        # --- splitter: bucket -> one routed card per artifact (ADR-087) ---
        # Reached only when the checker SUCCEEDED (failures `continue` above),
        # so a broken checker can never look like "every artifact cleared" and
        # mass-complete real work.
        if not spec.get("split"):
            continue
        live = finding.get("artifacts") or []

        # Clear first, then mint: completing frees in-flight budget in the same
        # run, so a steadily-worked queue keeps feeding instead of stalling for
        # a full throttle window.
        # NOTE: the per-SOURCE experiment needed a guard here, because merging
        # one pair's PR cleared the whole page and made every other pair for it
        # look resolved. Cards are per PAGE again, so a page leaving the finding
        # means its one card's work really did land — no guard, and none of the
        # dead safety code that would imply otherwise.
        for rkey in [k for k in routed if k.startswith(f"{spec['key']}::")]:
            artifact = rkey.split("::", 1)[1]
            if artifact in live:
                continue
            card_id = routed[rkey]["card"]
            done = _hermes([
                "complete", card_id,
                "--result",
                f"k2-intake: {artifact} no longer reported by checker "
                f"{spec['key']} — the finding this card was minted for is gone",
            ])
            # A worker that already completed it wins; drop our bookkeeping
            # either way so a card we can no longer act on cannot wedge the
            # in-flight budget forever.
            if done.returncode != 0:
                print(f"WARN k2-intake could not complete {card_id} ({artifact})")
            del routed[rkey]
            attempts.pop(rkey, None)
            parked.pop(rkey, None)
            counts["routed_cleared"] += 1

        # A surviving entry is in flight ONLY while its card is still open.
        # Measured 2026-08-30 (t_9de2917f): wiki-staleness sat at its cap for
        # 36h with routed_new=0 and a healthy heartbeat, because TERMINAL
        # cards — done-but-PR-closed, done-then-re-drifted, archived — held
        # slots while their artifacts stayed live. Status is never consulted
        # by the gone-clearing above, so a failed or re-drifted item could
        # neither clear nor re-mint. A terminal card + live artifact is a
        # zombie slot: free it, count the attempt, and after
        # MAX_ROUTE_ATTEMPTS park the artifact VISIBLY rather than re-carding
        # a failure forever. Blocked cards keep their slot (a human owes them
        # an unblock) but are counted in the heartbeat, never silent.
        for rkey in [k for k in routed if k.startswith(f"{spec['key']}::")]:
            zcard = routed[rkey]["card"]
            status = _card_status(zcard)
            if status == "blocked":
                counts["held_blocked"] += 1
                continue
            if status in ("done", "archived"):
                tries = attempts.get(rkey, 0) + 1
                attempts[rkey] = tries
                del routed[rkey]
                counts["slots_refreed"] += 1
                if tries >= MAX_ROUTE_ATTEMPTS:
                    parked[rkey] = {"card": zcard, "tries": tries,
                                    "why": f"card {status} x{tries}, artifact still live"}
                    counts["parked_failing"] += 1
                    print(f"WARN k2-intake PARKED after {tries} attempts: {rkey}")
                else:
                    print(f"K2 INTAKE refreed zombie slot (card {zcard} {status}): {rkey}")
        in_flight = sum(1 for k in routed if k.startswith(f"{spec['key']}::"))
        for artifact in live:
            rkey = _routed_key(spec["key"], artifact)
            if rkey in routed:
                continue
            if rkey in parked:
                counts["parked_skipped"] += 1
                continue
            if is_denied(artifact):
                counts["routed_denied"] += 1
                continue
            if routed_this_run >= MAX_NEW_ROUTED_PER_RUN:
                print(
                    f"WARN k2-intake routed per-run cap reached; deferring "
                    f"{spec['key']} ({len(live)} artifacts live)"
                )
                break
            if in_flight >= MAX_ROUTED_IN_FLIGHT:
                print(
                    f"WARN k2-intake routed in-flight cap reached for "
                    f"{spec['key']} ({in_flight}); deferring the rest"
                )
                break
            card_id = _create_routed_card(
                spec, artifact, (finding.get("sources_by_artifact") or {}).get(artifact)
            )
            if not card_id:
                print(f"WARN k2-intake could not mint routed card for {artifact}")
                continue
            routed[rkey] = {"card": card_id, "artifact": artifact}
            routed_this_run += 1
            in_flight += 1
            counts["routed_new"] += 1
            print(
                f"K2 INTAKE routed {BOARD}/{card_id} -> {ROUTED_ASSIGNEE}: "
                f"{artifact} (class {spec['split']['cls']})"
            )
    state["last_run_ts"] = now
    _save_state(state)
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(
        json.dumps(
            {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **counts}
        ),
        encoding="utf-8",
    )
    return counts


if __name__ == "__main__":
    result = sync(force="--force" in sys.argv)
    print(f"[k2-intake] {result}", file=sys.stderr)
