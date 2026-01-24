"""Datadog API client."""

import httpx

from config import config


class DatadogClient:
    """Client for Datadog API."""

    def __init__(self):
        self.base_url = "https://api.datadoghq.com/api/v2"
        self.api_key = config.DATADOG_API_KEY
        self.app_key = config.DATADOG_APP_KEY
        self.headers = {}
        if self.api_key and self.app_key:
            self.headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
            }

    def query_logs(self, query: str, timeframe: str = "1h") -> dict:
        """
        Query Datadog logs.

        Args:
            query: Datadog log query
            timeframe: Time range (e.g., '1h', '24h', '7d')

        Returns:
            Dict with log entries
        """
        if not self.api_key or not self.app_key:
            return {"error": "DATADOG_API_KEY or DATADOG_APP_KEY not configured"}

        try:
            # Convert timeframe to milliseconds
            timeframe_ms = self._parse_timeframe(timeframe)
            from_time = f"now-{timeframe}"

            response = httpx.post(
                f"{self.base_url}/logs/events/search",
                headers=self.headers,
                json={
                    "filter": {
                        "query": query,
                        "from": from_time,
                        "to": "now",
                    },
                    "page": {"limit": 50},
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            logs = []
            for log in data.get("data", []):
                attrs = log.get("attributes", {})
                logs.append(
                    {
                        "timestamp": attrs.get("timestamp"),
                        "message": attrs.get("message"),
                        "status": attrs.get("status"),
                        "service": attrs.get("service"),
                    }
                )

            return {"logs": logs, "total": len(logs)}

        except httpx.HTTPStatusError as e:
            return {"error": f"Datadog API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to query logs: {str(e)}"}

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to milliseconds."""
        # Simplified - Datadog API handles relative time strings
        return 0


# Singleton instance
datadog = DatadogClient()
