from __future__ import annotations

from dataclasses import dataclass

import anthropic
import httpx

from agent.providers import anthropic_provider as provider_mod


@dataclass
class _FakeBlock:
    type: str
    text: str = ""
    name: str = ""
    input: dict | None = None
    id: str = ""


class _FakeResponse:
    def __init__(self, stop_reason: str, content: list[_FakeBlock]):
        self.stop_reason = stop_reason
        self.content = content


class _FakeStreamCtx:
    def __init__(self, response: _FakeResponse, text_chunks: list[str]):
        self._response = response
        self.text_stream = iter(text_chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_message(self):
        return self._response


class _FakeMessagesAPI:
    def __init__(self, *, create_responses=None, stream_responses=None, create_error=None):
        self._create_responses = list(create_responses or [])
        self._stream_responses = list(stream_responses or [])
        self._create_error = create_error
        self.calls: list[dict] = []

    def create(self, **_kwargs):
        if self._create_error is not None:
            raise self._create_error
        return self._create_responses.pop(0)

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        if self._create_error is not None:
            raise self._create_error
        if self._stream_responses:
            response, text_chunks = self._stream_responses.pop(0)
        else:
            # investigate() streams too; serve the queued "create" responses.
            response, text_chunks = self._create_responses.pop(0), []
        return _FakeStreamCtx(response, text_chunks)


class _FakeClient:
    def __init__(self, messages_api: _FakeMessagesAPI):
        self.messages = messages_api


def _build_provider(monkeypatch) -> provider_mod.AnthropicAgentProvider:
    monkeypatch.setattr(provider_mod.config, "ANTHROPIC_API_KEY", "sk-ant-test")
    provider = provider_mod.AnthropicAgentProvider()
    provider.max_iterations = 3
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {
            "id": "model-x",
            "name": "Model X",
            "max_tokens": 1234,
            "reason": "test",
        },
    )
    return provider


def test_investigate_no_api_key_message(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "ANTHROPIC_API_KEY", None)
    provider = provider_mod.AnthropicAgentProvider()

    out = provider.investigate("hello")

    assert "ANTHROPIC_API_KEY not configured" in out


def test_investigate_end_turn_returns_text(monkeypatch):
    provider = _build_provider(monkeypatch)
    provider.client = _FakeClient(
        _FakeMessagesAPI(
            create_responses=[
                _FakeResponse("end_turn", [_FakeBlock(type="text", text="done")]),
            ]
        )
    )

    out = provider.investigate("hello")

    assert out == "done"


def test_investigate_tool_use_then_end_turn(monkeypatch):
    provider = _build_provider(monkeypatch)
    provider.client = _FakeClient(
        _FakeMessagesAPI(
            create_responses=[
                _FakeResponse(
                    "tool_use",
                    [
                        _FakeBlock(
                            type="tool_use",
                            name="search_code",
                            input={"repo": "r", "query": "q"},
                            id="tool-1",
                        )
                    ],
                ),
                _FakeResponse("end_turn", [_FakeBlock(type="text", text="final")]),
            ]
        )
    )
    monkeypatch.setattr(provider_mod, "execute_tool", lambda *_args, **_kwargs: '{"ok": true}')

    out = provider.investigate("hello")

    assert out == "final"


def test_investigate_handles_api_error(monkeypatch):
    provider = _build_provider(monkeypatch)
    provider.client = _FakeClient(
        _FakeMessagesAPI(create_error=anthropic.APIError(message="bad", request=None, body={}))
    )

    out = provider.investigate("hello")

    assert "Anthropic API error: bad" in out


def test_investigate_stream_end_turn(monkeypatch):
    provider = _build_provider(monkeypatch)
    provider.client = _FakeClient(
        _FakeMessagesAPI(
            stream_responses=[
                (_FakeResponse("end_turn", []), ["a", "b"]),
            ]
        )
    )

    out = "".join(provider.investigate_stream("hello"))

    assert out == "ab"


