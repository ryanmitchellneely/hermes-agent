"""OpenAI-compatible shim that forwards Hermes requests to Claude Agent ACP.

Spawns ``claude-agent-acp`` (Buzz/Zed adapter for Claude Agent SDK) as a
long-lived ACP session (reused across turns until close / idle / reset).
Claude Code owns Max-subscription OAuth and billing; Hermes stays the
orchestrating brain and only consumes the chat-completion shape. Prefer this
over the native Anthropic HTTP provider when you want plan limits without
third-party "extra usage" API routing.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import shlex
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from agent.file_safety import get_read_block_error, get_write_denied_error
from agent.redact import redact_sensitive_text
from tools.environments.local import hermes_subprocess_env

logger = logging.getLogger(__name__)

ACP_MARKER_BASE_URL = "acp://claude"
_DEFAULT_TIMEOUT_SECONDS = 900.0
_DEFAULT_IDLE_SECONDS = 900.0  # recycle idle ACP process after 15m

_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_TOOL_CALL_JSON_RE = re.compile(
    r"\{\s*\"id\"\s*:\s*\"[^\"]+\"\s*,\s*\"type\"\s*:\s*\"function\"\s*,\s*\"function\"\s*:\s*\{.*?\}\s*\}",
    re.DOTALL,
)


def _candidate_commands() -> list[str]:
    """Ordered command candidates for the Claude Agent ACP adapter."""
    env = (
        os.getenv("HERMES_CLAUDE_ACP_COMMAND", "").strip()
        or os.getenv("CLAUDE_ACP_PATH", "").strip()
    )
    home = Path(os.path.expanduser("~"))
    buzz = home / "Library/Application Support/Buzz/node-tools/bin/claude-agent-acp"
    return [
        c
        for c in [
            env,
            "claude-agent-acp",
            str(buzz),
            str(home / ".local/bin/claude-agent-acp"),
        ]
        if c
    ]


def _resolve_command() -> str:
    import shutil

    for candidate in _candidate_commands():
        p = Path(candidate).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        which = shutil.which(candidate)
        if which:
            return which
    return (
        os.getenv("HERMES_CLAUDE_ACP_COMMAND", "").strip()
        or os.getenv("CLAUDE_ACP_PATH", "").strip()
        or "claude-agent-acp"
    )


def _resolve_args() -> list[str]:
    # claude-agent-acp speaks ACP on stdio by default — no --acp/--stdio flags.
    raw = os.getenv("HERMES_CLAUDE_ACP_ARGS", "").strip()
    if not raw:
        return []
    return shlex.split(raw)


_CLAUDE_ACP_EFFORTS = {"default", "low", "medium", "high", "xhigh", "max"}


def _normalize_claude_acp_model(model: str | None) -> str | None:
    """Map Hermes model hints → Claude Agent ACP configOptions.model values."""
    if not model:
        return None
    m = str(model).strip().lower()
    if not m or m in {"claude-acp", "default"}:
        return "default"
    if m in {
        "opus",
        "opus[1m]",
        "claude-opus-5",
        "claude-opus-4-6",
        "claude-opus-4-8",
        "claude-opus-4-7",
    }:
        return "opus[1m]"
    if m in {"fable", "claude-fable-5", "claude-fable-5[1m]"}:
        return "claude-fable-5[1m]"
    if m in {"sonnet", "claude-sonnet-5", "claude-sonnet-4-6"}:
        return "sonnet"
    if m in {
        "haiku",
        "claude-haiku-4-5",
        "claude-haiku-4.5",
        "claude-haiku-4-5-20251001",
    }:
        return "haiku"
    return model


def _normalize_claude_acp_effort(
    *,
    reasoning_effort: Any = None,
    extra_body: Any = None,
) -> str | None:
    """Map Hermes reasoning dial → Claude ACP effort config value."""
    effort = None
    if isinstance(reasoning_effort, str) and reasoning_effort.strip():
        effort = reasoning_effort.strip().lower()
    elif isinstance(reasoning_effort, dict):
        e = reasoning_effort.get("effort")
        if isinstance(e, str) and e.strip():
            effort = e.strip().lower()
    if effort is None and isinstance(extra_body, dict):
        reasoning = extra_body.get("reasoning")
        if isinstance(reasoning, dict):
            e = reasoning.get("effort")
            if isinstance(e, str) and e.strip():
                effort = e.strip().lower()
            elif reasoning.get("enabled") is False:
                effort = "low"
        e2 = extra_body.get("reasoning_effort")
        if isinstance(e2, str) and e2.strip():
            effort = e2.strip().lower()

    if not effort:
        return None
    if effort in {"none", "off", "minimal"}:
        return "low"
    if effort == "ultra":
        return "max"
    if effort in _CLAUDE_ACP_EFFORTS:
        return effort
    return None


def _resolve_permission_mode() -> str:
    """deny (default) | auto — from config.yaml, env override last.

    Behavioral setting lives in config.yaml per AGENTS.md. Env is a last-resort
    override for tests / one-shot shells.
    """
    env = (
        os.getenv("HERMES_CLAUDE_ACP_PERMISSION_MODE", "").strip().lower()
        or os.getenv("CLAUDE_ACP_PERMISSION_MODE", "").strip().lower()
    )
    if env in {"deny", "auto"}:
        return env
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        model_cfg = cfg.get("model") if isinstance(cfg, dict) else None
        if isinstance(model_cfg, dict):
            block = model_cfg.get("claude_acp")
            if isinstance(block, dict):
                mode = str(block.get("permission_mode") or "").strip().lower()
                if mode in {"deny", "auto"}:
                    return mode
            # also allow top-level model.permission_mode under claude path
            mode = str(model_cfg.get("claude_acp_permission_mode") or "").strip().lower()
            if mode in {"deny", "auto"}:
                return mode
        top = cfg.get("claude_acp") if isinstance(cfg, dict) else None
        if isinstance(top, dict):
            mode = str(top.get("permission_mode") or "").strip().lower()
            if mode in {"deny", "auto"}:
                return mode
    except Exception:
        pass
    return "deny"


def _resolve_idle_seconds() -> float:
    env = os.getenv("HERMES_CLAUDE_ACP_IDLE_SECONDS", "").strip()
    if env:
        try:
            return max(30.0, float(env))
        except ValueError:
            pass
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        model_cfg = cfg.get("model") if isinstance(cfg, dict) else None
        if isinstance(model_cfg, dict):
            block = model_cfg.get("claude_acp")
            if isinstance(block, dict) and block.get("idle_seconds") is not None:
                return max(30.0, float(block["idle_seconds"]))
    except Exception:
        pass
    return _DEFAULT_IDLE_SECONDS


def _resolve_home_dir() -> str:
    """Return a stable HOME for child ACP processes."""
    home = os.environ.get("HOME", "").strip()
    if home:
        return home

    expanded = os.path.expanduser("~")
    if expanded and expanded != "~":
        return expanded

    try:
        import pwd

        resolved = pwd.getpwuid(os.getuid()).pw_dir.strip()  # windows-footgun: ok — POSIX fallback inside try/except (pwd import fails on Windows)
        if resolved:
            return resolved
    except Exception:
        pass

    return "/tmp"


def _build_subprocess_env() -> dict[str, str]:
    # Claude ACP needs Claude Code credential files under HOME and may need
    # Node on PATH. Keep Tier-1 secrets stripped (#29157) while inheriting
    # provider credentials for the Claude Agent SDK.
    env = hermes_subprocess_env(inherit_credentials=True)
    home = _resolve_home_dir()
    env["HOME"] = home
    from hermes_constants import apply_subprocess_home_env

    apply_subprocess_home_env(env)
    return env


def _jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _permission_denied(message_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": {
            "outcome": {
                "outcome": "cancelled",
            }
        },
    }


def _permission_granted(message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Select an allow option from an ACP permission request when offered."""
    options = params.get("options") if isinstance(params, dict) else None
    if not isinstance(options, list):
        options = []
    for want in ("allow_always", "allow_once"):
        for opt in options:
            if not isinstance(opt, dict):
                continue
            kind = str(opt.get("kind") or opt.get("optionId") or "").strip().lower()
            option_id = opt.get("optionId") or opt.get("option_id") or opt.get("id")
            if kind == want or str(option_id or "").strip().lower() == want:
                if option_id is None:
                    continue
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "outcome": {
                            "outcome": "selected",
                            "optionId": option_id,
                        }
                    },
                }
    # No allow option advertised — fall back to cancelled so the session
    # doesn't hang waiting for a selection that isn't offered.
    return _permission_denied(message_id)


