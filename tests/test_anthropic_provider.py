from __future__ import annotations

from dataclasses import dataclass

import anthropic

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

    def create(self, **_kwargs):
        if self._create_error is not None:
            raise self._create_error
        return self._create_responses.pop(0)

    def stream(self, **_kwargs):
        response, text_chunks = self._stream_responses.pop(0)
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

    assert "API Error" in out


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
