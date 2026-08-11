"""Unit tests for the custom provider profile's reasoning wiring.

``provider=custom`` covers any OpenAI-compatible endpoint the user points
Hermes at — local Ollama, vLLM, llama.cpp, and hosted reasoning APIs like
GLM-5.2 on Volcengine ARK. Before #57601's salvage, ``CustomProfile`` emitted
nothing when reasoning was *enabled*, so a configured ``reasoning_effort``
was silently dropped for every custom endpoint.

These tests pin the wire-shape contract:
  - disabled            → extra_body.think = False
  - enabled + effort    → top-level reasoning_effort (native OpenAI-compat
                          format GLM/ARK expect), passed through verbatim
                          including ``max``/``xhigh`` on **non-Ollama**
  - Ollama endpoints    → clamp Hermes-only levels (``xhigh``→``high``) so
                          desk global Grok default never HTTP 400s
                          (t_3a7f19db / t_0be4092d class)
  - enabled + no effort → nothing emitted (endpoint's server default applies)
  - ollama_num_ctx      → extra_body.options.num_ctx, orthogonal to reasoning
"""

from __future__ import annotations

import pytest


@pytest.fixture
def custom_profile():
    """Resolve the registered custom profile via the global registry.

    Importing ``model_tools`` triggers plugin discovery, which registers the
    ``custom`` profile. Going through ``get_provider_profile`` keeps the test
    honest — if the registered class is ever downgraded to a plain
    ``ProviderProfile``, the assertions below collapse.
    """
    import model_tools  # noqa: F401
    import providers

    profile = providers.get_provider_profile("custom")
    assert profile is not None, "custom provider profile must be registered"
    return profile


class TestCustomReasoningWireShape:
    """``build_api_kwargs_extras`` produces the correct wire format."""

    def test_no_reasoning_config_emits_nothing(self, custom_profile):
        """Unset reasoning → omit everything so the endpoint's default applies."""
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config=None, model="glm-5.2"
        )
        assert eb == {}
        assert tl == {}

    def test_disabled_sends_think_false(self, custom_profile):
        """enabled=False → reasoning_effort='none' top-level + think=False.

        Both fields are required: Ollama's /v1/chat/completions silently
        ignores extra_body.think (only /api/chat honours it — ollama#14820)
        but respects top-level reasoning_effort (#25758). think=False stays
        for proxies and the native /api/chat path.
        """
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False}, model="glm-5.2"
        )
        assert eb == {"think": False}
        assert tl == {"reasoning_effort": "none"}

    def test_effort_none_sends_think_false(self, custom_profile):
        """effort='none' is the disable alias → same dual emission."""
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "none"}, model="glm-5.2"
        )
        assert eb == {"think": False}
        assert tl == {"reasoning_effort": "none"}

    @pytest.mark.parametrize(
        "effort", ["minimal", "low", "medium", "high", "xhigh", "max"]
    )
    def test_enabled_effort_goes_top_level_non_ollama(self, custom_profile, effort):
        """enabled + effort on GLM/ARK → TOP-LEVEL reasoning_effort, verbatim.

        Non-Ollama custom endpoints must keep receiving Hermes levels
        including ``xhigh``/``max`` so deep-reasoning APIs keep working.
        """
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="glm-5.2",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        assert tl == {"reasoning_effort": effort}
        assert "reasoning_effort" not in eb
        assert "think" not in eb

    def test_does_not_force_think_true_on_enable(self, custom_profile):
        """We must never send think=True on enable — it's Ollama-only and
        would 400 on GLM/vLLM endpoints that don't recognize it."""
        eb, _ = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "high"}, model="glm-5.2"
        )
        assert eb.get("think") is not True


class TestCustomOllamaReasoningClamp:
    """Local Ollama must never see Hermes-only efforts like xhigh."""

    @pytest.mark.parametrize(
        "effort,expected",
        [
            ("xhigh", "high"),
            ("ultra", "max"),
            ("minimal", "low"),
            ("high", "high"),
            ("max", "max"),
            ("medium", "medium"),
            ("low", "low"),
        ],
    )
    def test_clamps_when_thinking_supported(self, custom_profile, effort, expected):
        """Thinking-capable Ollama models get clamped efforts on the wire."""
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="gpt-oss:120b",
            base_url="http://127.0.0.1:11435/v1",
            supports_reasoning=True,
        )
        assert tl == {"reasoning_effort": expected}
        assert "think" not in eb

    def test_non_thinking_omits_enabled_effort(self, custom_profile):
        """Non-thinking tags must not get high after xhigh-clamp.

        Live fail class: qwen2.5-coder:32b-64k → HTTP 400
        \"does not support thinking\" when reasoning_effort=high.
        """
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "xhigh"},
            model="qwen2.5-coder:32b-64k",
            base_url="http://127.0.0.1:11435/v1",
            supports_reasoning=False,
        )
        assert "reasoning_effort" not in tl
        assert "think" not in eb

    def test_xhigh_clamped_by_ollama_model_tag_when_thinking(self, custom_profile):
        _, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "xhigh"},
            model="qwen2.5-coder:32b-64k",
            base_url="http://10.0.0.5:9999/v1",
            supports_reasoning=True,
        )
        assert tl == {"reasoning_effort": "high"}

    def test_none_still_dual_emits_on_ollama(self, custom_profile):
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False},
            model="gpt-oss:120b",
            base_url="http://127.0.0.1:11435/v1",
            supports_reasoning=False,
        )
        assert eb == {"think": False}
        assert tl == {"reasoning_effort": "none"}

    def test_num_ctx_plus_non_thinking_xhigh_omits_effort(self, custom_profile):
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "xhigh"},
            ollama_num_ctx=65536,
            model="qwen2.5-coder:32b-64k",
            base_url="http://127.0.0.1:11435/v1",
            supports_reasoning=False,
        )
        assert eb == {"options": {"num_ctx": 65536}}
        assert tl == {}


class TestCustomReasoningWithNumCtx:
    """Ollama num_ctx and reasoning are independent and compose."""

    def test_num_ctx_alone(self, custom_profile):
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config=None, ollama_num_ctx=8192, model="qwen3"
        )
        assert eb == {"options": {"num_ctx": 8192}}
        assert tl == {}

    def test_num_ctx_plus_clamped_xhigh_thinking(self, custom_profile):
        eb, tl = custom_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "xhigh"},
            ollama_num_ctx=65536,
            model="gpt-oss:120b",
            base_url="http://127.0.0.1:11435/v1",
            supports_reasoning=True,
        )
        assert eb == {"options": {"num_ctx": 65536}}
        assert tl == {"reasoning_effort": "high"}
