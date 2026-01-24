"""Tool execution handlers."""

import json

from clients.datadog import datadog
from clients.github import github
from clients.jira import jira
from clients.sentry import sentry
from clients.websearch import web_search


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
        "query_jira": _handle_query_jira,
        "get_jira_issue": _handle_get_jira_issue,
        "web_search": _handle_web_search,
    }

    handler = handlers.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = handler(**inputs)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


def _handle_get_sentry_issue(issue_id: str) -> dict:
    """Handle get_sentry_issue tool."""
    return sentry.get_issue(issue_id)


def _handle_search_code(repo: str, query: str) -> dict:
    """Handle search_code tool."""
    return github.search_code(repo, query)


def _handle_read_file(repo: str, path: str, branch: str = "main") -> dict:
    """Handle read_file tool."""
    return github.read_file(repo, path, branch)


def _handle_list_directory(repo: str, path: str) -> dict:
    """Handle list_directory tool."""
    return github.list_directory(repo, path)


def _handle_query_datadog_logs(query: str, timeframe: str = "1h") -> dict:
    """Handle query_datadog_logs tool."""
    return datadog.query_logs(query, timeframe)


def _handle_query_jira(jql: str) -> dict:
    """Handle query_jira tool."""
    return jira.query_issues(jql)


def _handle_get_jira_issue(issue_key: str) -> dict:
    """Handle get_jira_issue tool."""
    return jira.get_issue(issue_key)


def _handle_web_search(query: str) -> dict:
    """Handle web_search tool using Google Custom Search."""
    return web_search.search(query)
