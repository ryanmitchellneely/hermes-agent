#!/usr/bin/env python3
"""Usage + success SURFACE over the cross-board model-call telemetry store.

``scripts/telemetry_query.py`` (MESH-TEL-2a) answers "what is in the store".
This answers Ryan's actual questions:

    "are we keeping track of how much money we are saving using local, how
     many runs etc? is there a place it can be live? not just a snapshot in
     time? I want a full overview of where every token is going, how long
     different systems are working or taking, bottlenecks."

so it is a scheduled digest, not a query CLI: it rolls up per model / provider
/ lane / effort, prices what can honestly be priced, ranks where the wall clock
actually goes, raises decision flags, writes a markdown surface, and heartbeats
every run whether it succeeded or not.

WHY A SECOND MODULE INSTEAD OF EXTENDING telemetry_query
--------------------------------------------------------
The store-reading primitives ARE reused — ``telemetry_dir``, ``parse_when``
and ``iter_records`` are imported from ``telemetry_query`` rather than
reimplemented. Its ``rollup()`` is not, because its buckets are lossy by
design: they keep running sums only. p50/p95 needs the retained samples, the
decision hooks need to compare groups against each other, and the cost split
needs a per-row classification. Bolting all of that onto the query CLI would
make one file serve two contracts (ad-hoc filter tool + scheduled job).

THREE CORRECTNESS RULES THIS FILE EXISTS TO ENFORCE
---------------------------------------------------
1. ``tokens_available=false`` rows are excluded from every token and cost
   total and reported as their own count. They are never summed as zero —
   that is what made the subscription lanes read as free. Pinned by
   ``test_tokens_unavailable_rows_never_enter_a_sum``.

2. Local-vs-hosted is derived from PROVIDER IDENTITY, never from a boolean a
   caller can set wrong. ``LAB-SCOREBOARD.jsonl`` carries 22 rows where
   ``sonnet`` / ``grok-4.5`` / ``opus`` are tagged ``is_local=true``. A
   provider this module cannot place is counted as ``unknown`` and printed as
   ``unknown`` — never guessed into a bucket. Note that ``custom`` is
   deliberately unknown: it covers both local Ollama and hosted
   OpenAI-compatible endpoints (GLM on Volcengine ARK), and schema v1 carries
   no ``base_url`` to tell them apart. Fix it with a provider-class map
   (``--provider-class-map``), which is operator configuration, not a guess.

3. Failures are as visible as successes. ``FLASH-SCOREBOARD.jsonl`` has never
   recorded a single failure in 25 runs, which makes its 100% meaningless.
   Every table here prints the failure columns even when they are zero, and
   any group thinner than ``LOW_CONFIDENCE_CALLS`` is stamped so a 100% built
   from 3 calls cannot be read as reliability.

Deliberately degrades to stdlib-only: pricing is a soft import, and when it is
unavailable the digest still renders with dollars marked unavailable.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from telemetry_query import (  # noqa: E402
    iter_records,
    parse_when,
    telemetry_dir,
)

HEARTBEAT_SYSTEM = "telemetry-digest"

#: Default cadence claimed by the heartbeat. A consumer treats the status file
#: as stale past this, exactly like ``deploy/kevin-spark/ds4-watchdog.sh``.
DEFAULT_INTERVAL_SECONDS = 86400

#: Below this many calls a group's success rate is noise, not a measurement.
LOW_CONFIDENCE_CALLS = 10

#: Decision flags stay silent below these sample counts. A flag that fires on
#: n=1 trains the reader to ignore flags.
MIN_CALLS_FOR_SUCCESS_FLAG = 5
MIN_CALLS_FOR_EFFORT_FLAG = 5

#: A model must be this far below its lane's success rate to be worth saying.
SUCCESS_RATE_FLAG_DELTA = 10.0

#: Providers whose inference runs on hardware in the fleet. Marginal token
#: cost is genuinely zero.
LOCAL_PROVIDERS = frozenset(
    {
        "spark",
        "kevin-spark",
        "mbp-ollama",
        "ollama",
        "local",
        "llama-cpp",
        "llamacpp",
        "vllm",
        "ds4",
        "exo",
    }
)

#: Flat-fee seats. Marginal token cost is zero but the seat is NOT free, so
#: these are never folded in with local — that conflation is the whole reason
#: ``tokens_available`` exists.
SUBSCRIPTION_PROVIDERS = frozenset(
    {
        "claude-acp",
        "copilot-acp",
        "openai-codex",
        "xai-oauth",
        "codex",
    }
)

#: Pay-per-token APIs. Real dollars leave the account.
METERED_PROVIDERS = frozenset(
    {
        "anthropic",
        "openai",
        "openai-api",
        "openrouter",
        "google",
        "gemini",
        "vertex",
        "fireworks",
        "nous",
        "minimax",
        "minimax-cn",
        "groq",
        "deepseek",
        "xai",
        "mistral",
        "together",
        "bedrock",
        "cerebras",
    }
)

COST_CLASSES = ("local", "subscription", "metered", "unknown")

SUMMABLE_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
)

OUTCOMES = ("ok", "error", "timeout", "refusal")


# ── cost classification ────────────────────────────────────────────────────


def load_provider_class_map(path: Optional[Path]) -> dict[str, str]:
    """Load an operator-supplied ``{provider: cost_class}`` override map.

    This is the supported way to resolve an ambiguous provider slug (``custom``
    being the live one). Configuration is not a guess: someone who knows which
    endpoint ``custom`` points at states it once, here.

    A missing file is not an error — the map is optional. Unknown class names
    are dropped rather than trusted.
    """
    if path is None or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key).strip().lower(): str(value).strip().lower()
        for key, value in raw.items()
        if str(value).strip().lower() in COST_CLASSES
    }


def classify_provider(provider: Any, class_map: Optional[dict[str, str]] = None) -> str:
    """Map a provider slug onto a cost class. Never guesses.

    Resolution order: operator override map, then the three known-provider
    tables, then ``unknown``. There is no fallback that infers "probably
    local" from a model name — that inference is exactly what mislabels 22
    LAB-SCOREBOARD rows.
    """
    name = str(provider or "").strip().lower()
    if not name:
        return "unknown"
    if class_map and name in class_map:
        return class_map[name]
    if name in LOCAL_PROVIDERS:
        return "local"
    if name in SUBSCRIPTION_PROVIDERS:
        return "subscription"
    if name in METERED_PROVIDERS:
        return "metered"
    return "unknown"


def _load_pricing():
    """Soft-import the repo pricing helpers. Returns ``None`` when unavailable.

    Keeps the digest runnable under a bare system ``python3`` with no venv —
    the same constraint ``telemetry_query.py`` holds itself to. Without it the
    token picture still renders; only the dollar columns go to ``unavailable``.
    """
    try:
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost

        return CanonicalUsage, estimate_usage_cost
    except Exception:
        return None


# ── statistics ─────────────────────────────────────────────────────────────


def percentile(values: list[int | float], q: float) -> Optional[float]:
    """Nearest-rank percentile of *q* in [0, 1]. ``None`` for an empty list.

    Nearest-rank (not interpolated) so every reported number is an observation
    that actually happened — an interpolated p95 of 6 samples invents a
    latency no call ever took.
    """
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return float(ordered[min(rank, len(ordered)) - 1])


def _blank_bucket() -> dict:
    bucket: dict[str, Any] = {
        "calls": 0,
        "calls_with_tokens": 0,
        "calls_without_tokens": 0,
        "wall_samples": [],
        "ttft_samples": [],
        "wall_ms_total": 0,
        "cost_usd": 0.0,
        "cost_priced_calls": 0,
        "cost_unpriced_calls": 0,
        "cost_unattributed_calls": 0,
        "cost_classes": {},
    }
    bucket.update({outcome: 0 for outcome in OUTCOMES})
    bucket.update({field: 0 for field in SUMMABLE_TOKEN_FIELDS})
    return bucket


def _accumulate(bucket: dict, record: dict, cost: Optional[float], cost_class: str) -> None:
    bucket["calls"] += 1

    outcome = str(record.get("outcome") or "error")
    bucket[outcome if outcome in OUTCOMES else "error"] += 1

    bucket["cost_classes"][cost_class] = bucket["cost_classes"].get(cost_class, 0) + 1

    wall = record.get("wall_ms")
    if isinstance(wall, (int, float)):
        bucket["wall_samples"].append(int(wall))
        bucket["wall_ms_total"] += int(wall)

    ttft = record.get("ttft_ms")
    if isinstance(ttft, (int, float)):
        bucket["ttft_samples"].append(int(ttft))

    # THE rule: a row without real token data contributes to no sum. It is
    # counted on its own line so it stays visible instead of reading as zero.
    if record.get("tokens_available") is True:
        bucket["calls_with_tokens"] += 1
        for field in SUMMABLE_TOKEN_FIELDS:
            value = record.get(field)
            if isinstance(value, (int, float)):
                bucket[field] += int(value)
        if cost is not None:
            bucket["cost_usd"] += cost
            bucket["cost_priced_calls"] += 1
        elif cost_class == "metered":
            bucket["cost_unpriced_calls"] += 1
        elif cost_class == "unknown":
            # Neither spent nor free — we do not know which. Tracked so a
            # mixed-class row cannot present an incomplete total as complete.
            bucket["cost_unattributed_calls"] += 1
    else:
        # Excluded from every sum above, but NOT dropped: the call still shows
        # up in `calls` and in its outcome, and this counter is what the
        # surface prints as "N calls with no token data".
        bucket["calls_without_tokens"] += 1


def _finalize(bucket: dict) -> dict:
    walls = bucket.pop("wall_samples")
    ttfts = bucket.pop("ttft_samples")
    out = dict(bucket)
    out["wall_p50_ms"] = percentile(walls, 0.50)
    out["wall_p95_ms"] = percentile(walls, 0.95)
    out["wall_max_ms"] = float(max(walls)) if walls else None
    out["wall_mean_ms"] = round(statistics.fmean(walls), 1) if walls else None
    out["wall_samples_n"] = len(walls)
    out["ttft_p50_ms"] = percentile(ttfts, 0.50)
    out["ttft_p95_ms"] = percentile(ttfts, 0.95)
    out["ttft_samples_n"] = len(ttfts)
    out["success_rate"] = (
        round(100.0 * bucket["ok"] / bucket["calls"], 1) if bucket["calls"] else None
    )
    out["failures"] = bucket["error"] + bucket["timeout"] + bucket["refusal"]
    out["low_confidence"] = bucket["calls"] < LOW_CONFIDENCE_CALLS
    out["cost_usd"] = round(bucket["cost_usd"], 6)
    return out


# ── summarize ──────────────────────────────────────────────────────────────


def _price_row(record: dict, cost_class: str, pricing) -> Optional[float]:
    """Dollars actually spent on this call, or ``None`` when unknowable.

    Only ``metered`` rows can cost money. ``local`` and ``subscription`` are
    zero marginal by construction — but they are returned as ``0.0``, not
    ``None``, so "we know it was free" is distinguishable from "we could not
    price it", which is the distinction the LAB scoreboard lost.
    """
    if cost_class in ("local", "subscription"):
        return 0.0
    if cost_class != "metered" or pricing is None:
        return None
    if record.get("tokens_available") is not True:
        return None
    canonical_cls, estimate = pricing
    try:
        usage = canonical_cls(
            input_tokens=int(record.get("input_tokens") or 0),
            output_tokens=int(record.get("output_tokens") or 0),
            cache_read_tokens=int(record.get("cache_read_tokens") or 0),
            cache_write_tokens=int(record.get("cache_write_tokens") or 0),
            reasoning_tokens=int(record.get("reasoning_tokens") or 0),
        )
        result = estimate(
            str(record.get("model") or ""),
            usage,
            provider=str(record.get("provider") or "") or None,
        )
        if result.amount_usd is None:
            return None
        return float(result.amount_usd)
    except Exception:
        return None


def summarize(
    records: Iterable[dict],
    *,
    class_map: Optional[dict[str, str]] = None,
    pricing: Any = None,
    now: Optional[datetime] = None,
) -> dict:
    """Roll the store up into everything the surface renders. Pure, no I/O."""
    class_map = class_map or {}
    now = now or datetime.now().astimezone()

    by_model: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}
    by_lane: dict[str, dict] = {}
    by_class: dict[str, dict] = {}
    by_model_effort: dict[tuple[str, str], dict] = {}
    by_model_lane: dict[tuple[str, str], dict] = {}
    by_task: dict[str, dict] = {}
    overall = _blank_bucket()

    unknown_providers: dict[str, int] = {}
    first_ms: Optional[int] = None
    last_ms: Optional[int] = None
    total = 0

    for record in records:
        total += 1
        model = str(record.get("model") or "unknown")
        provider = str(record.get("provider") or "unknown")
        lane = str(record.get("lane") or "unknown")
        effort = str(record.get("effort") or "-")
        task = str(record.get("task") or "unknown")

        cost_class = classify_provider(provider, class_map)
        if cost_class == "unknown":
            unknown_providers[provider] = unknown_providers.get(provider, 0) + 1
        cost = _price_row(record, cost_class, pricing)

        for mapping, key in (
            (by_model, model),
            (by_provider, provider),
            (by_lane, lane),
            (by_class, cost_class),
            (by_task, task),
        ):
            _accumulate(mapping.setdefault(key, _blank_bucket()), record, cost, cost_class)
        _accumulate(
            by_model_effort.setdefault((model, effort), _blank_bucket()),
            record,
            cost,
            cost_class,
        )
        _accumulate(
            by_model_lane.setdefault((lane, model), _blank_bucket()),
            record,
            cost,
            cost_class,
        )
        _accumulate(overall, record, cost, cost_class)

        stamp = record.get("ts_epoch_ms")
        if isinstance(stamp, int):
            first_ms = stamp if first_ms is None else min(first_ms, stamp)
            last_ms = stamp if last_ms is None else max(last_ms, stamp)

    finalized_model = {key: _finalize(value) for key, value in by_model.items()}
    finalized_lane = {key: _finalize(value) for key, value in by_lane.items()}
    finalized_model_lane = {key: _finalize(value) for key, value in by_model_lane.items()}
    finalized_effort = {key: _finalize(value) for key, value in by_model_effort.items()}

    summary = {
        "generated_at": now.isoformat(timespec="seconds"),
        "calls": total,
        "first_ts": _stamp(first_ms),
        "last_ts": _stamp(last_ms),
        "first_ms": first_ms,
        "last_ms": last_ms,
        "overall": _finalize(overall),
        "by_model": finalized_model,
        "by_provider": {key: _finalize(value) for key, value in by_provider.items()},
        "by_lane": finalized_lane,
        "by_cost_class": {key: _finalize(value) for key, value in by_class.items()},
        "by_model_effort": finalized_effort,
        "by_model_lane": finalized_model_lane,
        "by_task": {key: _finalize(value) for key, value in by_task.items()},
        "unknown_providers": unknown_providers,
        "pricing_available": pricing is not None,
    }
    summary["flags"] = build_flags(summary)
    summary["caveats"] = build_caveats(summary)
    return summary


# ── decision hooks ─────────────────────────────────────────────────────────


def build_flags(summary: dict) -> list[dict]:
    """Turn the rollup into things a human should act on.

    Every flag carries the evidence that produced it and every one is gated on
    a sample floor. The eviction and effort hooks are the two the card names;
    the token-coverage and attribution flags exist because a surface that
    silently loses rows is the failure mode this whole store was built after.
    """
    flags: list[dict] = []
    overall = summary["overall"]

    # 1. A model doing measurably worse than the lane it runs in.
    for (lane, model), bucket in sorted(summary["by_model_lane"].items()):
        lane_bucket = summary["by_lane"].get(lane)
        if not lane_bucket or bucket["calls"] < MIN_CALLS_FOR_SUCCESS_FLAG:
            continue
        if bucket["success_rate"] is None or lane_bucket["success_rate"] is None:
            continue
        delta = lane_bucket["success_rate"] - bucket["success_rate"]
        if delta >= SUCCESS_RATE_FLAG_DELTA:
            flags.append(
                {
                    "kind": "success_below_lane",
                    "severity": "warn",
                    "subject": f"{model} in lane {lane}",
                    "detail": (
                        f"{bucket['success_rate']}% ok over {bucket['calls']} calls "
                        f"vs lane average {lane_bucket['success_rate']}% "
                        f"({delta:.1f}pp below)"
                    ),
                }
            )

    # 2. Reasoning effort buying nothing. Only fires when BOTH arms of the
    #    comparison clear the floor — otherwise it is a coin flip with a label.
    by_effort_for_model: dict[str, dict[str, dict]] = {}
    for (model, effort), bucket in summary["by_model_effort"].items():
        by_effort_for_model.setdefault(model, {})[effort] = bucket
    order = ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
    for model, arms in sorted(by_effort_for_model.items()):
        ranked = [
            (order.index(effort), effort, bucket)
            for effort, bucket in arms.items()
            if effort in order and bucket["calls"] >= MIN_CALLS_FOR_EFFORT_FLAG
        ]
        ranked.sort()
        for i in range(len(ranked) - 1):
            _, low_effort, low_bucket = ranked[i]
            _, high_effort, high_bucket = ranked[i + 1]
            if low_bucket["success_rate"] is None or high_bucket["success_rate"] is None:
                continue
            if high_bucket["success_rate"] <= low_bucket["success_rate"]:
                slower = ""
                if low_bucket["wall_p50_ms"] and high_bucket["wall_p50_ms"]:
                    ratio = high_bucket["wall_p50_ms"] / low_bucket["wall_p50_ms"]
                    slower = f", and {ratio:.1f}x the p50 wall time"
                flags.append(
                    {
                        "kind": "effort_not_earning",
                        "severity": "warn",
                        "subject": f"{model} at effort={high_effort}",
                        "detail": (
                            f"effort={high_effort} scores {high_bucket['success_rate']}% "
                            f"over {high_bucket['calls']} calls, no better than "
                            f"effort={low_effort} at {low_bucket['success_rate']}% "
                            f"over {low_bucket['calls']} calls{slower}"
                        ),
                    }
                )

    # 3. Token attribution gaps — the failure this store was built to prevent.
    if overall["calls_without_tokens"]:
        flags.append(
            {
                "kind": "tokens_missing",
                "severity": "info",
                "subject": "token coverage",
                "detail": (
                    f"{overall['calls_without_tokens']} of {overall['calls']} calls "
                    f"carry no token data and are excluded from every total below "
                    f"(never summed as zero)"
                ),
            }
        )

    # 4. Cost-class attribution gaps — the LAB-SCOREBOARD failure.
    if summary["unknown_providers"]:
        listed = ", ".join(
            f"{name} ({count})"
            for name, count in sorted(
                summary["unknown_providers"].items(), key=lambda kv: -kv[1]
            )
        )
        flags.append(
            {
                "kind": "cost_class_unknown",
                "severity": "warn",
                "subject": "local-vs-hosted attribution",
                "detail": (
                    f"{listed} could not be placed as local / subscription / metered. "
                    f"Counted as unknown, never guessed. Resolve with a "
                    f"provider-class map (--provider-class-map)."
                ),
            }
        )

    # 5. Thin data. Says so instead of letting a 100% off 6 calls read as
    #    reliability — the FLASH-SCOREBOARD 25/25 mistake.
    if overall["calls"] < LOW_CONFIDENCE_CALLS:
        flags.append(
            {
                "kind": "thin_data",
                "severity": "info",
                "subject": "sample size",
                "detail": (
                    f"only {overall['calls']} calls in window; success rates here "
                    f"are not yet a measurement of reliability"
                ),
            }
        )
    elif overall["failures"] == 0:
        flags.append(
            {
                "kind": "no_failures_observed",
                "severity": "info",
                "subject": "failure coverage",
                "detail": (
                    f"0 failures across {overall['calls']} calls. Confirm the failure "
                    f"emit site (run_agent.py::_invoke_api_request_error_hook) is "
                    f"actually firing before reading this as reliability"
                ),
            }
        )

    return flags


def eviction_candidates(
    all_records: Iterable[dict], *, now_ms: int, idle_days: int = 7
) -> list[dict]:
    """Models seen historically but silent for *idle_days* — residency evictions.

    Deliberately computed over the WHOLE store rather than the digest window:
    "no calls in 7 days" is only meaningful against models that were once
    called at all.
    """
    cutoff = now_ms - idle_days * 86400 * 1000
    last_seen: dict[tuple[str, str], int] = {}
    counts: dict[tuple[str, str], int] = {}
    for record in all_records:
        key = (
            str(record.get("provider") or "unknown"),
            str(record.get("model") or "unknown"),
        )
        stamp = record.get("ts_epoch_ms")
        if not isinstance(stamp, int):
            continue
        counts[key] = counts.get(key, 0) + 1
        last_seen[key] = max(last_seen.get(key, 0), stamp)

    idle = []
    for key, stamp in sorted(last_seen.items()):
        if stamp < cutoff:
            idle.append(
                {
                    "provider": key[0],
                    "model": key[1],
                    "last_seen": _stamp(stamp),
                    "lifetime_calls": counts[key],
                    "idle_days": round((now_ms - stamp) / 86400000.0, 1),
                }
            )
    return idle


def build_caveats(summary: dict) -> list[str]:
    """State plainly what this data CANNOT answer.

    Required by the brief: name the gap rather than invent a bottleneck metric
    the schema does not support.
    """
    caveats = []
    overall = summary["overall"]

    if overall["ttft_samples_n"] == 0:
        caveats.append(
            "No row carries ttft_ms, so wall time cannot be split into queue/"
            "startup wait vs generation time. The ACP and chat-completions "
            "transports do not measure first-token latency. Total wall time and "
            "its distribution are real; 'why is it slow' is not answerable from "
            "this store alone."
        )
    if overall["wall_samples_n"] < overall["calls"]:
        missing = overall["calls"] - overall["wall_samples_n"]
        caveats.append(
            f"{missing} of {overall['calls']} calls carry no wall_ms (the aux "
            f"fallback chain has no per-attempt timing at its emit site), so "
            f"latency percentiles describe only the {overall['wall_samples_n']} "
            f"timed calls."
        )
    if not summary["pricing_available"]:
        caveats.append(
            "agent.usage_pricing could not be imported, so metered spend shows "
            "as unavailable rather than as $0."
        )
    if overall["cost_unpriced_calls"]:
        caveats.append(
            f"{overall['cost_unpriced_calls']} metered call(s) had no pricing "
            f"entry for their model and are excluded from the spend total."
        )
    caveats.append(
        "One row is one model CALL, not one run. A single kanban run makes many "
        "calls, so these counts are a floor on runs, never a run count."
    )
    caveats.append(
        "Known emit gaps (MESH-TEL-2b): calls retried inside a provider SDK, and "
        "the streaming aux path, are not counted at all."
    )
    return caveats


# ── rendering ──────────────────────────────────────────────────────────────


def _stamp(ms: Optional[int]) -> Optional[str]:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000.0).astimezone().isoformat(timespec="seconds")


def _n(value: Optional[float], suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}{suffix}"
    return f"{value:,.1f}{suffix}"


def _tokens_cell(bucket: dict, field: str) -> str:
    """Print ``no data`` — never ``0`` — for a group where nothing reported tokens.

    A zero here is precisely the misread (a subscription lane looking free)
    that this store exists to prevent.
    """
    if not bucket["calls_with_tokens"]:
        return "no data"
    return f"{bucket[field]:,}"


def _rate_cell(bucket: dict) -> str:
    if bucket["success_rate"] is None:
        return "—"
    mark = " ⚠thin" if bucket["low_confidence"] else ""
    return f"{bucket['success_rate']:.1f}%{mark}"


def _cost_cell(bucket: dict, pricing_available: bool, cost_class: Optional[str] = None) -> str:
    """Render spend so a zero can never be mistaken for "free".

    ``$0.0000`` is the exact ambiguity that makes a subscription lane look
    free, so a zero-marginal class prints WHY it is zero, and a class we
    cannot place prints that we cannot place it.
    """
    if cost_class == "local":
        return "$0 (local)"
    if cost_class == "subscription":
        return "$0 marginal (seat)"
    if cost_class == "unknown":
        return "not attributable"
    if not pricing_available:
        return "unavailable"
    if bucket["cost_unpriced_calls"] and not bucket["cost_priced_calls"]:
        return "unpriced"
    text = f"${bucket['cost_usd']:.4f}"
    notes = []
    if bucket["cost_unpriced_calls"]:
        notes.append(f"{bucket['cost_unpriced_calls']} unpriced")
    if bucket["cost_unattributed_calls"]:
        notes.append(f"{bucket['cost_unattributed_calls']} unattributed")
    if notes:
        text += " (+" + ", ".join(notes) + ")"
    return text


def _delta_row(label: str, previous: Any, current: Any, suffix: str = "") -> list[str]:
    """One trend row. Renders ``—`` rather than a fake 0 when a side is missing.

    A window with no data is not a window with zero — treating it as zero
    manufactures a 100% drop out of an absent measurement.
    """
    if previous is None or current is None:
        change = "—"
    else:
        diff = current - previous
        pct = f" ({100.0 * diff / previous:+.0f}%)" if previous else ""
        change = f"{diff:+,.1f}{suffix}{pct}" if isinstance(diff, float) else f"{diff:+,}{suffix}{pct}"
    return [
        label,
        _n(previous, suffix) if previous is not None else "—",
        _n(current, suffix) if current is not None else "—",
        change,
    ]


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["", "_(no rows)_"]
    lines = ["", "| " + " | ".join(header) + " |"]
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def render_markdown(
    summary: dict,
    *,
    store: Path,
    window_label: str,
    evictions: Optional[list[dict]] = None,
) -> str:
    overall = summary["overall"]
    pricing_available = summary["pricing_available"]
    lines: list[str] = [
        "# Model-call usage + success surface",
        "",
        f"_generated {summary['generated_at']} · window `{window_label}` · store `{store}`_",
        "",
    ]

    if not summary["calls"]:
        lines += [
            "## No calls in this window",
            "",
            "The store has no rows matching this window. On an active fleet that "
            "means the emit sites stopped firing, not that nothing ran — check "
            "`agent/call_telemetry.py` callers before assuming an idle system.",
            "",
        ]
        return "\n".join(lines) + "\n"

    # ── headline ──
    lines += [
        "## Headline",
        "",
        f"- **{overall['calls']:,} model calls** observed "
        f"({summary['first_ts']} → {summary['last_ts']})",
        f"- **{overall['ok']:,} ok · {overall['failures']:,} failed** "
        f"({overall['error']} error / {overall['timeout']} timeout / "
        f"{overall['refusal']} refusal) → {_rate_cell(overall)} success",
        f"- **{_tokens_cell(overall, 'total_tokens')} tokens** total "
        f"({_tokens_cell(overall, 'input_tokens')} in / "
        f"{_tokens_cell(overall, 'output_tokens')} out / "
        f"{_tokens_cell(overall, 'cache_read_tokens')} cache-read / "
        f"{_tokens_cell(overall, 'cache_write_tokens')} cache-write / "
        f"{_tokens_cell(overall, 'reasoning_tokens')} reasoning)",
        f"- **token coverage**: {overall['calls_with_tokens']} of {overall['calls']} "
        f"calls carry real token data; {overall['calls_without_tokens']} carry none "
        f"and are excluded from every total above (never summed as zero)",
        f"- **wall clock**: p50 {_n(overall['wall_p50_ms'], ' ms')} · "
        f"p95 {_n(overall['wall_p95_ms'], ' ms')} · "
        f"max {_n(overall['wall_max_ms'], ' ms')} "
        f"over {overall['wall_samples_n']} timed calls",
        (
            f"- **time to first token**: p50 {_n(overall['ttft_p50_ms'], ' ms')} · "
            f"p95 {_n(overall['ttft_p95_ms'], ' ms')} "
            f"over {overall['ttft_samples_n']} calls that report it"
            if overall["ttft_samples_n"]
            else "- **time to first token**: not reported by any call in this "
            "window (see the caveats at the bottom)"
        ),
        "",
    ]

    # ── where the money is ──
    lines += ["## Cost picture", ""]
    class_rows = []
    for name in COST_CLASSES:
        bucket = summary["by_cost_class"].get(name)
        if not bucket:
            continue
        class_rows.append(
            [
                f"**{name}**",
                f"{bucket['calls']:,}",
                _tokens_cell(bucket, "total_tokens"),
                _cost_cell(bucket, pricing_available, cost_class=name),
                _rate_cell(bucket),
            ]
        )
    lines += _table(
        ["cost class", "calls", "tokens", "spent (USD)", "success"], class_rows
    )
    lines += [
        "",
        "- `local` — inference on fleet hardware. Marginal token cost genuinely $0.",
        "- `subscription` — flat-fee seat (claude-acp, copilot-acp, codex). $0 "
        "marginal, but **the seat is not free** — never read this as savings.",
        "- `metered` — pay-per-token API. Real dollars leave the account.",
        "- `unknown` — the provider slug does not identify the hosting. Counted "
        "as unknown on purpose rather than guessed into a bucket.",
        "",
        "**Money saved by running local is not asserted here.** Doing so needs a "
        "counterfactual (\"what would this have cost on model X\"), which is an "
        "estimate, not a measurement. Pass `--counterfactual MODEL` to compute it "
        "explicitly; the number is then labelled as the estimate it is.",
        "",
    ]
    if summary.get("counterfactual"):
        counter = summary["counterfactual"]
        lines += [
            f"### Counterfactual vs `{counter['model']}` (estimate, not a measurement)",
            "",
        ]
        if counter.get("error"):
            # Requested but not computable — say so. Dropping the section would
            # read as "nothing to report" instead of "this failed".
            lines += [f"- **not computed** — {counter['error']}", ""]
        else:
            lines += [
                f"- local + subscription tokens repriced on `{counter['model']}`: "
                f"**${counter['would_have_cost_usd']:.4f}** across "
                f"{counter['calls']:,} calls",
                "- actually spent on those calls: **$0.00** marginal",
                f"- this assumes `{counter['model']}` would have produced the same "
                f"token counts on the same work, which is an assumption, not data.",
            ]
            if counter.get("unpriced_calls"):
                lines.append(
                    f"- {counter['unpriced_calls']} eligible call(s) could not be "
                    f"repriced and are excluded from the figure."
                )
            lines.append("")

    # ── trend ──
    if summary.get("previous"):
        prev = summary["previous"]
        lines += [
            f"## Trend vs the previous {window_label}",
            "",
            f"_{prev['window_label']}_",
            "",
        ]
        if not prev["calls"]:
            lines += [
                "- no calls in the previous window, so there is nothing to "
                "compare against yet.",
                "",
            ]
        else:
            lines += _table(
                ["metric", "previous", "current", "change"],
                [
                    _delta_row("calls", prev["calls"], overall["calls"]),
                    _delta_row(
                        "success rate",
                        prev["success_rate"],
                        overall["success_rate"],
                        suffix="%",
                    ),
                    _delta_row("failures", prev["failures"], overall["failures"]),
                    _delta_row(
                        "tokens",
                        prev["total_tokens"] if prev["calls_with_tokens"] else None,
                        overall["total_tokens"] if overall["calls_with_tokens"] else None,
                    ),
                    _delta_row(
                        "wall p50 (ms)", prev["wall_p50_ms"], overall["wall_p50_ms"]
                    ),
                    _delta_row(
                        "wall p95 (ms)", prev["wall_p95_ms"], overall["wall_p95_ms"]
                    ),
                ],
            )
            lines.append("")

    # ── failures first ──
    lines += [
        "## Failures",
        "",
    ]
    failing = sorted(
        (
            (key, bucket)
            for key, bucket in summary["by_model"].items()
            if bucket["failures"]
        ),
        key=lambda item: -item[1]["failures"],
    )
    if failing:
        lines += _table(
            ["model", "failures", "error", "timeout", "refusal", "calls", "success"],
            [
                [
                    key,
                    f"{bucket['failures']:,}",
                    f"{bucket['error']:,}",
                    f"{bucket['timeout']:,}",
                    f"{bucket['refusal']:,}",
                    f"{bucket['calls']:,}",
                    _rate_cell(bucket),
                ]
                for key, bucket in failing
            ],
        )
    else:
        lines += [
            f"No failed calls in {overall['calls']:,} observed. This section prints "
            f"whether or not there are failures — a scoreboard that only ever shows "
            f"successes is measuring its own blind spot, not reliability.",
        ]
    lines.append("")

    # ── per model ──
    lines += ["## By model", ""]
    lines += _table(
        ["model", "class(es)", "calls", "success", "in", "out", "total", "p50 ms", "p95 ms", "no-tok"],
        [
            [
                key,
                ", ".join(sorted(bucket["cost_classes"])),
                f"{bucket['calls']:,}",
                _rate_cell(bucket),
                _tokens_cell(bucket, "input_tokens"),
                _tokens_cell(bucket, "output_tokens"),
                _tokens_cell(bucket, "total_tokens"),
                _n(bucket["wall_p50_ms"]),
                _n(bucket["wall_p95_ms"]),
                f"{bucket['calls_without_tokens']:,}",
            ]
            for key, bucket in sorted(
                summary["by_model"].items(), key=lambda kv: -kv[1]["calls"]
            )
        ],
    )
    lines.append("")

    # ── per provider ──
    lines += ["## By provider", ""]
    lines += _table(
        ["provider", "class", "calls", "success", "tokens", "spent", "p50 ms", "p95 ms"],
        [
            [
                key,
                classify_provider(key, summary.get("class_map")),
                f"{bucket['calls']:,}",
                _rate_cell(bucket),
                _tokens_cell(bucket, "total_tokens"),
                _cost_cell(
                    bucket,
                    pricing_available,
                    cost_class=classify_provider(key, summary.get("class_map")),
                ),
                _n(bucket["wall_p50_ms"]),
                _n(bucket["wall_p95_ms"]),
            ]
            for key, bucket in sorted(
                summary["by_provider"].items(), key=lambda kv: -kv[1]["calls"]
            )
        ],
    )
    lines.append("")

    # ── per lane ──
    lines += ["## By lane (top 5 by token spend)", ""]
    ranked_lanes = sorted(
        summary["by_lane"].items(),
        key=lambda kv: (-kv[1]["total_tokens"], -kv[1]["calls"]),
    )[:5]
    lines += _table(
        ["lane", "calls", "success", "tokens", "spent", "wall total", "p50 ms", "p95 ms"],
        [
            [
                key,
                f"{bucket['calls']:,}",
                _rate_cell(bucket),
                _tokens_cell(bucket, "total_tokens"),
                _cost_cell(bucket, pricing_available),
                _n(round(bucket["wall_ms_total"] / 1000.0, 1), " s"),
                _n(bucket["wall_p50_ms"]),
                _n(bucket["wall_p95_ms"]),
            ]
            for key, bucket in ranked_lanes
        ],
    )
    lines.append("")

    # ── where the wall clock goes ──
    lines += [
        "## Where the wall clock goes",
        "",
        "Share of total observed wall time. This is the honest bottleneck signal "
        "the schema supports: it says which model is consuming the clock, not why.",
        "",
    ]
    wall_total = overall["wall_ms_total"] or 0
    wall_rows = []
    for key, bucket in sorted(
        summary["by_model"].items(), key=lambda kv: -kv[1]["wall_ms_total"]
    ):
        if not bucket["wall_ms_total"]:
            continue
        share = 100.0 * bucket["wall_ms_total"] / wall_total if wall_total else 0.0
        wall_rows.append(
            [
                key,
                f"{bucket['wall_ms_total'] / 1000.0:,.1f} s",
                f"{share:.1f}%",
                f"{bucket['calls']:,}",
                _n(bucket["wall_p50_ms"]),
                _n(bucket["wall_p95_ms"]),
                _n(bucket["wall_max_ms"]),
            ]
        )
    lines += _table(
        ["model", "wall total", "share", "calls", "p50 ms", "p95 ms", "max ms"], wall_rows
    )
    lines.append("")

    # ── effort ladder ──
    lines += ["## Success by model × effort", ""]
    lines += _table(
        ["model", "effort", "calls", "ok", "err", "t/o", "refusal", "success", "p50 ms"],
        [
            [
                key[0],
                key[1],
                f"{bucket['calls']:,}",
                f"{bucket['ok']:,}",
                f"{bucket['error']:,}",
                f"{bucket['timeout']:,}",
                f"{bucket['refusal']:,}",
                _rate_cell(bucket),
                _n(bucket["wall_p50_ms"]),
            ]
            for key, bucket in sorted(summary["by_model_effort"].items())
        ],
    )
    lines.append("")

    # ── decisions ──
    lines += ["## Decision flags", ""]
    if summary["flags"]:
        for flag in summary["flags"]:
            marker = "🔴" if flag["severity"] == "warn" else "•"
            lines.append(f"- {marker} **{flag['subject']}** — {flag['detail']}")
    else:
        lines.append("- none raised")
    lines.append("")

    if evictions:
        lines += [
            "## Eviction candidates (no calls in 7 days)",
            "",
        ]
        lines += _table(
            ["provider", "model", "last seen", "idle days", "lifetime calls"],
            [
                [
                    row["provider"],
                    row["model"],
                    row["last_seen"] or "—",
                    f"{row['idle_days']}",
                    f"{row['lifetime_calls']:,}",
                ]
                for row in evictions
            ],
        )
        lines.append("")
    elif evictions is not None:
        lines += [
            "## Eviction candidates (no calls in 7 days)",
            "",
            "- none; every model seen in the store has been called within 7 days",
            "",
        ]

    # ── what this cannot tell you ──
    lines += ["## What this data cannot tell you", ""]
    for caveat in summary["caveats"]:
        lines.append(f"- {caveat}")
    lines.append("")

    return "\n".join(lines) + "\n"


# ── serialization ──────────────────────────────────────────────────────────


def jsonable(summary: dict) -> dict:
    """Flatten the tuple-keyed groupings so the rollup can be serialized.

    ``by_model_effort`` / ``by_model_lane`` key on pairs, which JSON cannot
    represent as object keys — they become lists of rows carrying their key
    parts as fields.
    """
    out = dict(summary)
    for name, fields in (
        ("by_model_effort", ("model", "effort")),
        ("by_model_lane", ("lane", "model")),
    ):
        rows = []
        for key, bucket in sorted(summary.get(name, {}).items()):
            row = dict(zip(fields, key))
            row.update(bucket)
            rows.append(row)
        out[name] = rows
    return out


# ── counterfactual ─────────────────────────────────────────────────────────


def compute_counterfactual(
    records: list[dict], reference: str, pricing, class_map
) -> Optional[dict]:
    """Reprice zero-marginal-cost tokens against *reference*. An ESTIMATE.

    *reference* is ``model`` or ``model@provider``. Most pricing tables key on
    (provider, model), so a bare model name frequently resolves to no route at
    all — hence the explicit ``@provider`` form.

    Kept opt-in and labelled everywhere it surfaces because "we saved $X" is
    the single easiest number in this system to fabricate: it rests entirely on
    a run that never happened.

    Returns a dict carrying either a priced result or an ``error`` explaining
    why it could not be priced. It never returns ``None`` for a *requested*
    counterfactual — silently omitting the section would leave the reader
    thinking the tool had nothing to say, when in fact it failed.
    """
    model, _, provider = reference.partition("@")
    model = model.strip()
    provider = provider.strip() or None

    if pricing is None:
        return {
            "model": model,
            "error": "agent.usage_pricing could not be imported, so no reference price is available",
        }

    canonical_cls, estimate = pricing
    total = 0.0
    calls = 0
    eligible = 0
    unpriced = 0
    for record in records:
        if record.get("tokens_available") is not True:
            continue
        if classify_provider(record.get("provider"), class_map) not in ("local", "subscription"):
            continue
        eligible += 1
        try:
            usage = canonical_cls(
                input_tokens=int(record.get("input_tokens") or 0),
                output_tokens=int(record.get("output_tokens") or 0),
                cache_read_tokens=int(record.get("cache_read_tokens") or 0),
                cache_write_tokens=int(record.get("cache_write_tokens") or 0),
                reasoning_tokens=int(record.get("reasoning_tokens") or 0),
            )
            result = estimate(model, usage, provider=provider)
            if result.amount_usd is None:
                unpriced += 1
                continue
            total += float(result.amount_usd)
            calls += 1
        except Exception:
            unpriced += 1

    if not eligible:
        return {
            "model": model,
            "error": (
                "no local or subscription calls with token data in this window, "
                "so there is nothing to reprice"
            ),
        }
    if not calls:
        return {
            "model": model,
            "error": (
                f"no pricing entry for reference model {model!r}"
                + (f" on provider {provider!r}" if provider else "")
                + ". Most pricing tables key on (provider, model) — try "
                f"--counterfactual '{model}@anthropic' (or the right provider)"
            ),
        }
    return {
        "model": model if not provider else f"{model}@{provider}",
        "would_have_cost_usd": round(total, 6),
        "calls": calls,
        "unpriced_calls": unpriced,
    }


# ── heartbeat + surface ────────────────────────────────────────────────────


def write_heartbeat(path: Path, payload: dict) -> None:
    """Write the status file atomically. Shape matches ds4-watchdog.sh.

    Called on EVERY run including the failure path — a missing or stale status
    file must unambiguously mean "the digest itself is dead", never be
    confusable with "ran fine, nothing to report".
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def heartbeat_payload(
    status: str, *, interval_seconds: int, detail: str, **extra: Any
) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "system": HEARTBEAT_SYSTEM,
        "status": status,
        "fired_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fired_at_epoch": int(now.timestamp()),
        "expected_interval_seconds": int(interval_seconds),
        "detail": detail,
    }
    payload.update(extra)
    return payload