def _messages_stable_json(messages: list[dict[str, Any]]) -> str:
    try:
        return json.dumps(messages, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return repr(messages)


def _format_messages_as_prompt(
    messages: list[dict[str, Any]],
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any = None,
    *,
    include_preamble: bool = True,
    delta_only: bool = False,
) -> str:
    sections: list[str] = []
    if include_preamble:
        sections.extend(
            [
                "You are being used as the active ACP agent backend for Hermes.",
                "Use ACP capabilities to complete tasks.",
                "IMPORTANT: If you take an action with a tool, you MUST output tool calls using <tool_call>{...}</tool_call> blocks with JSON exactly in OpenAI function-call shape.",
                "If no tool is needed, answer normally.",
            ]
        )
        if model:
            sections.append(f"Hermes requested model hint: {model}")

        if isinstance(tools, list) and tools:
            tool_specs: list[dict[str, Any]] = []
            for t in tools:
                if not isinstance(t, dict):
                    continue
                fn = t.get("function") or {}
                if not isinstance(fn, dict):
                    continue
                name = fn.get("name")
                if not isinstance(name, str) or not name.strip():
                    continue
                tool_specs.append(
                    {
                        "name": name.strip(),
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {}),
                    }
                )
            if tool_specs:
                sections.append(
                    "Available tools (OpenAI function schema). "
                    "When using a tool, emit ONLY <tool_call>{...}</tool_call> with one JSON object "
                    "containing id/type/function{name,arguments}. arguments must be a JSON string.\n"
                    + json.dumps(tool_specs, ensure_ascii=False)
                )

        if tool_choice is not None:
            sections.append(f"Tool choice hint: {json.dumps(tool_choice, ensure_ascii=False)}")

    transcript: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "unknown").strip().lower()
        if role == "tool":
            role = "tool"
        elif role not in {"system", "user", "assistant"}:
            role = "context"

        content = message.get("content")
        rendered = _render_message_content(content)
        # Surface assistant tool_calls when content is empty so the ACP
        # session still sees that Hermes executed tools next.
        if not rendered and role == "assistant":
            tcs = message.get("tool_calls")
            if tcs:
                rendered = json.dumps(tcs, ensure_ascii=False, default=str)
        if not rendered:
            continue

        label = {
            "system": "System",
            "user": "User",
            "assistant": "Assistant",
            "tool": "Tool",
            "context": "Context",
        }.get(role, role.title())
        transcript.append(f"{label}:\n{rendered}")

    if transcript:
        if delta_only:
            sections.append(
                "Continuation (new messages only — prior turns already live in this ACP session):\n\n"
                + "\n\n".join(transcript)
            )
        else:
            sections.append("Conversation transcript:\n\n" + "\n\n".join(transcript))

    sections.append("Continue the conversation from the latest user request.")
    return "\n\n".join(section.strip() for section in sections if section and section.strip())


