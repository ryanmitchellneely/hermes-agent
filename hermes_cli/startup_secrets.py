"""Refuse-to-serve gate for T1000 serving surfaces (P1 Distillery pattern).

At startup of any serving process, verify every *required* secret resolves the
same way runtime code resolves it — never raw os.environ-only checks that miss
fallback chains. Placeholder or unreadable secrets → refuse to bind, loud error.

Outage lesson (K2):
  1. Call the same resolver the serving code calls.
  2. Deploy preflight: boot the new instance and pass health before stopping the
     healthy one (see deploy/preflight_bind_check.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence


@dataclass
class SecretRequirement:
    """One secret a serving surface needs before it may bind."""

    name: str  # human/log name, e.g. TELEGRAM_BOT_TOKEN
    # Resolver returns the secret string or "" if unresolved. Must mirror runtime.
    resolve: Callable[[], str]
    min_length: int = 8
    required: bool = True
    # When False, missing is OK (optional surface). When True and bad → refuse.
    enabled: bool = True


@dataclass
class SecretCheckResult:
    name: str
    ok: bool
    reason: str = ""
    source_hint: str = ""


@dataclass
class StartupSecretsReport:
    ok: bool
    results: List[SecretCheckResult] = field(default_factory=list)
    refused: List[str] = field(default_factory=list)

    @property
    def error_message(self) -> str:
        if self.ok:
            return ""
        lines = ["REFUSE-TO-SERVE: required secrets unresolved or placeholder:"]
        for name in self.refused:
            match = next((r for r in self.results if r.name == name), None)
            detail = match.reason if match else "unresolved"
            lines.append(f"  - {name}: {detail}")
        lines.append(
            "Fix the secret via the same path the runtime uses "
            "(HERMES_HOME .env / auth.json / credential pool), then restart."
        )
        return "\n".join(lines)


def _has_usable(value: str, *, min_length: int) -> bool:
    try:
        from hermes_cli.auth import has_usable_secret

        return has_usable_secret(value, min_length=min_length)
    except Exception:
        cleaned = (value or "").strip()
        if len(cleaned) < min_length:
            return False
        placeholders = {
            "",
            "changeme",
            "replace-me",
            "your-token-here",
            "x",
            "todo",
            "none",
            "null",
            "undefined",
            "placeholder",
            "example",
            "xxx",
            "test",
            "secret",
        }
        return cleaned.lower() not in placeholders


def check_requirements(
    requirements: Sequence[SecretRequirement],
) -> StartupSecretsReport:
    """Evaluate requirements; ok=False means the process must not bind."""
    results: List[SecretCheckResult] = []
    refused: List[str] = []
    for req in requirements:
        if not req.enabled:
            results.append(
                SecretCheckResult(name=req.name, ok=True, reason="disabled-skip")
            )
            continue
        try:
            value = req.resolve() or ""
        except Exception as exc:  # noqa: BLE001 — refuse loud on resolver failure
            results.append(
                SecretCheckResult(
                    name=req.name,
                    ok=False,
                    reason=f"resolver error: {exc}",
                )
            )
            if req.required:
                refused.append(req.name)
            continue
        if _has_usable(value, min_length=req.min_length):
            results.append(
                SecretCheckResult(name=req.name, ok=True, reason="resolved")
            )
        else:
            reason = "missing" if not (value or "").strip() else "placeholder-or-weak"
            results.append(SecretCheckResult(name=req.name, ok=False, reason=reason))
            if req.required:
                refused.append(req.name)
    return StartupSecretsReport(ok=not refused, results=results, refused=refused)


def refuse_if_unresolved(requirements: Sequence[SecretRequirement]) -> None:
    """Raise SystemExit with a loud message when required secrets fail."""
    report = check_requirements(requirements)
    if not report.ok:
        raise SystemExit(report.error_message)


# --- Runtime-faithful resolvers (same paths serving code uses) ----------------


def resolve_env_or_hermes_dotenv(env_name: str) -> str:
    """Resolve like hermes_cli.config.get_env_value: process env then HERMES_HOME/.env."""
    direct = (os.environ.get(env_name) or "").strip()
    if direct:
        return direct
    try:
        from hermes_cli.config import get_env_value

        return (get_env_value(env_name) or "").strip()
    except Exception:
        return ""


def resolve_telegram_bot_token() -> str:
    """Mirror gateway platform token resolution for Telegram."""
    # Prefer already-loaded platform config when available; fall back to env chain.
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN"):
        val = resolve_env_or_hermes_dotenv(key)
        if val:
            return val
    return ""


def resolve_provider_api_key(provider_id: str) -> str:
    """Use the same provider secret resolver auth.py uses (includes pool fallback)."""
    try:
        from hermes_cli.auth import (
            PROVIDER_REGISTRY,
            _resolve_api_key_provider_secret,
        )

        pconfig = PROVIDER_REGISTRY.get(provider_id)
        if pconfig is None:
            return ""
        secret, _source = _resolve_api_key_provider_secret(provider_id, pconfig)
        return (secret or "").strip()
    except Exception:
        # Narrow fallback: common env names only — still better than silent boot.
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "xai": "XAI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        env_name = env_map.get(provider_id, "")
        return resolve_env_or_hermes_dotenv(env_name) if env_name else ""


def resolve_gmail_readonly_token(path: Optional[str] = None) -> str:
    """Juice Gmail read-only token — file must exist, be non-empty, non-placeholder JSON."""
    import json
    from pathlib import Path

    candidates = []
    if path:
        candidates.append(Path(path))
    home = Path(os.path.expanduser("~"))
    candidates.extend(
        [
            home / ".sovereign" / "juice" / "gmail-readonly.json",
            home / ".t1000" / "google_accounts" / "joinsov.json",
            Path(os.environ.get("HERMES_HOME", str(home / ".t1000")))
            / "google_token.json",
        ]
    )
    for p in candidates:
        try:
            if not p.is_file():
                continue
            raw = p.read_text(encoding="utf-8")
            if not raw.strip():
                continue
            data = json.loads(raw)
            token = (
                data.get("token")
                or data.get("access_token")
                or data.get("refresh_token")
                or ""
            )
            if isinstance(token, str) and token.strip():
                return token.strip()
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    return ""


def gateway_secret_requirements(
    *,
    telegram_enabled: bool = True,
    require_model_provider: Optional[str] = None,
) -> List[SecretRequirement]:
    """Default requirements for the T1000 gateway serving process."""
    reqs: List[SecretRequirement] = [
        SecretRequirement(
            name="TELEGRAM_BOT_TOKEN",
            resolve=resolve_telegram_bot_token,
            min_length=20,
            required=True,
            enabled=telegram_enabled,
        ),
    ]
    if require_model_provider:
        pid = require_model_provider

        def _resolve(p=pid) -> str:
            return resolve_provider_api_key(p)

        reqs.append(
            SecretRequirement(
                name=f"PROVIDER_KEY:{pid}",
                resolve=_resolve,
                min_length=8,
                required=False,  # OAuth providers may have no API key
                enabled=True,
            )
        )
    return reqs


def juice_mail_secret_requirements(
    *,
    token_path: Optional[str] = None,
    required: bool = True,
) -> List[SecretRequirement]:
    """Requirements for Juice timers that touch Gmail credentials."""

    def _resolve() -> str:
        return resolve_gmail_readonly_token(token_path)

    return [
        SecretRequirement(
            name="GMAIL_READONLY_TOKEN",
            resolve=_resolve,
            min_length=12,
            required=required,
            enabled=True,
        )
    ]


def assert_gateway_may_bind(
    *,
    telegram_enabled: bool = True,
    skip: bool = False,
) -> StartupSecretsReport:
    """Call at gateway startup before binding/polling. Exits process if refused."""
    if skip or os.environ.get("HERMES_SKIP_STARTUP_SECRETS", "").strip() in {
        "1",
        "true",
        "yes",
    }:
        return StartupSecretsReport(ok=True, results=[])
    reqs = gateway_secret_requirements(telegram_enabled=telegram_enabled)
    report = check_requirements(reqs)
    if not report.ok:
        raise SystemExit(report.error_message)
    return report
