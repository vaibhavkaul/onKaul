from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import main
from api import conversation_store, web_chat

ALICE = {"onkaul_user_id": "alice"}
MALLORY = {"onkaul_user_id": "mallory"}


def _turns(messages: list[dict]) -> list[dict]:
    """Messages without their timestamps (asserted separately)."""
    assert all("ts" in m for m in messages)
    return [{"role": m["role"], "content": m["content"]} for m in messages]


class _FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, _ttl, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


@pytest.fixture
def redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(conversation_store, "get_redis_connection", lambda: fake)
    return fake


@pytest.fixture
def agent_reply(monkeypatch):
    """Make the agent stream fixed chunks (or raise) and record what it was given."""
    calls: list[dict] = []
    behaviour = {"chunks": ["Hel", "lo"], "raise": None}

    def fake_stream(message, context="", thread_history=None, event_context=None):
        calls.append({"message": message, "history": thread_history})
        yield from behaviour["chunks"]
        if behaviour["raise"]:
            raise behaviour["raise"]

    monkeypatch.setattr(web_chat.agent, "investigate_stream", fake_stream)
    return behaviour, calls


def _chat(client, message, session_id=None, cookies=None):
    client.cookies.clear()
    for k, v in (cookies or {}).items():
        client.cookies.set(k, v)
    response = client.post("/web/chat/stream", json={"message": message, "session_id": session_id})
    events = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    return response, events


def _get(client, path, cookies):
    client.cookies.clear()
    for k, v in cookies.items():
        client.cookies.set(k, v)
    return client.get(path)


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def alice_session(client, redis, agent_reply):
    _, events = _chat(client, "secret question", cookies=ALICE)
    return events[0]["session_id"]


def test_owner_can_read_their_session(client, redis, alice_session):
    detail = _get(client, f"/web/sessions/{alice_session}", ALICE).json()

    assert detail["status"] == "done"
    assert [m["content"] for m in detail["messages"]] == ["secret question", "Hello"]


def test_other_user_cannot_read_session(client, redis, alice_session):
    assert _get(client, f"/web/sessions/{alice_session}", MALLORY).status_code == 404
    assert _get(client, f"/web/sessions/{alice_session}", {}).status_code == 404


def test_other_user_cannot_continue_or_overwrite_session(client, redis, agent_reply, alice_session):
    _, calls = agent_reply

    response, _ = _chat(client, "what did they ask?", session_id=alice_session, cookies=MALLORY)

    assert response.status_code == 404
    assert len(calls) == 1  # only alice's original turn reached the agent
    detail = _get(client, f"/web/sessions/{alice_session}", ALICE).json()
    assert len(detail["messages"]) == 2


def test_other_user_cannot_delete_session(client, redis, alice_session):
    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "mallory")
    client.delete(f"/web/sessions/{alice_session}")

    assert _get(client, f"/web/sessions/{alice_session}", ALICE).status_code == 200


def test_owner_continues_with_history(client, redis, agent_reply, alice_session):
    _, calls = agent_reply

    _chat(client, "follow up", session_id=alice_session, cookies=ALICE)

    assert _turns(calls[1]["history"]) == [
        {"role": "user", "content": "secret question"},
        {"role": "assistant", "content": "Hello"},
    ]


def test_question_is_saved_before_the_answer_streams(client, redis, monkeypatch):
    seen: list[dict] = []

    def stream_and_peek(message, context="", thread_history=None, event_context=None):
        sid = event_context["session_id"]
        seen.append(json.loads(redis.data[f"chat_session:{sid}"]))
        yield "ok"

    monkeypatch.setattr(web_chat.agent, "investigate_stream", stream_and_peek)

    _chat(client, "q", cookies=ALICE)

    assert seen[0]["status"] == "streaming"
    assert _turns(seen[0]["messages"]) == [{"role": "user", "content": "q"}]


def test_partial_reply_is_saved_on_error(client, redis, agent_reply):
    behaviour, _ = agent_reply
    behaviour["raise"] = RuntimeError("provider blew up")

    _, events = _chat(client, "q", cookies=ALICE)

    assert events[-1] == {"type": "error", "content": "provider blew up"}
    detail = _get(client, f"/web/sessions/{events[0]['session_id']}", ALICE).json()
    assert detail["status"] == "error"
    assert _turns(detail["messages"])[-1] == {"role": "assistant", "content": "Hello"}


def test_cookie_is_httponly_and_refreshed(client, redis, agent_reply):
    response, _ = _chat(client, "q", cookies=ALICE)

    cookie = response.headers["set-cookie"]
    assert "onkaul_user_id=alice" in cookie
    assert "HttpOnly" in cookie


def test_legacy_sessions_without_owner_cannot_be_claimed(client, redis, agent_reply):
    redis.data["chat_session:old"] = json.dumps({"title": "t", "messages": [], "updated_at": ""})

    response, _ = _chat(client, "mine now", session_id="old", cookies=ALICE)

    assert response.status_code == 404


def test_rename_is_owner_only_and_survives_new_turns(client, redis, agent_reply, alice_session):
    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "mallory")
    assert (
        client.patch(f"/web/sessions/{alice_session}", json={"title": "pwned"}).status_code == 404
    )

    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "alice")
    renamed = client.patch(f"/web/sessions/{alice_session}", json={"title": "  Checkout   bug "})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Checkout bug"

    _chat(client, "follow up", session_id=alice_session, cookies=ALICE)

    detail = _get(client, f"/web/sessions/{alice_session}", ALICE).json()
    assert detail["title"] == "Checkout bug"
    assert len(detail["messages"]) == 4
    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "alice")
    assert client.get("/web/sessions").json()[0]["title"] == "Checkout bug"


def test_rename_rejects_blank_titles(client, redis, alice_session):
    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "alice")

    assert client.patch(f"/web/sessions/{alice_session}", json={"title": ""}).status_code == 422
    assert client.patch(f"/web/sessions/{alice_session}", json={"title": "   "}).status_code == 422


def test_rename_keeps_position_and_updated_at(client, redis, agent_reply):
    _, first = _chat(client, "first", cookies=ALICE)
    _, second = _chat(client, "second", cookies=ALICE)
    first_id, second_id = first[0]["session_id"], second[0]["session_id"]
    before = {s["session_id"]: s for s in _get(client, "/web/sessions", ALICE).json()}

    client.cookies.clear()
    client.cookies.set("onkaul_user_id", "alice")
    assert client.patch(f"/web/sessions/{first_id}", json={"title": "Renamed"}).status_code == 200

    after = _get(client, "/web/sessions", ALICE).json()
    assert [s["session_id"] for s in after] == [second_id, first_id]
    assert after[1]["title"] == "Renamed"
    assert after[1]["updated_at"] == before[first_id]["updated_at"]
    detail = _get(client, f"/web/sessions/{first_id}", ALICE).json()
    assert detail["title"] == "Renamed"
    assert detail["updated_at"] == before[first_id]["updated_at"]


def test_sessions_and_cookie_last_seven_days(client, redis, agent_reply):
    ttls: list[int] = []
    original = redis.setex
    redis.setex = lambda key, ttl, value: ttls.append(ttl) or original(key, ttl, value)

    response, _ = _chat(client, "q", cookies=ALICE)

    assert set(ttls) == {7 * 86400}
    assert "Max-Age=604800" in response.headers["set-cookie"]
