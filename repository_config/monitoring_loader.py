"""Load monitoring configuration from JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_monitoring_config() -> dict:
    """
    Load monitoring configuration from a JSON file.

    Env:
      MONITORING_CONFIG_PATH: Path to JSON config
    """
    path_str = os.getenv("MONITORING_CONFIG_PATH", "").strip()
    if not path_str:
        path_str = "./repository_config/monitoring_config_example.json"

    path = Path(path_str)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parents[1]
        path = base_dir / path

    if not path.exists():
        return {
            "sentry_teams": {},
            "datadog_services": {},
            "datadog_tiers": {},
            "datadog_common_tags": [],
            "datadog_metric_prefixes": {},
            "queue_to_team_mapping": {},
            "datadog_query_patterns": {},
            "sentry_query_patterns": {},
            "_configured": False,
            "_error": (
                f"MONITORING_CONFIG_PATH does not exist: {path}. "
                "Set MONITORING_CONFIG_PATH to an existing file "
                "(for example repository_config/monitoring_config_example.json)."
            ),
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {
            "sentry_teams": {},
            "datadog_services": {},
            "datadog_tiers": {},
            "datadog_common_tags": [],
            "datadog_metric_prefixes": {},
            "queue_to_team_mapping": {},
            "datadog_query_patterns": {},
            "sentry_query_patterns": {},
            "_configured": False,
            "_error": f"Failed to parse MONITORING_CONFIG_PATH ({path}): {exc}",
        }

    if not isinstance(data, dict):
        return {
            "sentry_teams": {},
            "datadog_services": {},
            "datadog_tiers": {},
            "datadog_common_tags": [],
            "datadog_metric_prefixes": {},
            "queue_to_team_mapping": {},
            "datadog_query_patterns": {},
            "sentry_query_patterns": {},
            "_configured": False,
            "_error": "Monitoring config JSON must be an object at top level.",
        }

    loaded = {
        "sentry_teams": data.get("sentry_teams", {}),
        "datadog_services": data.get("datadog_services", {}),
        "datadog_tiers": data.get("datadog_tiers", {}),
        "datadog_common_tags": data.get("datadog_common_tags", []),
        "datadog_metric_prefixes": data.get("datadog_metric_prefixes", {}),
        "queue_to_team_mapping": data.get("queue_to_team_mapping", {}),
        "datadog_query_patterns": data.get("datadog_query_patterns", {}),
        "sentry_query_patterns": data.get("sentry_query_patterns", {}),
        "_configured": False,
        "_error": "",
    }
    loaded["_configured"] = bool(loaded["sentry_teams"] or loaded["datadog_tiers"])
    if not loaded["_configured"]:
        loaded["_error"] = (
            "Monitoring config is empty. Populate sentry_teams/datadog_tiers or "
            "point MONITORING_CONFIG_PATH to a valid config file."
        )
    return loaded
