"""Custom / Ollama (local) provider profile.

Covers any endpoint registered as provider="custom", including local
Ollama instances and OpenAI-compatible reasoning endpoints (GLM-5.2 on
Volcengine ARK, vLLM, llama.cpp). Key quirks:
  - ollama_num_ctx → extra_body.options.num_ctx (local context window)
  - reasoning_config disabled → top-level reasoning_effort="none"
    (Ollama /v1/chat/completions ignores think=False — ollama#14820)
    + extra_body.think = False for /api/chat and proxies
  - reasoning_config enabled + effort → top-level reasoning_effort
    (the native OpenAI-compatible format GLM/ARK expect; unset omits it
    so the endpoint's server default applies)
  - **Ollama effort clamp**: local Ollama only accepts
    ``high|medium|low|max|none``. Desk default ``xhigh`` (Grok) must never
    reach the wire or the call 400s before tokens (Ryan desk
    ``t_3a7f19db`` / ``t_0be4092d``). Non-Ollama custom endpoints (GLM)
    still pass Hermes efforts through verbatim.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from providers import register_provider
from providers.base import ProviderProfile

# Ollama /v1/chat/completions allowlist (error text and ollama-cloud docs).
_OLLAMA_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "max"})

# Hermes levels that Ollama rejects (or never listed) → nearest safe value.
# Mirrors ollama-cloud's xhigh/ultra → max for deep tiers; minimal → low.
_OLLAMA_EFFORT_CLAMP = {
    "minimal": "low",
    "xhigh": "high",
    "ultra": "max",
}

# Common local Ollama listen ports (MBP :11434, Spark tunnel :11435, lab :11436).
_OLLAMA_LOCAL_PORTS = frozenset({11434, 11435, 11436, 11437})

# Ollama library tags look like ``qwen2.5-coder:32b-64k`` / ``hermes3:8b``.
# Not a perfect detector alone (could collide with rare non-Ollama names) —
# combined with local URL / port / "ollama" host below.
_OLLAMA_TAG_RE = re.compile(
    r"^[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)?$"
)
_OLLAMA_SIZE_HINT_RE = re.compile(
    r"(?:^|:)(?:latest|[\w.-]*\d+b(?:-\d+k)?|[\w.-]*\d+k)(?:$|:)",
    re.IGNORECASE,
)


def _looks_like_ollama(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> bool:
    """Return True when the request is almost certainly local/cloud Ollama.

    Used only to decide whether to clamp ``reasoning_effort`` values that
    Ollama rejects. Prefer false-negatives over false-positives so GLM/ARK
    custom endpoints keep receiving ``xhigh``/``max`` verbatim.
    """
    bu = (base_url or "").strip()
    if bu:
        lower = bu.lower()
        if "ollama.com" in lower or "ollama" in lower:
            return True
        try:
            parsed = urlparse(lower if "://" in lower else f"http://{lower}")
            host = (parsed.hostname or "").lower()
            port = parsed.port
            if host in {"localhost", "127.0.0.1", "::1"} and port in _OLLAMA_LOCAL_PORTS:
                return True
            if port in _OLLAMA_LOCAL_PORTS:
                return True
            if host.endswith(".ollama") or host.startswith("ollama."):
                return True
        except Exception:
            if any(f":{p}" in lower for p in _OLLAMA_LOCAL_PORTS):
                return True

    m = (model or "").strip()
    if not m:
        return False
    # HuggingFace GGUF pulls through Ollama use hf.co/… tags.
    if m.lower().startswith("hf.co/"):
        return True
    # Colon tags without a provider slash (openai/gpt-4 style uses /).
    if "/" in m.split(":")[0]:
        return False
    if ":" in m and _OLLAMA_TAG_RE.match(m) and _OLLAMA_SIZE_HINT_RE.search(m):
        return True
    return False


def clamp_ollama_reasoning_effort(effort: str) -> str | None:
    """Map a Hermes effort string onto Ollama's allowlist, or None to omit.

    Returns:
      - ``\"none\"`` / ``low`` / ``medium`` / ``high`` / ``max`` when valid
      - clamped value for Hermes-only levels (``xhigh``→``high``, …)
      - ``None`` when the input is empty/unrecognized (caller omits field)
    """
    e = (effort or "").strip().lower()
    if not e:
        return None
    if e in _OLLAMA_REASONING_EFFORTS:
        return e
    if e in _OLLAMA_EFFORT_CLAMP:
        return _OLLAMA_EFFORT_CLAMP[e]
    # Unknown — omit rather than 400 (same posture as ollama-cloud profile).
    return None


class CustomProfile(ProviderProfile):
    """Custom/Ollama local provider — think=false and num_ctx support."""

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        ollama_num_ctx: int | None = None,
        model: str | None = None,
        base_url: str | None = None,
        supports_reasoning: bool = False,
        **ctx: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        # Ollama context window
        if ollama_num_ctx:
            options = extra_body.get("options", {})
            options["num_ctx"] = ollama_num_ctx
            extra_body["options"] = options

        # Reasoning / thinking control for custom OpenAI-compatible endpoints
        # (GLM-5.2 on Volcengine ARK, vLLM, Ollama, llama.cpp, …).
        #
        #   - disabled  → extra_body.think = False (Ollama's thinking-off flag)
        #   - enabled + effort set → TOP-LEVEL reasoning_effort string, the
        #     format GLM-5.2/ARK and other OpenAI-compatible reasoning APIs
        #     expect (GLM documents "high" and "max"; "max" is its default).
        #   - enabled + no effort  → omit both, so the endpoint applies its own
        #     server-side default (do NOT force a level the user didn't pick).
        #
        # We deliberately do NOT emit ``think=True`` on enable: it is an
        # Ollama-only flag and thinking is already server-default-on for these
        # backends, so forcing it risks a 400 on GLM/vLLM endpoints that don't
        # recognize it. Mirrors the DeepSeek/Zai profile precedent.
        #
        # Ollama (local + cloud-shaped):
        #   1. Clamp Hermes-only levels (xhigh→high, ultra→max, minimal→low)
        #      so desk global Grok xhigh never hits the wire as invalid.
        #   2. Gate enabled efforts on supports_reasoning (/api/show
        #      ``thinking``). Non-thinking tags (qwen2.5-coder:32b-64k) 400
        #      with "does not support thinking" if any effort other than
        #      none is sent — omit the field instead (ollama-cloud posture).
        if reasoning_config and isinstance(reasoning_config, dict):
            _effort = (reasoning_config.get("effort") or "").strip().lower()
            _enabled = reasoning_config.get("enabled", True)
            _ollama = _looks_like_ollama(base_url=base_url, model=model)

            if _effort == "none" or _enabled is False:
                # Ollama's /v1/chat/completions silently ignores
                # extra_body.think (only /api/chat honours it — ollama#14820)
                # but respects the top-level reasoning_effort field, so both
                # are needed to actually stop a thinking-capable model from
                # reasoning (#25758). Endpoints that recognize neither simply
                # ignore them.
                top_level["reasoning_effort"] = "none"
                extra_body["think"] = False
            elif _effort:
                if _ollama:
                    if not supports_reasoning:
                        # Non-thinking / unknown: do NOT emit high after
                        # xhigh-clamp — that still 400s ("does not support
                        # thinking"). Omit; num_ctx already applied above.
                        pass
                    else:
                        clamped = clamp_ollama_reasoning_effort(_effort)
                        if clamped == "none":
                            top_level["reasoning_effort"] = "none"
                            extra_body["think"] = False
                        elif clamped:
                            top_level["reasoning_effort"] = clamped
                else:
                    # Non-Ollama custom (GLM/ARK/vLLM): pass through verbatim
                    # including xhigh/max so deep-reasoning APIs keep working.
                    top_level["reasoning_effort"] = _effort

        return extra_body, top_level

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Custom/Ollama: base_url is user-configured; fetch if set."""
        if not (base_url or self.base_url):
            return None
        return super().fetch_models(api_key=api_key, base_url=base_url, timeout=timeout)


custom = CustomProfile(
    name="custom",
    aliases=(
        "ollama",
        "local",
        "vllm",
        "llamacpp",
        "llama.cpp",
        "llama-cpp",
    ),
    env_vars=(),  # No fixed key — custom endpoint
    base_url="",  # User-configured
    # Without this, no max_tokens is sent and Ollama falls back to its internal
    # num_predict=128, truncating responses after a few tokens (#39281). This is
    # only a floor used when the user hasn't set model.max_tokens — they can
    # override per-model — so we set it generously rather than lowballing it.
    default_max_tokens=65536,
)

register_provider(custom)
