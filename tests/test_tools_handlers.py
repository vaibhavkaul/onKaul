from __future__ import annotations

import json

from tools import handlers


def _loads(value: str) -> dict:
    return json.loads(value)


def test_execute_tool_unknown_tool_returns_error():
    result = _loads(handlers.execute_tool("missing_tool", {}))

    assert result["error"] == "Unknown tool: missing_tool"


def test_execute_tool_catches_tool_exceptions(monkeypatch):
    monkeypatch.setattr(
        handlers, "_handle_web_search", lambda **_kwargs: (_ for _ in ()).throw(ValueError("boom"))
    )

    result = _loads(handlers.execute_tool("web_search", {"query": "x"}))

    assert "Tool execution failed: boom" in result["error"]


def test_handle_search_code_uses_local_result_first(monkeypatch):
    monkeypatch.setattr(handlers, "REPO_CONFIGURED", True)
    monkeypatch.setattr(
        handlers, "search_code_local", lambda repo, query: {"matches": [f"{repo}:{query}"]}
    )
    monkeypatch.setattr(handlers.github, "search_code", lambda repo, query: {"matches": ["github"]})

    result = handlers._handle_search_code("repo-a", "needle")

    assert result == {"matches": ["repo-a:needle"]}


def test_handle_search_code_falls_back_to_github(monkeypatch):
    monkeypatch.setattr(handlers, "REPO_CONFIGURED", True)
    monkeypatch.setattr(handlers, "search_code_local", lambda repo, query: {"error": "not local"})
    monkeypatch.setattr(
        handlers.github, "search_code", lambda repo, query: {"matches": ["github-fallback"]}
    )

    result = handlers._handle_search_code("repo-a", "needle")

    assert result == {"matches": ["github-fallback"]}


def test_handle_search_code_returns_config_error_when_repo_not_ready(monkeypatch):
    monkeypatch.setattr(handlers, "REPO_CONFIGURED", False)
    monkeypatch.setattr(handlers, "REPO_CONFIG_ERROR", "missing config")

    result = handlers._handle_search_code("repo-a", "needle")

    assert result["error"] == "Repository config is not set. missing config"


def test_handle_query_datadog_logs_returns_config_error(monkeypatch):
    monkeypatch.setattr(handlers, "MONITORING_CONFIGURED", False)
    monkeypatch.setattr(handlers, "MONITORING_CONFIG_ERROR", "missing monitor config")

    result = handlers._handle_query_datadog_logs("service:api")

    assert result["error"] == "Monitoring config is not set. missing monitor config"


def test_handle_read_confluence_page_extracts_id_from_url(monkeypatch):
    called = {"page_id": None}

    def _fake_read(page_id: str) -> dict:
        called["page_id"] = page_id
        return {"ok": True}

    monkeypatch.setattr(handlers.confluence, "read_page", _fake_read)

    result = handlers._handle_read_confluence_page(
        "https://example.atlassian.net/wiki/spaces/ENG/pages/123456789/Foo"
    )

    assert called["page_id"] == "123456789"
    assert result == {"ok": True}


def test_handle_read_file_local_first_then_github_fallback(monkeypatch):
    monkeypatch.setattr(handlers, "REPO_CONFIGURED", True)
    monkeypatch.setattr(handlers, "read_file_local", lambda repo, path: {"content": "local"})
    monkeypatch.setattr(handlers.github, "read_file", lambda repo, path, branch: {"content": "gh"})

    local = handlers._handle_read_file("repo-a", "a.txt")
    assert local["content"] == "local"

    monkeypatch.setattr(handlers, "read_file_local", lambda repo, path: {"error": "nope"})
    gh = handlers._handle_read_file("repo-a", "a.txt", branch="dev")
    assert gh["content"] == "gh"


def test_handle_list_directory_local_first_then_github_fallback(monkeypatch):
    monkeypatch.setattr(handlers, "REPO_CONFIGURED", True)
    monkeypatch.setattr(handlers, "list_directory_local", lambda repo, path: {"items": ["local"]})
    monkeypatch.setattr(handlers.github, "list_directory", lambda repo, path: {"items": ["gh"]})

    local = handlers._handle_list_directory("repo-a", "")
    assert local["items"] == ["local"]

    monkeypatch.setattr(handlers, "list_directory_local", lambda repo, path: {"error": "nope"})
    gh = handlers._handle_list_directory("repo-a", "")
    assert gh["items"] == ["gh"]


def test_datadog_handlers_success_paths(monkeypatch):
    monkeypatch.setattr(handlers, "MONITORING_CONFIGURED", True)
    monkeypatch.setattr(
        handlers.datadog,
        "query_logs",
        lambda query, timeframe, limit: {"q": query, "t": timeframe, "l": limit},
    )
    monkeypatch.setattr(handlers.datadog, "list_monitors", lambda tags=None: {"tags": tags})
    monkeypatch.setattr(handlers.datadog, "get_monitor", lambda monitor_id: {"id": monitor_id})
    monkeypatch.setattr(handlers.datadog, "query_metrics", lambda q, t: {"q": q, "t": t})
    monkeypatch.setattr(handlers.datadog, "list_incidents", lambda q: {"q": q})
    monkeypatch.setattr(handlers.datadog, "search_events", lambda q, t: {"q": q, "t": t})

    assert handlers._handle_query_datadog_logs("service:api") == {
        "q": "service:api",
        "t": "1h",
        "l": 50,
    }
    assert handlers._handle_list_datadog_monitors("a,b") == {"tags": ["a", "b"]}
    assert handlers._handle_get_datadog_monitor(7) == {"id": 7}
    assert handlers._handle_query_datadog_metrics("m") == {"q": "m", "t": "1h"}
    assert handlers._handle_list_datadog_incidents() == {"q": "state:active"}
    assert handlers._handle_search_datadog_events("evt") == {"q": "evt", "t": "1h"}


def test_jira_web_search_pr_and_close_handlers(monkeypatch):
    monkeypatch.setattr(handlers.jira, "query_issues", lambda jql: {"jql": jql})
    monkeypatch.setattr(handlers.jira, "get_issue", lambda issue_key: {"key": issue_key})
    monkeypatch.setattr(handlers.brave_search, "search", lambda q, c: {"q": q, "count": c})
    monkeypatch.setattr(
        handlers,
        "create_pr_from_plan",
        lambda repo, title, body, context, base_branch: {"repo": repo, "base": base_branch},
    )
    monkeypatch.setattr(
        handlers,
        "update_pr_from_plan",
        lambda pr_url, title, body, context: {"pr_url": pr_url},
    )
    monkeypatch.setattr(handlers.github, "close_pr", lambda pr_url: {"closed": pr_url})

    assert handlers._handle_query_jira("project=ABC") == {"jql": "project=ABC"}
    assert handlers._handle_get_jira_issue("ABC-1") == {"key": "ABC-1"}
    assert handlers._handle_web_search("x", count=3) == {"q": "x", "count": 3}
    assert handlers._handle_create_pr_from_plan("repo", "t", "b", "c") == {
        "repo": "repo",
        "base": "main",
    }
    assert handlers._handle_update_pr_from_plan("https://x/pr/1", "t", "b", "c") == {
        "pr_url": "https://x/pr/1"
    }
    assert handlers._handle_close_pr("https://x/pr/1") == {"closed": "https://x/pr/1"}


def test_read_confluence_page_uses_id_as_is_when_not_url(monkeypatch):
    monkeypatch.setattr(handlers.confluence, "read_page", lambda page_id: {"id": page_id})
    assert handlers._handle_read_confluence_page("123") == {"id": "123"}
