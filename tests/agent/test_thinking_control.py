import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent.auxiliary_client import _build_call_kwargs
from agent.thinking_control import apply_thinking_control
from agent.transports.chat_completions import ChatCompletionsTransport
from hermes_constants import VALID_REASONING_EFFORTS

ROOT = Path(__file__).resolve().parents[2]
STUB_URL = "http://127.0.0.1:9/v1"

QWEN = {
    "kind": "chat_template_kwargs",
    "switch_key": "enable_thinking",
    "effort_key": "reasoning_effort",
    "effort_map": {
        "minimal": "low",
        "low": "low",
        "medium": "medium",
        "high": "xhigh",
        "xhigh": "xhigh",
        "max": "xhigh",
        "ultra": "xhigh",
    },
}
DS4 = {
    "kind": "chat_template_kwargs",
    "switch_key": "thinking",
    "effort_key": "reasoning_effort",
    "effort_map": {
        "minimal": "high",
        "low": "high",
        "medium": "high",
        "high": "high",
        "xhigh": "max",
        "max": "max",
        "ultra": "max",
    },
}
MAPS = {"qwen": QWEN, "ds4": DS4}
EFFORTS = ("none", "low", "high", "max", "minimal", "unknown")


def _reasoning(effort: str) -> dict:
    if effort == "none":
        return {"enabled": False}
    return {"enabled": True, "effort": effort}


def _expected(style: str, effort: str) -> dict:
    block = MAPS[style]
    switch = block["switch_key"]
    if effort == "none":
        return {switch: False}
    mapped = block["effort_map"].get(effort)
    body = {switch: True}
    if mapped is not None:
        body["reasoning_effort"] = mapped
    return body


def _install(monkeypatch, block: dict) -> None:
    entry = {
        "name": "stub",
        "_thinking_control_provider": "stub",
        "base_url": STUB_URL,
        "thinking_control": block,
    }
    monkeypatch.setattr(
        "agent.thinking_control.lookup_provider_entry",
        lambda *_args, **_kwargs: entry,
    )


def _aux(effort: str, caller: dict | None = None) -> dict:
    return _build_call_kwargs(
        "stub",
        "stub-model",
        [{"role": "user", "content": "ping"}],
        extra_body=caller,
        reasoning_config=_reasoning(effort),
        base_url=STUB_URL,
    )


def _profile(effort: str, caller_ctk: dict | None = None) -> dict:
    from providers import get_provider_profile

    params = {
        "reasoning_config": _reasoning(effort),
        "base_url": STUB_URL,
        "supports_reasoning": True,
        "provider_name": "custom",
    }
    if caller_ctk is not None:
        params["request_overrides"] = {"extra_body": {"chat_template_kwargs": caller_ctk}}
    return ChatCompletionsTransport().build_kwargs(
        model="stub-model",
        messages=[{"role": "user", "content": "ping"}],
        tools=None,
        provider_profile=get_provider_profile("custom"),
        **params,
    )


def _legacy(effort: str, caller_ctk: dict | None = None) -> dict:
    params = {
        "reasoning_config": _reasoning(effort),
        "base_url": STUB_URL,
        "supports_reasoning": True,
        "provider_name": "stub",
    }
    if caller_ctk is not None:
        params["request_overrides"] = {"extra_body": {"chat_template_kwargs": caller_ctk}}
    return ChatCompletionsTransport().build_kwargs(
        model="stub-model",
        messages=[{"role": "user", "content": "ping"}],
        tools=None,
        **params,
    )


def _assert_controlled(kwargs: dict, expected: dict) -> None:
    extra = kwargs.get("extra_body") or {}
    assert extra.get("chat_template_kwargs") == expected
    assert "reasoning" not in extra
    assert "reasoning_effort" not in kwargs


@pytest.mark.parametrize("builder", ("aux", "profile", "legacy"))
@pytest.mark.parametrize("style", ("qwen", "ds4"))
@pytest.mark.parametrize("effort", EFFORTS)
def test_b1_builders_map_effort_and_drop_legacy_reasoning(monkeypatch, builder, style, effort):
    _install(monkeypatch, MAPS[style])
    kwargs = {"aux": _aux, "profile": _profile, "legacy": _legacy}[builder](effort)
    _assert_controlled(kwargs, _expected(style, effort))


