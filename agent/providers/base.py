"""Provider interface for core onKaul investigations."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class AgentProvider(Protocol):
    """Common contract for core investigation providers."""

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        """Run investigation and return final response."""

    def investigate_stream(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> Iterator[str]:
        """Run investigation and stream response text chunks."""
