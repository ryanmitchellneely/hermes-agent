#!/usr/bin/env python3
"""Drive real Hermes call paths at a 127.0.0.1 stub and report the wire body.

The probe never builds a chat-completions body. It only writes a temporary
HERMES_HOME, calls public entry points, and inspects the bytes the stub
received. It does not touch /opt/t1000 or ~/.t1000, and it does not open any
socket except the stub it binds on 127.0.0.1.
"""

from __future__ import annotations

import argparse
import json
import locale
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_HOME = Path("/tmp/hermes-thinking-control-probe")
FROZEN_NOW = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
STAGE_A_PATHS = ("aux", "main-stream", "moa")
ALL_PATHS = ("aux", "main-stream", "main-nonstream", "moa")

QWEN_THINKING = {
    "kind": "chat_template_kwargs",
    "switch_key": "enable_thinking",
    "effort_key": "reasoning_effort",
    "effort_map": {
        "low": "low",
        "medium": "medium",
        "high": "xhigh",
        "xhigh": "xhigh",
        "max": "xhigh",
    },
}
DS4_THINKING = {
    "kind": "chat_template_kwargs",
    "switch_key": "thinking",
    "effort_key": "reasoning_effort",
    "effort_map": {"high": "high", "xhigh": "max", "max": "max"},
}


def _scrub_provider_env() -> None:
    drop_exact = {
        "OPENAI_BASE_URL",
        "OPENROUTER_BASE_URL",
        "CUSTOM_BASE_URL",
        "OPENAI_API_BASE",
        "HERMES_HOME",
    }
    for key in list(os.environ):
        if key in drop_exact or key.endswith("_API_KEY") or key.endswith("_API_TOKEN"):
            os.environ.pop(key, None)


def _pin_locale() -> None:
    os.environ["LC_ALL"] = "en_US.UTF-8"
    os.environ["LANG"] = "en_US.UTF-8"
    os.environ["TZ"] = "UTC"
    os.environ["HERMES_TIMEZONE"] = "UTC"
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except locale.Error:
        pass


class _StubHandler(BaseHTTPRequestHandler):
    records: list[dict] = []
    lock = threading.Lock()
    jsonl_path: Path | None = None

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        payload = {
            "object": "list",
            "data": [{"id": "stub-model", "object": "model", "owned_by": "stub"}],
        }
        self._send(200, json.dumps(payload).encode(), "application/json")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = None
        record = {"path": self.path, "raw": raw, "body": body}
        with self.lock:
            self.records.append(record)
            if self.jsonl_path is not None:
                with self.jsonl_path.open("ab") as handle:
                    handle.write(raw + b"\n")
        stream = isinstance(body, dict) and body.get("stream") is True
        if stream:
            self._send(200, _sse_body(), "text/event-stream")
        else:
            self._send(200, _completion_body(), "application/json")


