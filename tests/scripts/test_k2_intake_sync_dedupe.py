"""Router dedupe holes closed for t_b20d2a14 (harness): a card that is
non-terminal but has never opened a PR must still hold its routed slot.

Background: t_6a69ecd2 (2026-09-01) made the router hold a slot for a
done/archived card with an OPEN PR. That left a second hole: a card that is
still ready/claimed/running/blocked — no PR yet at all, because the work
simply isn't finished — held NOTHING, so the very next pulse (exactly one
THROTTLE_SECS later, since sync() only runs its full logic on that cadence)
minted a twin. Measured 2026-09-05: three duplicate KB-verify cards (#6131,
#6152, #6170) for pages whose first card was still working.

Contract under test: any NON-terminal card (ready/claimed/running/blocked/
triage/...) holds its slot regardless of PR state until it reaches done/
archived, or until it goes quiet (no new task_events) for a full
THROTTLE_SECS window, at which point it is released and charged an attempt
— same as any other zombie slot, eventually parking the artifact rather than
re-carding it forever.

SAFETY: every test here MUST run against the `mod` fixture below, never
against a hand-rolled module load — a stray real-desk run against the LIVE
k2-intake-state.json on 2026-09-06 (during the first draft of this file) is
exactly the mistake `mod`'s assertion below exists to make impossible.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def mod(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("K2_INTAKE_CLONE", str(tmp_path / "clone"))
    monkeypatch.setenv("K2_INTAKE_MODEL_PROBE", "off")
    (tmp_path / "cache").mkdir()
    (tmp_path / "clone").mkdir()
    spec = importlib.util.spec_from_file_location(
        "k2_intake_sync_dedupe", REPO / "scripts" / "k2_intake_sync.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    m._board_has_workdir = lambda: True
    # Fail loudly rather than silently touching a real desk: HOME/DESK must
    # resolve inside pytest's own tmp_path, never a real ~/.t1000 or
    # /opt/t1000/home. This is the guard the 2026-09-06 contamination
    # incident showed was missing.
    assert str(m.HOME) == str(tmp_path), f"HOME escaped tmp_path: {m.HOME}"
    assert str(m.DESK).startswith(str(tmp_path)), f"DESK escaped tmp_path: {m.DESK}"
    assert str(m.STATE_PATH).startswith(str(tmp_path)), (
        f"STATE_PATH escaped tmp_path: {m.STATE_PATH}"
    )
    return m


class HermesStub:
    """Same contract as test_k2_intake_sync.py's stub: records verbs, mints
    ascending fake card ids on `create`."""

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


class BoardStub:
    """A fake board: per-card status/PR/last-event-timestamp, settable by the
    test as the story unfolds across ticks. Replaces every sqlite-backed peek
    `sync()` consults so tests never touch a real kanban.db."""

    def __init__(self):
        self.status: dict[str, str] = {}
        self.pr: dict[str, int | None] = {}
        self.pr_state: dict[int, str | None] = {}
        self.event_ts: dict[str, int | None] = {}
        self.run_summary: dict[str, str | None] = {}

    def install(self, mod):
        mod._card_status = lambda cid: self.status.get(cid)
        mod._card_pr_number = lambda cid: self.pr.get(cid)
        mod._pr_state = lambda pr: self.pr_state.get(pr)
        mod._card_last_event_ts = lambda cid: self.event_ts.get(cid)
        mod._card_last_run_summary = lambda cid: self.run_summary.get(cid)


def _single_split_checker(key="wiki-staleness", artifact="docs/knowledge-base/foo.md"):
    return [{
        "key": key,
        "title": "t",
        "argv": ["true"],
        "line_re": "x",
        "split": {"cls": 1, "artifact_re": r"(\S+)", "title": "verify {artifact}", "receipt": "r"},
    }], artifact


def _fix_checkers(mod, key, count, artifacts):
    mod.run_checker = lambda spec, clone: (
        {"count": count, "samples": [], "artifacts": artifacts, "sources_by_artifact": {}}
        if spec["key"] == key else None
    )


def _mint_one(mod, stub, board, key, artifact, status, event_ts=100):
    """Drive one sync() tick that mints exactly one routed card, and seed the
    board's view of it. Returns (rkey, card_id, counts)."""
    _fix_checkers(mod, key, 1, [artifact])
    before = set(mod._load_state().get("routed", {}))
    counts = mod.sync(force=True)
    state = mod._load_state()
    (rkey,) = set(state["routed"]) - before
    card_id = state["routed"][rkey]["card"]
    board.status[card_id] = status
    board.pr[card_id] = None
    board.event_ts[card_id] = event_ts
    return rkey, card_id, counts


def test_running_card_without_pr_holds_slot_across_next_tick(mod):
    """The literal 2026-09-05 shape: a card still RUNNING, no PR opened yet.
    A second full sync() tick — the throttle's own cadence, one THROTTLE_SECS
    later in real incidents — must NOT mint a twin."""
    checkers, artifact = _single_split_checker()
    mod.CHECKERS = checkers
    stub = HermesStub()
    mod._hermes = stub
    board = BoardStub()
    board.install(mod)

    rkey, card_id, c1 = _mint_one(mod, stub, board, "wiki-staleness", artifact, "running")
    assert c1["routed_new"] == 1

    # Next tick: checker still reports the same artifact (work not merged
    # yet), card is still "running" with no PR. Must hold, not re-mint.
    c2 = mod.sync(force=True)
    assert c2["routed_new"] == 0
    assert c2["dedup_nonterminal"] == 1
    assert c2["throttle_held"] == 1
    state = mod._load_state()
    assert rkey in state["routed"], "the original slot must still be held"
    assert len([v for v in state["routed"].values() if v["card"].startswith("t_")]) == 1


