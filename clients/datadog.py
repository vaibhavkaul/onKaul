"""Comprehensive Datadog client using official SDK."""

from datetime import datetime, timedelta

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.api.metrics_api import MetricsApi
from datadog_api_client.v2.api.incidents_api import IncidentsApi
from datadog_api_client.v2.api.events_api import EventsApi

from config import config


class DatadogClient:
    """Comprehensive Datadog client for logs, monitors, metrics, traces, incidents."""

    def __init__(self):
        self.api_key = config.DATADOG_API_KEY
        self.app_key = config.DATADOG_APP_KEY
        self.site = config.DATADOG_SITE

        # Configure API client
        if self.api_key and self.app_key:
            configuration = Configuration()
            configuration.api_key["apiKeyAuth"] = self.api_key
            configuration.api_key["appKeyAuth"] = self.app_key
            configuration.server_variables["site"] = self.site
            # Enable unstable operations
            configuration.unstable_operations["list_incidents"] = True

            self.api_client = ApiClient(configuration)
            self.logs_api = LogsApi(self.api_client)
            self.monitors_api = MonitorsApi(self.api_client)
            self.metrics_api = MetricsApi(self.api_client)
            self.incidents_api = IncidentsApi(self.api_client)
            self.events_api = EventsApi(self.api_client)
        else:
            self.api_client = None

    # ============================================================================
    # LOGS
    # ============================================================================

    def query_logs(self, query: str, timeframe: str = "1h", limit: int = 50) -> dict:
        """
        Query Datadog logs.

        Args:
            query: Datadog log query (e.g., 'status:error service:api')
            timeframe: Time range (e.g., '1h', '24h', '7d')
            limit: Max results (default: 50)

        Returns:
            Dict with log entries
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured (DD_API_KEY, DD_APP_KEY in ~/.zshrc)"}

        try:
            # Calculate time range
            now = datetime.now()
            from_time = self._parse_timeframe(timeframe)

            # Build request
            from datadog_api_client.v2.model.logs_list_request import LogsListRequest
            from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
            from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter

            body = LogsListRequest(
                filter=LogsQueryFilter(
                    query=query,
                    _from=from_time.isoformat() + "Z",
                    to=now.isoformat() + "Z",
                ),
                page=LogsListRequestPage(limit=limit),
            )

            # Query logs
            response = self.logs_api.list_logs(body=body)

            logs = []
            for log in response.data or []:
                attrs = log.attributes
                logs.append(
                    {
                        "timestamp": attrs.timestamp.isoformat() if attrs.timestamp else None,
                        "message": attrs.message if attrs.message else "",
                        "status": attrs.status if attrs.status else "unknown",
                        "service": attrs.service if attrs.service else "unknown",
                        "tags": attrs.tags if attrs.tags else [],
                    }
                )

            return {"logs": logs, "total": len(logs), "query": query, "timeframe": timeframe}

        except Exception as e:
            return {"error": f"Failed to query logs: {str(e)}"}

    # ============================================================================
    # MONITORS
    # ============================================================================

    def list_monitors(self, tags: list[str] | None = None, monitor_tags: list[str] | None = None) -> dict:
        """
        List Datadog monitors.

        Args:
            tags: Filter by tags (e.g., ['env:prod', 'team:backend'])
            monitor_tags: Filter by monitor tags

        Returns:
            Dict with monitors
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured"}

        try:
            # Build kwargs only if values are present
            kwargs = {}
            if tags:
                kwargs["tags"] = ",".join(tags)
            if monitor_tags:
                kwargs["monitor_tags"] = ",".join(monitor_tags)

            monitors = self.monitors_api.list_monitors(**kwargs)

            results = []
            for monitor in monitors:
                results.append(
                    {
                        "id": monitor.id,
                        "name": monitor.name,
                        "type": str(monitor.type),  # Convert enum to string
                        "query": monitor.query,
                        "message": monitor.message if monitor.message else "",
                        "tags": monitor.tags if monitor.tags else [],
                        "overall_state": str(monitor.overall_state) if hasattr(monitor, "overall_state") else None,
                    }
                )

            return {"monitors": results, "total": len(results)}

        except Exception as e:
            return {"error": f"Failed to list monitors: {str(e)}"}

    def get_monitor(self, monitor_id: int) -> dict:
        """
        Get monitor details.

        Args:
            monitor_id: Monitor ID

        Returns:
            Dict with monitor details
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured"}

        try:
            monitor = self.monitors_api.get_monitor(monitor_id)

            return {
                "id": monitor.id,
                "name": monitor.name,
                "type": str(monitor.type),  # Convert enum to string
                "query": monitor.query,
                "message": monitor.message if monitor.message else "",
                "tags": monitor.tags if monitor.tags else [],
                "options": str(monitor.options) if monitor.options else None,
                "overall_state": str(monitor.overall_state) if hasattr(monitor, "overall_state") else None,
                "created": monitor.created.isoformat() if monitor.created else None,
                "modified": monitor.modified.isoformat() if monitor.modified else None,
            }

        except Exception as e:
            return {"error": f"Failed to get monitor: {str(e)}"}

    # ============================================================================
    # METRICS
    # ============================================================================

    def query_metrics(self, query: str, from_time: str = "1h") -> dict:
        """
        Query Datadog metrics.

        Args:
            query: Metric query (e.g., 'avg:system.cpu.user{*}')
            from_time: Time range (e.g., '1h', '24h')

        Returns:
            Dict with metric data
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured"}

        try:
            # Calculate time range
            now = datetime.now()
            from_dt = self._parse_timeframe(from_time)

            # Query metrics using v1 API (v2 metrics API is different)
            from datadog_api_client.v1.api.metrics_api import MetricsApi as MetricsApiV1

            metrics_v1 = MetricsApiV1(self.api_client)
            response = metrics_v1.query_metrics(
                _from=int(from_dt.timestamp()),
                to=int(now.timestamp()),
                query=query,
            )

            series = []
            if response.series:
                for s in response.series:
                    series.append(
                        {
                            "metric": s.metric if hasattr(s, "metric") else query,
                            "points": s.pointlist[:10] if hasattr(s, "pointlist") and s.pointlist else [],
                            "scope": s.scope if hasattr(s, "scope") else None,
                        }
                    )

            return {"series": series, "query": query}

        except Exception as e:
            return {"error": f"Failed to query metrics: {str(e)}"}

    # ============================================================================
    # INCIDENTS
    # ============================================================================

    def list_incidents(self, query: str = "state:active") -> dict:
        """
        List Datadog incidents.

        Args:
            query: Filter query - currently only supports filtering by 'state:active' or 'state:stable'
                   (Note: Filtering is done client-side after fetching)

        Returns:
            Dict with incidents
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured"}

        try:
            # Note: list_incidents doesn't support query params - we filter client-side
            response = self.incidents_api.list_incidents(page_size=100)

            incidents = []
            if hasattr(response, "data") and response.data:
                for incident in response.data:
                    attrs = incident.attributes if hasattr(incident, "attributes") else None
                    if attrs:
                        # Client-side filtering by state if requested
                        state = str(attrs.state).lower() if hasattr(attrs, "state") else ""

                        # Parse query (simple state:value filter)
                        if "state:" in query.lower():
                            requested_state = query.lower().split("state:")[1].strip()
                            if requested_state not in state:
                                continue  # Skip if doesn't match filter

                        incidents.append(
                            {
                                "id": incident.id,
                                "title": attrs.title if hasattr(attrs, "title") else "Unknown",
                                "severity": str(attrs.severity) if hasattr(attrs, "severity") else None,
                                "state": state,
                                "created": attrs.created.isoformat() if hasattr(attrs, "created") and attrs.created else None,
                            }
                        )

            return {"incidents": incidents, "total": len(incidents)}

        except Exception as e:
            return {"error": f"Failed to list incidents: {str(e)}"}

    # ============================================================================
    # EVENTS
    # ============================================================================

    def search_events(self, query: str, timeframe: str = "1h") -> dict:
        """
        Search Datadog events (deployments, config changes).

        Args:
            query: Event query
            timeframe: Time range

        Returns:
            Dict with events
        """
        if not self.api_client:
            return {"error": "Datadog API keys not configured"}

        try:
            from datadog_api_client.v2.model.events_list_request import EventsListRequest
            from datadog_api_client.v2.model.events_query_filter import EventsQueryFilter
            from datadog_api_client.v2.model.events_request_page import EventsRequestPage

            # Calculate time range
            now = datetime.now()
            from_dt = self._parse_timeframe(timeframe)

            body = EventsListRequest(
                filter=EventsQueryFilter(
                    query=query,
                    _from=from_dt.isoformat() + "Z",
                    to=now.isoformat() + "Z",
                ),
                page=EventsRequestPage(limit=50),
            )

            response = self.events_api.search_events(body=body)

            events = []
            if hasattr(response, "data") and response.data:
                for event in response.data:
                    attrs = event.attributes if hasattr(event, "attributes") else None
                    if attrs:
                        events.append(
                            {
                                "id": event.id if hasattr(event, "id") else None,
                                "title": attrs.title if hasattr(attrs, "title") else "Unknown",
                                "text": attrs.text if hasattr(attrs, "text") else "",
                                "timestamp": attrs.timestamp.isoformat() if hasattr(attrs, "timestamp") and attrs.timestamp else None,
                                "tags": attrs.tags if hasattr(attrs, "tags") else [],
                            }
                        )

            return {"events": events, "total": len(events)}

        except Exception as e:
            return {"error": f"Failed to search events: {str(e)}"}

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _parse_timeframe(self, timeframe: str) -> datetime:
        """Parse timeframe string (e.g., '1h', '24h', '7d') to datetime."""
        now = datetime.now()

        # Parse format: <number><unit> where unit is m/h/d
        import re

        match = re.match(r"(\d+)([mhd])", timeframe)
        if not match:
            # Default to 1 hour
            return now - timedelta(hours=1)

        value = int(match.group(1))
        unit = match.group(2)

        if unit == "m":
            return now - timedelta(minutes=value)
        elif unit == "h":
            return now - timedelta(hours=value)
        elif unit == "d":
            return now - timedelta(days=value)

        return now - timedelta(hours=1)


# Singleton instance
datadog = DatadogClient()
