"""Agent core with pluggable investigation providers."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from agent.providers.anthropic_provider import AnthropicAgentProvider
from agent.providers.base import AgentProvider
from agent.providers.openai_provider import OpenAIAgentProvider
from config import config
from utils.events import emit, iterate_in_run_context, run_context


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
        self,
        user_message: str,
        context: str = "",
        thread_history: list | None = None,
        event_context: dict[str, Any] | None = None,
    ) -> str:
        """Run an investigation; ``event_context`` tags its events (channel, ids, ...)."""
        with run_context(provider=self.provider_name, **(event_context or {})):
            start = time.monotonic()
            try:
                response = self.provider.investigate(
                    user_message, context=context, thread_history=thread_history
                )
            except Exception as e:
                self._emit_run(start, ok=False, error=str(e)[:500])
                raise
            self._emit_run(start, ok=True, response_chars=len(response))
            return response

    def investigate_stream(
        self,
        user_message: str,
        context: str = "",
        thread_history: list | None = None,
        event_context: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Stream an investigation; ``event_context`` tags its events (channel, ids, ...)."""

        def run() -> Iterator[str]:
            start = time.monotonic()
            chars = 0
            try:
                for chunk in self.provider.investigate_stream(
                    user_message, context=context, thread_history=thread_history
                ):
                    chars += len(chunk)
                    yield chunk
            except GeneratorExit:
                self._emit_run(start, ok=False, interrupted=True, response_chars=chars)
                raise
            except Exception as e:
                self._emit_run(start, ok=False, error=str(e)[:500])
                raise
            self._emit_run(start, ok=True, response_chars=chars)

        yield from iterate_in_run_context(run, provider=self.provider_name, **(event_context or {}))

    @staticmethod
    def _emit_run(start: float, **fields: Any) -> None:
        emit("run", duration_ms=round((time.monotonic() - start) * 1000), **fields)


# Singleton instance
agent = Agent()
