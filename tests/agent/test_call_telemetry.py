"""Contract tests for the cross-board model-call telemetry sink.

The load-bearing ones:

* eight REAL concurrent processes appending 200 records produce exactly 200
  intact, parseable lines (the reason the store is O_APPEND JSONL rather than
  SQLite);
* a claude-acp style hardcoded-zero usage object is stored as
  ``tokens_available=false`` with ``null`` token fields, never as 0 tokens —
  storing it as 0 makes the subscription lanes read as free and inverts any
  local-vs-subscription split.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.call_telemetry import (
    SCHEMA_VERSION,
    TOKEN_FIELDS,
    build_record,
    iter_records,
    log_path_for,
    record_model_call,
    telemetry_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
QUERY_SCRIPT = REPO_ROOT / "scripts" / "telemetry_query.py"

# What agent/claude_acp_client.py:1103 and :1237 actually build.
ACP_ZERO_USAGE = SimpleNamespace(
    prompt_tokens=0,
    completion_tokens=0,
    total_tokens=0,
    prompt_tokens_details=SimpleNamespace(cached_tokens=0),
)

OPENAI_USAGE = SimpleNamespace(
    prompt_tokens=1200,
    completion_tokens=300,
    total_tokens=1500,
    prompt_tokens_details=SimpleNamespace(cached_tokens=200),
    completion_tokens_details=SimpleNamespace(reasoning_tokens=120),
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the sink at an isolated store for the duration of a test."""
    root = tmp_path / "telemetry"
    monkeypatch.setenv("T1000_TELEMETRY_DIR", str(root))
    for name in (
        "HERMES_KANBAN_BOARD",
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_RUN_ID",
        "HERMES_SESSION_ID",
        "HERMES_PROFILE",
    ):
        monkeypatch.delenv(name, raising=False)
    return root


def read_all(root: Path) -> list[dict]:
    return list(iter_records(root))


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------


def test_writes_one_parseable_line_carrying_every_required_field(store):
    record_model_call(
        provider="spark",
        model="gpt-oss:120b",
        effort="high",
        usage=OPENAI_USAGE,
        wall_ms=4210,
        ttft_ms=380,
        outcome="ok",
        lane="worker",
        task_id="t_abc123",
        board="mesh",
        run_id="206",
        session_id="20260809_065934_93ef27",
        task="main_loop",
    )

    files = sorted(store.glob("model_calls-*.jsonl"))
    assert len(files) == 1, files
    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    row = json.loads(lines[0])
    assert row["schema_version"] == SCHEMA_VERSION
    for field in (
        "ts",
        "ts_epoch_ms",
        "board",
        "task_id",
        "run_id",
        "session_id",
        "lane",
        "task",
        "provider",
        "model",
        "effort",
        "tokens_available",
        "wall_ms",
        "ttft_ms",
        "outcome",
        "error_class",
    ):
        assert field in row, f"missing required field {field}"
    assert row["board"] == "mesh"
    assert row["task_id"] == "t_abc123"
    assert row["run_id"] == "206"
    assert row["lane"] == "worker"
    assert row["model"] == "gpt-oss:120b"
    assert row["effort"] == "high"
    assert row["wall_ms"] == 4210
    assert row["ttft_ms"] == 380
    assert row["error_class"] is None
    # ISO8601 + epoch ms, and they agree.
    assert abs(row["ts_epoch_ms"] / 1000.0 - _iso_epoch(row["ts"])) < 1.0


