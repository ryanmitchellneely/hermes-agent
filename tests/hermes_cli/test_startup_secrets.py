"""Proof tests for refuse-to-serve on weak/unresolved secrets (P1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.startup_secrets import (
    SecretRequirement,
    assert_gateway_may_bind,
    check_requirements,
    juice_mail_secret_requirements,
    resolve_gmail_readonly_token,
    resolve_env_or_hermes_dotenv,
)


def test_placeholder_secret_refuses_to_bind():
    reqs = [
        SecretRequirement(
            name="TELEGRAM_BOT_TOKEN",
            resolve=lambda: "changeme",
            min_length=8,
            required=True,
        )
    ]
    report = check_requirements(reqs)
    assert report.ok is False
    assert "TELEGRAM_BOT_TOKEN" in report.refused
    assert "placeholder" in report.error_message.lower() or "REFUSE-TO-SERVE" in report.error_message


def test_missing_required_secret_refuses():
    reqs = [
        SecretRequirement(
            name="TELEGRAM_BOT_TOKEN",
            resolve=lambda: "",
            min_length=8,
            required=True,
        )
    ]
    report = check_requirements(reqs)
    assert report.ok is False
    assert report.refused == ["TELEGRAM_BOT_TOKEN"]


def test_legitimate_secret_binds_cleanly():
    reqs = [
        SecretRequirement(
            name="TELEGRAM_BOT_TOKEN",
            resolve=lambda: "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
            min_length=20,
            required=True,
        )
    ]
    report = check_requirements(reqs)
    assert report.ok is True
    assert report.refused == []


def test_fallback_resolver_chain_not_false_missing(monkeypatch):
    """A secret that resolves via fallback is not 'missing' — outage lesson #1."""

    def runtime_resolver() -> str:
        # Simulate: process env empty, fallback chain returns real value
        primary = ""
        fallback = "sk-live-fallback-resolved-value-ok"
        return primary or fallback

    reqs = [
        SecretRequirement(
            name="OPENAI_API_KEY",
            resolve=runtime_resolver,
            min_length=8,
            required=True,
        )
    ]
    report = check_requirements(reqs)
    assert report.ok is True


def test_disabled_surface_skips_secret():
    reqs = [
        SecretRequirement(
            name="TELEGRAM_BOT_TOKEN",
            resolve=lambda: "",
            required=True,
            enabled=False,
        )
    ]
    report = check_requirements(reqs)
    assert report.ok is True


def test_assert_gateway_may_bind_exits_on_placeholder(monkeypatch):
    monkeypatch.delenv("HERMES_SKIP_STARTUP_SECRETS", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "replace-me")
    # Also clear HERMES dotenv path interference by forcing resolve via env only
    from hermes_cli import startup_secrets as ss

    monkeypatch.setattr(ss, "resolve_telegram_bot_token", lambda: "replace-me")
    with pytest.raises(SystemExit) as ei:
        assert_gateway_may_bind(telegram_enabled=True)
    assert "REFUSE-TO-SERVE" in str(ei.value)


def test_assert_gateway_may_bind_ok(monkeypatch):
    from hermes_cli import startup_secrets as ss

    monkeypatch.setattr(
        ss,
        "resolve_telegram_bot_token",
        lambda: "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
    )
    report = assert_gateway_may_bind(telegram_enabled=True)
    assert report.ok is True


def test_gmail_token_resolver_reads_file(tmp_path: Path):
    token_file = tmp_path / "gmail-readonly.json"
    token_file.write_text(
        json.dumps({"refresh_token": "1//0gVALID_REFRESH_TOKEN_VALUE_HERE"}),
        encoding="utf-8",
    )
    val = resolve_gmail_readonly_token(str(token_file))
    assert val.startswith("1//")

    reqs = juice_mail_secret_requirements(token_path=str(token_file), required=True)
    report = check_requirements(reqs)
    assert report.ok is True


def test_gmail_placeholder_refuses(tmp_path: Path):
    token_file = tmp_path / "gmail-readonly.json"
    token_file.write_text(json.dumps({"refresh_token": "changeme"}), encoding="utf-8")
    reqs = juice_mail_secret_requirements(token_path=str(token_file), required=True)
    report = check_requirements(reqs)
    assert report.ok is False
