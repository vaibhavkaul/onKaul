"""Load repository configuration from JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_repo_config() -> dict:
    """
    Load repo configuration from a JSON file.

    Env:
      REPO_CONFIG_PATH: Path to JSON config
    """
    path_str = os.getenv("REPO_CONFIG_PATH", "").strip()
    if not path_str:
        path_str = "./repository_config/repo_config_example.json"

    path = Path(path_str)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parents[1]
        path = base_dir / path

    if not path.exists():
        return {
            "repositories": {},
            "investigation_strategy": {},
            "additional_context": {},
            "_configured": False,
            "_error": (
                f"REPO_CONFIG_PATH does not exist: {path}. "
                "Set REPO_CONFIG_PATH to an existing file "
                "(for example repository_config/repo_config_example.json)."
            ),
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {
            "repositories": {},
            "investigation_strategy": {},
            "additional_context": {},
            "_configured": False,
            "_error": f"Failed to parse REPO_CONFIG_PATH ({path}): {exc}",
        }

    if not isinstance(data, dict):
        return {
            "repositories": {},
            "investigation_strategy": {},
            "additional_context": {},
            "_configured": False,
            "_error": "Repo config JSON must be an object at top level.",
        }

    repositories = data.get("repositories")
    if not isinstance(repositories, dict):
        return {
            "repositories": {},
            "investigation_strategy": {},
            "additional_context": {},
            "_configured": False,
            "_error": "Repo config must include a 'repositories' object.",
        }

    investigation_strategy = data.get("investigation_strategy", {})
    if investigation_strategy is None:
        investigation_strategy = {}

    additional_context = data.get("additional_context", {})
    if additional_context is None:
        additional_context = {}

    return {
        "repositories": repositories,
        "investigation_strategy": investigation_strategy,
        "additional_context": additional_context,
        "_configured": bool(repositories),
        "_error": ""
        if repositories
        else "Repo config is empty. Add repositories or point to a valid config file.",
    }
