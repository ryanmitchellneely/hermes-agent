"""K2 intake bridge (t_f3dd22e3): checker findings become parked cards.

Contract under test: one card per checker class, born-then-blocked (never
dispatchable on arrival), count changes comment, clean checkers complete
their card, new cards capped per run, runs throttled.
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def mod(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("K2_INTAKE_CLONE", str(tmp_path / "clone"))
    (tmp_path / "cache").mkdir()
    (tmp_path / "clone").mkdir()
    spec = importlib.util.spec_from_file_location(
        "k2_intake_sync", REPO / "scripts" / "k2_intake_sync.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


class HermesStub:
    def __init__(self):
        self.calls = []
        self.next_id = 0xA000

    def __call__(self, args):
        self.calls.append(args)

        class R:
            returncode = 0
            stdout = ""

        if args[0] == "create":
            self.next_id += 1
            R.stdout = f"Created t_{self.next_id:08x}\n"
        return R()

    def verbs(self):
        return [c[0] for c in self.calls]


def _fix_checkers(mod, findings):
    """Replace checker execution: findings maps key -> {count, samples}."""
    mod.run_checker = lambda spec, clone: findings.get(spec["key"])


def test_finding_creates_card_then_blocks_it(mod):
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(mod, {"wiki-staleness": {"count": 39, "samples": ["a.md", "b.md"]}})
    counts = mod.sync(force=True)
    assert counts["new_cards"] == 1
    assert stub.verbs() == ["create", "block"]
    assert "needs_input" in stub.calls[1]


def test_count_change_comments_once_and_clean_completes(mod):
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(mod, {"wiki-staleness": {"count": 39, "samples": []}})
    mod.sync(force=True)
    _fix_checkers(mod, {"wiki-staleness": {"count": 41, "samples": []}})
    c2 = mod.sync(force=True)
    assert c2["updated"] == 1
    _fix_checkers(mod, {"wiki-staleness": {"count": 0, "samples": []}})
    c3 = mod.sync(force=True)
    assert c3["completed"] == 1
    assert stub.verbs() == ["create", "block", "comment", "unblock", "complete"]


def test_same_count_is_silent(mod):
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(mod, {"wiki-staleness": {"count": 39, "samples": []}})
    mod.sync(force=True)
    n = len(stub.calls)
    mod.sync(force=True)
    assert len(stub.calls) == n  # no comment, no create — nothing changed


def test_new_card_cap_per_run(mod, monkeypatch):
    stub = HermesStub()
    mod._hermes = stub
    mod.MAX_NEW_CARDS_PER_RUN = 2
    mod.CHECKERS = [
        {"key": f"k{i}", "title": "t", "argv": ["true"], "line_re": "x"} for i in range(4)
    ]
    _fix_checkers(mod, {f"k{i}": {"count": 1, "samples": []} for i in range(4)})
    counts = mod.sync(force=True)
    assert counts["new_cards"] == 2


def test_throttle_skips_unforced_runs(mod):
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(mod, {"wiki-staleness": {"count": 1, "samples": []}})
    mod.sync(force=True)
    result = mod.sync(force=False)
    assert result == {"skipped": "throttled"}


def test_failed_checker_never_creates_or_completes(mod):
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(mod, {"wiki-staleness": {"count": 3, "samples": []}})
    mod.sync(force=True)
    # Checker now errors (returns None): the existing card must be left
    # alone — a broken checker is not a clean checker.
    _fix_checkers(mod, {})
    counts = mod.sync(force=True)
    assert counts["completed"] == 0
    assert "complete" not in stub.verbs()


def test_real_checker_parsers_against_recorded_output(mod):
    """Pin the four regexes against verbatim output captured live 2026-08-19."""
    import re
    wiki = "Wiki staleness check — 73 pages\n  STALE  a.md\n  FRESH  b.md\n  STALE  c.md\n"
    premise = "x.md:1: warning: progress-claim language but no Premise: line\n"
    deferred = "deferred-followups: 46 due, 167 waiting, 0 dropped\n\nDUE  [x] owner=k\n"
    parts = "parts-catalog check: 398 parts, 0 rotted paths, 24 uncatalogued units\n"
    specs = {s["key"]: s for s in mod.CHECKERS}
    assert len([l for l in wiki.splitlines() if re.search(specs["wiki-staleness"]["line_re"], l)]) == 2
    assert len([l for l in premise.splitlines() if re.search(specs["inbox-premise"]["line_re"], l)]) == 1
    assert re.search(specs["deferred-followups"]["summary_re"], deferred).group(1) == "46"
    assert re.search(specs["parts-catalog"]["summary_re"], parts).group(1) == "24"


# --- card-template clauses for the 19 close causes (campaign option 1,
# harness t_39357274/t_da2f74c4) --------------------------------------------
#
# Each clause below maps to a close-cause bucket recorded in
# docs/research/2026-09-05-next-agent-build/VERIFY-code-reader.md target 5's
# corrected bucketing (vacuous 6, hollow 3, stale/superseded 5, scope-overrun
# 3, format/gate-parse 1, circular-cite 1 = 19). These tests render the
# amended wiki-staleness receipt template and assert each new clause survived
# — a template edit that silently drops a clause is worse than no edit, since
# nothing would catch it short of a real card going wrong again.


def _render_wiki_receipt(mod, **overrides):
    specs = {s["key"]: s for s in mod.CHECKERS}
    receipt = specs["wiki-staleness"]["split"]["receipt"]
    fmt = {
        "page": "docs/knowledge-base/example.md",
        "sources": "`scripts/example.py`",
        "n_sources": 1,
    }
    fmt.update(overrides)
    return receipt.format(**fmt)


def test_receipt_restates_scope_ceiling(mod):
    """scope-overrun (3 close causes: #5655, #5656, #5659)."""
    rendered = _render_wiki_receipt(mod)
    assert "SCOPE CEILING" in rendered
    assert "touches ONLY" in rendered
    assert "#5655" in rendered and "#5656" in rendered and "#5659" in rendered


def test_receipt_has_unconditional_finish_protocol_naming_vacuous_and_hollow(mod):
    """vacuous (6) + hollow (3) close causes — the modal failure on this lane."""
    rendered = _render_wiki_receipt(mod)
    assert "FINISH PROTOCOL, unconditional" in rendered
    assert "VACUOUS" in rendered
    assert "HOLLOW" in rendered
    assert "#5688" in rendered  # the hollow-shape PR


def test_receipt_has_duplicate_work_check(mod):
    """stale/superseded (5 close causes) — a card verifying an already-handled page."""
    rendered = _render_wiki_receipt(mod)
    assert "DUPLICATE-WORK CHECK" in rendered
    assert "OPEN PR" in rendered
    assert "kanban block" in rendered


def test_receipt_keeps_verbatim_quote_and_not_found_rules(mod):
    """format/gate-parse (1) + circular-cite (1) close causes."""
    rendered = _render_wiki_receipt(mod)
    assert "claim | file:line | quote | verdict" in rendered
    assert "NOT FOUND" in rendered
    assert "quote_fidelity_check.py" in rendered
    assert "never `verified`" in rendered


# --- DRAFT characterization-tests class: mints blocked, never ready --------


def test_characterization_tests_class_has_no_split_key(mod):
    """A "split" key is what lets a checker mint a READY, assigned card — the
    routing the campaign's build conditions forbid arming for this DRAFT
    class. Guard the key name itself so a future edit can't silently arm it
    by renaming back to "split" without also touching this test."""
    specs = {s["key"]: s for s in mod.CHECKERS}
    spec = specs["characterization-tests"]
    assert "split" not in spec
    assert "split_DRAFT_needs_promotion" in spec


def test_characterization_tests_mints_blocked_not_ready(mod):
    """The draft class must go create -> block, never create -> (ready, done).

    Same assertion shape as test_finding_creates_card_then_blocks_it for
    wiki-staleness — this is the create-then-block contract (PB-006) the
    class relies on for safety instead of any routing-code change.
    """
    stub = HermesStub()
    mod._hermes = stub
    _fix_checkers(
        mod,
        {
            "characterization-tests": {
                "count": 2,
                "samples": [
                    "MISSING_TEST scripts/claim_check.py",
                    "MISSING_TEST scripts/drift_check.py",
                ],
            }
        },
    )
    counts = mod.sync(force=True)
    assert counts["new_cards"] == 1
    assert counts["routed_new"] == 0  # never dispatchable — no routed mint
    assert stub.verbs() == ["create", "block"]
    assert "needs_input" in stub.calls[1]
