from __future__ import annotations

from worker import tasks


class _LogCapture:
    def __init__(self):
        self.calls: list[dict] = []

    def log_response(
        self,
        *,
        source: str,
        response: str,
        metadata: dict,
        investigation_duration_ms: float | None = None,
    ):
        self.calls.append(
            {
                "source": source,
                "response": response,
                "metadata": metadata,
                "investigation_duration_ms": investigation_duration_ms,
            }
        )


def test_handle_slack_mention_posts_success(monkeypatch):
    logs = _LogCapture()
    posts: list[tuple[str, str, str]] = []

    monkeypatch.setattr(tasks.config, "ENABLE_SLACK_POSTING", True)
    monkeypatch.setattr(tasks.agent, "investigate", lambda *args, **kwargs: "investigation result")
    monkeypatch.setattr(tasks, "format_for_slack", lambda text: f"formatted:{text}")
    monkeypatch.setattr(tasks.logger, "log_response", logs.log_response)
    monkeypatch.setattr(
        tasks.slack,
        "post_message",
        lambda channel, message, thread_ts: (
            posts.append((channel, message, thread_ts)) or {"success": True, "ts": "1.23"}
        ),
    )

    tasks.handle_slack_mention(
        channel="C1",
        thread_ts="11.0",
        user_message="@onkaul investigate this",
        user_id="U1",
        thread_context=[
            {"user": "U2", "text": "previous"},
            {"user": "U1", "text": "@onkaul investigate this"},
        ],
        attachments=[
            {"filename": "a.txt", "extracted_text": "abc"},
            {"filename": "b.txt", "extracted_text": ""},
        ],
    )

    assert len(logs.calls) == 1
    assert logs.calls[0]["source"] == "slack"
    assert logs.calls[0]["response"] == "investigation result"
    assert logs.calls[0]["metadata"]["channel"] == "C1"
    assert posts == [("C1", "formatted:investigation result", "11.0")]


def test_handle_slack_mention_logs_and_posts_error(monkeypatch):
    logs = _LogCapture()
    posts: list[tuple[str, str, str]] = []

    monkeypatch.setattr(tasks.config, "ENABLE_SLACK_POSTING", True)
    monkeypatch.setattr(
        tasks.agent,
        "investigate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(tasks, "format_for_slack", lambda text: f"formatted:{text}")
    monkeypatch.setattr(tasks.logger, "log_response", logs.log_response)
    monkeypatch.setattr(
        tasks.slack,
        "post_message",
        lambda channel, message, thread_ts: (
            posts.append((channel, message, thread_ts)) or {"success": True}
        ),
    )

    tasks.handle_slack_mention(
        channel="C1",
        thread_ts="11.0",
        user_message="@onkaul explode",
        user_id="U1",
    )

    assert len(logs.calls) == 1
    assert logs.calls[0]["source"] == "slack"
    assert "Sorry, I encountered an error: boom" in logs.calls[0]["response"]
    assert posts and "formatted:Sorry, I encountered an error: boom" in posts[0][1]


def test_handle_jira_mention_posts_success(monkeypatch):
    logs = _LogCapture()
    comments: list[tuple[str, object, object]] = []

    monkeypatch.setattr(tasks.config, "ENABLE_JIRA_POSTING", True)
    monkeypatch.setattr(tasks.config, "JIRA_BASE_URL", "https://jira.example.com")
    monkeypatch.setattr(tasks.agent, "investigate", lambda *args, **kwargs: "jira investigation")
    monkeypatch.setattr(tasks, "markdown_to_adf", lambda text: {"adf": text})
    monkeypatch.setattr(tasks.logger, "log_response", logs.log_response)
    monkeypatch.setattr(
        tasks.jira,
        "add_comment",
        lambda issue_key, _legacy_body, adf_body=None: (
            comments.append((issue_key, _legacy_body, adf_body))
            or {"success": True, "comment_id": "100"}
        ),
    )

    tasks.handle_jira_mention(issue_key="ABC-1", comment_body="@onkaul investigate", author="Alice")

    assert len(logs.calls) == 1
    assert logs.calls[0]["source"] == "jira"
    assert logs.calls[0]["response"] == "jira investigation"
    assert comments == [("ABC-1", None, {"adf": "jira investigation"})]


def test_handle_jira_mention_logs_and_posts_error(monkeypatch):
    logs = _LogCapture()
    comments: list[tuple[str, object, object]] = []

    monkeypatch.setattr(tasks.config, "ENABLE_JIRA_POSTING", True)
    monkeypatch.setattr(
        tasks.agent,
        "investigate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("jira boom")),
    )
    monkeypatch.setattr(tasks, "markdown_to_adf", lambda text: {"adf": text})
    monkeypatch.setattr(tasks.logger, "log_response", logs.log_response)
    monkeypatch.setattr(
        tasks.jira,
        "add_comment",
        lambda issue_key, _legacy_body, adf_body=None: (
            comments.append((issue_key, _legacy_body, adf_body)) or {"success": True}
        ),
    )

    tasks.handle_jira_mention(issue_key="ABC-1", comment_body="@onkaul break", author="Alice")

    assert len(logs.calls) == 1
    assert logs.calls[0]["source"] == "jira"
    assert "Sorry, I encountered an error: jira boom" in logs.calls[0]["response"]
    assert comments and "jira boom" in comments[0][2]["adf"]
