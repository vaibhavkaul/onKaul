from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

import main
from api import chat_runs, conversation_store, web_chat
from tests.test_web_sessions import _FakeRedis


@pytest.fixture
def redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(conversation_store, "get_redis_connection", lambda: fake)
    return fake


@pytest.fixture
def client():
    return TestClient(main.app)


class SlowAgent:
    """Streams numbered chunks with a delay; records whether it was closed."""

    def __init__(self, chunks: int = 5, delay: float = 0.05):
        self.chunks, self.delay = chunks, delay
        self.closed = threading.Event()
        self.yielded = 0

    def __call__(self, message, context="", thread_history=None, event_context=None):
        try:
            for i in range(self.chunks):
                time.sleep(self.delay)
                self.yielded += 1
                yield f"c{i} "
        finally:
            self.closed.set()


def _saved(redis, session_id: str) -> dict:
    return json.loads(redis.data[f"chat_session:{session_id}"])


def _wait_finished(session_id: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while chat_runs.active_run(session_id) is not None:
        assert time.monotonic() < deadline, "run did not finish"
        time.sleep(0.01)


def _cookies(client, user: str) -> None:
    client.cookies.clear()
    client.cookies.set("onkaul_user_id", user)


def test_closing_the_connection_does_not_cancel_the_reply(client, redis, monkeypatch):
    agent = SlowAgent(chunks=5)
    monkeypatch.setattr(web_chat.agent, "investigate_stream", agent)
    _cookies(client, "alice")

    with client.stream("POST", "/web/chat/stream", json={"message": "q"}) as response:
        first = next(response.iter_lines())  # session event, then hang up
    session_id = json.loads(first[6:])["session_id"]
    _wait_finished(session_id)

    saved = _saved(redis, session_id)
    assert saved["status"] == "done"
    assert saved["messages"][-1]["content"] == "c0 c1 c2 c3 c4 "
    assert agent.yielded == 5


def test_stop_interrupts_saves_partial_and_closes_agent(redis):
    agent = SlowAgent(chunks=1000, delay=0.01)
    run = chat_runs.start_run(
        session_id="s1",
        user_id="alice",
        title="t",
        messages=[{"role": "user", "content": "q", "ts": "x"}],
        stream=lambda: agent("q"),
    )
    while not run.chunks:
        time.sleep(0.005)

    assert chat_runs.stop_run("s1", "mallory") is False
    assert chat_runs.stop_run("s1", "alice") is True
    assert run.finished.wait(5)

    saved = _saved(redis, "s1")
    assert saved["status"] == "interrupted"
    assert saved["messages"][-1]["content"].startswith("c0 ")
    # The driving thread closes the agent (and its provider stream) at its next chunk.
    assert agent.closed.wait(2)
    assert agent.yielded < 1000


def test_stop_endpoint_is_owner_only(client, redis, monkeypatch):
    monkeypatch.setattr(web_chat.agent, "investigate_stream", SlowAgent(chunks=1000, delay=0.01))
    run = chat_runs.start_run(
        session_id="s2",
        user_id="alice",
        title="t",
        messages=[{"role": "user", "content": "q", "ts": "x"}],
        stream=lambda: web_chat.agent.investigate_stream("q"),
    )

    _cookies(client, "mallory")
    assert client.post("/web/sessions/s2/stop").status_code == 404
    _cookies(client, "alice")
    assert client.post("/web/sessions/s2/stop").status_code == 204
    assert run.finished.wait(5)
    assert client.post("/web/sessions/s2/stop").status_code == 404  # nothing running now


def test_second_message_while_answering_gets_409(client, redis, monkeypatch):
    monkeypatch.setattr(web_chat.agent, "investigate_stream", SlowAgent(chunks=1000, delay=0.01))
    _cookies(client, "alice")
    with client.stream("POST", "/web/chat/stream", json={"message": "q1"}) as response:
        session_id = json.loads(next(response.iter_lines())[6:])["session_id"]

    _cookies(client, "alice")
    second = client.post("/web/chat/stream", json={"message": "q2", "session_id": session_id})

    assert second.status_code == 409
    chat_runs.stop_run(session_id, "alice")
    _wait_finished(session_id)
    contents = [m["content"] for m in _saved(redis, session_id)["messages"]]
    assert "q2" not in contents


def test_done_event_reports_interrupted_status(client, redis, monkeypatch):
    agent = SlowAgent(chunks=1000, delay=0.01)
    monkeypatch.setattr(web_chat.agent, "investigate_stream", agent)
    _cookies(client, "alice")

    events = []
    with client.stream("POST", "/web/chat/stream", json={"message": "q"}) as response:
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            events.append(event)
            if event["type"] == "text" and len(events) == 3:
                chat_runs.stop_run(events[0]["session_id"], "alice")

    assert events[-1] == {"type": "done", "status": "interrupted"}


def test_stop_while_model_is_still_thinking_frees_the_session_at_once(redis):
    agent = SlowAgent(chunks=3, delay=1.0)  # first chunk only after 1s
    run = chat_runs.start_run(
        session_id="s3",
        user_id="alice",
        title="t",
        messages=[{"role": "user", "content": "q", "ts": "x"}],
        stream=lambda: agent("q"),
    )
    time.sleep(0.1)

    started = time.monotonic()
    assert chat_runs.stop_run("s3", "alice")

    assert run.finished.is_set() and time.monotonic() - started < 0.5
    assert chat_runs.active_run("s3") is None
    assert _saved(redis, "s3")["status"] == "interrupted"
    # The driving thread exits quietly later without saving again.
    assert agent.closed.wait(3)
    assert _saved(redis, "s3")["status"] == "interrupted"
    assert run.chunks == []


def test_rename_during_a_reply_is_not_undone(client, redis, monkeypatch):
    monkeypatch.setattr(web_chat.agent, "investigate_stream", SlowAgent(chunks=10, delay=0.02))
    _cookies(client, "alice")
    with client.stream("POST", "/web/chat/stream", json={"message": "q"}) as response:
        session_id = json.loads(next(response.iter_lines())[6:])["session_id"]

    _cookies(client, "alice")
    assert client.patch(f"/web/sessions/{session_id}", json={"title": "Renamed"}).status_code == 200
    _wait_finished(session_id)

    saved = _saved(redis, session_id)
    assert saved["status"] == "done"
    assert saved["title"] == "Renamed"
