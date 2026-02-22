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
        path_str = "./repository_config/repo_config.json"

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"REPO_CONFIG_PATH does not exist: {path}"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Repo config JSON must be an object at top level.")

    repositories = data.get("repositories")
    if not isinstance(repositories, dict) or not repositories:
        raise ValueError("Repo config must include non-empty 'repositories' object.")

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
    }
