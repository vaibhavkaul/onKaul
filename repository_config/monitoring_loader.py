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
        path_str = "./repository_config/monitoring_config.json"

    path = Path(path_str)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parents[1]
        path = base_dir / path

    if not path.exists():
        raise FileNotFoundError(
            f"MONITORING_CONFIG_PATH does not exist: {path}. "
            "Create repository_config/monitoring_config.json (copy from monitoring_config_example.json)."
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Monitoring config JSON must be an object at top level.")

    return {
        "sentry_teams": data.get("sentry_teams", {}),
        "datadog_services": data.get("datadog_services", {}),
        "datadog_tiers": data.get("datadog_tiers", {}),
        "datadog_common_tags": data.get("datadog_common_tags", []),
        "datadog_metric_prefixes": data.get("datadog_metric_prefixes", {}),
        "queue_to_team_mapping": data.get("queue_to_team_mapping", {}),
        "datadog_query_patterns": data.get("datadog_query_patterns", {}),
        "sentry_query_patterns": data.get("sentry_query_patterns", {}),
    }
