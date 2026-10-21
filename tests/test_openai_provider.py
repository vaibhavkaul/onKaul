from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import APIError, AuthenticationError, RateLimitError

from agent.providers import openai_provider as provider_mod


@dataclass
class _FakeEvent:
    type: str
    delta: str


class _FakeOutputItem:
    def __init__(
        self,
        item_type: str,
        *,
        call_id: str = "",
        name: str = "",
        arguments: str = "{}",
        dump_data: dict | None = None,
    ):
        self.type = item_type
        self.call_id = call_id
        self.name = name
        self.arguments = arguments
        self._dump_data = dump_data if dump_data is not None else {"type": item_type}

    def model_dump(self) -> dict:
        return self._dump_data


class _FakeResponse:
    def __init__(self, response_id: str, output: list, output_text: str = ""):
        self.id = response_id
        self.output = output
        self.output_text = output_text


class _FakeStream:
    def __init__(self, response: _FakeResponse, events: list[_FakeEvent]):
        self._response = response
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_response(self):
        return self._response


class _FakeResponsesAPI:
    def __init__(self, streams: list[_FakeStream]):
        self._streams = streams
        self.calls: list[dict] = []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        return self._streams.pop(0)


class _FakeClient:
    def __init__(self, streams: list[_FakeStream]):
        self.responses = _FakeResponsesAPI(streams)


class _ErrorResponsesAPI:
    def __init__(self, error: Exception):
        self.error = error

    def stream(self, **kwargs):
        raise self.error


class _ErrorClient:
    def __init__(self, error: Exception):
        self.responses = _ErrorResponsesAPI(error)


