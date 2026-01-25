"""Detect when questions require deep web research."""

import re


class ResearchDetector:
    """Detect questions that need deep web research vs. internal investigation."""

    # Keywords indicating external research needed
    RESEARCH_KEYWORDS = [
        # Competitive/market analysis
        "compare",
        "comparison",
        "versus",
        "vs",
        "alternative",
        "competitors",
        "competitive",
        "market research",
        "industry standard",
        # Service evaluation
        "should we use",
        "which service",
        "which tool",
        "evaluate",
        "pros and cons",
        "advantages",
        "disadvantages",
        # External knowledge
        "best practices",
        "what are the options",
        "what payment methods",
        "what remittance",
        "popular in",
        "commonly used",
        # Research indicators
        "research",
        "investigate options",
        "explore alternatives",
    ]

    # Keywords indicating INTERNAL work (NOT research)
    INTERNAL_KEYWORDS = [
        "our code",
        "our system",
        "appian-frontend",
        "appian-server",
        "tts-business",
        "sentry issue",
        "datadog",
        "bug",
        "error",
        "crash",
        "broken",
        "not working",
    ]

    def is_research_question(self, message: str, context: str = "") -> bool:
        """
        Determine if question requires deep web research.

        Args:
            message: User's message
            context: Thread/issue context

        Returns:
            True if deep research needed
        """
        combined = (message + " " + context).lower()

        # If it's about internal systems, NOT research
        if any(keyword in combined for keyword in self.INTERNAL_KEYWORDS):
            return False

        # If it has research keywords, likely research
        if any(keyword in combined for keyword in self.RESEARCH_KEYWORDS):
            return True

        return False

    def parse_confirmation(self, message: str) -> str | None:
        """
        Parse user's confirmation response.

        Args:
            message: User's message

        Returns:
            'yes', 'no', or None (unclear)
        """
        text = message.lower().strip()

        # Remove @mention
        text = re.sub(r"<@\w+>", "", text).strip()
        text = re.sub(r"@\w+", "", text).strip()

        # Affirmative
        affirmative = [
            "yes",
            "yeah",
            "yep",
            "sure",
            "go for it",
            "do it",
            "proceed",
            "go ahead",
            "please",
            "ok",
            "okay",
            "sounds good",
            "let's do it",
            "confirm",
        ]

        # Negative
        negative = ["no", "nope", "don't", "skip", "cancel", "nevermind", "stop"]

        for word in affirmative:
            if word in text:
                return "yes"

        for word in negative:
            if word in text:
                return "no"

        return None  # Unclear

    def already_requested_confirmation(self, bot_messages: list) -> bool:
        """
        Check if bot already asked for research confirmation in thread.

        Args:
            bot_messages: List of bot's own messages in thread

        Returns:
            True if confirmation already requested
        """
        for msg in bot_messages:
            text = msg.lower()
            if "deep research" in text and "should i proceed" in text:
                return True
            if "requires deep research" in text:
                return True

        return False

    def already_completed_research(self, bot_messages: list) -> bool:
        """
        Check if bot already completed research in thread.

        Args:
            bot_messages: List of bot's own messages in thread

        Returns:
            True if research already done
        """
        for msg in bot_messages:
            text = msg.lower()
            if "research complete" in text:
                return True
            if "deep research complete" in text:
                return True

        return False


# Singleton instance
research_detector = ResearchDetector()