def _render_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        if "text" in content:
            return str(content.get("text") or "").strip()
        if "content" in content and isinstance(content.get("content"), str):
            return str(content.get("content") or "").strip()
        return json.dumps(content, ensure_ascii=True)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return str(content).strip()


def _build_openai_tool_call(
    *,
    call_id: str,
    name: str,
    arguments: str,
) -> ChatCompletionMessageToolCall:
    """Build an OpenAI-compatible tool-call object for downstream handling."""
    return ChatCompletionMessageToolCall(
        id=call_id,
        call_id=call_id,
        response_item_id=None,
        type="function",
        function=Function(name=name, arguments=arguments),
    )


def _completion_to_stream_chunks(completion: SimpleNamespace) -> list[SimpleNamespace]:
    """Convert a one-shot ACP response into OpenAI-style stream chunks.

    Fallback when a caller forces stream=True but we already have the full
    completion (error-retry paths). Prefer ``_iter_live_stream_chunks`` for
    real-time thought/message delivery.
    """
    choice = completion.choices[0]
    message = choice.message
    chunks: list[SimpleNamespace] = []

    reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
    if reasoning:
        chunks.append(
            _openai_stream_chunk(
                model=completion.model,
                reasoning=str(reasoning),
                finish_reason=None,
            )
        )

    tool_call_deltas = None
    if message.tool_calls:
        tool_call_deltas = []
        for index, tool_call in enumerate(message.tool_calls):
            tool_call_deltas.append(
                SimpleNamespace(
                    index=index,
                    id=getattr(tool_call, "id", None),
                    type=getattr(tool_call, "type", "function"),
                    function=SimpleNamespace(
                        name=getattr(tool_call.function, "name", None),
                        arguments=getattr(tool_call.function, "arguments", None),
                    ),
                )
            )

    if message.content or tool_call_deltas:
        chunks.append(
            _openai_stream_chunk(
                model=completion.model,
                content=message.content or None,
                tool_calls=tool_call_deltas,
                finish_reason=choice.finish_reason,
            )
        )
    else:
        chunks.append(
            _openai_stream_chunk(
                model=completion.model,
                finish_reason=choice.finish_reason or "stop",
            )
        )

    chunks.append(
        SimpleNamespace(
            choices=[],
            model=completion.model,
            usage=completion.usage,
        )
    )
    return chunks


def _openai_stream_chunk(
    *,
    model: str | None,
    content: str | None = None,
    reasoning: str | None = None,
    tool_calls: list | None = None,
    finish_reason: str | None = None,
    role: str | None = "assistant",
) -> SimpleNamespace:
    delta = SimpleNamespace(
        role=role,
        content=content,
        tool_calls=tool_calls,
        reasoning_content=reasoning,
        reasoning=reasoning,
    )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                index=0,
                delta=delta,
                finish_reason=finish_reason,
            )
        ],
        model=model,
        usage=None,
    )


