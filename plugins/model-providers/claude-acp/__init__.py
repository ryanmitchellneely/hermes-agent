"""Claude Agent ACP provider profile.

claude-acp spawns ``claude-agent-acp`` (Claude Agent SDK over ACP stdio).
Auth and Max-subscription billing stay inside Claude Code — Hermes only
orchestrates. Prefer this over the native Anthropic HTTP provider when you
want subscription plan usage without third-party extra-usage API routing.
"""

from providers import register_provider
from providers.base import ProviderProfile


class ClaudeACPProfile(ProviderProfile):
    """Claude Agent ACP — external process, no REST models endpoint."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Model listing is handled inside the Claude Agent ACP session."""
        return None


claude_acp = ClaudeACPProfile(
    name="claude-acp",
    aliases=("claude-code-acp", "claude-agent-acp", "anthropic-acp"),
    api_mode="chat_completions",
    env_vars=(),
    base_url="acp://claude",
    auth_type="external_process",
)

register_provider(claude_acp)
