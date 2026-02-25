"""Agent core with pluggable investigation providers."""

from __future__ import annotations

from collections.abc import Iterator

from agent.providers.anthropic_provider import AnthropicAgentProvider
from agent.providers.base import AgentProvider
from agent.providers.openai_provider import OpenAIAgentProvider
from config import config


class _UnsupportedProvider:
    """Fallback provider for unknown or not-yet-implemented providers."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        return (
            "❌ Unsupported AGENT_PROVIDER configuration.\n\n"
            f"Configured provider: `{self.provider_name}`\n"
            "Supported in this build: `anthropic`\n\n"
            "Set `AGENT_PROVIDER=anthropic` in `.env` and restart."
        )

    def investigate_stream(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> Iterator[str]:
        yield self.investigate(user_message, context, thread_history)


class Agent:
    """Agent that delegates investigation to a configured provider."""

    def __init__(self):
        self.provider_name = config.AGENT_PROVIDER
        self.provider: AgentProvider = self._create_provider(self.provider_name)

    def _create_provider(self, provider_name: str) -> AgentProvider:
        if provider_name == "anthropic":
            return AnthropicAgentProvider()
        if provider_name == "openai":
            return OpenAIAgentProvider()
        return _UnsupportedProvider(provider_name)

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        return self.provider.investigate(
            user_message, context=context, thread_history=thread_history
        )

    def investigate_stream(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> Iterator[str]:
        yield from self.provider.investigate_stream(
            user_message, context=context, thread_history=thread_history
        )


# Singleton instance
agent = Agent()
