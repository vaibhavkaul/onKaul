"""Monitoring configuration loaded from JSON."""

from repository_config.monitoring_loader import load_monitoring_config

_config = load_monitoring_config()

SENTRY_TEAMS = _config.get("sentry_teams", {})
DATADOG_SERVICES = _config.get("datadog_services", {})
DATADOG_TIERS = _config.get("datadog_tiers", {})
DATADOG_COMMON_TAGS = _config.get("datadog_common_tags", [])
DATADOG_METRIC_PREFIXES = _config.get("datadog_metric_prefixes", {})
QUEUE_TO_TEAM_MAPPING = _config.get("queue_to_team_mapping", {})
DATADOG_QUERY_PATTERNS = _config.get("datadog_query_patterns", {})
SENTRY_QUERY_PATTERNS = _config.get("sentry_query_patterns", {})


def get_sentry_team(team_key: str) -> dict:
    """Get Sentry team information."""
    return SENTRY_TEAMS.get(team_key, {})


def get_all_sentry_teams() -> dict:
    """Get all Sentry teams."""
    return SENTRY_TEAMS


def get_datadog_services_by_category(category: str) -> list:
    """Get Datadog services by category."""
    return DATADOG_SERVICES.get(category, [])


def get_datadog_query_pattern(pattern_name: str, **kwargs) -> str:
    """Get a common Datadog query pattern with substitutions."""
    pattern = DATADOG_QUERY_PATTERNS.get(pattern_name, "")
    return pattern.format(**kwargs) if pattern else ""