def test_investigate_stream_tool_then_end_turn(monkeypatch):
    provider = _build_provider(monkeypatch)
    provider.client = _FakeClient(
        _FakeMessagesAPI(
            stream_responses=[
                (
                    _FakeResponse(
                        "tool_use",
                        [
                            _FakeBlock(
                                type="tool_use",
                                name="read_file",
                                input={"repo": "r", "path": "p"},
                                id="tool-2",
                            )
                        ],
                    ),
                    ["x"],
                ),
                (_FakeResponse("end_turn", []), ["y"]),
            ]
        )
    )
    monkeypatch.setattr(provider_mod, "execute_tool", lambda *_args, **_kwargs: '{"ok": true}')

    out = "".join(provider.investigate_stream("hello"))

    assert out == "xy"


def _status_error(cls, status: int):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("nope", response=httpx.Response(status, request=request), body=None)


def test_investigate_sends_full_web_history(monkeypatch):
    provider = _build_provider(monkeypatch)
    api = _FakeMessagesAPI(
        create_responses=[_FakeResponse("end_turn", [_FakeBlock(type="text", text="a2")])]
    )
    calls = api.calls
    provider.client = _FakeClient(api)

    history = [
        {"role": "user", "content": "q1", "timestamp": "t1"},
        {"role": "assistant", "content": "a1", "timestamp": "t2"},
    ]
    provider.investigate("q2", thread_history=history)

    assert calls[0]["messages"] == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]


def test_api_error_message_blames_key_only_on_auth_failure():
    auth = provider_mod.AnthropicAgentProvider._api_error_message(
        _status_error(anthropic.AuthenticationError, 401)
    )
    overloaded = provider_mod.AnthropicAgentProvider._api_error_message(
        _status_error(anthropic.InternalServerError, 529)
    )

    assert "ANTHROPIC_API_KEY" in auth
    assert "HTTP 529" in overloaded
    assert "ANTHROPIC_API_KEY" not in overloaded


def test_effort_is_sent_as_output_config(monkeypatch):
    provider = _build_provider(monkeypatch)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {
            "id": "claude-opus-5-5",
            "name": "Opus 5.5",
            "max_tokens": 16384,
            "effort": "high",
            "reason": "test",
        },
    )
    api = _FakeMessagesAPI(
        create_responses=[_FakeResponse("end_turn", [_FakeBlock(type="text", text="ok")])]
    )
    calls = api.calls
    provider.client = _FakeClient(api)

    provider.investigate("q")

    assert calls[0]["output_config"] == {"effort": "high"}
    assert "thinking" not in calls[0] and "temperature" not in calls[0]


def test_request_has_date_block_and_web_search_tool(monkeypatch):
    provider = _build_provider(monkeypatch)
    monkeypatch.setattr(provider_mod.config, "ENABLE_WEB_SEARCH", True)

    params = provider._request_params({"id": "claude-opus-5-5", "max_tokens": 10}, [])

    stable, dated = params["system"]
    assert stable["text"] == provider_mod.SYSTEM_PROMPT
    assert dated["text"].startswith("Current date: ")
    assert params["tools"][-1] == {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": provider_mod.config.WEB_SEARCH_MAX_USES,
    }


def test_older_models_get_basic_web_search_and_it_can_be_disabled(monkeypatch):
    provider = _build_provider(monkeypatch)
    monkeypatch.setattr(provider_mod.config, "ENABLE_WEB_SEARCH", True)
    assert provider._server_tools("claude-haiku-4-5")[0]["type"] == "web_search_20250305"

    monkeypatch.setattr(provider_mod.config, "ENABLE_WEB_SEARCH", False)
    assert provider._server_tools("claude-opus-5-5") == []


def test_pause_turn_is_resumed(monkeypatch):
    provider = _build_provider(monkeypatch)
    paused = _FakeResponse("pause_turn", [_FakeBlock(type="server_tool_use", name="web_search")])
    api = _FakeMessagesAPI(
        create_responses=[
            paused,
            _FakeResponse("end_turn", [_FakeBlock(type="text", text="found")]),
        ]
    )
    provider.client = _FakeClient(api)

    assert provider.investigate("search it") == "found"
    resumed = api.calls[1]["messages"]
    assert resumed[-1] == {"role": "assistant", "content": paused.content}


def test_refusal_is_reported(monkeypatch):
    provider = _build_provider(monkeypatch)
    refused = _FakeResponse("refusal", [])
    refused.stop_details = type("Details", (), {"category": "cyber"})()
    provider.client = _FakeClient(_FakeMessagesAPI(create_responses=[refused]))

    assert (
        provider.investigate("q")
        == "⚠️ The model declined to answer this request (category: cyber)."
    )
