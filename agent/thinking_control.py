from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agent.thinking_control")

_INCOMPLETE_WARNED: set[tuple[str, tuple[str, ...]]] = set()
_IGNORED_PROVIDER_NAMES = {"", "custom", "auto"}


def thinking_control_block(provider_entry: dict | None) -> dict | None:
    if not isinstance(provider_entry, dict):
        return None
    block = provider_entry.get("thinking_control")
    if not isinstance(block, dict):
        return None
    if block.get("kind") != "chat_template_kwargs":
        return None
    switch_key = block.get("switch_key")
    if not isinstance(switch_key, str) or not switch_key.strip():
        return None
    return block


def _norm_base(url: Any) -> str:
    text = str(url or "").strip().rstrip("/").casefold()
    if text.endswith("/v1"):
        text = text[:-3].rstrip("/")
    return text


def _provider_label(provider_entry: dict | None) -> str:
    if not isinstance(provider_entry, dict):
        return "?"
    label = provider_entry.get("_thinking_control_provider") or provider_entry.get("name")
    return str(label or "?")


def lookup_provider_entry(provider_name: str | None, base_url: str | None) -> dict | None:
    from hermes_cli.config import load_config

    config = load_config() or {}
    providers = config.get("providers")
    if not isinstance(providers, dict):
        return None
    name = str(provider_name or "").strip()
    if name.lower().startswith("custom:"):
        name = name.split(":", 1)[1].strip()
    if name.casefold() not in _IGNORED_PROVIDER_NAMES:
        for key, entry in providers.items():
            if not isinstance(entry, dict):
                continue
            names = {str(key).strip().casefold(), str(entry.get("name") or "").strip().casefold()}
            if name.casefold() in names:
                stamped = dict(entry)
                stamped["_thinking_control_provider"] = str(key)
                return stamped
    target = _norm_base(base_url)
    if not target:
        return None
    for key, entry in providers.items():
        if not isinstance(entry, dict):
            continue
        for field in ("base_url", "url", "api"):
            if _norm_base(entry.get(field)) == target:
                stamped = dict(entry)
                stamped["_thinking_control_provider"] = str(key)
                return stamped
    return None


def _resolve_when_active(
    extra_body: dict | None,
    reasoning_config: dict | None,
    model: str | None = None,
) -> dict | None:
    if isinstance(reasoning_config, dict):
        return reasoning_config
    embedded = extra_body.get("reasoning") if isinstance(extra_body, dict) else None
    if isinstance(embedded, dict) and ("enabled" in embedded or "effort" in embedded):
        if embedded.get("enabled") is False:
            return {"enabled": False}
        effort = embedded.get("effort")
        if effort:
            return {"enabled": True, "effort": effort}
        return {"enabled": True}
    from hermes_cli.config import load_config
    from hermes_constants import resolve_reasoning_config

    # Empty model would resolve against the config's main model and ignore a
    # per-model override for the model this request is actually calling.
    requested = model.strip() if isinstance(model, str) else ""
    return resolve_reasoning_config(load_config() or {}, requested)


def _mapped_effort(effort_map: dict, effort: str) -> Any:
    if effort in effort_map:
        return effort_map[effort]
    lowered = effort.casefold()
    for key, value in effort_map.items():
        if str(key).strip().casefold() == lowered:
            return value
    return None


def apply_thinking_control(
    extra_body: dict | None,
    reasoning_config: dict | None,
    provider_entry: dict | None,
    model: str | None = None,
) -> dict | None:
    block = thinking_control_block(provider_entry)
    if block is None:
        return extra_body
    source = extra_body if isinstance(extra_body, dict) else None
    resolved = _resolve_when_active(
        source,
        reasoning_config if isinstance(reasoning_config, dict) else None,
        model,
    )
    if not isinstance(resolved, dict):
        return extra_body
    body = dict(source or {})
    body.pop("reasoning", None)
    switch_key = str(block.get("switch_key")).strip()
    generated: dict[str, Any] = {}
    if resolved.get("enabled") is False:
        generated[switch_key] = False
    else:
        generated[switch_key] = True
        effort_key = block.get("effort_key")
        effort = resolved.get("effort")
        if isinstance(effort_key, str) and effort_key.strip() and effort is not None and str(effort).strip():
            effort_map = block.get("effort_map") if isinstance(block.get("effort_map"), dict) else {}
            mapped = _mapped_effort(effort_map, str(effort).strip())
            if mapped is None:
                logger.warning(
                    "thinking_control: provider %s dropped unmapped reasoning effort %r",
                    _provider_label(provider_entry),
                    effort,
                )
            else:
                generated[effort_key.strip()] = mapped
    if "chat_template_kwargs" in body and not isinstance(body.get("chat_template_kwargs"), dict):
        logger.warning(
            "thinking_control: provider %s left non-dict chat_template_kwargs unchanged",
            _provider_label(provider_entry),
        )
        return body
    existing = body.get("chat_template_kwargs")
    if not isinstance(existing, dict):
        existing = {}
    body["chat_template_kwargs"] = {**generated, **existing}
    return body


def warn_incomplete_thinking_control(config: dict | None) -> None:
    from hermes_constants import VALID_REASONING_EFFORTS

    if not isinstance(config, dict):
        return
    entries: list[tuple[str, dict]] = []
    providers = config.get("providers")
    if isinstance(providers, dict):
        for key, entry in providers.items():
            if isinstance(entry, dict):
                entries.append((str(key), entry))
    custom = config.get("custom_providers")
    if isinstance(custom, list):
        for entry in custom:
            if isinstance(entry, dict):
                entries.append((str(entry.get("name") or entry.get("provider_key") or "?"), entry))
    required = tuple(VALID_REASONING_EFFORTS)
    for name, entry in entries:
        block = entry.get("thinking_control")
        if not isinstance(block, dict):
            continue
        if block.get("kind") not in (None, "chat_template_kwargs"):
            continue
        effort_key = block.get("effort_key")
        if not isinstance(effort_key, str) or not effort_key.strip():
            continue
        effort_map = block.get("effort_map") if isinstance(block.get("effort_map"), dict) else {}
        covered = {str(key).strip().casefold() for key in effort_map}
        missing = tuple(effort for effort in required if effort not in covered)
        if not missing:
            continue
        dedup = (name, missing)
        if dedup in _INCOMPLETE_WARNED:
            continue
        _INCOMPLETE_WARNED.add(dedup)
        logger.warning(
            "providers.%s.thinking_control: effort_map is missing efforts %s",
            name,
            ", ".join(missing),
        )
