from __future__ import annotations

import hashlib
import hmac

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import webhooks


class _FakeQueue:
    def __init__(self):
        self.calls: list[tuple[object, dict]] = []

    def enqueue(self, fn, **kwargs):
        self.calls.append((fn, kwargs))


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(webhooks.router)
    return TestClient(app)


def test_verify_slack_signature_disabled(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", False)

    ok, error = webhooks._verify_slack_signature(b"{}", {})

    assert ok is True
    assert error is None


def test_verify_slack_signature_missing_secret(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", True)
    monkeypatch.setattr(webhooks.config, "SLACK_SIGNING_SECRET", None)

    ok, error = webhooks._verify_slack_signature(b"{}", {})

    assert ok is False
    assert error == "SLACK_SIGNING_SECRET not set"


def test_verify_slack_signature_success(monkeypatch):
    secret = "test-secret"
    body = b'{"a":1}'
    ts = "1700000000"
    base = f"v0:{ts}:".encode("utf-8") + body
    sig = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()

    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", True)
    monkeypatch.setattr(webhooks.config, "SLACK_SIGNING_SECRET", secret)
    monkeypatch.setattr(webhooks.time, "time", lambda: float(ts))

    ok, error = webhooks._verify_slack_signature(
        body,
        {"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig},
    )

    assert ok is True
    assert error is None


def test_slack_webhook_url_verification(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", False)
    client = _build_client()

    resp = client.post("/webhook/slack", json={"type": "url_verification", "challenge": "abc"})

    assert resp.status_code == 200
    assert resp.json() == {"challenge": "abc"}


def test_slack_webhook_no_event(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", False)
    client = _build_client()

    resp = client.post("/webhook/slack", json={"type": "event_callback"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": False, "error": "No event in payload"}


def test_slack_webhook_ignores_bot_messages(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", False)
    client = _build_client()

    resp = client.post(
        "/webhook/slack",
        json={
            "event": {
                "type": "app_mention",
                "channel": "C1",
                "ts": "1.0",
                "text": "@onkaul hello",
                "user": "U1",
                "bot_id": "B1",
            }
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Ignored bot message"}


def test_slack_webhook_queues_investigation_with_attachments_and_thread(monkeypatch):
    monkeypatch.setattr(webhooks.config, "SLACK_VERIFY_SIGNATURE", False)
    monkeypatch.setattr(webhooks.config, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(webhooks.config, "JOB_TIMEOUT_SECONDS", 321)

    fake_queue = _FakeQueue()
    monkeypatch.setattr(webhooks, "get_queue", lambda: fake_queue)
    monkeypatch.setattr(webhooks.slack, "add_reaction", lambda *_args, **_kwargs: {"success": True})
    monkeypatch.setattr(
        webhooks.slack,
        "get_thread",
        lambda *_args, **_kwargs: {"success": True, "messages": [{"text": "earlier"}]},
    )
    monkeypatch.setattr(
        webhooks.attachment_processor,
        "process_slack_file",
        lambda file_data, token: {
            "processed": True,
            "filename": file_data["name"],
            "extracted_text": "hello world",
            "token_used": token,
        },
    )

    client = _build_client()
    resp = client.post(
        "/webhook/slack",
        json={
            "event": {
                "type": "app_mention",
                "channel": "C1",
                "ts": "10.0",
                "thread_ts": "9.0",
                "text": "@onkaul investigate",
                "user": "U1",
                "files": [{"name": "file.txt", "filetype": "text"}],
            }
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Investigation queued"}
    assert len(fake_queue.calls) == 1
    _, kwargs = fake_queue.calls[0]
    assert kwargs["channel"] == "C1"
    assert kwargs["thread_ts"] == "9.0"
    assert kwargs["user_message"] == "@onkaul investigate"
    assert kwargs["user_id"] == "U1"
    assert kwargs["thread_context"] == [{"text": "earlier"}]
    assert kwargs["job_timeout"] == 321
    assert kwargs["attachments"][0]["filename"] == "file.txt"
    assert kwargs["attachments"][0]["token_used"] == "xoxb-test"


def test_jira_webhook_verification_missing_secret(monkeypatch):
    monkeypatch.setattr(webhooks.config, "ENABLE_JIRA_WEBHOOK_VERIFICATION", True)
    monkeypatch.setattr(webhooks.config, "JIRA_WEBHOOK_SECRET", "secret")
    client = _build_client()

    resp = client.post(
        "/webhook/jira",
        json={
            "issue": {"key": "ABC-1"},
            "comment": {"body": "@onkaul hi", "author": {"displayName": "Alice"}},
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": False, "error": "Missing Jira webhook secret"}


def test_jira_webhook_verification_invalid_secret(monkeypatch):
    monkeypatch.setattr(webhooks.config, "ENABLE_JIRA_WEBHOOK_VERIFICATION", True)
    monkeypatch.setattr(webhooks.config, "JIRA_WEBHOOK_SECRET", "secret")
    client = _build_client()

    resp = client.post(
        "/webhook/jira",
        headers={"X-Webhook-Secret": "wrong"},
        json={
            "issue": {"key": "ABC-1"},
            "comment": {"body": "@onkaul hi", "author": {"displayName": "Alice"}},
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": False, "error": "Invalid Jira webhook secret"}


def test_jira_webhook_ignores_non_mentions(monkeypatch):
    monkeypatch.setattr(webhooks.config, "ENABLE_JIRA_WEBHOOK_VERIFICATION", False)
    fake_queue = _FakeQueue()
    monkeypatch.setattr(webhooks, "get_queue", lambda: fake_queue)
    client = _build_client()

    resp = client.post(
        "/webhook/jira",
        json={
            "issue": {"key": "ABC-1"},
            "comment": {"body": "hello", "author": {"displayName": "Alice"}},
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "No mention, ignored"}
    assert len(fake_queue.calls) == 0


def test_jira_webhook_queues_mentions(monkeypatch):
    monkeypatch.setattr(webhooks.config, "ENABLE_JIRA_WEBHOOK_VERIFICATION", True)
    monkeypatch.setattr(webhooks.config, "JIRA_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr(webhooks.config, "JOB_TIMEOUT_SECONDS", 654)
    fake_queue = _FakeQueue()
    monkeypatch.setattr(webhooks, "get_queue", lambda: fake_queue)
    client = _build_client()

    resp = client.post(
        "/webhook/jira",
        headers={"X-Webhook-Secret": "secret"},
        json={
            "issue": {"key": "ABC-1"},
            "comment": {"body": "@onKaul can you help?", "author": {"displayName": "Alice"}},
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Investigation queued"}
    assert len(fake_queue.calls) == 1
    _, kwargs = fake_queue.calls[0]
    assert kwargs["issue_key"] == "ABC-1"
    assert kwargs["comment_body"] == "@onKaul can you help?"
    assert kwargs["author"] == "Alice"
    assert kwargs["job_timeout"] == 654
