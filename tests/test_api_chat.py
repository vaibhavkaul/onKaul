from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.chat import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_chat_endpoint_returns_agent_response(monkeypatch):
    def _fake_investigate(message: str, context: str = "", thread_history=None) -> str:
        assert message == "hello"
        assert context == "ctx"
        return "ok-response"

    monkeypatch.setattr("api.chat.agent.investigate", _fake_investigate)
    client = _build_client()

    resp = client.post("/chat", json={"message": "hello", "context": "ctx"})

    assert resp.status_code == 200
    assert resp.json() == {"response": "ok-response"}


def test_chat_stream_endpoint_streams_chunks(monkeypatch):
    def _fake_investigate_stream(message: str, context: str = "", thread_history=None):
        assert message == "hello"
        assert context == "ctx"
        yield "a"
        yield ""
        yield "b"

    monkeypatch.setattr("api.chat.agent.investigate_stream", _fake_investigate_stream)
    client = _build_client()

    resp = client.post("/chat/stream", json={"message": "hello", "context": "ctx"})

    assert resp.status_code == 200
    assert resp.text == "ab"
    assert resp.headers["content-type"].startswith("text/plain")


def test_chat_endpoint_validates_message_non_empty():
    client = _build_client()

    resp = client.post("/chat", json={"message": "", "context": "ctx"})

    assert resp.status_code == 422