# ── CLI ────────────────────────────────────────────────────────────────────


def default_surface_path(root: Path) -> Path:
    return root / "USAGE-DIGEST-latest.md"


def default_heartbeat_path(root: Path) -> Path:
    return root / "telemetry-digest-heartbeat.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telemetry-digest",
        description="Render the usage + success surface over the model-call store.",
    )
    parser.add_argument("--dir", help="store root (default $T1000_TELEMETRY_DIR or ~/.t1000/telemetry)")
    parser.add_argument("--since", default="24h", help="24h | 7d | 2026-08-01 | ISO8601 (default 24h)")
    parser.add_argument("--until", help="upper bound, same formats")
    parser.add_argument("--board", help="filter to one kanban board")
    parser.add_argument("--lane", help="filter to one profile/lane")
    parser.add_argument("--out", help="markdown surface path (default <store>/USAGE-DIGEST-latest.md)")
    parser.add_argument("--heartbeat", help="status file path (default <store>/telemetry-digest-heartbeat.json)")
    parser.add_argument("--no-heartbeat", action="store_true", help="skip the status file (tests / ad-hoc runs)")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="cadence this digest claims in its heartbeat (default 86400)",
    )
    parser.add_argument("--provider-class-map", help="JSON {provider: local|subscription|metered}")
    parser.add_argument("--counterfactual", help="reprice local+subscription tokens on this model (an ESTIMATE)")
    parser.add_argument("--idle-days", type=int, default=7, help="eviction threshold (default 7)")
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="skip the trend section (by default the equal-length window "
        "immediately before --since is rolled up for comparison)",
    )
    parser.add_argument("--json", action="store_true", help="emit the rollup as JSON instead of markdown")
    parser.add_argument("--quiet", action="store_true", help="write files but do not print the body")
    parser.add_argument(
        "--no-alert-on-empty",
        action="store_true",
        help="exit 0 when the window has no calls (default: exit 1, because a "
        "silent telemetry digest manufactures false confidence)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = telemetry_dir(args.dir)
    heartbeat_path = Path(args.heartbeat) if args.heartbeat else default_heartbeat_path(root)
    surface_path = Path(args.out) if args.out else default_surface_path(root)

    try:
        since_ms = parse_when(args.since) if args.since else None
        until_ms = parse_when(args.until) if args.until else None
        class_map = load_provider_class_map(
            Path(args.provider_class_map).expanduser()
            if args.provider_class_map
            else root / "provider_classes.json"
        )
        pricing = _load_pricing()

        records = []
        for record in iter_records(root, since_ms, until_ms):
            if args.board and str(record.get("board") or "") != args.board:
                continue
            if args.lane and str(record.get("lane") or "") != args.lane:
                continue
            records.append(record)

        summary = summarize(records, class_map=class_map, pricing=pricing)
        summary["class_map"] = class_map
        summary["store"] = str(root)
        summary["window"] = args.since

        # "not just a snapshot in time" — the immediately preceding window of
        # equal length, so every render carries its own direction of travel.
        if since_ms is not None and not args.no_compare:
            span = (until_ms or int(datetime.now().timestamp() * 1000)) - since_ms
            if span > 0:
                prior = [
                    record
                    for record in iter_records(root, since_ms - span, since_ms - 1)
                    if (not args.board or str(record.get("board") or "") == args.board)
                    and (not args.lane or str(record.get("lane") or "") == args.lane)
                ]
                previous = summarize(prior, class_map=class_map, pricing=pricing)[
                    "overall"
                ]
                previous["calls"] = len(prior)
                previous["window_label"] = (
                    f"{_stamp(since_ms - span)} → {_stamp(since_ms)}"
                )
                summary["previous"] = previous

        if args.counterfactual:
            counter = compute_counterfactual(records, args.counterfactual, pricing, class_map)
            if counter:
                summary["counterfactual"] = counter

        now_ms = int(datetime.now().timestamp() * 1000)
        evictions = eviction_candidates(
            iter_records(root, None, None), now_ms=now_ms, idle_days=args.idle_days
        )

        body = (
            json.dumps(jsonable(summary), indent=2, sort_keys=True, default=str)
            if args.json
            else render_markdown(
                summary, store=root, window_label=args.since, evictions=evictions
            )
        )

        # Surface is written BEFORE anything can fail downstream, so the last
        # good digest stays readable even when delivery breaks (kevin_digest.py
        # establishes this ordering).
        if not args.json:
            try:
                surface_path.parent.mkdir(parents=True, exist_ok=True)
                surface_path.write_text(body, encoding="utf-8")
            except OSError:
                pass

        empty = summary["calls"] == 0
        warn_flags = [flag for flag in summary["flags"] if flag["severity"] == "warn"]
        status = "empty" if empty else ("degraded" if warn_flags else "ok")
        if not args.no_heartbeat:
            write_heartbeat(
                heartbeat_path,
                heartbeat_payload(
                    status,
                    interval_seconds=args.interval_seconds,
                    detail=(
                        f"{summary['calls']} calls in window {args.since}; "
                        f"{len(warn_flags)} warn flag(s)"
                    ),
                    calls_in_window=summary["calls"],
                    failures=summary["overall"]["failures"],
                    warn_flags=len(warn_flags),
                    surface=str(surface_path),
                    window=args.since,
                ),
            )

        if not args.quiet:
            print(body)

        if empty and not args.no_alert_on_empty:
            print(
                f"telemetry-digest: NO CALLS in window {args.since} — the emit "
                f"sites may have stopped firing",
                file=sys.stderr,
            )
            return 1
        return 0

    except Exception as exc:  # noqa: BLE001 - the job must report its own death
        if not args.no_heartbeat:
            write_heartbeat(
                heartbeat_path,
                heartbeat_payload(
                    "error",
                    interval_seconds=args.interval_seconds,
                    detail=f"{type(exc).__name__}: {exc}"[:400],
                ),
            )
        print(f"telemetry-digest FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
