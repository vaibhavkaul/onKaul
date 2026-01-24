"""Slack client for posting messages."""

import httpx

from config import config


class SlackClient:
    """Client for Slack API."""

    def __init__(self):
        self.base_url = "https://slack.com/api"
        self.token = config.SLACK_BOT_TOKEN
        self.headers = {}
        if self.token:
            self.headers = {"Authorization": f"Bearer {self.token}"}

    def get_thread(self, channel: str, thread_ts: str) -> dict:
        """
        Fetch thread messages for context.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp

        Returns:
            Dict with messages list or error
        """
        if not self.token:
            return {"error": "SLACK_BOT_TOKEN not configured", "messages": []}

        try:
            response = httpx.get(
                f"{self.base_url}/conversations.replies",
                headers=self.headers,
                params={"channel": channel, "ts": thread_ts},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                return {"error": f"Slack API error: {data.get('error')}", "messages": []}

            messages = data.get("messages", [])
            return {"messages": messages, "success": True}

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "messages": []}
        except Exception as e:
            return {"error": f"Failed to fetch thread: {str(e)}", "messages": []}

    def add_reaction(self, channel: str, timestamp: str, emoji: str) -> dict:
        """
        Add emoji reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name without colons (e.g., 'onkaul', 'eyes', 'rocket')

        Returns:
            Dict with success/error status
        """
        if not self.token:
            return {"error": "SLACK_BOT_TOKEN not configured", "success": False}

        try:
            response = httpx.post(
                f"{self.base_url}/reactions.add",
                headers=self.headers,
                json={
                    "channel": channel,
                    "timestamp": timestamp,
                    "name": emoji,
                },
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                error = data.get("error", "unknown")
                # Ignore "already_reacted" error - it's fine
                if error == "already_reacted":
                    return {"success": True, "message": "Already reacted"}
                return {"error": f"Slack API error: {error}", "success": False}

            return {"success": True, "message": f"Added :{emoji}: reaction"}

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "success": False}
        except Exception as e:
            return {"error": f"Failed to add reaction: {str(e)}", "success": False}

    def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> dict:
        """
        Post a message to a Slack channel.

        Args:
            channel: Channel ID (e.g., 'C123456')
            text: Message text
            thread_ts: Thread timestamp to reply in thread (optional)

        Returns:
            Dict with success/error status
        """
        if not self.token:
            return {"error": "SLACK_BOT_TOKEN not configured", "success": False}

        try:
            payload = {
                "channel": channel,
                "text": text,
            }

            # Reply in thread if thread_ts provided
            if thread_ts:
                payload["thread_ts"] = thread_ts

            response = httpx.post(
                f"{self.base_url}/chat.postMessage",
                headers=self.headers,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                return {"error": f"Slack API error: {data.get('error')}", "success": False}

            return {
                "success": True,
                "message": f"Message posted to channel {channel}",
                "ts": data.get("ts"),
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "success": False}
        except Exception as e:
            return {"error": f"Failed to post message: {str(e)}", "success": False}


# Singleton instance
slack = SlackClient()
