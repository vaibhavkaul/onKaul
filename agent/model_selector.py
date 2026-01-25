"""Smart model selection based on task type."""

import re


class ModelSelector:
    """Select appropriate Claude model based on task complexity."""

    # Model configurations
    MODELS = {
        "opus": {
            "id": "claude-opus-4-5-20251101",
            "name": "Opus 4.5",
            "max_tokens": 16384,
            "best_for": "Deep research, complex reasoning, architectural analysis",
        },
        "sonnet_thinking": {
            "id": "claude-sonnet-4-5-20241022",
            "name": "Sonnet 4.5 (Extended Thinking)",
            "max_tokens": 8192,
            "thinking_budget": 10000,
            "best_for": "Complex debugging, multi-step reasoning",
        },
        "sonnet": {
            "id": "claude-sonnet-4-20250514",
            "name": "Sonnet 4",
            "max_tokens": 8192,
            "best_for": "Standard investigations, quick analysis",
        },
    }

    # Keywords that indicate deep research tasks
    DEEP_RESEARCH_KEYWORDS = [
        "architecture",
        "architectural",
        "design pattern",
        "how does",
        "explain how",
        "understand",
        "deep dive",
        "comprehensive",
        "thorough",
        "analyze the design",
        "system design",
        "data flow",
        "explain the implementation",
        "how is this implemented",
        "walk me through",
    ]

    # Keywords for complex debugging
    COMPLEX_DEBUG_KEYWORDS = [
        "why is this happening",
        "root cause",
        "trace the flow",
        "debug this",
        "find the bug",
        "complex issue",
        "hard to reproduce",
        "intermittent",
    ]

    def select_model(self, user_message: str, context: str = "") -> dict:
        """
        Select appropriate model based on task.

        Args:
            user_message: User's question/request
            context: Additional context (thread, Jira, etc.)

        Returns:
            Dict with model config: {id, max_tokens, thinking_budget?}
        """
        combined_text = (user_message + " " + context).lower()

        # Check for deep research indicators
        if self._is_deep_research(combined_text):
            return {
                "id": self.MODELS["opus"]["id"],
                "name": self.MODELS["opus"]["name"],
                "max_tokens": self.MODELS["opus"]["max_tokens"],
                "reason": "Deep research/architectural task detected",
            }

        # Check for complex debugging
        if self._is_complex_debug(combined_text):
            return {
                "id": self.MODELS["sonnet_thinking"]["id"],
                "name": self.MODELS["sonnet_thinking"]["name"],
                "max_tokens": self.MODELS["sonnet_thinking"]["max_tokens"],
                "thinking": {"type": "enabled", "budget_tokens": 10000},
                "reason": "Complex debugging task detected",
            }

        # Default: Standard Sonnet for quick investigations
        return {
            "id": self.MODELS["sonnet"]["id"],
            "name": self.MODELS["sonnet"]["name"],
            "max_tokens": self.MODELS["sonnet"]["max_tokens"],
            "reason": "Standard investigation",
        }

    def _is_deep_research(self, text: str) -> bool:
        """Check if task requires deep research."""
        return any(keyword in text for keyword in self.DEEP_RESEARCH_KEYWORDS)

    def _is_complex_debug(self, text: str) -> bool:
        """Check if task requires complex debugging."""
        return any(keyword in text for keyword in self.COMPLEX_DEBUG_KEYWORDS)


# Singleton instance
model_selector = ModelSelector()