def _iso_epoch(text: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(text).timestamp()


def test_daily_rotation_puts_each_local_date_in_its_own_file(store):
    from datetime import datetime, timedelta

    today = datetime.now().astimezone()
    yesterday = today - timedelta(days=1)
    record_model_call(provider="spark", model="a", usage=OPENAI_USAGE, timestamp=today)
    record_model_call(provider="spark", model="b", usage=OPENAI_USAGE, timestamp=yesterday)

    files = sorted(p.name for p in store.glob("model_calls-*.jsonl"))
    assert files == sorted(
        [log_path_for(yesterday, store).name, log_path_for(today, store).name]
    )
    assert len(read_all(store)) == 2


def test_real_usage_is_normalized_not_char_estimated(store):
    record_model_call(provider="openai", model="gpt-x", usage=OPENAI_USAGE)
    row = read_all(store)[0]

    assert row["tokens_available"] is True
    # normalize_usage subtracts cached tokens out of the prompt total.
    assert row["input_tokens"] == 1000
    assert row["cache_read_tokens"] == 200
    assert row["output_tokens"] == 300
    assert row["reasoning_tokens"] == 120
    assert row["prompt_tokens"] == 1200
    assert row["total_tokens"] == 1500


def test_dict_usage_is_accepted(store):
    record_model_call(
        provider="openai",
        model="gpt-x",
        usage={
            "prompt_tokens": 500,
            "completion_tokens": 50,
            "prompt_tokens_details": {"cached_tokens": 100},
        },
    )
    row = read_all(store)[0]
    assert (row["input_tokens"], row["cache_read_tokens"], row["output_tokens"]) == (400, 100, 50)


def test_already_canonical_usage_passes_through_unmangled(store):
    from agent.usage_pricing import CanonicalUsage

    record_model_call(
        provider="anthropic",
        model="claude-x",
        usage=CanonicalUsage(
            input_tokens=10,
            output_tokens=20,
            cache_read_tokens=30,
            cache_write_tokens=40,
            reasoning_tokens=5,
        ),
    )
    row = read_all(store)[0]
    assert row["input_tokens"] == 10
    assert row["output_tokens"] == 20
    assert row["cache_read_tokens"] == 30
    assert row["cache_write_tokens"] == 40
    assert row["reasoning_tokens"] == 5
    assert row["prompt_tokens"] == 80
    assert row["total_tokens"] == 100


# --------------------------------------------------------------------------
# the tokens_available contract
# --------------------------------------------------------------------------


def test_claude_acp_zero_usage_is_unavailable_with_null_tokens_not_zero(store):
    record_model_call(
        provider="claude-acp",
        model="opus[1m]",
        effort="high",
        usage=ACP_ZERO_USAGE,
        wall_ms=9000,
    )
    row = read_all(store)[0]

    assert row["tokens_available"] is False
    for field in TOKEN_FIELDS:
        assert row[field] is None, f"{field} must be null, not {row[field]!r}"
    # The call itself is still fully attributed — model/provider/effort survive.
    assert (row["provider"], row["model"], row["effort"]) == ("claude-acp", "opus[1m]", "high")
    assert row["outcome"] == "ok"


def test_copilot_acp_is_also_flagged_tokenless(store):
    record_model_call(provider="copilot-acp", model="gpt-5", usage=ACP_ZERO_USAGE)
    assert read_all(store)[0]["tokens_available"] is False


def test_missing_usage_is_unavailable_not_zero(store):
    record_model_call(provider="spark", model="gpt-oss:120b", usage=None, outcome="timeout")
    row = read_all(store)[0]
    assert row["tokens_available"] is False
    assert row["total_tokens"] is None
    assert row["outcome"] == "timeout"


def test_all_zero_usage_from_any_provider_is_unavailable(store):
    record_model_call(provider="some-proxy", model="m", usage=ACP_ZERO_USAGE)
    assert read_all(store)[0]["tokens_available"] is False


def test_caller_may_force_tokens_available(store):
    """2c will recover real ACP token counts; it must be able to say so."""
    record_model_call(
        provider="claude-acp",
        model="opus[1m]",
        usage={"prompt_tokens": 100, "completion_tokens": 10},
        tokens_available=True,
    )
    row = read_all(store)[0]
    assert row["tokens_available"] is True
    assert row["total_tokens"] == 110


# --------------------------------------------------------------------------
# outcomes, defaults, and never-raise
# --------------------------------------------------------------------------


def test_unknown_outcome_is_coerced_to_error_and_preserved(store):
    record_model_call(
        provider="spark", model="m", outcome="EXPLODED", error_class="ReadTimeout"
    )
    row = read_all(store)[0]
    assert row["outcome"] == "error"
    assert row["outcome_raw"] == "exploded"
    assert row["error_class"] == "ReadTimeout"


def test_defaults_come_from_the_dispatcher_environment(store, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "mesh")
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_3a1b8b6b")
    monkeypatch.setenv("HERMES_KANBAN_RUN_ID", "206")
    monkeypatch.setenv("HERMES_SESSION_ID", "sess-1")
    monkeypatch.setenv("HERMES_PROFILE", "worker")

    record_model_call(provider="spark", model="gpt-oss:120b")
    row = read_all(store)[0]
    assert (row["board"], row["task_id"], row["run_id"]) == ("mesh", "t_3a1b8b6b", "206")
    assert (row["session_id"], row["lane"], row["task"]) == ("sess-1", "worker", "main_loop")


def test_recording_never_raises_on_garbage(store):
    class Exploding:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    record_model_call(provider=None, model=None, usage=Exploding(), wall_ms="not-a-number")
    record_model_call(provider="spark", model="m", usage=object())
    # No exception escaped; the store is still readable.
    read_all(store)


def test_recording_never_raises_when_the_store_is_unwritable(tmp_path, monkeypatch):
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    monkeypatch.setenv("T1000_TELEMETRY_DIR", str(blocker / "telemetry"))
    record_model_call(provider="spark", model="m", usage=OPENAI_USAGE)


def test_build_record_is_pure(tmp_path, monkeypatch):
    monkeypatch.setenv("T1000_TELEMETRY_DIR", str(tmp_path / "nope"))
    record = build_record(provider="spark", model="m", usage=OPENAI_USAGE)
    assert record["total_tokens"] == 1500
    assert not (tmp_path / "nope").exists()


def test_telemetry_dir_defaults_under_dot_t1000(monkeypatch):
    monkeypatch.delenv("T1000_TELEMETRY_DIR", raising=False)
    monkeypatch.setenv("HERMES_REAL_HOME", "/home/example")
    # Explicitly NOT under HERMES_HOME — that is per-profile, this store is not.
    monkeypatch.setenv("HERMES_HOME", "/home/example/.t1000/profiles/worker")
    assert telemetry_dir() == Path("/home/example/.t1000/telemetry")


# --------------------------------------------------------------------------
# concurrency — the acceptance test
# --------------------------------------------------------------------------


_CHILD = """
import os, sys, time
sys.path.insert(0, {repo!r})
from agent.call_telemetry import record_model_call
from types import SimpleNamespace

worker, start_at = int(sys.argv[1]), float(sys.argv[2])
real_dir, warmup_dir = sys.argv[3], sys.argv[4]
usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=100,
                        prompt_tokens_details=SimpleNamespace(cached_tokens=0))
# Warm every lazy import (agent.usage_pricing) against a throwaway store BEFORE
# the barrier, so all 8 processes hit the real file inside the same few
# milliseconds — import skew would otherwise serialize them and the test would
# prove nothing about concurrent appends.
os.environ["T1000_TELEMETRY_DIR"] = warmup_dir
record_model_call(provider="warmup", model="warmup", usage=usage)
os.environ["T1000_TELEMETRY_DIR"] = real_dir
while time.time() < start_at:
    pass
for i in range({per_worker}):
    record_model_call(
        provider="spark",
        model="gpt-oss:120b",
        effort="high",
        usage=usage,
        wall_ms=1000 + i,
        ttft_ms=50,
        outcome="ok",
        lane="worker-%d" % worker,
        task_id="t_%03d_%03d" % (worker, i),
        board="mesh",
        run_id=str(worker),
        session_id="sess-%d" % worker,
        task="main_loop",
        error_class="x" * 150,
    )
"""


def test_eight_concurrent_processes_write_200_intact_lines(tmp_path):
    import time

    workers, per_worker = 8, 25
    root = tmp_path / "telemetry"
    warmup = tmp_path / "warmup"
    env = dict(os.environ)
    env["T1000_TELEMETRY_DIR"] = str(root)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    source = _CHILD.format(repo=str(REPO_ROOT), per_worker=per_worker)
    start_at = time.time() + 3.0  # barrier: every child spins until this instant
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", source, str(worker), str(start_at), str(root), str(warmup)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for worker in range(workers)
    ]
    for proc in procs:
        _, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err.decode()

    raw_lines: list[str] = []
    for path in sorted(root.glob("model_calls-*.jsonl")):
        raw_lines.extend(path.read_text(encoding="utf-8").splitlines())

    assert len(raw_lines) == workers * per_worker, (
        f"expected {workers * per_worker} lines, got {len(raw_lines)}"
    )
    rows = [json.loads(line) for line in raw_lines]  # raises on any torn line
    assert len({(row["run_id"], row["task_id"]) for row in rows}) == workers * per_worker
    assert {row["provider"] for row in rows} == {"spark"}
    assert all(row["total_tokens"] == 1100 for row in rows)
    assert len({row["pid"] for row in rows}) == workers

    # The writes must actually have overlapped, otherwise this is a sequential
    # append test wearing a concurrency costume. If the 8 workers had each run
    # to completion in turn, file order would be exactly 8 contiguous pid blocks.
    blocks = 1 + sum(
        1 for prev, cur in zip(rows, rows[1:]) if prev["pid"] != cur["pid"]
    )
    assert blocks > workers, f"writes did not interleave (only {blocks} pid blocks)"


