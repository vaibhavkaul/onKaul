"""Response logger for monitoring and debugging investigations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from config import config


class ResponseLogger:
    """Logs responses that would be posted to Slack/Jira."""

    def __init__(self):
        self.log_file = config.RESPONSE_LOG_FILE

    def log_response(
        self,
        source: Literal["slack", "jira"],
        response: str,
        metadata: dict,
        investigation_duration_ms: float | None = None,
    ):
        """
        Log a response.

        Args:
            source: Where the response would be posted ("slack" or "jira")
            response: The response text
            metadata: Additional context (channel, issue_key, user_message, etc.)
            investigation_duration_ms: How long the investigation took
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "response": response,
            "investigation_duration_ms": investigation_duration_ms,
            **metadata,
        }

        # Console output (pretty)
        self._log_to_console(log_entry)

        # File output (JSONL)
        self._log_to_file(log_entry)

    def _log_to_console(self, entry: dict):
        """Print formatted log to console."""
        source = entry["source"].upper()
        timestamp = entry["timestamp"]
        duration = entry.get("investigation_duration_ms")

        print("\n" + "=" * 80)
        print(f"[{timestamp}] {source} RESPONSE")
        if duration:
            print(f"Duration: {duration:.2f}ms")
        print("-" * 80)

        if source == "SLACK":
            print(f"Channel: {entry.get('channel', 'N/A')}")
            print(f"Thread: {entry.get('thread_ts', 'N/A')}")
            print(f"User Message: {entry.get('user_message', 'N/A')}")
        elif source == "JIRA":
            print(f"Issue: {entry.get('issue_key', 'N/A')}")
            print(f"Author: {entry.get('author', 'N/A')}")
            print(f"Comment: {entry.get('comment_body', 'N/A')}")

        print("-" * 80)
        print(entry["response"])
        print("=" * 80 + "\n")

    def _log_to_file(self, entry: dict):
        """Append log entry to JSONL file."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


# Singleton instance
logger = ResponseLogger()