def _completion_body() -> bytes:
    payload = {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "created": 0,
        "model": "stub-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "pong"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    return json.dumps(payload).encode()


def _sse_body() -> bytes:
    chunks = [
        {
            "id": "chatcmpl-stub",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "stub-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "pong"},
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-stub",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "stub-model",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        },
        {
            "id": "chatcmpl-stub",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "stub-model",
            "choices": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    ]
    parts = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
    parts.append("data: [DONE]\n\n")
    return "".join(parts).encode()


def _write_config(home: Path, base_url: str, args: argparse.Namespace) -> None:
    import yaml

    provider: dict = {
        "base_url": base_url,
        "api_key": "stub-key",
        "default_model": "stub-model",
    }
    if not args.omit_extra_body and args.mode == "stage-a":
        provider["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    if args.mode == "stage-b":
        provider["thinking_control"] = dict(
            DS4_THINKING if args.thinking_control == "ds4" else QWEN_THINKING
        )
    config: dict = {
        "model": {"provider": "stub", "default": "stub-model"},
        "providers": {"stub": provider},
        "auxiliary": {
            "title_generation": {
                "provider": "stub",
                "model": "stub-model",
                "timeout": 30,
                "enabled": False,
            },
            "compression": {"enabled": False},
        },
    }
    if args.mode == "stage-b" and args.reasoning:
        config["agent"] = {"reasoning_effort": args.reasoning}
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )


def _freeze_clock() -> None:
    import hermes_time

    hermes_time.reset_cache()
    hermes_time.now = lambda: FROZEN_NOW


def _snapshot() -> int:
    with _StubHandler.lock:
        return len(_StubHandler.records)


def _new_records(start: int) -> list[dict]:
    with _StubHandler.lock:
        return list(_StubHandler.records[start:])


def _select_record(path: str, records: list[dict]) -> dict | None:
    parsed = [
        rec for rec in records
        if isinstance(rec.get("body"), dict) and "messages" in rec["body"]
    ]
    if path == "moa":
        for rec in parsed:
            if rec["body"].get("max_tokens") == 4096:
                return rec
        return None
    if path == "main-stream":
        for rec in parsed:
            if rec["body"].get("stream") is True:
                return rec
        return None
    if path == "main-nonstream":
        for rec in parsed:
            if rec["body"].get("stream") is not True:
                return rec
        return None
    return parsed[0] if parsed else None


def _detail(body: dict | None) -> str:
    if not isinstance(body, dict):
        return "keys=[] chat_template_kwargs=None reasoning=None reasoning_effort=None max_tokens=None"
    ctk = body.get("chat_template_kwargs")
    return (
        f"keys={sorted(body.keys())} "
        f"chat_template_kwargs={json.dumps(ctk, sort_keys=True, default=str)} "
        f"reasoning={json.dumps(body.get('reasoning'), sort_keys=True, default=str)} "
        f"reasoning_effort={json.dumps(body.get('reasoning_effort'), default=str)} "
        f"max_tokens={json.dumps(body.get('max_tokens'), default=str)}"
    )


def _switch_key(args: argparse.Namespace) -> str:
    if args.thinking_control == "ds4":
        return "thinking"
    return "enable_thinking"


def _judge(path: str, body: dict | None, warnings: list[str], args: argparse.Namespace) -> tuple[bool, str]:
    if not isinstance(body, dict):
        if path == "moa":
            return False, "no reference body with max_tokens 4096"
        return False, "no captured body"
    ctk = body.get("chat_template_kwargs")
    if not isinstance(ctk, dict):
        ctk = {}
    if args.mode in {"stage-a", "golden"}:
        value = ctk.get("enable_thinking", None)
        if value is False:
            return True, "chat_template_kwargs.enable_thinking is false"
        if "enable_thinking" not in ctk and not isinstance(body.get("chat_template_kwargs"), dict):
            return False, "lacks chat_template_kwargs.enable_thinking"
        return False, "lacks chat_template_kwargs.enable_thinking == false"

    switch = _switch_key(args)
    effort_in_ctk = ctk.get("reasoning_effort", None)
    top_effort = body.get("reasoning_effort", None)
    if args.reasoning == "none":
        if ctk.get(switch) is False and "reasoning_effort" not in ctk and "reasoning_effort" not in body:
            return True, f"chat_template_kwargs.{switch} is false and no reasoning_effort"
        return False, f"expected {switch}=false and no reasoning_effort, got ctk={ctk} top={top_effort!r}"
    if args.reasoning == "low" and args.thinking_control != "ds4":
        ok = (
            ctk.get(switch) is True
            and effort_in_ctk == "low"
            and "reasoning_effort" not in body
        )
        if ok:
            return True, "enable_thinking true, reasoning_effort low"
        return False, f"expected enable_thinking true and reasoning_effort low, got ctk={ctk} top={top_effort!r}"
    if args.reasoning == "high" and args.thinking_control != "ds4":
        raw_high = effort_in_ctk == "high" or top_effort == "high"
        ok = ctk.get(switch) is True and effort_in_ctk == "xhigh" and not raw_high
        if ok:
            return True, "reasoning_effort xhigh, never high"
        return False, f"expected reasoning_effort xhigh and never high, got ctk={ctk} top={top_effort!r}"
    if args.reasoning == "minimal" or (args.thinking_control == "ds4" and args.reasoning == "low"):
        named = any(
            "dropped unmapped" in line and args.reasoning in line for line in warnings
        )
        if ctk.get(switch) is True and "reasoning_effort" not in ctk and "reasoning_effort" not in body and named:
            return True, f"no effort key; WARNING names {args.reasoning}"
        if "reasoning_effort" in ctk or "reasoning_effort" in body:
            return False, f"unmapped effort was sent: ctk={ctk} top={top_effort!r}"
        if not named:
            return False, f"no WARNING naming {args.reasoning}"
        return False, f"expected {switch}=true and no effort key, got ctk={ctk}"
    if args.thinking_control == "ds4" and args.reasoning == "high":
        ok = ctk.get(switch) is True and effort_in_ctk == "high" and "reasoning_effort" not in body
        if ok:
            return True, "thinking true, reasoning_effort high"
        return False, f"expected DS4 high mapping, got ctk={ctk} top={top_effort!r}"
    if args.thinking_control == "ds4" and args.reasoning == "none":
        return _judge(path, body, warnings, args)
    return False, f"no judge for mode={args.mode} reasoning={args.reasoning}"


class _WarningTap(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _run_path(path: str) -> list[str]:
    tap = _WarningTap()
    root = logging.getLogger()
    root.addHandler(tap)
    previous = root.level
    if root.level > logging.WARNING:
        root.setLevel(logging.WARNING)
    try:
        if path == "aux":
            _run_aux()
        elif path == "main-stream":
            _run_main(stream=True)
        elif path == "main-nonstream":
            _run_main(stream=False)
        elif path == "moa":
            _run_moa()
        else:
            raise RuntimeError(f"unknown path {path}")
    finally:
        root.removeHandler(tap)
        root.setLevel(previous)
    return list(tap.lines)


def _run_aux() -> None:
    from agent.auxiliary_client import call_llm

    call_llm(
        task="title_generation",
        messages=[{"role": "user", "content": "Reply with the single word pong."}],
        timeout=30,
    )


def _run_main(stream: bool) -> None:
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_constants import resolve_reasoning_config
    from run_agent import AIAgent

    runtime = resolve_runtime_provider(requested="stub", target_model="stub-model")
    reasoning = resolve_reasoning_config(load_config(), "stub-model")
    agent = AIAgent(
        provider=runtime.get("provider"),
        requested_provider=runtime.get("requested_provider") or "stub",
        base_url=runtime.get("base_url"),
        api_key=runtime.get("api_key"),
        api_mode=runtime.get("api_mode") or "chat_completions",
        model=runtime.get("model") or "stub-model",
        request_overrides=runtime.get("request_overrides"),
        reasoning_config=reasoning,
        quiet_mode=True,
        skip_memory=True,
        skip_context_files=True,
        skip_background_review=True,
        enabled_toolsets=[],
        max_iterations=2,
        session_id="probe-session-fixed",
        save_trajectories=False,
        verbose_logging=False,
        checkpoints_enabled=False,
    )
    agent._disable_streaming = not stream
    try:
        agent.run_conversation(
            "Reply with the single word pong.",
            task_id="probe-task-fixed",
        )
    finally:
        close = getattr(agent, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def _run_moa() -> None:
    from agent.moa_loop import aggregate_moa_context

    aggregate_moa_context(
        user_prompt="Reply with the single word pong.",
        api_messages=[{"role": "user", "content": "Reply with the single word pong."}],
        reference_models=[
            {
                "provider": "stub",
                "model": "stub-model",
                "enabled": True,
                "max_tokens": 4096,
            }
        ],
        aggregator={"provider": "stub", "model": "stub-model"},
        reference_max_tokens=4096,
    )


def _save_parsed(directory: Path, path: str, body: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{path}.json"
    target.write_text(
        json.dumps(body, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _save_raw(directory: Path, path: str, raw: bytes) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{path}.body").write_bytes(raw)


def _check_raw(directory: Path, path: str, raw: bytes) -> str | None:
    target = directory / f"{path}.body"
    if not target.is_file():
        return f"missing golden {target}"
    expected = target.read_bytes()
    if expected != raw:
        return f"byte mismatch against {target} ({len(raw)} != {len(expected)})"
    return None


def _prepare_home(base_url: str, args: argparse.Namespace) -> None:
    if PROBE_HOME.exists():
        import shutil

        shutil.rmtree(PROBE_HOME)
    PROBE_HOME.mkdir(parents=True)
    _write_config(PROBE_HOME, base_url, args)
    os.environ["HERMES_HOME"] = str(PROBE_HOME)
    os.environ["HERMES_TIMEZONE"] = "UTC"
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    _freeze_clock()
    from hermes_cli.config import _LOAD_CONFIG_CACHE

    _LOAD_CONFIG_CACHE.clear()


def run(args: argparse.Namespace) -> int:
    _scrub_provider_env()
    _pin_locale()
    _StubHandler.records = []
    jsonl_path = PROBE_HOME / "wire.jsonl"
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    host, port = server.server_address[:2]
    if host != "127.0.0.1":
        server.server_close()
        print("PATH setup FAIL stub bound something other than 127.0.0.1", file=sys.stderr)
        return 2
    base_url = f"http://127.0.0.1:{port}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _prepare_home(base_url, args)
        jsonl_path = PROBE_HOME / "wire.jsonl"
        _StubHandler.jsonl_path = jsonl_path
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
        paths = tuple(args.paths.split(",")) if args.paths else (
            STAGE_A_PATHS if args.mode == "stage-a" else ALL_PATHS
        )
        failed = False
        for path in paths:
            start = _snapshot()
            error = ""
            warnings: list[str] = []
            try:
                warnings = _run_path(path)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            records = _new_records(start)
            selected = _select_record(path, records)
            body = selected.get("body") if selected else None
            if error:
                ok, reason = False, error
            elif args.mode == "golden":
                if not selected:
                    ok, reason = False, "no captured body"
                else:
                    mismatch = None
                    if args.check_golden:
                        mismatch = _check_raw(Path(args.check_golden), path, selected["raw"])
                    if args.save_golden:
                        _save_raw(Path(args.save_golden), path, selected["raw"])
                    ok, reason = (mismatch is None), (mismatch or "captured")
            else:
                ok, reason = _judge(path, body, warnings, args)
            if args.save_fixtures and isinstance(body, dict):
                _save_parsed(Path(args.save_fixtures), path, body)
            status = "PASS" if ok else "FAIL"
            if not ok:
                failed = True
            print(f"PATH {path} {status} {reason}")
            print(f"{path} {_detail(body if isinstance(body, dict) else None)}")
            for line in warnings:
                if "thinking_control" in line or args.reasoning and args.reasoning in line:
                    print(f"{path} WARNING {line}")
        return 1 if failed else 0
    finally:
        server.shutdown()
        server.server_close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture provider wire bodies from real Hermes call paths.")
    parser.add_argument("--mode", choices=("stage-a", "stage-b", "golden"), default="stage-a")
    parser.add_argument("--omit-extra-body", action="store_true")
    parser.add_argument("--reasoning", default="")
    parser.add_argument("--thinking-control", choices=("qwen", "ds4", "none"), default="qwen")
    parser.add_argument("--paths", default="")
    parser.add_argument("--save-fixtures", default="")
    parser.add_argument("--save-golden", default="")
    parser.add_argument("--check-golden", default="")
    args = parser.parse_args(argv)
    if args.mode == "stage-b" and not args.reasoning:
        parser.error("--mode stage-b requires --reasoning")
    if args.omit_extra_body and args.mode != "stage-a":
        parser.error("--omit-extra-body is only valid with --mode stage-a")
    return args


if __name__ == "__main__":
    sys.exit(run(parse_args(sys.argv[1:])))
