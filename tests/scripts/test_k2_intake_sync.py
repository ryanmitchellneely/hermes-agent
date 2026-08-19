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
