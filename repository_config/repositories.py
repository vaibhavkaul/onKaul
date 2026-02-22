"""Repository configuration loader."""

from __future__ import annotations

from repository_config.loader import load_repo_config

_config = load_repo_config()

REPOSITORIES = _config["repositories"]
INVESTIGATION_STRATEGY = _config["investigation_strategy"]
ADDITIONAL_CONTEXT = _config["additional_context"]


def get_repository_info(repo_name: str) -> dict:
    """Get information about a specific repository."""
    return REPOSITORIES.get(repo_name, {})


def get_all_repositories() -> dict:
    """Get all repository configurations."""
    return REPOSITORIES


def get_investigation_strategy() -> dict:
    """Get mapping of issue types to repositories."""
    return INVESTIGATION_STRATEGY


def get_additional_context() -> dict:
    """Get mapping of additional context sources."""
    return ADDITIONAL_CONTEXT
