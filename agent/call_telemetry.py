"""Cross-board model-call telemetry sink (append-only JSONL under ``~/.t1000``).

Ryan's question — "how many model calls, at what effort, what success rate,
how much deepseek vs 120b, how many tokens" — is cross-board by nature, so
this store deliberately lives OUTSIDE any per-board ``kanban.db``:

    ~/.t1000/telemetry/model_calls-YYYY-MM-DD.jsonl   (one line per model CALL)

JSONL is the source of truth rather than SQLite because the fleet runs many
worker processes concurrently. A single ``os.write()`` of one newline-terminated
buffer to a file opened ``O_APPEND`` is atomic against other appenders on macOS
and Linux, so concurrent writers cannot tear or interleave each other's lines —
no locking, no WAL, no writer-starvation. ``tests/agent/test_call_telemetry.py``
proves this with 8 real processes.

Writing is STRICTLY best-effort: the entire body of :func:`record_model_call`
is wrapped in ``try/except`` and swallows everything, exactly like
``agent/aux_accounting.py:record_aux_usage``. Accounting must never break a
model call.

THE tokens_available CONTRACT (the reason this schema shipped ahead of its
callers). ``agent/claude_acp_client.py`` (:1103 non-streaming, :1237 streaming)
and ``agent/copilot_acp_client.py`` (:481) hardcode::

    usage = SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0, ...)

so those lanes emit a REAL ZERO, not a missing value. Stored naively as 0 the
subscription lanes look free and any local-vs-subscription split comes out
inverted. Every row therefore carries a required ``tokens_available`` boolean,
and rows with ``tokens_available=false`` write ``null`` (not ``0``) into every
token field so a naive ``SUM`` cannot silently undercount — it either skips
them or raises. Consumers report those calls as their own count
("N calls with no token data") instead of folding them into a total.

Token normalization is delegated to ``agent/usage_pricing.py:normalize_usage``
so provider quirks (bedrock cache accounting, codex Responses shape, DeepSeek
``prompt_cache_hit_tokens``) stay in exactly one place. Tokens are NEVER
estimated from character counts here.

Schema reference: ``docs/telemetry/model-calls-schema.md``.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)

# Bump when a field changes meaning or disappears. Consumers should tolerate
# unknown *additional* fields without a bump (additive changes are safe).
SCHEMA_VERSION = 1

#: Lanes known to report a hardcoded zero-token usage object. Rows from these
#: providers are always flagged ``tokens_available=false`` even if a future
#: usage object looks populated-but-zero.
TOKENLESS_PROVIDERS = frozenset({"claude-acp", "copilot-acp"})

#: The closed set of outcomes. Anything else is coerced to ``error`` with the
#: original preserved in ``outcome_raw``.
OUTCOMES = frozenset({"ok", "error", "timeout", "refusal"})

#: Token fields that are ``null`` (never ``0``) when ``tokens_available`` is false.
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "prompt_tokens",
    "total_tokens",
)

_FILE_PREFIX = "model_calls-"
_FILE_SUFFIX = ".jsonl"

# A record is a few hundred bytes. This ceiling exists only so a pathological
# error string cannot produce a line big enough to risk a short write.
_MAX_LINE_BYTES = 16384


def telemetry_dir() -> Path:
    """Return the append-only telemetry root, honouring ``T1000_TELEMETRY_DIR``.

    Defaults to ``~/.t1000/telemetry``. Deliberately NOT derived from
    ``HERMES_HOME``: that points at a per-profile directory
    (``~/.t1000/profiles/worker``) and this store is cross-profile as well as
    cross-board.
    """
    override = os.environ.get("T1000_TELEMETRY_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    home = os.environ.get("HERMES_REAL_HOME", "").strip() or str(Path.home())
    return Path(home).expanduser() / ".t1000" / "telemetry"


def log_path_for(when: datetime, root: Optional[Path] = None) -> Path:
    """Return the daily-rotated log file for *when* (local date)."""
    base = root if root is not None else telemetry_dir()
    return base / f"{_FILE_PREFIX}{when.strftime('%Y-%m-%d')}{_FILE_SUFFIX}"


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_str(value: Any, limit: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _as_namespace(value: Any) -> Any:
    """Turn a usage ``dict`` into the attribute shape ``normalize_usage`` expects."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _as_namespace(v) for k, v in value.items()})
    return value