def test_blocked_card_without_pr_holds_slot_not_released_immediately(mod):
    """The exact code path the old zombie scan mishandled: status=='blocked',
    no PR yet. Old behaviour charged an attempt and freed the slot on first
    sight; that must no longer happen while genuinely fresh."""
    checkers, artifact = _single_split_checker()
    mod.CHECKERS = checkers
    stub = HermesStub()
    mod._hermes = stub
    board = BoardStub()
    board.install(mod)

    rkey, card_id, c1 = _mint_one(mod, stub, board, "wiki-staleness", artifact, "blocked")
    assert c1["routed_new"] == 1

    c2 = mod.sync(force=True)
    assert c2["routed_new"] == 0
    assert c2["dedup_nonterminal"] == 1
    assert c2["throttle_held"] == 1
    assert c2["blocked_released"] == 0
    state = mod._load_state()
    assert rkey in state["routed"]
    attempts = state.get("route_attempts", {})
    assert attempts.get(rkey, 0) == 0, "genuinely fresh — no attempt charged"


def test_activity_resets_the_staleness_clock_past_one_throttle_window(mod):
    """A card that keeps changing (fresh task_events each tick) must never
    read stale, no matter how many throttle windows pass since it was
    minted — staleness is measured from the card's OWN last activity, never
    from its mint time."""
    checkers, artifact = _single_split_checker()
    mod.CHECKERS = checkers
    stub = HermesStub()
    mod._hermes = stub
    board = BoardStub()
    board.install(mod)

    rkey, card_id, _ = _mint_one(mod, stub, board, "wiki-staleness", artifact, "running", event_ts=100)

    # Three more ticks, each with a NEW event timestamp (real progress).
    for i, ts in enumerate((200, 300, 400), start=1):
        board.event_ts[card_id] = ts
        counts = mod.sync(force=True)
        assert counts["routed_new"] == 0, f"tick {i}: must not re-mint"
        assert counts["throttle_held"] == 1, f"tick {i}: activity must keep holding"

    state = mod._load_state()
    assert rkey in state["routed"]
    assert state.get("route_attempts", {}).get(rkey, 0) == 0


def test_no_activity_for_a_full_throttle_window_eventually_parks(mod, monkeypatch):
    """The escape hatch: a card that goes genuinely quiet — same
    task_events timestamp, tick after tick — must eventually free its slot
    (charging an attempt) rather than holding forever, and after
    MAX_ROUTE_ATTEMPTS park the artifact instead of re-minting a twin."""
    checkers, artifact = _single_split_checker()
    mod.CHECKERS = checkers
    mod.MAX_ROUTE_ATTEMPTS = 2
    stub = HermesStub()
    mod._hermes = stub
    board = BoardStub()
    board.install(mod)

    rkey, card_id, _ = _mint_one(mod, stub, board, "wiki-staleness", artifact, "blocked", event_ts=100)

    now = [1_000_000.0]
    monkeypatch.setattr(mod.time, "time", lambda: now[0])

    # Tick 2: still no new event, but less than one throttle window has
    # elapsed since we first observed the quiet — must still hold.
    now[0] += 10
    c2 = mod.sync(force=True)
    assert c2["throttle_held"] == 1
    assert c2["slots_refreed"] == 0

    # Tick 3: a full throttle window has now elapsed with zero new activity
    # — first attempt charged, slot freed, but not yet parked.
    now[0] += mod.THROTTLE_SECS + 1
    c3 = mod.sync(force=True)
    assert c3["slots_refreed"] == 1
    state = mod._load_state()
    assert rkey not in state["routed"]
    assert state["route_attempts"][rkey] == 1
    assert rkey not in state.get("parked_artifacts", {})

    # The artifact is still reported live and the same zombie card is still
    # blocked with no PR. Mirror the real router: `attempts` persists by
    # rkey even after a slot is freed, and re-occupies the slot for the same
    # underlying artifact/card on its next eligible pass.
    board.event_ts[card_id] = 100  # unchanged again — still quiet
    state = mod._load_state()
    state["routed"][rkey] = {"card": card_id, "artifact": artifact}
    mod._save_state(state)

    # Tick 4: the slot was just re-seeded, so held_clock has no entry for it
    # yet — first sight after re-occupying resets the clock fresh (same as
    # any newly-held card) and holds one more window.
    now[0] += 10
    c4 = mod.sync(force=True)
    assert c4["throttle_held"] == 1
    assert c4["slots_refreed"] == 0
    assert state_attempts(mod, rkey) == 1, "no second attempt charged yet"

    # Tick 5: a full throttle window elapses again with zero new activity —
    # second attempt exhausts MAX_ROUTE_ATTEMPTS=2, so this time it parks
    # instead of merely re-freeing (never re-minting a twin for a truly
    # stuck artifact).
    now[0] += mod.THROTTLE_SECS + 1
    c5 = mod.sync(force=True)
    assert c5["parked_failing"] == 1
    state = mod._load_state()
    assert rkey in state["parked_artifacts"]
    assert rkey not in state["routed"]


def state_attempts(mod, rkey):
    return mod._load_state().get("route_attempts", {}).get(rkey, 0)