@pytest.mark.parametrize("builder", ("aux", "profile", "legacy"))
@pytest.mark.parametrize("effort", ("low", "high"))
def test_b1a_no_effort_key_sends_switch_only(monkeypatch, builder, effort):
    _install(
        monkeypatch,
        {"kind": "chat_template_kwargs", "switch_key": "enable_thinking"},
    )
    kwargs = {"aux": _aux, "profile": _profile, "legacy": _legacy}[builder](effort)
    extra = kwargs.get("extra_body") or {}
    assert extra.get("chat_template_kwargs") == {"enable_thinking": True}
    assert "reasoning_effort" not in extra.get("chat_template_kwargs", {})
    assert "reasoning_effort" not in kwargs
    assert "reasoning" not in extra


@pytest.mark.parametrize("builder", ("aux", "profile", "legacy"))
def test_b1b_caller_kwargs_win_and_merge(monkeypatch, builder):
    _install(monkeypatch, QWEN)
    call = {"aux": _aux, "profile": _profile, "legacy": _legacy}[builder]
    if builder == "aux":
        kept = call("none", caller={"chat_template_kwargs": {"enable_thinking": True}})
        merged = call("low", caller={"chat_template_kwargs": {"foo": 1}})
    else:
        kept = call("none", caller_ctk={"enable_thinking": True})
        merged = call("low", caller_ctk={"foo": 1})
    assert kept["extra_body"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert "reasoning_effort" not in kept["extra_body"]["chat_template_kwargs"]
    assert "reasoning_effort" not in kept
    assert merged["extra_body"]["chat_template_kwargs"] == {
        "foo": 1,
        "enable_thinking": True,
        "reasoning_effort": "low",
    }


def test_b3_unmapped_effort_logs_once_for_the_call(monkeypatch, caplog):
    # minimal is in the corrected Qwen map. Drop it so this bar still sees an unmapped effort.
    partial = {
        **QWEN,
        "effort_map": {key: value for key, value in QWEN["effort_map"].items() if key != "minimal"},
    }
    _install(monkeypatch, partial)
    with caplog.at_level(logging.WARNING, logger="agent.thinking_control"):
        kwargs = _aux("minimal")
    extra = kwargs["extra_body"]
    assert "reasoning_effort" not in extra["chat_template_kwargs"]
    assert extra["chat_template_kwargs"] == {"enable_thinking": True}
    dropped = [rec.getMessage() for rec in caplog.records if "dropped unmapped" in rec.getMessage()]
    assert len(dropped) == 1
    assert "minimal" in dropped[0]


def test_inactive_block_returns_the_same_object():
    body = {"reasoning": {"enabled": True, "effort": "high"}}
    assert apply_thinking_control(body, {"enabled": True, "effort": "high"}, None) is body
    assert apply_thinking_control(body, {"enabled": True, "effort": "high"}, {}) is body


def _probe(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/probe_provider_wire_body.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=proc_env,
    )


def _system_text(raw: bytes) -> str:
    body = json.loads(raw.decode("utf-8"))
    for message in body.get("messages") or []:
        if isinstance(message, dict) and message.get("role") == "system":
            content = message.get("content")
            return content if isinstance(content, str) else json.dumps(content)
    return ""


@pytest.mark.parametrize("reasoning", ("none", "low", "high"))
def test_b2_probe_qwen_wire(reasoning):
    proc = _probe([
        "--mode", "stage-b",
        "--reasoning", reasoning,
        "--thinking-control", "qwen",
    ])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for path in ("aux", "main-stream", "main-nonstream", "moa"):
        assert f"PATH {path} PASS" in proc.stdout
    if reasoning == "high":
        assert "xhigh" in proc.stdout
        assert "never high" in proc.stdout


def test_b3_probe_unmapped_effort_on_the_wire():
    proc = _probe([
        "--mode", "stage-b",
        "--reasoning", "minimal",
        "--thinking-control", "partial",
        "--paths", "aux",
    ])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PATH aux PASS" in proc.stdout
    assert "dropped unmapped" in proc.stdout
    assert "minimal" in proc.stdout


def test_b5_golden_bytes_without_thinking_control(tmp_path):
    golden = [
        "--mode", "golden",
        "--check-golden",
        "tests/fixtures/provider_wire_body/golden",
    ]
    proc = _probe(golden)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    other_home = tmp_path / "alt-hermes-home"
    captured = tmp_path / "captured"
    alt = _probe(
        [*golden, "--save-golden", str(captured)],
        env={
            "HERMES_PROBE_HOME": str(other_home),
            "HERMES_PROBE_FROZEN_NOW": "2019-07-04T01:02:03+00:00",
        },
    )
    assert alt.returncode == 0, alt.stdout + alt.stderr
    saved = _system_text((captured / "main-stream.body").read_bytes())
    committed = _system_text((ROOT / "tests/fixtures/provider_wire_body/golden/main-stream.body").read_bytes())
    assert str(other_home) in saved
    assert "Thursday, July 04, 2019" in saved
    assert saved != committed


def _write_config(home: Path, payload: dict) -> None:
    import yaml

    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _write_provider(home: Path, block: dict) -> None:
    import yaml

    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "stub": {
                        "base_url": STUB_URL,
                        "api_key": "stub-key",
                        "thinking_control": block,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _load_fresh(monkeypatch, home: Path):
    monkeypatch.setenv("HERMES_HOME", str(home))
    from agent import thinking_control
    from hermes_cli.config import _LOAD_CONFIG_CACHE, load_config

    thinking_control._INCOMPLETE_WARNED.clear()
    _LOAD_CONFIG_CACHE.clear()
    return load_config()


def test_b7_partial_map_warns_and_complete_map_does_not(tmp_path, monkeypatch, caplog):
    missing = [effort for effort in VALID_REASONING_EFFORTS if effort != "low"]
    _write_provider(
        tmp_path / "partial",
        {
            "kind": "chat_template_kwargs",
            "switch_key": "enable_thinking",
            "effort_key": "reasoning_effort",
            "effort_map": {"low": "low"},
        },
    )
    with caplog.at_level(logging.WARNING, logger="agent.thinking_control"):
        _load_fresh(monkeypatch, tmp_path / "partial")
    partial = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "agent.thinking_control" and "effort_map is missing" in rec.getMessage()
    ]
    assert len(partial) == 1
    assert partial[0].startswith("providers.stub.thinking_control:")
    named = partial[0].split("missing efforts ", 1)[1].split(", ")
    assert named == missing

    for name, block in (("qwen", QWEN), ("ds4", DS4)):
        caplog.clear()
        _write_provider(tmp_path / name, block)
        with caplog.at_level(logging.WARNING, logger="agent.thinking_control"):
            _load_fresh(monkeypatch, tmp_path / name)
        printed = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == "agent.thinking_control" and "effort_map is missing" in rec.getMessage()
        ]
        assert printed == [], name