def _canonical_usage(usage: Any, provider: Optional[str], api_mode: Optional[str]) -> Any:
    """Normalize *usage* into ``CanonicalUsage``, passing through if already one."""
    if usage is None:
        return None
    # Already canonical (e.g. the main loop normalized it before us) — reusing
    # normalize_usage here would misread CanonicalUsage.prompt_tokens (a derived
    # property) as a raw prompt total and lose output_tokens entirely.
    if all(hasattr(usage, attr) for attr in ("input_tokens", "output_tokens", "cache_read_tokens")):
        return usage
    from agent.usage_pricing import normalize_usage

    return normalize_usage(_as_namespace(usage), provider=provider, api_mode=api_mode)


def build_record(
    *,
    provider: Any,
    model: Any,
    effort: Any = None,
    usage: Any = None,
    wall_ms: Any = None,
    ttft_ms: Any = None,
    outcome: Any = "ok",
    error_class: Any = None,
    lane: Any = None,
    task_id: Any = None,
    board: Any = None,
    run_id: Any = None,
    session_id: Any = None,
    task: Any = None,
    api_mode: Any = None,
    tokens_available: Optional[bool] = None,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build one telemetry record. Pure — no I/O, raises on programmer error.

    Split out from :func:`record_model_call` so tests (and downstream callers
    that want to inspect what would be written) can assert on the schema
    without touching the filesystem.
    """
    now = timestamp or datetime.now().astimezone()
    if now.tzinfo is None:
        now = now.astimezone()

    provider_name = _clean_str(provider, 100) or "unknown"
    canonical = _canonical_usage(usage, provider_name, _clean_str(api_mode, 60))

    if tokens_available is None:
        if canonical is None:
            tokens_available = False
        elif provider_name.lower() in TOKENLESS_PROVIDERS:
            # The lane hardcodes zeros — see module docstring.
            tokens_available = False
        else:
            tokens_available = bool(
                (_to_int(getattr(canonical, "input_tokens", 0)) or 0)
                or (_to_int(getattr(canonical, "output_tokens", 0)) or 0)
                or (_to_int(getattr(canonical, "cache_read_tokens", 0)) or 0)
                or (_to_int(getattr(canonical, "cache_write_tokens", 0)) or 0)
                or (_to_int(getattr(canonical, "reasoning_tokens", 0)) or 0)
            )
    tokens_available = bool(tokens_available)

    outcome_text = (_clean_str(outcome, 40) or "ok").lower()
    outcome_raw = None
    if outcome_text not in OUTCOMES:
        outcome_raw = outcome_text
        outcome_text = "error"

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": now.isoformat(timespec="milliseconds"),
        "ts_epoch_ms": int(now.timestamp() * 1000),
        "board": _clean_str(board, 100) or _env("HERMES_KANBAN_BOARD"),
        "task_id": _clean_str(task_id, 100) or _env("HERMES_KANBAN_TASK"),
        "run_id": _clean_str(run_id, 60) or _env("HERMES_KANBAN_RUN_ID"),
        "session_id": _clean_str(session_id, 120) or _env("HERMES_SESSION_ID"),
        "lane": _clean_str(lane, 100) or _env("HERMES_PROFILE"),
        "task": _clean_str(task, 120) or "main_loop",
        "provider": provider_name,
        "model": _clean_str(model, 200) or "unknown",
        "effort": _clean_str(effort, 40),
        "api_mode": _clean_str(api_mode, 60),
        "tokens_available": tokens_available,
        "wall_ms": _to_int(wall_ms),
        "ttft_ms": _to_int(ttft_ms),
        "outcome": outcome_text,
        "error_class": _clean_str(error_class, 200),
        "pid": os.getpid(),
        "host": _clean_str(socket.gethostname(), 120),
    }
    if outcome_raw:
        record["outcome_raw"] = outcome_raw

    if tokens_available and canonical is not None:
        input_tokens = _to_int(getattr(canonical, "input_tokens", 0)) or 0
        output_tokens = _to_int(getattr(canonical, "output_tokens", 0)) or 0
        cache_read = _to_int(getattr(canonical, "cache_read_tokens", 0)) or 0
        cache_write = _to_int(getattr(canonical, "cache_write_tokens", 0)) or 0
        reasoning = _to_int(getattr(canonical, "reasoning_tokens", 0)) or 0
        prompt_tokens = input_tokens + cache_read + cache_write
        record.update(
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write,
                "reasoning_tokens": reasoning,
                "prompt_tokens": prompt_tokens,
                "total_tokens": prompt_tokens + output_tokens,
            }
        )
    else:
        # null, never 0 — a naive SUM must not read "no data" as "free".
        record.update({field: None for field in TOKEN_FIELDS})

    return record


def _serialize(record: dict) -> bytes:
    line = json.dumps(record, ensure_ascii=True, separators=(",", ":"), default=str)
    data = (line + "\n").encode("ascii", "backslashreplace")
    if len(data) > _MAX_LINE_BYTES:
        trimmed = dict(record)
        trimmed["error_class"] = _clean_str(record.get("error_class"), 80)
        line = json.dumps(trimmed, ensure_ascii=True, separators=(",", ":"), default=str)
        data = (line + "\n").encode("ascii", "backslashreplace")
    return data


def _append_line(path: Path, data: bytes) -> None:
    """Append one pre-serialized line atomically w.r.t. other appenders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        written = os.write(fd, data)
    finally:
        os.close(fd)
    if written != len(data):
        # Not recoverable — a retry would duplicate the written prefix. Loud in
        # the log, silent to the caller.
        logger.warning(
            "call telemetry short write (%d/%d bytes) to %s", written, len(data), path
        )


def record_model_call(
    *,
    provider: Any,
    model: Any,
    effort: Any = None,
    usage: Any = None,
    wall_ms: Any = None,
    ttft_ms: Any = None,
    outcome: Any = "ok",
    error_class: Any = None,
    lane: Any = None,
    task_id: Any = None,
    board: Any = None,
    run_id: Any = None,
    session_id: Any = None,
    task: Any = None,
    api_mode: Any = None,
    tokens_available: Optional[bool] = None,
    timestamp: Optional[datetime] = None,
) -> None:
    """Append one model-call record to the cross-board telemetry store.

    Every argument is keyword-only and everything except *provider* and *model*
    is optional; ``board`` / ``task_id`` / ``run_id`` / ``session_id`` / ``lane``
    fall back to the dispatcher's environment (``HERMES_KANBAN_BOARD``,
    ``HERMES_KANBAN_TASK``, ``HERMES_KANBAN_RUN_ID``, ``HERMES_SESSION_ID``,
    ``HERMES_PROFILE``) so call sites do not have to thread them through.

    *usage* is the provider's own usage object (OpenAI/Anthropic/Responses
    shape, a ``dict``, or an already-normalized ``CanonicalUsage``); it is run
    through ``agent.usage_pricing.normalize_usage``. Pass ``None`` for calls
    that failed before returning usage.

    *tokens_available* is auto-detected (no usage, a known tokenless lane, or
    an all-zero usage object -> ``False``) and may be forced by callers that
    know better. When it is false every token field is written as ``null``.

    *task* is the aux task name (``vision``, ``compression``, ...) or
    ``"main_loop"``. *ttft_ms* is ``null`` where the transport cannot measure it.

    Never raises. Never blocks on a lock.
    """
    try:
        record = build_record(
            provider=provider,
            model=model,
            effort=effort,
            usage=usage,
            wall_ms=wall_ms,
            ttft_ms=ttft_ms,
            outcome=outcome,
            error_class=error_class,
            lane=lane,
            task_id=task_id,
            board=board,
            run_id=run_id,
            session_id=session_id,
            task=task,
            api_mode=api_mode,
            tokens_available=tokens_available,
            timestamp=timestamp,
        )
        when = datetime.fromtimestamp(record["ts_epoch_ms"] / 1000.0)
        _append_line(log_path_for(when), _serialize(record))
    except Exception:
        logger.debug("call telemetry recording failed (non-fatal)", exc_info=True)


def iter_records(
    root: Optional[Path] = None,
    *,
    since_epoch_ms: Optional[int] = None,
    until_epoch_ms: Optional[int] = None,
) -> Iterator[dict]:
    """Yield records from the store oldest-file-first, skipping unparseable lines.

    A partially-written final line (writer killed mid-``write``) is skipped
    rather than raising — the store is designed to be read while it is being
    appended to.
    """
    base = root if root is not None else telemetry_dir()
    if not base.is_dir():
        return
    for path in sorted(base.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}")):
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
                    stamp = record.get("ts_epoch_ms")
                    if since_epoch_ms is not None and (stamp or 0) < since_epoch_ms:
                        continue
                    if until_epoch_ms is not None and (stamp or 0) > until_epoch_ms:
                        continue
                    yield record
        except OSError:
            continue


def utc_now_ms() -> int:
    """Epoch milliseconds — small helper so callers avoid re-deriving it."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)