def _acp_content_text(content: Any) -> str:
    """Pull display text out of an ACP content block (text | thought | nested)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return str(content)
    for key in ("text", "thought", "thinking", "content", "message", "title"):
        val = content.get(key)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):
            nested = _acp_content_text(val)
            if nested:
                return nested
    return ""


def _format_acp_activity(kind: str, update: dict[str, Any]) -> str | None:
    """Turn tool_call / plan ACP updates into short thinking-panel lines."""
    if kind == "tool_call":
        title = (
            str(update.get("title") or "").strip()
            or str(update.get("toolName") or update.get("name") or "").strip()
            or str(update.get("kind") or "tool").strip()
        )
        status = str(update.get("status") or "").strip()
        path = ""
        raw_input = update.get("rawInput") or update.get("input") or {}
        if isinstance(raw_input, dict):
            for k in ("path", "file_path", "filePath", "command", "pattern", "query"):
                if raw_input.get(k):
                    path = str(raw_input.get(k))
                    break
        line = f"▸ {title}"
        if path:
            # keep activity scannable
            short = path if len(path) <= 80 else ("…" + path[-77:])
            line += f"  {short}"
        if status and status not in {"pending", "in_progress"}:
            line += f"  ({status})"
        return line + "\n"
    if kind == "tool_call_update":
        status = str(update.get("status") or "").strip()
        title = str(update.get("title") or update.get("toolCallId") or "").strip()
        if status in {"completed", "failed", "cancelled"}:
            mark = "✓" if status == "completed" else "✗"
            return f"{mark} {title or 'tool'} {status}\n"
        return None
    if kind == "plan":
        entries = update.get("entries") or update.get("plan") or []
        if not isinstance(entries, list) or not entries:
            return None
        lines = ["Plan:"]
        for entry in entries[:12]:
            if isinstance(entry, dict):
                text = str(entry.get("content") or entry.get("title") or entry.get("text") or "").strip()
                st = str(entry.get("status") or "").strip()
                bullet = "•"
                if st in {"completed", "done"}:
                    bullet = "✓"
                elif st in {"in_progress", "active"}:
                    bullet = "→"
                if text:
                    lines.append(f"  {bullet} {text}")
            elif isinstance(entry, str) and entry.strip():
                lines.append(f"  • {entry.strip()}")
        return ("\n".join(lines) + "\n") if len(lines) > 1 else None
    return None


def _extract_tool_calls_from_text(text: str) -> tuple[list[ChatCompletionMessageToolCall], str]:
    if not isinstance(text, str) or not text.strip():
        return [], ""

    extracted: list[ChatCompletionMessageToolCall] = []
    consumed_spans: list[tuple[int, int]] = []

    def _try_add_tool_call(raw_json: str) -> None:
        try:
            obj = json.loads(raw_json)
        except Exception:
            return
        if not isinstance(obj, dict):
            return
        fn = obj.get("function")
        if not isinstance(fn, dict):
            return
        fn_name = fn.get("name")
        if not isinstance(fn_name, str) or not fn_name.strip():
            return
        fn_args = fn.get("arguments", "{}")
        if not isinstance(fn_args, str):
            fn_args = json.dumps(fn_args, ensure_ascii=False)
        call_id = obj.get("id")
        if not isinstance(call_id, str) or not call_id.strip():
            call_id = f"acp_call_{len(extracted)+1}"

        extracted.append(
            _build_openai_tool_call(
                call_id=call_id,
                name=fn_name.strip(),
                arguments=fn_args,
            )
        )

    for m in _TOOL_CALL_BLOCK_RE.finditer(text):
        raw = m.group(1)
        _try_add_tool_call(raw)
        consumed_spans.append((m.start(), m.end()))

    # Only try bare-JSON fallback when no XML blocks were found.
    if not extracted:
        for m in _TOOL_CALL_JSON_RE.finditer(text):
            raw = m.group(0)
            _try_add_tool_call(raw)
            consumed_spans.append((m.start(), m.end()))

    if not consumed_spans:
        return extracted, text.strip()

    consumed_spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in consumed_spans:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    parts: list[str] = []
    cursor = 0
    for start, end in merged:
        if cursor < start:
            parts.append(text[cursor:start])
        cursor = max(cursor, end)
    if cursor < len(text):
        parts.append(text[cursor:])

    cleaned = "\n".join(p.strip() for p in parts if p and p.strip()).strip()
    return extracted, cleaned


def _ensure_path_within_cwd(path_text: str, cwd: str) -> Path:
    candidate = Path(path_text)
    if not candidate.is_absolute():
        raise PermissionError("ACP file-system paths must be absolute.")
    resolved = candidate.resolve()
    root = Path(cwd).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"Path '{resolved}' is outside the session cwd '{root}'.") from exc
    return resolved


class _ACPChatCompletions:
    def __init__(self, client: "ClaudeACPClient"):
        self._client = client

    def create(self, **kwargs: Any) -> Any:
        return self._client._create_chat_completion(**kwargs)


class _ACPChatNamespace:
    def __init__(self, client: "ClaudeACPClient"):
        self.completions = _ACPChatCompletions(client)


class ClaudeACPClient:
    """Minimal OpenAI-client-compatible facade for Claude Agent ACP.

    Process + ACP session are reused across chat.completions.create calls on
    the same client instance (one Hermes agent turn-loop). On context
    compression / non-prefix history changes the session is recycled so Claude
    does not see duplicated transcripts.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
        acp_command: str | None = None,
        acp_args: list[str] | None = None,
        acp_cwd: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        **_: Any,
    ):
        self.api_key = api_key or "claude-acp"
        self.base_url = base_url or ACP_MARKER_BASE_URL
        self._default_headers = dict(default_headers or {})
        self._acp_command = acp_command or command or _resolve_command()
        self._acp_args = list(acp_args or args or _resolve_args())
        self._acp_cwd = str(Path(acp_cwd or os.getcwd()).resolve())
        self.chat = _ACPChatNamespace(self)
        self.is_closed = False

        self._lock = threading.RLock()
        self._active_process: subprocess.Popen[str] | None = None
        self._inbox: queue.Queue[dict[str, Any]] | None = None
        self._stderr_tail: deque[str] = deque(maxlen=40)
        self._next_id = 0
        self._session_id: str | None = None
        self._applied_model: str | None = None
        self._applied_effort: str | None = None
        self._sent_messages_json: str | None = None
        self._sent_message_count = 0
        self._last_used_at = 0.0
        self._idle_seconds = _resolve_idle_seconds()
        self._permission_mode = _resolve_permission_mode()
        self._reader_threads: list[threading.Thread] = []

    def close(self) -> None:
        with self._lock:
            self._teardown_process_unlocked()
            self.is_closed = True

    def _teardown_process_unlocked(self) -> None:
        proc = self._active_process
        self._active_process = None
        self._inbox = None
        self._session_id = None
        self._applied_model = None
        self._applied_effort = None
        self._sent_messages_json = None
        self._sent_message_count = 0
        self._reader_threads = []
        if proc is None:
            return
        try:
            if proc.stdin:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _create_chat_completion(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        timeout: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        stream: bool = False,
        reasoning_effort: Any = None,
        extra_body: Any = None,
        **kwargs: Any,
    ) -> Any:
        if reasoning_effort is None and "reasoning" in kwargs:
            reasoning_effort = kwargs.get("reasoning")
        effort = _normalize_claude_acp_effort(
            reasoning_effort=reasoning_effort,
            extra_body=extra_body if extra_body is not None else kwargs.get("extra_body"),
        )
        acp_model = _normalize_claude_acp_model(model)

        if timeout is None:
            effective_timeout = _DEFAULT_TIMEOUT_SECONDS
        elif isinstance(timeout, (int, float)):
            effective_timeout = float(timeout)
        else:
            candidates = [
                getattr(timeout, attr, None)
                for attr in ("read", "write", "connect", "pool", "timeout")
            ]
            numeric = [float(v) for v in candidates if isinstance(v, (int, float))]
            effective_timeout = max(numeric) if numeric else _DEFAULT_TIMEOUT_SECONDS

        messages_list = list(messages or [])

        if stream:
            return self._iter_live_stream(
                messages_list,
                timeout_seconds=effective_timeout,
                acp_model=acp_model,
                acp_effort=effort,
                hermes_model_hint=model,
                tools=tools,
                tool_choice=tool_choice,
            )

        response_text, reasoning_text = self._run_prompt(
            messages_list,
            timeout_seconds=effective_timeout,
            acp_model=acp_model,
            acp_effort=effort,
            hermes_model_hint=model,
            tools=tools,
            tool_choice=tool_choice,
        )

        tool_calls, cleaned_text = _extract_tool_calls_from_text(response_text)

        usage = SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        assistant_message = SimpleNamespace(
            content=cleaned_text,
            tool_calls=tool_calls,
            reasoning=reasoning_text or None,
            reasoning_content=reasoning_text or None,
            reasoning_details=None,
        )
        finish_reason = "tool_calls" if tool_calls else "stop"
        choice = SimpleNamespace(message=assistant_message, finish_reason=finish_reason)
        return SimpleNamespace(
            choices=[choice],
            usage=usage,
            model=model or "claude-acp",
        )

    def _iter_live_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        timeout_seconds: float,
        acp_model: str | None,
        acp_effort: str | None,
        hermes_model_hint: str | None,
        tools: list[dict[str, Any]] | None,
        tool_choice: Any,
    ):
        """Yield OpenAI-style chunks as ACP session/update events arrive.

        Thought chunks → ``delta.reasoning_content`` (Desktop Thinking accordion).
        Message chunks → ``delta.content``.
        Native tool/plan activity → short reasoning lines (Claude Desktop vibe).
        """
        model_name = hermes_model_hint or "claude-acp"
        live_q: queue.Queue[tuple[str, Any]] = queue.Queue()
        _DONE = object()
        result_box: dict[str, Any] = {}

        def _on_live(kind: str, text: str) -> None:
            if text:
                live_q.put((kind, text))

        def _worker() -> None:
            try:
                text, reasoning = self._run_prompt(
                    messages,
                    timeout_seconds=timeout_seconds,
                    acp_model=acp_model,
                    acp_effort=acp_effort,
                    hermes_model_hint=hermes_model_hint,
                    tools=tools,
                    tool_choice=tool_choice,
                    on_live_delta=_on_live,
                )
                result_box["text"] = text
                result_box["reasoning"] = reasoning
            except Exception as exc:
                result_box["error"] = exc
            finally:
                live_q.put((_DONE, None))

        thread = threading.Thread(target=_worker, daemon=True, name="claude-acp-stream")
        thread.start()

        saw_role = False
        while True:
            kind, payload = live_q.get()
            if kind is _DONE:
                break
            if not saw_role:
                # First chunk carries role so OpenAI-shaped consumers open the turn.
                saw_role = True
                role = "assistant"
            else:
                role = None
            if kind in {"thought", "activity"}:
                yield _openai_stream_chunk(
                    model=model_name,
                    reasoning=str(payload),
                    role=role,
                )
            elif kind == "message":
                yield _openai_stream_chunk(
                    model=model_name,
                    content=str(payload),
                    role=role,
                )

        thread.join(timeout=5)
        if "error" in result_box:
            raise result_box["error"]

        response_text = str(result_box.get("text") or "")
        tool_calls, cleaned_text = _extract_tool_calls_from_text(response_text)

        # If the live path somehow missed the final text (e.g. only tool_call
        # blocks with no agent_message_chunk), emit cleaned remainder once.
        # We don't re-emit reasoning — live path already streamed it.
        if tool_calls:
            tool_call_deltas = []
            for index, tool_call in enumerate(tool_calls):
                tool_call_deltas.append(
                    SimpleNamespace(
                        index=index,
                        id=getattr(tool_call, "id", None),
                        type=getattr(tool_call, "type", "function"),
                        function=SimpleNamespace(
                            name=getattr(tool_call.function, "name", None),
                            arguments=getattr(tool_call.function, "arguments", None),
                        ),
                    )
                )
            yield _openai_stream_chunk(
                model=model_name,
                content=cleaned_text or None,
                tool_calls=tool_call_deltas,
                finish_reason="tool_calls",
                role=None if saw_role else "assistant",
            )
        else:
            yield _openai_stream_chunk(
                model=model_name,
                finish_reason="stop",
                role=None if saw_role else "assistant",
            )

        yield SimpleNamespace(
            choices=[],
            model=model_name,
            usage=SimpleNamespace(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                prompt_tokens_details=SimpleNamespace(cached_tokens=0),
            ),
        )

    def _run_prompt(
        self,
        messages: list[dict[str, Any]],
        *,
        timeout_seconds: float,
        acp_model: str | None = None,
        acp_effort: str | None = None,
        hermes_model_hint: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        on_live_delta: Any = None,
    ) -> tuple[str, str]:
        with self._lock:
            try:
                return self._run_prompt_unlocked(
                    messages,
                    timeout_seconds=timeout_seconds,
                    acp_model=acp_model,
                    acp_effort=acp_effort,
                    hermes_model_hint=hermes_model_hint,
                    tools=tools,
                    tool_choice=tool_choice,
                    on_live_delta=on_live_delta,
                )
            except Exception:
                # Dead/broken session — hard reset and retry once cold.
                self._teardown_process_unlocked()
                return self._run_prompt_unlocked(
                    messages,
                    timeout_seconds=timeout_seconds,
                    acp_model=acp_model,
                    acp_effort=acp_effort,
                    hermes_model_hint=hermes_model_hint,
                    tools=tools,
                    tool_choice=tool_choice,
                    force_full=True,
                    on_live_delta=on_live_delta,
                )

    def _run_prompt_unlocked(
        self,
        messages: list[dict[str, Any]],
        *,
        timeout_seconds: float,
        acp_model: str | None = None,
        acp_effort: str | None = None,
        hermes_model_hint: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        force_full: bool = False,
        on_live_delta: Any = None,
    ) -> tuple[str, str]:
        now = time.monotonic()
        if (
            self._active_process is not None
            and self._last_used_at
            and (now - self._last_used_at) > self._idle_seconds
        ):
            logger.info("Claude ACP idle timeout — recycling session")
            self._teardown_process_unlocked()

        reuse = (
            not force_full
            and self._session_id
            and self._active_process is not None
            and self._active_process.poll() is None
            and self._sent_messages_json is not None
        )

        delta_messages: list[dict[str, Any]] = messages
        delta_only = False
        if reuse:
            prev_count = self._sent_message_count
            if prev_count <= len(messages):
                prefix = messages[:prev_count]
                if _messages_stable_json(prefix) == self._sent_messages_json:
                    delta_messages = messages[prev_count:]
                    delta_only = True
                else:
                    # History rewritten (compression / edit) — new session.
                    self._teardown_process_unlocked()
                    reuse = False
                    delta_messages = messages
                    delta_only = False
            else:
                self._teardown_process_unlocked()
                reuse = False

        if not reuse:
            self._ensure_process_unlocked(timeout_seconds=timeout_seconds)
            self._ensure_session_unlocked(
                timeout_seconds=timeout_seconds,
                acp_model=acp_model,
                acp_effort=acp_effort,
            )
        else:
            self._apply_config_unlocked(
                timeout_seconds=timeout_seconds,
                acp_model=acp_model,
                acp_effort=acp_effort,
            )

        # Empty delta (e.g. pure retry of same prefix) — nudge continue.
        if delta_only and not delta_messages:
            prompt_text = (
                "Continue. Prior turns already live in this ACP session. "
                "If a tool result is still needed, wait; otherwise answer."
            )
        else:
            prompt_text = _format_messages_as_prompt(
                delta_messages,
                model=hermes_model_hint,
                tools=tools if not delta_only else None,
                tool_choice=tool_choice if not delta_only else None,
                include_preamble=not delta_only,
                delta_only=delta_only,
            )

        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        assert self._session_id
        self._request_unlocked(
            "session/prompt",
            {
                "sessionId": self._session_id,
                "prompt": [
                    {
                        "type": "text",
                        "text": prompt_text,
                    }
                ],
            },
            timeout_seconds=timeout_seconds,
            text_parts=text_parts,
            reasoning_parts=reasoning_parts,
            on_live_delta=on_live_delta,
        )

        self._sent_message_count = len(messages)
        self._sent_messages_json = _messages_stable_json(messages)
        self._last_used_at = time.monotonic()
        return "".join(text_parts), "".join(reasoning_parts)

    def _ensure_process_unlocked(self, *, timeout_seconds: float) -> None:
        if self._active_process is not None and self._active_process.poll() is None:
            return
        self._teardown_process_unlocked()
        self.is_closed = False
        try:
            from hermes_cli._subprocess_compat import windows_hide_flags

            proc = subprocess.Popen(
                [self._acp_command] + self._acp_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=self._acp_cwd,
                env=_build_subprocess_env(),
                creationflags=windows_hide_flags(),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Could not start Claude ACP command '{self._acp_command}'. "
                "Install @agentclientprotocol/claude-agent-acp or set HERMES_CLAUDE_ACP_COMMAND."
            ) from exc

        if proc.stdin is None or proc.stdout is None:
            proc.kill()
            raise RuntimeError("Claude ACP process did not expose stdin/stdout pipes.")

        self._active_process = proc
        self._inbox = queue.Queue()
        self._stderr_tail = deque(maxlen=40)
        self._next_id = 0

        def _stdout_reader() -> None:
            if proc.stdout is None:
                return
            for line in proc.stdout:
                try:
                    if self._inbox is not None:
                        self._inbox.put(json.loads(line))
                except Exception:
                    if self._inbox is not None:
                        self._inbox.put({"raw": line.rstrip("\n")})

        def _stderr_reader() -> None:
            if proc.stderr is None:
                return
            for line in proc.stderr:
                self._stderr_tail.append(line.rstrip("\n"))

        out_thread = threading.Thread(target=_stdout_reader, daemon=True)
        err_thread = threading.Thread(target=_stderr_reader, daemon=True)
        out_thread.start()
        err_thread.start()
        self._reader_threads = [out_thread, err_thread]

        self._request_unlocked(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {
                    "fs": {
                        "readTextFile": True,
                        "writeTextFile": True,
                    }
                },
                "clientInfo": {
                    "name": "hermes-agent",
                    "title": "Hermes Agent",
                    "version": "0.0.0",
                },
            },
            timeout_seconds=timeout_seconds,
        )

    def _ensure_session_unlocked(
        self,
        *,
        timeout_seconds: float,
        acp_model: str | None,
        acp_effort: str | None,
    ) -> None:
        if self._session_id:
            self._apply_config_unlocked(
                timeout_seconds=timeout_seconds,
                acp_model=acp_model,
                acp_effort=acp_effort,
            )
            return
        session = (
            self._request_unlocked(
                "session/new",
                {
                    "cwd": self._acp_cwd,
                    "mcpServers": [],
                },
                timeout_seconds=timeout_seconds,
            )
            or {}
        )
        session_id = str(session.get("sessionId") or "").strip()
        if not session_id:
            raise RuntimeError("Claude ACP did not return a sessionId.")
        self._session_id = session_id
        self._applied_model = None
        self._applied_effort = None
        self._apply_config_unlocked(
            timeout_seconds=timeout_seconds,
            acp_model=acp_model,
            acp_effort=acp_effort,
        )

    def _apply_config_unlocked(
        self,
        *,
        timeout_seconds: float,
        acp_model: str | None,
        acp_effort: str | None,
    ) -> None:
        if not self._session_id:
            return
        if acp_model and acp_model != self._applied_model:
            try:
                self._request_unlocked(
                    "session/set_config_option",
                    {
                        "sessionId": self._session_id,
                        "configId": "model",
                        "value": acp_model,
                    },
                    timeout_seconds=min(timeout_seconds, 60.0),
                )
                self._applied_model = acp_model
            except Exception as exc:
                logger.debug("Claude ACP set model=%s failed: %s", acp_model, exc)
        if acp_effort and acp_effort != self._applied_effort:
            try:
                self._request_unlocked(
                    "session/set_config_option",
                    {
                        "sessionId": self._session_id,
                        "configId": "effort",
                        "value": acp_effort,
                    },
                    timeout_seconds=min(timeout_seconds, 60.0),
                )
                self._applied_effort = acp_effort
            except Exception as exc:
                logger.debug("Claude ACP set effort=%s failed: %s", acp_effort, exc)

    def _request_unlocked(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout_seconds: float,
        text_parts: list[str] | None = None,
        reasoning_parts: list[str] | None = None,
        on_live_delta: Any = None,
    ) -> Any:
        proc = self._active_process
        inbox = self._inbox
        if proc is None or proc.stdin is None or inbox is None:
            raise RuntimeError("Claude ACP process is not running.")

        self._next_id += 1
        request_id = self._next_id
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                msg = inbox.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._handle_server_message(
                msg,
                process=proc,
                cwd=self._acp_cwd,
                text_parts=text_parts,
                reasoning_parts=reasoning_parts,
                on_live_delta=on_live_delta,
            ):
                continue

            if msg.get("id") != request_id:
                continue
            if "error" in msg:
                err = msg.get("error") or {}
                err_msg = str(err.get("message") or err)
                data = err.get("data") if isinstance(err, dict) else None
                kind = ""
                if isinstance(data, dict):
                    kind = str(data.get("errorKind") or "")
                if (
                    kind == "authentication_failed"
                    or "authenticate" in err_msg.lower()
                    or "oauth" in err_msg.lower()
                    or "not logged in" in err_msg.lower()
                ):
                    raise RuntimeError(
                        f"Claude ACP authentication failed: {err_msg}\n\n"
                        "Fix: run `claude auth login` in a terminal (Claude Max),\n"
                        "then retry. Hermes stays the brain; Claude ACP is the engine.\n"
                        "Binary: HERMES_CLAUDE_ACP_COMMAND or claude-agent-acp on PATH."
                    )
                raise RuntimeError(f"Claude ACP {method} failed: {err_msg}")
            return msg.get("result")

        stderr_text = "\n".join(self._stderr_tail).strip()
        if proc.poll() is not None and stderr_text:
            raise RuntimeError(f"Claude ACP process exited early: {stderr_text}")
        raise TimeoutError(f"Timed out waiting for Claude ACP response to {method}.")

    def _handle_server_message(
        self,
        msg: dict[str, Any],
        *,
        process: subprocess.Popen[str],
        cwd: str,
        text_parts: list[str] | None,
        reasoning_parts: list[str] | None,
        on_live_delta: Any = None,
    ) -> bool:
        method = msg.get("method")
        if not isinstance(method, str):
            return False

        if method == "session/update":
            params = msg.get("params") or {}
            update = params.get("update") or {}
            if not isinstance(update, dict):
                return True
            kind = str(
                update.get("sessionUpdate") or update.get("kind") or ""
            ).strip()
            content = update.get("content")
            chunk_text = _acp_content_text(content)
            # Some agents put text at the update root.
            if not chunk_text:
                chunk_text = _acp_content_text(update)

            if kind in {"agent_message_chunk", "agent_message", "message"}:
                if chunk_text and text_parts is not None:
                    text_parts.append(chunk_text)
                    if on_live_delta:
                        try:
                            on_live_delta("message", chunk_text)
                        except Exception:
                            pass
            elif kind in {
                "agent_thought_chunk",
                "agent_thought",
                "thought",
                "thought_message_chunk",
            }:
                if chunk_text and reasoning_parts is not None:
                    reasoning_parts.append(chunk_text)
                    if on_live_delta:
                        try:
                            on_live_delta("thought", chunk_text)
                        except Exception:
                            pass
            elif kind in {"tool_call", "tool_call_update", "plan"}:
                activity = _format_acp_activity(kind, update)
                if activity and reasoning_parts is not None:
                    reasoning_parts.append(activity)
                    if on_live_delta:
                        try:
                            on_live_delta("activity", activity)
                        except Exception:
                            pass
            return True

        if process.stdin is None:
            return True

        message_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "session/request_permission":
            mode = self._permission_mode
            if mode == "auto":
                response = _permission_granted(message_id, params if isinstance(params, dict) else {})
            else:
                response = _permission_denied(message_id)
        elif method == "fs/read_text_file":
            try:
                path = _ensure_path_within_cwd(str(params.get("path") or ""), cwd)
                block_error = get_read_block_error(str(path))
                if block_error:
                    raise PermissionError(block_error)
                try:
                    content = path.read_text(encoding="utf-8")
                except FileNotFoundError:
                    content = ""
                line = params.get("line")
                limit = params.get("limit")
                if isinstance(line, int) and line > 1:
                    lines = content.splitlines(keepends=True)
                    start = line - 1
                    end = start + limit if isinstance(limit, int) and limit > 0 else None
                    content = "".join(lines[start:end])
                if content:
                    content = redact_sensitive_text(content, force=True)
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "content": content,
                    },
                }
            except Exception as exc:
                response = _jsonrpc_error(message_id, -32602, str(exc))
        elif method == "fs/write_text_file":
            try:
                path = _ensure_path_within_cwd(str(params.get("path") or ""), cwd)
                denied = get_write_denied_error(str(path))
                if denied:
                    raise PermissionError(denied)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(params.get("content") or ""), encoding="utf-8")
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": None,
                }
            except Exception as exc:
                response = _jsonrpc_error(message_id, -32602, str(exc))
        else:
            response = _jsonrpc_error(
                message_id,
                -32601,
                f"ACP client method '{method}' is not supported by Hermes yet.",
            )

        process.stdin.write(json.dumps(response) + "\n")
        process.stdin.flush()
        return True
