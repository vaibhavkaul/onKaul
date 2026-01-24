"""Sentry API client."""

import httpx

from config import config


class SentryClient:
    """Client for Sentry API."""

    def __init__(self):
        self.base_url = "https://sentry.io/api/0"
        self.token = config.SENTRY_TOKEN
        self.org = config.SENTRY_ORG
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get_issue(self, issue_id: str) -> dict:
        """
        Fetch Sentry issue details.

        Args:
            issue_id: Sentry issue ID

        Returns:
            Dict with title, stacktrace, frequency, etc.
        """
        if not self.token:
            return {"error": "SENTRY_TOKEN not configured"}

        try:
            # Fetch issue details
            response = httpx.get(
                f"{self.base_url}/issues/{issue_id}/",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Fetch latest event for stacktrace
            event_response = httpx.get(
                f"{self.base_url}/issues/{issue_id}/events/latest/",
                headers=self.headers,
                timeout=10.0,
            )
            event_response.raise_for_status()
            latest_event = event_response.json()

            return {
                "title": data.get("title", "Unknown"),
                "culprit": data.get("culprit", "Unknown"),
                "first_seen": data.get("firstSeen"),
                "last_seen": data.get("lastSeen"),
                "count": data.get("count", 0),
                "user_count": data.get("userCount", 0),
                "permalink": data.get("permalink"),
                "level": data.get("level", "error"),
                "status": data.get("status", "unresolved"),
                "stacktrace": self._extract_stacktrace(latest_event),
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"Sentry API error: {e.response.status_code} {e.response.text}"}
        except Exception as e:
            return {"error": f"Failed to fetch Sentry issue: {str(e)}"}

    def _extract_stacktrace(self, event: dict) -> str:
        """Extract readable stacktrace from event."""
        try:
            entries = event.get("entries", [])
            for entry in entries:
                if entry.get("type") == "exception":
                    values = entry.get("data", {}).get("values", [])
                    if values:
                        frames = values[0].get("stacktrace", {}).get("frames", [])
                        if frames:
                            return self._format_frames(frames[-10:])  # Last 10 frames
            return "No stacktrace available"
        except Exception:
            return "Error parsing stacktrace"

    def _format_frames(self, frames: list) -> str:
        """Format stacktrace frames."""
        lines = []
        for frame in reversed(frames):
            filename = frame.get("filename", "?")
            lineno = frame.get("lineNo", "?")
            function = frame.get("function", "?")
            context = frame.get("context_line", "").strip()
            lines.append(f"  {filename}:{lineno} in {function}")
            if context:
                lines.append(f"    {context}")
        return "\n".join(lines)


# Singleton instance
sentry = SentryClient()
