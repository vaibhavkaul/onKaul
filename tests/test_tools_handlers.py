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