def test_openai_provider_no_api_key_non_stream(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", None)
    provider = provider_mod.OpenAIAgentProvider()

    out = provider.investigate("hello")

    assert "OPENAI_API_KEY not configured" in out


def test_openai_provider_no_api_key_stream(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", None)
    provider = provider_mod.OpenAIAgentProvider()

    out = "".join(provider.investigate_stream("hello"))

    assert "OPENAI_API_KEY not configured" in out


def test_openai_provider_uses_previous_response_id_when_store_enabled(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(provider_mod.config, "OPENAI_STORE", True)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {"id": "gpt-test", "name": "GPT test", "reason": "test"},
    )
    monkeypatch.setattr(provider_mod, "execute_tool", lambda *_args, **_kwargs: '{"ok": true}')

    first_response = _FakeResponse(
        "resp_1",
        [
            _FakeOutputItem(
                "function_call",
                call_id="call_1",
                name="get_sentry_issue",
                arguments='{"issue_id":"123"}',
            )
        ],
    )
    second_response = _FakeResponse("resp_2", [], output_text="done")

    fake_client = _FakeClient(
        [
            _FakeStream(first_response, []),
            _FakeStream(second_response, [_FakeEvent("response.output_text.delta", "done")]),
        ]
    )

    provider = provider_mod.OpenAIAgentProvider()
    provider.client = fake_client

    result = provider.investigate("hello")

    assert result == "done"
    assert len(fake_client.responses.calls) == 2
    assert fake_client.responses.calls[0]["store"] is True
    assert "previous_response_id" not in fake_client.responses.calls[0]
    assert fake_client.responses.calls[1]["previous_response_id"] == "resp_1"


def test_openai_provider_avoids_previous_response_id_when_store_disabled(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(provider_mod.config, "OPENAI_STORE", False)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {"id": "gpt-test", "name": "GPT test", "reason": "test"},
    )
    monkeypatch.setattr(provider_mod, "execute_tool", lambda *_args, **_kwargs: '{"ok": true}')

    first_response = _FakeResponse(
        "resp_1",
        [
            _FakeOutputItem(
                "function_call",
                call_id="call_1",
                name="get_sentry_issue",
                arguments='{"issue_id":"123"}',
                dump_data={
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "get_sentry_issue",
                    "arguments": '{"issue_id":"123"}',
                },
            )
        ],
    )
    second_response = _FakeResponse("resp_2", [], output_text="done")

    fake_client = _FakeClient(
        [
            _FakeStream(first_response, []),
            _FakeStream(second_response, [_FakeEvent("response.output_text.delta", "done")]),
        ]
    )

    provider = provider_mod.OpenAIAgentProvider()
    provider.client = fake_client

    result = provider.investigate("hello")

    assert result == "done"
    assert len(fake_client.responses.calls) == 2
    assert fake_client.responses.calls[0]["store"] is False
    assert "previous_response_id" not in fake_client.responses.calls[1]
    # With store disabled, second call includes accumulated conversation input.
    assert len(fake_client.responses.calls[1]["input"]) >= 3


def test_openai_provider_api_error_path(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(provider_mod.config, "OPENAI_STORE", True)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {"id": "gpt-test", "name": "GPT test", "reason": "test"},
    )

    provider = provider_mod.OpenAIAgentProvider()
    provider.client = _ErrorClient(APIError("bad", request=None, body={}))

    out = provider.investigate("hello")

    assert "OpenAI API error: bad" in out


def test_openai_provider_unexpected_error_path(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(provider_mod.config, "OPENAI_STORE", True)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {"id": "gpt-test", "name": "GPT test", "reason": "test"},
    )

    provider = provider_mod.OpenAIAgentProvider()
    provider.client = _ErrorClient(RuntimeError("boom"))

    out = provider.investigate("hello")

    assert "Unexpected error during investigation: boom" in out


def test_openai_extract_tool_calls_handles_bad_json(monkeypatch):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    provider = provider_mod.OpenAIAgentProvider()
    response = _FakeResponse(
        "resp_1",
        [_FakeOutputItem("function_call", call_id="c1", name="tool", arguments="{not-json}")],
    )

    calls = provider._extract_tool_calls(response)

    assert calls == [{"call_id": "c1", "name": "tool", "args": {}}]


def _provider_with_streams(monkeypatch, streams):
    monkeypatch.setattr(provider_mod.config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(provider_mod.config, "OPENAI_STORE", False)
    monkeypatch.setattr(
        provider_mod.model_selector,
        "select_model",
        lambda *_args, **_kwargs: {"id": "gpt-test", "name": "GPT test", "reason": "test"},
    )
    provider = provider_mod.OpenAIAgentProvider()
    provider.client = _FakeClient(streams)
    return provider


def test_openai_provider_sends_thread_history(monkeypatch):
    stream = _FakeStream(
        _FakeResponse("r1", []), [_FakeEvent(type="response.output_text.delta", delta="a2")]
    )
    provider = _provider_with_streams(monkeypatch, [stream])

    history = [
        {"role": "user", "content": "q1", "timestamp": "t1"},
        {"role": "assistant", "content": "a1"},
    ]
    out = provider.investigate("q2", thread_history=history)

    assert out == "a2"
    assert provider.client.responses.calls[0]["input"] == [
        {"role": "user", "content": [{"type": "input_text", "text": "q1"}]},
        {"role": "assistant", "content": [{"type": "output_text", "text": "a1"}]},
        {"role": "user", "content": [{"type": "input_text", "text": "q2"}]},
    ]


class _FinalizeFailsStream(_FakeStream):
    def get_final_response(self):
        raise RuntimeError("finalize failed")


def test_openai_provider_keeps_streamed_text_when_finalize_fails(monkeypatch):
    stream = _FinalizeFailsStream(
        _FakeResponse("r1", []), [_FakeEvent(type="response.output_text.delta", delta="answer")]
    )
    provider = _provider_with_streams(monkeypatch, [stream])

    assert provider.investigate("hello") == "answer"


def test_openai_provider_reports_finalize_failure_without_text(monkeypatch):
    provider = _provider_with_streams(
        monkeypatch, [_FinalizeFailsStream(_FakeResponse("r1", []), [])]
    )

    assert "finalize failed" in provider.investigate("hello")


def test_openai_api_error_message_blames_key_only_on_auth_failure():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    auth = provider_mod.OpenAIAgentProvider._api_error_message(
        AuthenticationError("nope", response=httpx.Response(401, request=request), body=None)
    )
    limited = provider_mod.OpenAIAgentProvider._api_error_message(
        RateLimitError("slow down", response=httpx.Response(429, request=request), body=None)
    )

    assert "OPENAI_API_KEY" in auth
    assert "HTTP 429" in limited
    assert "OPENAI_API_KEY" not in limited
