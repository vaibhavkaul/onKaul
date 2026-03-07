"""Load repository configuration from JSON."""

from __future__ import annotations

import json
import os
import re
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


def repo_config_path() -> Path | None:
    """Return the resolved path to the active repo config file, or None if it doesn't exist."""
    path_str = os.getenv("REPO_CONFIG_PATH", "").strip()
    if not path_str:
        return None  # only the example file — don't write to it
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path


def parse_github_url(url: str) -> tuple[str, str]:
    """Return (org, repo_name) parsed from a GitHub URL."""
    url = url.strip().rstrip("/")
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    parts = url.split("/")
    return (parts[-2] if len(parts) >= 2 else ""), parts[-1].replace(".git", "")


def add_repo_to_config(key: str, entry: dict) -> None:
    """Persist a new repository entry to the active repo config JSON file."""
    path = repo_config_path()
    if path is None or not path.exists():
        raise RuntimeError("REPO_CONFIG_PATH is not set or does not exist — cannot persist repo.")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("repositories", {})[key] = entry
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