def test_b8_requested_model_override_beats_the_main_model(tmp_path, monkeypatch):
    """Aux and MoA with no caller reasoning_config use the requested model's override.

    Main model x-ai/grok-main plus a global high must not leak onto spark-qwen,
    whose override is none. A second local model with no override gets high
    mapped through the Qwen map (xhigh). An explicit caller config still wins.
    """
    from hermes_constants import resolve_reasoning_config

    home = tmp_path / "b8"
    _write_config(
        home,
        {
            "model": "x-ai/grok-main",
            "agent": {
                "reasoning_effort": "high",
                "reasoning_overrides": {"spark-qwen": "none"},
            },
            "providers": {
                "spark": {
                    "base_url": STUB_URL,
                    "api_key": "stub-key",
                    "thinking_control": QWEN,
                }
            },
        },
    )
    cfg = _load_fresh(monkeypatch, home)
    assert resolve_reasoning_config(cfg, "") == {"enabled": True, "effort": "high"}
    assert resolve_reasoning_config(cfg, "spark-qwen") == {"enabled": False}
    assert resolve_reasoning_config(cfg, "spark-plain") == {"enabled": True, "effort": "high"}

    messages = [{"role": "user", "content": "ping"}]

    def wire(model: str, **extra):
        kwargs = _build_call_kwargs(
            "spark",
            model,
            messages,
            base_url=STUB_URL,
            **extra,
        )
        body = kwargs.get("extra_body") or {}
        assert "reasoning" not in body
        assert "reasoning_effort" not in kwargs
        return body.get("chat_template_kwargs")

    assert wire("spark-qwen") == {"enable_thinking": False}
    assert wire("spark-qwen", task="moa_reference") == {"enable_thinking": False}
    assert wire("spark-plain") == {"enable_thinking": True, "reasoning_effort": "xhigh"}
    assert wire("spark-plain", task="moa_reference") == {
        "enable_thinking": True,
        "reasoning_effort": "xhigh",
    }
    assert wire("spark-qwen", reasoning_config={"enabled": True, "effort": "low"}) == {
        "enable_thinking": True,
        "reasoning_effort": "low",
    }


