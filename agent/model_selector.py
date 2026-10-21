"""Smart model selection based on task type."""

from config import config


class ModelSelector:
    """Select appropriate model based on task complexity and provider."""

    def __init__(self):
        # Model configurations by provider.
        self.models = {
            "anthropic": {
                # Current models always think, and thinking counts toward
                # max_tokens. Opus 5.5 defaults to medium effort, so the deep
                # tier asks for high explicitly.
                "deep": {
                    "id": config.ANTHROPIC_REASONING_MODEL or "claude-opus-5-5",
                    "name": "Opus 5.5",
                    "max_tokens": 16384,
                    "effort": "high",
                    "best_for": "Deep research, complex reasoning, architectural analysis",
                },
                "standard": {
                    "id": config.ANTHROPIC_MODEL or "claude-sonnet-5-5",
                    "name": "Sonnet 5.5",
                    "max_tokens": 16384,
                    "best_for": "Standard investigations, quick analysis",
                },
            },
            "openai": {
                "deep": {
                    "id": config.OPENAI_REASONING_MODEL or "gpt-6.1-sol",
                    "name": "GPT-6.1 Sol",
                    "best_for": "Deep research, complex reasoning, architectural analysis",
                },
                "standard": {
                    "id": config.OPENAI_MODEL or "gpt-6.1-sol",
                    "name": "GPT-6.1 Sol",
                    "best_for": "Standard investigations, quick analysis",
                },
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

    def select_model(
        self, user_message: str, context: str = "", provider: str = "anthropic"
    ) -> dict:
        """
        Select appropriate model based on task.

        Args:
            user_message: User's question/request
            context: Additional context (thread, Jira, etc.)
            provider: Model provider ("anthropic" or "openai")

        Returns:
            Dict with model config: {id, name, reason, max_tokens?, effort?}
        """
        combined_text = (user_message + " " + context).lower()
        provider_models = self.models.get(provider, self.models["anthropic"])
        use_deep_model = self._is_deep_research(combined_text) or self._is_complex_debug(
            combined_text
        )
        selected = provider_models["deep"] if use_deep_model else provider_models["standard"]

        # Check for deep research or complex debugging - use Opus for both
        reason = (
            "Deep research/architectural task"
            if self._is_deep_research(combined_text)
            else (
                "Complex debugging task"
                if self._is_complex_debug(combined_text)
                else "Standard investigation"
            )
        )
        return {
            "id": selected["id"],
            "name": selected["name"],
            "reason": reason,
            **({"max_tokens": selected["max_tokens"]} if "max_tokens" in selected else {}),
            **({"effort": selected["effort"]} if "effort" in selected else {}),
        }

    def _is_deep_research(self, text: str) -> bool:
        """Check if task requires deep research."""
        return any(keyword in text for keyword in self.DEEP_RESEARCH_KEYWORDS)

    def _is_complex_debug(self, text: str) -> bool:
        """Check if task requires complex debugging."""
        return any(keyword in text for keyword in self.COMPLEX_DEBUG_KEYWORDS)


# Singleton instance
model_selector = ModelSelector()