# --------------------------------------------------------------------------
# the query script
# --------------------------------------------------------------------------


def run_query(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(QUERY_SCRIPT), "--dir", str(root), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_query_on_empty_store_exits_zero_with_no_data_yet(tmp_path):
    result = run_query(tmp_path / "never-created")
    assert result.returncode == 0, result.stderr
    assert "no data yet" in result.stdout
    assert "Traceback" not in result.stderr


def test_query_on_existing_but_empty_store_exits_zero(tmp_path):
    root = tmp_path / "telemetry"
    root.mkdir()
    result = run_query(root)
    assert result.returncode == 0, result.stderr
    assert "no data yet" in result.stdout


def test_query_excludes_tokenless_rows_from_sums_and_counts_them(store):
    for _ in range(3):
        record_model_call(
            provider="spark", model="gpt-oss:120b", effort="high", usage=OPENAI_USAGE, wall_ms=100
        )
    for _ in range(2):
        record_model_call(
            provider="claude-acp", model="opus[1m]", effort="high", usage=ACP_ZERO_USAGE
        )
    record_model_call(
        provider="spark", model="gpt-oss:120b", effort="high", usage=None, outcome="timeout"
    )

    result = run_query(store, "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    overall = payload["overall"]
    assert overall["calls"] == 6
    assert overall["calls_with_tokens"] == 3
    assert overall["calls_without_tokens"] == 3
    # 3 x 1500 — the acp rows and the timeout contributed nothing.
    assert overall["total_tokens"] == 4500
    assert overall["ok"] == 5
    assert overall["timeout"] == 1

    acp = [r for r in payload["by_model_provider"] if r["provider"] == "claude-acp"][0]
    assert acp["calls"] == 2
    assert acp["calls_without_tokens"] == 2
    assert acp["total_tokens"] == 0

    effort_rows = {(r["model"], r["effort"]): r for r in payload["by_model_effort"]}
    spark = effort_rows[("gpt-oss:120b", "high")]
    assert (spark["calls"], spark["ok"], spark["timeout"]) == (4, 3, 1)


def test_query_text_output_reports_the_two_required_rollups(store):
    record_model_call(provider="spark", model="gpt-oss:120b", effort="high", usage=OPENAI_USAGE)
    record_model_call(provider="claude-acp", model="opus[1m]", effort="high", usage=ACP_ZERO_USAGE)

    result = run_query(store)
    assert result.returncode == 0, result.stderr
    assert "CALLS + TOKENS BY MODEL x PROVIDER" in result.stdout
    assert "SUCCESS RATE BY MODEL x EFFORT" in result.stdout
    assert "1 call(s) with no token data" in result.stdout
    # The claude-acp row must read "no data", never "0" — a zero there is the
    # exact misread ("that lane is free") this store exists to prevent.
    acp_row = [line for line in result.stdout.splitlines() if "claude-acp" in line][0]
    assert "no data" in acp_row
    assert " 0 " not in acp_row


def test_query_filters_by_board_and_since(store):
    from datetime import datetime, timedelta

    old = datetime.now().astimezone() - timedelta(days=3)
    record_model_call(
        provider="spark", model="m", usage=OPENAI_USAGE, board="k2", timestamp=old
    )
    record_model_call(provider="spark", model="m", usage=OPENAI_USAGE, board="mesh")

    scoped = json.loads(run_query(store, "--board", "mesh", "--json").stdout)
    assert scoped["overall"]["calls"] == 1

    recent = json.loads(run_query(store, "--since", "24h", "--json").stdout)
    assert recent["overall"]["calls"] == 1

    everything = json.loads(run_query(store, "--json").stdout)
    assert everything["overall"]["calls"] == 2
