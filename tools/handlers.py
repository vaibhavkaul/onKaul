"""Tool execution handlers."""

import json
import time

from clients.brave_search import brave_search
from clients.confluence import confluence
from clients.datadog import datadog
from clients.github import github
from clients.jira import jira
from clients.sentry import sentry
from repository_config.monitoring import MONITORING_CONFIG_ERROR, MONITORING_CONFIGURED
from repository_config.repositories import REPO_CONFIG_ERROR, REPO_CONFIGURED
from tools.local_code import list_directory_local, read_file_local, search_code_local
from utils.events import emit


def _repo_config_not_ready() -> dict | None:
    if REPO_CONFIGURED:
        return None
    return {
        "error": (
            "Repository config is not set. "
            f"{REPO_CONFIG_ERROR or 'Set REPO_CONFIG_PATH in .env to a valid config file.'}"
        )
    }


def _monitoring_config_not_ready() -> dict | None:
    if MONITORING_CONFIGURED:
        return None
    return {
        "error": (
            "Monitoring config is not set. "
            f"{MONITORING_CONFIG_ERROR or 'Set MONITORING_CONFIG_PATH in .env to a valid config file.'}"
        )
    }


def execute_tool(name: str, inputs: dict) -> str:
    """
    Execute a tool and return result as JSON string.

    Args:
        name: Tool name
        inputs: Tool input parameters

    Returns:
        JSON string with result
    """
    handlers = {
        "get_sentry_issue": _handle_get_sentry_issue,
        "search_code": _handle_search_code,
        "read_file": _handle_read_file,
        "list_directory": _handle_list_directory,
        "query_datadog_logs": _handle_query_datadog_logs,
        "list_datadog_monitors": _handle_list_datadog_monitors,
        "get_datadog_monitor": _handle_get_datadog_monitor,
        "query_datadog_metrics": _handle_query_datadog_metrics,
        "list_datadog_incidents": _handle_list_datadog_incidents,
        "search_datadog_events": _handle_search_datadog_events,
        "query_jira": _handle_query_jira,
        "get_jira_issue": _handle_get_jira_issue,
        "web_search": _handle_web_search,
        "close_pr": _handle_close_pr,
        "read_confluence_page": _handle_read_confluence_page,
    }

    handler = handlers.get(name)
    if not handler:
        emit("tool.call", tool=name, args=_audit_args(inputs), ok=False, error="unknown tool")
        return json.dumps({"error": f"Unknown tool: {name}"})

    start = time.monotonic()
    try:
        result = handler(**inputs)
    except Exception as e:
        emit(
            "tool.call",
            tool=name,
            args=_audit_args(inputs),
            duration_ms=round((time.monotonic() - start) * 1000),
            ok=False,
            error=str(e)[:500],
        )
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})

    output = json.dumps(result, indent=2)
    error = result.get("error") if isinstance(result, dict) else None
    emit(
        "tool.call",
        tool=name,
        args=_audit_args(inputs),
        duration_ms=round((time.monotonic() - start) * 1000),
        ok=not error,
        error=str(error)[:500] if error else None,
        result_chars=len(output),
    )
    return output


def _audit_args(inputs: dict) -> dict:
    """Tool arguments for the audit log, with long strings truncated."""
    return {
        key: value[:500] + "…" if isinstance(value, str) and len(value) > 500 else value
        for key, value in inputs.items()
    }


def _handle_get_sentry_issue(issue_id: str) -> dict:
    """Handle get_sentry_issue tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return sentry.get_issue(issue_id)


def _handle_search_code(repo: str, query: str) -> dict:
    """Handle search_code tool."""
    cfg_error = _repo_config_not_ready()
    if cfg_error:
        return cfg_error
    local_result = search_code_local(repo, query)
    if "error" not in local_result:
        return local_result
    return github.search_code(repo, query)


def _handle_read_file(repo: str, path: str, branch: str = "main") -> dict:
    """Handle read_file tool."""
    cfg_error = _repo_config_not_ready()
    if cfg_error:
        return cfg_error
    local_result = read_file_local(repo, path)
    if "error" not in local_result:
        return local_result
    return github.read_file(repo, path, branch)


def _handle_list_directory(repo: str, path: str) -> dict:
    """Handle list_directory tool."""
    cfg_error = _repo_config_not_ready()
    if cfg_error:
        return cfg_error
    local_result = list_directory_local(repo, path)
    if "error" not in local_result:
        return local_result
    return github.list_directory(repo, path)


def _handle_query_datadog_logs(query: str, timeframe: str = "1h", limit: int = 50) -> dict:
    """Handle query_datadog_logs tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return datadog.query_logs(query, timeframe, limit)


def _handle_list_datadog_monitors(tags: str | None = None) -> dict:
    """Handle list_datadog_monitors tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    tag_list = tags.split(",") if tags else None
    return datadog.list_monitors(tags=tag_list)


def _handle_get_datadog_monitor(monitor_id: int) -> dict:
    """Handle get_datadog_monitor tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return datadog.get_monitor(monitor_id)


def _handle_query_datadog_metrics(query: str, timeframe: str = "1h") -> dict:
    """Handle query_datadog_metrics tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return datadog.query_metrics(query, timeframe)


def _handle_list_datadog_incidents(query: str = "state:active") -> dict:
    """Handle list_datadog_incidents tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return datadog.list_incidents(query)


def _handle_search_datadog_events(query: str, timeframe: str = "1h") -> dict:
    """Handle search_datadog_events tool."""
    cfg_error = _monitoring_config_not_ready()
    if cfg_error:
        return cfg_error
    return datadog.search_events(query, timeframe)


def _handle_query_jira(jql: str) -> dict:
    """Handle query_jira tool."""
    return jira.query_issues(jql)


def _handle_get_jira_issue(issue_key: str) -> dict:
    """Handle get_jira_issue tool."""
    return jira.get_issue(issue_key)


def _handle_web_search(query: str, count: int = 5) -> dict:
    """Handle web_search tool using Brave Search API."""
    return brave_search.search(query, count)


def _handle_close_pr(pr_url: str) -> dict:
    """Handle close_pr tool."""
    return github.close_pr(pr_url)


def _handle_read_confluence_page(page_id: str) -> dict:
    """Handle read_confluence_page tool."""
    # Extract page ID from URL if full URL provided
    import re

    match = re.search(r"pages/(\d+)", page_id)
    if match:
        page_id = match.group(1)

    return confluence.read_page(page_id)
