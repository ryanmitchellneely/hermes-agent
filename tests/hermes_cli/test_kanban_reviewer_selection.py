"""Reviewer selection for review dispatch (t_6f7689e4).

THE BUG THESE PIN: review dispatch spawned the task's own assignee, so the
implementer reviewed its own work. On t_d107022a that produced 11 runs, all
profile ``sonnet``, ten consecutive ``review_requested`` outcomes and ~32
minutes of worker time for no progress -- each run re-verified an already
committed deliverable and re-requested review, re-arming the exact claimable
state the dispatcher had just consumed. The same self-spawn is how a profile
could approve its own work (t_eaeae889), which fleet doctrine forbids.

The guard is REFUSE, never fall back: if no distinct reviewer is eligible the
dispatcher defers rather than spawning the implementer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


# --------------------------------------------------------------------------
# pick_reviewer_profile -- the selection rule itself
# --------------------------------------------------------------------------


def test_implementer_is_never_chosen_as_its_own_reviewer():
    """The whole point: sonnet implemented it, so sonnet must not review it."""
    got, reason = kb.pick_reviewer_profile(
        "sonnet",
        candidates=["sonnet", "grok"],
        profile_exists=lambda _n: True,
    )
    assert got == "grok", "must skip the implementer even when listed first"


def test_returns_none_rather_than_falling_back_to_the_implementer():
    """No eligible reviewer -> defer. Falling back to the assignee IS the bug."""
    got, reason = kb.pick_reviewer_profile(
        "sonnet",
        candidates=["sonnet"],
        profile_exists=lambda _n: True,
    )
    assert got is None
    assert reason == "unavailable", "operator must know no reviewer is configured"


def test_empty_candidate_list_defers():
    """Unconfigured review_profiles must not silently self-spawn."""
    got, reason = kb.pick_reviewer_profile(
        "sonnet", candidates=[], profile_exists=lambda _n: True
    )
    assert got is None
    assert reason == "unavailable"


def test_order_is_preference_order():
    got, reason = kb.pick_reviewer_profile(
        "worker",
        candidates=["grok", "sonnet"],
        profile_exists=lambda _n: True,
    )
    assert got == "grok"


def test_nonexistent_profiles_are_skipped():
    got, reason = kb.pick_reviewer_profile(
        "worker",
        candidates=["ghost", "sonnet"],
        profile_exists=lambda n: n != "ghost",
    )
    assert got == "sonnet"


def test_capped_reviewer_is_skipped_for_the_next_candidate():
    """The cap is the REVIEWER's, since the reviewer's slot is consumed."""
    got, reason = kb.pick_reviewer_profile(
        "worker",
        candidates=["grok", "sonnet"],
        profile_exists=lambda _n: True,
        per_profile_cap=2,
        per_profile_running={"grok": 2, "sonnet": 0},
    )
    assert got == "sonnet"


def test_all_candidates_capped_defers():
    got, reason = kb.pick_reviewer_profile(
        "worker",
        candidates=["grok", "sonnet"],
        profile_exists=lambda _n: True,
        per_profile_cap=1,
        per_profile_running={"grok": 1, "sonnet": 1},
    )
    assert got is None
    assert reason == "capped", (
        "all-capped is TRANSIENT and must not be reported as a stuck task -- "
        "the codebase keeps 'profile busy' and 'genuinely stuck' in separate "
        "buckets on purpose"
    )


def test_no_implementer_still_selects():
    """An unassigned task should still get a reviewer if one is configured."""
    got, reason = kb.pick_reviewer_profile(
        None, candidates=["grok"], profile_exists=lambda _n: True
    )
    assert got == "grok"


# --------------------------------------------------------------------------
# review_profile_candidates -- config parsing
# --------------------------------------------------------------------------


def _patch_config(monkeypatch, cfg):
    import hermes_cli.config as config_mod

    monkeypatch.setattr(config_mod, "load_config", lambda: cfg)


def test_candidates_read_from_config(monkeypatch):
    _patch_config(monkeypatch, {"kanban": {"review_profiles": ["grok", "sonnet"]}})
    assert kb.review_profile_candidates() == ["grok", "sonnet"]


def test_candidates_absent_is_empty(monkeypatch):
    _patch_config(monkeypatch, {"kanban": {}})
    assert kb.review_profile_candidates() == []


def test_candidates_tolerates_a_bare_string(monkeypatch):
    _patch_config(monkeypatch, {"kanban": {"review_profiles": "grok"}})
    assert kb.review_profile_candidates() == ["grok"]


def test_candidates_dedupes_and_strips(monkeypatch):
    _patch_config(
        monkeypatch, {"kanban": {"review_profiles": [" grok ", "grok", "sonnet"]}}
    )
    assert kb.review_profile_candidates() == ["grok", "sonnet"]


def test_candidates_rejects_a_non_list(monkeypatch):
    _patch_config(monkeypatch, {"kanban": {"review_profiles": 42}})
    assert kb.review_profile_candidates() == []


# --------------------------------------------------------------------------
# claim_review_task -- the reviewer must reach task_runs, NOT tasks.assignee
# --------------------------------------------------------------------------


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_CRASH_GRACE_SECONDS", "0")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    db_path = kb.kanban_db_path(board="default")
    kb._INITIALIZED_PATHS.discard(str(db_path.resolve()))
    kb.init_db()
    return home


@pytest.fixture
def conn(kanban_home):
    with kb.connect() as c:
        yield c


def _task_in_review(conn, assignee="sonnet"):
    tid = kb.create_task(conn, title="t", assignee=assignee)
    claimed = kb.claim_task(conn, tid, claimer="builder:1")
    assert claimed is not None
    kb.request_review(conn, tid, expected_run_id=claimed.current_run_id)
    return tid


def test_reviewer_becomes_the_run_profile_not_the_task_assignee(conn):
    """The run records WHO REVIEWED; the card still belongs to the implementer."""
    tid = _task_in_review(conn, assignee="sonnet")

    claimed = kb.claim_review_task(conn, tid, reviewer="grok")
    assert claimed is not None

    row = conn.execute(
        "SELECT profile FROM task_runs WHERE task_id = ? ORDER BY id DESC LIMIT 1",
        (tid,),
    ).fetchone()
    assert row["profile"] == "grok", "task_runs.profile must name the reviewer"

    db_assignee = conn.execute(
        "SELECT assignee FROM tasks WHERE id = ?", (tid,)
    ).fetchone()["assignee"]
    assert db_assignee == "sonnet", "ownership must stay with the implementer"

    assert claimed.assignee == "grok", (
        "the returned Task carries the reviewer so the caller spawns and "
        "cap-counts the reviewer, not the implementer"
    )


def test_claim_without_a_reviewer_is_unchanged(conn):
    """Back-compat: existing callers that pass no reviewer behave as before."""
    tid = _task_in_review(conn, assignee="sonnet")

    claimed = kb.claim_review_task(conn, tid)
    assert claimed is not None
    assert claimed.assignee == "sonnet"

    row = conn.execute(
        "SELECT profile FROM task_runs WHERE task_id = ? ORDER BY id DESC LIMIT 1",
        (tid,),
    ).fetchone()
    assert row["profile"] == "sonnet"


def test_reviewer_is_recorded_on_the_claim_event(conn):
    """The board must show who was sent to review, for auditability."""
    import json

    tid = _task_in_review(conn, assignee="sonnet")
    kb.claim_review_task(conn, tid, reviewer="grok")

    rows = conn.execute(
        "SELECT kind, payload FROM task_events WHERE task_id = ? ORDER BY id DESC",
        (tid,),
    ).fetchall()
    claimed_events = [r for r in rows if r["kind"] == "claimed"]
    assert claimed_events, "expected a claimed event"
    payload = json.loads(claimed_events[0]["payload"])
    assert payload.get("reviewer") == "grok"
    assert payload.get("source_status") == "review"


# --------------------------------------------------------------------------
# dispatch level -- the actual t_eaeae889 governance guarantee
# --------------------------------------------------------------------------


def test_dispatcher_never_spawns_the_implementer_onto_its_own_review(
    kanban_home, monkeypatch
):
    """Reproduces t_eaeae889 at the level the incident actually happened.

    The real event trail: run 423 (profile ``grok``, the implementer) finished
    with review_requested and an explicit "Needs Ryan green before
    implementation children." Ninety seconds later run 425 -- the SAME grok
    profile -- claimed the card with source_status:'review' and completed it,
    summary "Reviewed and approved." The human gate the worker asked for was
    closed by the worker itself.

    The picker tests above prove pick_reviewer_profile() refuses. This proves
    the DISPATCHER refuses, which is the guarantee that actually matters.
    """
    import hermes_cli.config as cfgmod
    import hermes_cli.profiles as profmod

    with kb.connect() as conn:
        tid = kb.create_task(conn, title="grok's own work", assignee="grok")
        kb.claim_task(conn, tid)
        kb.request_review(
            conn, tid, summary="Needs Ryan green before implementation children.",
            expected_run_id=kb.get_task(conn, tid).current_run_id,
        )
        assert kb.get_task(conn, tid).status == "review"

        # Every profile is spawnable, so nothing but the reviewer-must-differ
        # rule can prevent grok from being handed its own review.
        monkeypatch.setattr(profmod, "profile_exists", lambda name: True)
        monkeypatch.setattr(
            cfgmod, "load_config",
            lambda *a, **k: {
                "kanban": {
                    "review_dispatch": True,
                    # grok is listed FIRST and is still refused.
                    "review_profiles": ["grok", "sonnet"],
                }
            },
        )

        res = kb.dispatch_once(conn, dry_run=True)
        spawned = {t[0]: t[1] for t in res.spawned}

        assert tid in spawned, "the card should still be reviewed, just not by grok"
        assert spawned[tid] != "grok", (
            "t_eaeae889: the implementer must never be dispatched onto its own "
            "review -- that is how a worker closed its own human gate"
        )
        assert spawned[tid] == "sonnet"


def test_dispatcher_holds_rather_than_self_approving_when_only_implementer_configured(
    kanban_home, monkeypatch
):
    """If the ONLY configured reviewer is the implementer, hold — never fall back.

    This is the case that makes the guarantee real rather than cosmetic: with
    no one else eligible, the tempting behaviour is to let the implementer
    through 'so the card can move'. That is precisely the bug.
    """
    import hermes_cli.config as cfgmod
    import hermes_cli.profiles as profmod

    with kb.connect() as conn:
        tid = kb.create_task(conn, title="solo", assignee="grok")
        kb.claim_task(conn, tid)
        kb.request_review(
            conn, tid, summary="done",
            expected_run_id=kb.get_task(conn, tid).current_run_id,
        )

        monkeypatch.setattr(profmod, "profile_exists", lambda name: True)
        monkeypatch.setattr(
            cfgmod, "load_config",
            lambda *a, **k: {
                "kanban": {"review_dispatch": True, "review_profiles": ["grok"]}
            },
        )

        res = kb.dispatch_once(conn, dry_run=True)
        assert tid not in [t[0] for t in res.spawned], "must not self-approve"
        assert kb.get_task(conn, tid).status == "review", "must stay parked for a human"
        assert tid in [t[0] for t in res.skipped_no_reviewer], (
            "the hold must be VISIBLE in the dispatch result, not silent"
        )
