#!/usr/bin/env python3
"""Query the cross-board model-call telemetry store written by
``agent/call_telemetry.py``.

Answers the two questions MESH-TEL-2 was opened for, from the store alone:

  1. calls + tokens grouped by model x provider
  2. success rate by model x effort

Rows whose ``tokens_available`` is false (the claude-acp / copilot-acp lanes
hardcode zero-token usage objects) are EXCLUDED from every token sum and
reported as their own count, so a subscription lane can never read as "free".

Usage:
  telemetry-query                          # everything in the store
  telemetry-query --since 24h              # 24h | 7d | 90m | 2026-08-01
  telemetry-query --board mesh --lane worker
  telemetry-query --provider spark --model gpt-oss:120b
  telemetry-query --json                   # machine-readable rollup
  telemetry-query --dir /tmp/store         # or T1000_TELEMETRY_DIR=...

Deliberately stdlib-only and repo-import-free so it runs under any python3
(including a bare system interpreter with no Hermes venv on PATH).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

FILE_PREFIX = "model_calls-"
FILE_SUFFIX = ".jsonl"

# Kept in sync with agent/call_telemetry.py:TOKEN_FIELDS.
SUMMABLE_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
)

_RELATIVE = re.compile(r"^(\d+)\s*([mhdw])$", re.I)
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def telemetry_dir(explicit: str | None = None) -> Path:
    """Resolve the store root the same way ``agent/call_telemetry.py`` does."""
    if explicit:
        return Path(explicit).expanduser()
    override = os.environ.get("T1000_TELEMETRY_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    home = os.environ.get("HERMES_REAL_HOME", "").strip() or str(Path.home())
    return Path(home).expanduser() / ".t1000" / "telemetry"


def parse_when(text: str) -> int:
    """Parse ``24h`` / ``7d`` / ``2026-08-01`` / ISO8601 into epoch milliseconds."""
    text = text.strip()
    match = _RELATIVE.match(text)
    if match:
        seconds = int(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()]
        return int((datetime.now().astimezone() - timedelta(seconds=seconds)).timestamp() * 1000)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"cannot parse time {text!r} (want 24h, 7d, 2026-08-01, or ISO8601)"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return int(parsed.timestamp() * 1000)


def iter_records(root: Path, since_ms: int | None, until_ms: int | None):
    """Yield parsed records oldest-file-first; skip torn/unparseable lines."""
    if not root.is_dir():
        return
    for path in sorted(root.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}")):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    stamp = record.get("ts_epoch_ms") or 0
                    if since_ms is not None and stamp < since_ms:
                        continue
                    if until_ms is not None and stamp > until_ms:
                        continue
                    yield record
        except OSError:
            continue


def matches(record: dict, args: argparse.Namespace) -> bool:
    for field, wanted in (
        ("board", args.board),
        ("lane", args.lane),
        ("provider", args.provider),
        ("model", args.model),
        ("task", args.task),
    ):
        if wanted and str(record.get(field) or "") != wanted:
            return False
    return True


def _blank_bucket() -> dict:
    bucket = {
        "calls": 0,
        "ok": 0,
        "error": 0,
        "timeout": 0,
        "refusal": 0,
        "calls_with_tokens": 0,
        "calls_without_tokens": 0,
        "wall_ms_total": 0,
        "wall_ms_samples": 0,
    }
    bucket.update({field: 0 for field in SUMMABLE_TOKEN_FIELDS})
    return bucket


def _accumulate(bucket: dict, record: dict) -> None:
    bucket["calls"] += 1
    outcome = str(record.get("outcome") or "error")
    if outcome in bucket:
        bucket[outcome] += 1
    else:
        bucket["error"] += 1

    wall = record.get("wall_ms")
    if isinstance(wall, (int, float)):
        bucket["wall_ms_total"] += int(wall)
        bucket["wall_ms_samples"] += 1

    # THE point of the tokens_available flag: rows without real token data are
    # counted separately and contribute nothing to any sum.
    if record.get("tokens_available") is True:
        bucket["calls_with_tokens"] += 1
        for field in SUMMABLE_TOKEN_FIELDS:
            value = record.get(field)
            if isinstance(value, (int, float)):
                bucket[field] += int(value)
    else:
        bucket["calls_without_tokens"] += 1


def rollup(records) -> dict:
    by_model_provider: dict[tuple[str, str], dict] = {}
    by_model_effort: dict[tuple[str, str], dict] = {}
    overall = _blank_bucket()
    first_ms: int | None = None
    last_ms: int | None = None

    for record in records:
        model = str(record.get("model") or "unknown")
        provider = str(record.get("provider") or "unknown")
        effort = record.get("effort") or "-"

        _accumulate(by_model_provider.setdefault((model, provider), _blank_bucket()), record)
        _accumulate(by_model_effort.setdefault((model, str(effort)), _blank_bucket()), record)
        _accumulate(overall, record)

        stamp = record.get("ts_epoch_ms")
        if isinstance(stamp, int):
            first_ms = stamp if first_ms is None else min(first_ms, stamp)
            last_ms = stamp if last_ms is None else max(last_ms, stamp)

    return {
        "overall": overall,
        "by_model_provider": by_model_provider,
        "by_model_effort": by_model_effort,
        "first_ms": first_ms,
        "last_ms": last_ms,
    }


def _pct(numerator: int, denominator: int) -> str:
    if not denominator:
        return "  -  "
    return f"{100.0 * numerator / denominator:5.1f}"


def _thousands(value: int) -> str:
    return f"{value:,}"


def _stamp(ms: int | None) -> str:
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000.0).astimezone().isoformat(timespec="seconds")


def render_text(data: dict, root: Path) -> str:
    overall = data["overall"]
    lines = [
        f"model-call telemetry  store={root}",
        f"window: {_stamp(data['first_ms'])}  ->  {_stamp(data['last_ms'])}",
        (
            f"calls: {overall['calls']}   ok: {overall['ok']}   "
            f"error: {overall['error']}   timeout: {overall['timeout']}   "
            f"refusal: {overall['refusal']}"
        ),
        (
            f"token coverage: {overall['calls_with_tokens']} of {overall['calls']} calls "
            f"carry real token data; {overall['calls_without_tokens']} call(s) with no "
            f"token data (excluded from every sum below)"
        ),
        "",
        "CALLS + TOKENS BY MODEL x PROVIDER",
        f"{'model':<34} {'provider':<16} {'calls':>6} {'ok%':>6} "
        f"{'in':>12} {'out':>12} {'total':>13} {'no-tok':>7}",
        "-" * 118,
    ]
    ordered = sorted(
        data["by_model_provider"].items(),
        key=lambda item: (-item[1]["total_tokens"], -item[1]["calls"], item[0]),
    )
    for (model, provider), bucket in ordered:
        # A lane where NO call reported tokens prints "no data", never "0" — a
        # zero here is exactly the misread (claude-acp looks free) this store
        # exists to prevent.
        if bucket["calls_with_tokens"]:
            tokens = (
                f"{_thousands(bucket['input_tokens']):>12} "
                f"{_thousands(bucket['output_tokens']):>12} "
                f"{_thousands(bucket['total_tokens']):>13}"
            )
        else:
            tokens = f"{'no data':>12} {'no data':>12} {'no data':>13}"
        lines.append(
            f"{model[:34]:<34} {provider[:16]:<16} {bucket['calls']:>6} "
            f"{_pct(bucket['ok'], bucket['calls']):>6} "
            f"{tokens} {bucket['calls_without_tokens']:>7}"
        )
    lines.append(
        f"{'TOTAL':<34} {'':<16} {overall['calls']:>6} "
        f"{_pct(overall['ok'], overall['calls']):>6} "
        f"{_thousands(overall['input_tokens']):>12} "
        f"{_thousands(overall['output_tokens']):>12} "
        f"{_thousands(overall['total_tokens']):>13} "
        f"{overall['calls_without_tokens']:>7}"
    )

    lines += [
        "",
        "SUCCESS RATE BY MODEL x EFFORT",
        f"{'model':<34} {'effort':<10} {'calls':>6} {'ok':>6} {'err':>5} "
        f"{'t/o':>5} {'refu':>5} {'ok%':>7} {'avg ms':>9}",
        "-" * 96,
    ]
    ordered_effort = sorted(
        data["by_model_effort"].items(),
        key=lambda item: (item[0][0], item[0][1]),
    )
    for (model, effort), bucket in ordered_effort:
        avg_ms = (
            f"{bucket['wall_ms_total'] // bucket['wall_ms_samples']:,}"
            if bucket["wall_ms_samples"]
            else "-"
        )
        lines.append(
            f"{model[:34]:<34} {effort[:10]:<10} {bucket['calls']:>6} "
            f"{bucket['ok']:>6} {bucket['error']:>5} {bucket['timeout']:>5} "
            f"{bucket['refusal']:>5} {_pct(bucket['ok'], bucket['calls']):>7} {avg_ms:>9}"
        )
    return "\n".join(lines)


def to_json(data: dict, root: Path) -> str:
    def flatten(mapping: dict, second_key: str) -> list[dict]:
        rows = []
        for key, bucket in mapping.items():
            row = {"model": key[0], second_key: key[1]}
            row.update(bucket)
            rows.append(row)
        return sorted(rows, key=lambda row: (row["model"], row[second_key]))

    payload = {
        "store": str(root),
        "first_ts": _stamp(data["first_ms"]),
        "last_ts": _stamp(data["last_ms"]),
        "overall": data["overall"],
        "by_model_provider": flatten(data["by_model_provider"], "provider"),
        "by_model_effort": flatten(data["by_model_effort"], "effort"),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="telemetry-query",
        description="Roll up the cross-board model-call telemetry store.",
    )
    parser.add_argument("--dir", help="store root (default $T1000_TELEMETRY_DIR or ~/.t1000/telemetry)")
    parser.add_argument("--since", type=parse_when, help="24h | 7d | 2026-08-01 | ISO8601")
    parser.add_argument("--until", type=parse_when, help="24h | 7d | 2026-08-01 | ISO8601")
    parser.add_argument("--board", help="filter to one kanban board")
    parser.add_argument("--lane", help="filter to one profile/lane")
    parser.add_argument("--provider", help="filter to one provider")
    parser.add_argument("--model", help="filter to one model slug")
    parser.add_argument("--task", help="filter to one aux task (or main_loop)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of tables")
    args = parser.parse_args(argv)

    root = telemetry_dir(args.dir)
    records = [
        record
        for record in iter_records(root, args.since, args.until)
        if matches(record, args)
    ]

    if not records:
        if args.json:
            print(json.dumps({"store": str(root), "calls": 0, "message": "no data yet"}, indent=2))
        else:
            exists = root.is_dir()
            where = str(root)
            print(f"no data yet — {where}" + ("" if exists else " (store not created yet)"))
            print("Nothing has been recorded through agent/call_telemetry.py for this filter.")
        return 0

    data = rollup(records)
    print(to_json(data, root) if args.json else render_text(data, root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
