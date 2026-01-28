"""Tool execution handlers."""

import json

from clients.confluence import confluence
from clients.datadog import datadog
from clients.github import github
from clients.jira import jira
from clients.sentry import sentry
from tools.legal import get_compliance_rules
from tools.pr_review import review_github_pr


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
        "get_legal_compliance_rules": _handle_get_legal_compliance_rules,
        "review_github_pr": _handle_review_github_pr,
        "read_confluence_page": _handle_read_confluence_page,
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


def _handle_query_datadog_logs(query: str, timeframe: str = "1h", limit: int = 50) -> dict:
    """Handle query_datadog_logs tool."""
    return datadog.query_logs(query, timeframe, limit)


def _handle_list_datadog_monitors(tags: str | None = None) -> dict:
    """Handle list_datadog_monitors tool."""
    tag_list = tags.split(",") if tags else None
    return datadog.list_monitors(tags=tag_list)


def _handle_get_datadog_monitor(monitor_id: int) -> dict:
    """Handle get_datadog_monitor tool."""
    return datadog.get_monitor(monitor_id)


def _handle_query_datadog_metrics(query: str, timeframe: str = "1h") -> dict:
    """Handle query_datadog_metrics tool."""
    return datadog.query_metrics(query, timeframe)


def _handle_list_datadog_incidents(query: str = "state:active") -> dict:
    """Handle list_datadog_incidents tool."""
    return datadog.list_incidents(query)


def _handle_search_datadog_events(query: str, timeframe: str = "1h") -> dict:
    """Handle search_datadog_events tool."""
    return datadog.search_events(query, timeframe)


def _handle_query_jira(jql: str) -> dict:
    """Handle query_jira tool."""
    return jira.query_issues(jql)


def _handle_get_jira_issue(issue_key: str) -> dict:
    """Handle get_jira_issue tool."""
    return jira.get_issue(issue_key)


def _handle_web_search(query: str) -> dict:
    """
    Handle web_search tool.

    Placeholder - not implemented.
    """
    return {
        "message": "Web search not implemented",
        "query": query,
        "suggestion": "Try searching manually or use GitHub search for code",
    }


def _handle_get_legal_compliance_rules(category: str = "all") -> dict:
    """Handle get_legal_compliance_rules tool."""
    return get_compliance_rules(category)


def _handle_review_github_pr(pr_url: str) -> dict:
    """Handle review_github_pr tool."""
    return review_github_pr(pr_url)


def _handle_read_confluence_page(page_id: str) -> dict:
    """Handle read_confluence_page tool."""
    # Extract page ID from URL if full URL provided
    import re
    match = re.search(r"pages/(\d+)", page_id)
    if match:
        page_id = match.group(1)

    return confluence.read_page(page_id)
