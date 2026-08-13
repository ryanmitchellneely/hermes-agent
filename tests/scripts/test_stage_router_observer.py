"""Tests for the ST-13 Phase 1 stage-router observer (scripts/stage_router_observer.py).

The pure scorer (TurnSignals -> score_window -> ObserverVerdict) is the
only part of this card required to be "unit-tested, no I/O" — that's
what these tests exercise. The offline log/DB parsing is exercised
separately via a tiny synthetic log fixture, still with no real I/O
outside tmp_path.
"""

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import stage_router_observer as obs  # noqa: E402


# ── pure scorer: score_window ───────────────────────────────────────────


def test_all_zero_signals_score_zero():
    v = obs.score_window(obs.TurnSignals())
    assert v.score == 0.0
    assert not v.hard_override


def test_one_full_signal_scores_about_point_four_six():
    for kwargs in ({"severity": 1.0}, {"spinning": 1.0}, {"exploring": 1.0}):
        v = obs.score_window(obs.TurnSignals(**kwargs))
        assert math.isclose(v.score, math.tanh(0.5), rel_tol=1e-9)
        assert 0.45 < v.score < 0.47  # matches the ~0.46 documented in SIG-20260811-06
        assert v.score < 0.5  # one signal alone must NOT cross a 0.5 boundary


def test_two_corroborating_signals_cross_point_five():
    v = obs.score_window(obs.TurnSignals(severity=1.0, spinning=1.0))
    assert math.isclose(v.score, math.tanh(1.0), rel_tol=1e-9)
    assert v.score > 0.5


def test_production_intensity_dampens_escalate_signal():
    escalating = obs.score_window(obs.TurnSignals(severity=1.0))
    dampened = obs.score_window(obs.TurnSignals(severity=1.0, production_intensity=1.0))
    assert dampened.score < escalating.score
    assert dampened.score == 0.0  # fully countered -> raw floored at 0


def test_production_intensity_alone_never_escalates():
    v = obs.score_window(obs.TurnSignals(production_intensity=1.0))
    assert v.score == 0.0


def test_critical_error_hard_override_wins_regardless_of_other_axes():
    v = obs.score_window(obs.TurnSignals(production_intensity=1.0, critical_error=True))
    assert v.hard_override
    assert v.score == 1.0
    assert v.would_escalate(threshold=0.99)


def test_would_escalate_respects_threshold():
    v = obs.score_window(obs.TurnSignals(severity=1.0))  # score ~0.46
    assert v.would_escalate(threshold=0.4)
    assert not v.would_escalate(threshold=0.5)


def test_score_window_is_pure_and_deterministic():
    sig = obs.TurnSignals(severity=0.3, spinning=0.2, exploring=0.1, production_intensity=0.05)
    a = obs.score_window(sig)
    b = obs.score_window(sig)
    assert a == b


def test_turn_signals_rejects_out_of_range():
    try:
        obs.TurnSignals(severity=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for out-of-range signal")


# ── action classification (icon vocabulary from agent/display.py) ──────


def test_action_class_maps_known_icons():
    assert obs._action_class("📖") == "read"
    assert obs._action_class("✍️") == "write"
    assert obs._action_class("🔧") == "write"
    assert obs._action_class("🔎") == "explore"
    assert obs._action_class("💻") == "shell"
    assert obs._action_class("🤷") == "other"


# ── windowed signal derivation from a synthetic tool-call sequence ─────


def _events(classes):
    return [obs.LogEvent(line_no=i, action_class=c, is_error=False) for i, c in enumerate(classes)]


def test_signals_from_window_all_reads_is_exploring_not_spinning():
    win = _events(["read", "read", "explore", "explore"])
    sig = obs.signals_from_window(win)
    assert sig.exploring > 0
    assert sig.production_intensity == 0.0
    assert sig.spinning == 0.0  # >=2 reads present, so not "no reads or writes"


def test_signals_from_window_pure_shell_churn_is_spinning():
    win = _events(["shell", "shell", "shell", "other"])
    sig = obs.signals_from_window(win)
    assert sig.spinning == 1.0
    assert sig.exploring > 0.0 or sig.exploring == 0.0  # shell isn't counted as explore either way, just no false read credit


def test_signals_from_window_writes_raise_production_intensity_and_zero_exploring():
    win = _events(["read", "write", "write", "read"])
    sig = obs.signals_from_window(win)
    assert sig.production_intensity > 0.0
    assert sig.exploring == 0.0  # writes present -> not "producing nothing"


def test_signals_from_window_empty_window_is_all_zero():
    sig = obs.signals_from_window([])
    assert sig == obs.TurnSignals()


# ── log parsing against a small synthetic transcript ────────────────────


_SYNTHETIC_LOG = "\n".join(
    [
        "Query: work kanban task t_fake0001",
        "  ┊ 🔎 grep      needle  0.1s",
        "  ┊ 🔎 find      needle.py  0.2s",
        "  ┊ 📖 read      needle.py L1-200  0.1s",
        "  ┊ 💻 $         ls -R  0.1s",
        "  ┊ 🔎 find      thing  12.0s",
        "⚠️  API call failed (attempt 1/3): RuntimeError",
        "  ┊ 🔎 find      thing  9.0s",
        "  ┊ 🔎 find      thing  11.0s",
    ]
)


def test_parse_worker_log_extracts_actions_and_errors(tmp_path):
    p = tmp_path / "t_fake0001.log"
    p.write_text(_SYNTHETIC_LOG)
    events = obs.parse_worker_log(p)
    classes = [e.action_class for e in events]
    assert classes.count("explore") == 5  # 4 find/grep + nothing else miscounted
    assert classes.count("read") == 1
    assert classes.count("shell") == 1
    assert any(e.is_error for e in events)


def test_windows_slides_by_one_and_caps_at_size(tmp_path):
    p = tmp_path / "t_fake0001.log"
    p.write_text(_SYNTHETIC_LOG)
    events = obs.parse_worker_log(p)
    seen = list(obs.windows(events, size=3))
    # only FULL windows are yielded (see windows() docstring: ramp-up
    # windows of size 1/2 caused small-n false "spinning" flags)
    assert len(seen) == len(events) - 3 + 1
    assert all(len(win) == 3 for _, win in seen)
    # last window ends at the full event count
    assert seen[-1][0] == len(events)


def test_windows_shorter_than_size_yields_one_partial_window():
    events = _events(["read", "explore"])
    seen = list(obs.windows(events, size=8))
    assert len(seen) == 1
    end, win = seen[0]
    assert end == 2
    assert len(win) == 2


def test_windows_empty_events_yields_nothing():
    assert list(obs.windows([], size=8)) == []