def test_b9_iteration_summary_maps_kwargs_on_the_socket(tmp_path, monkeypatch):
    """The hand-built iteration-limit summary posts mapped kwargs to the stub."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    captured: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8"))
            captured.append(body)
            payload = {
                "id": "chatcmpl-stub",
                "object": "chat.completion",
                "created": 0,
                "model": "spark-qwen",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address[:2]
    assert host == "127.0.0.1"
    base_url = f"http://127.0.0.1:{port}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        home = tmp_path / "b9"
        _write_config(
            home,
            {
                "model": "spark-qwen",
                "agent": {"reasoning_effort": "high"},
                "providers": {
                    "spark": {
                        "base_url": base_url,
                        "api_key": "stub-key",
                        "thinking_control": QWEN,
                    }
                },
            },
        )
        _load_fresh(monkeypatch, home)
        from agent.chat_completion_helpers import handle_max_iterations
        from run_agent import AIAgent

        agent = AIAgent(
            provider="spark",
            api_key="stub-key",
            base_url=base_url,
            api_mode="chat_completions",
            model="spark-qwen",
            reasoning_config={"enabled": True, "effort": "high"},
            quiet_mode=True,
            skip_memory=True,
            skip_context_files=True,
            skip_background_review=True,
            max_iterations=2,
            save_trajectories=False,
        )
        try:
            text = handle_max_iterations(
                agent,
                [{"role": "user", "content": "ping"}],
                2,
            )
        finally:
            close = getattr(agent, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        assert text == "pong"
        posted = [body for body in captured if isinstance(body, dict) and body.get("messages")]
        assert posted, "stub socket received no summary request"
        for body in posted:
            assert body.get("chat_template_kwargs") == {
                "enable_thinking": True,
                "reasoning_effort": "xhigh",
            }
            assert "reasoning" not in body
            assert "reasoning_effort" not in body
    finally:
        server.shutdown()
        server.server_close()


def test_b10_nondict_caller_kwargs_reach_the_wire_unchanged(monkeypatch, caplog):
    _install(monkeypatch, QWEN)
    with caplog.at_level(logging.WARNING, logger="agent.thinking_control"):
        kwargs = _build_call_kwargs(
            "stub",
            "stub-model",
            [{"role": "user", "content": "ping"}],
            extra_body={"chat_template_kwargs": "x", "keep": 1},
            reasoning_config=_reasoning("low"),
            base_url=STUB_URL,
        )
    extra = kwargs["extra_body"]
    assert extra["chat_template_kwargs"] == "x"
    assert extra.get("keep") == 1
    assert "reasoning" not in extra
    assert "enable_thinking" not in extra
    warnings = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "agent.thinking_control" and "non-dict" in rec.getMessage()
    ]
    assert len(warnings) == 1
    assert "stub" in warnings[0]
