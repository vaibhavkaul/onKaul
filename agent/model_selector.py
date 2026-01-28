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
        "review",  # PR reviews need deep analysis
        "pull request",
        "github.com/",  # PR URLs
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

        # Check for deep research or complex debugging - use Opus for both
        if self._is_deep_research(combined_text) or self._is_complex_debug(combined_text):
            reason = "Deep research/architectural task" if self._is_deep_research(combined_text) else "Complex debugging task"
            return {
                "id": self.MODELS["opus"]["id"],
                "name": self.MODELS["opus"]["name"],
                "max_tokens": self.MODELS["opus"]["max_tokens"],
                "reason": reason,
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
