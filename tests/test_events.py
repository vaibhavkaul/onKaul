from __future__ import annotations

import json
import threading
from types import SimpleNamespace

from agent import core
from agent.providers import anthropic_provider, openai_provider
from config import config
from tools import handlers
from utils.events import emit, iterate_in_run_context, run_context


def _events() -> list[dict]:
    path = config.EVENTS_LOG_FILE
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_emit_includes_run_context_and_nested_fields():
    with run_context(channel="slack") as outer:
        with run_context(thread_ts="1.0"):
            emit("x", n=1)
        emit("y")
    emit("z")

    x, y, z = _events()
    assert x["channel"] == "slack" and x["thread_ts"] == "1.0" and x["n"] == 1
    assert x["run_id"] == y["run_id"] == outer["run_id"]
    assert "thread_ts" not in y
    assert "run_id" not in z


def test_emit_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "EVENTS_LOG_FILE", tmp_path / "missing" / "events.jsonl")

    emit("x")


def test_iterate_in_run_context_survives_thread_hops():
    def gen():
        emit("a")
        yield 1
        emit("b")
        yield 2

    it = iterate_in_run_context(gen, channel="web")
    # Advance each step from a different thread, as Starlette's threadpool does.
    for _ in range(3):
        t = threading.Thread(target=lambda: next(it, None))
        t.start()
        t.join()

    a, b = _events()
    assert a["channel"] == b["channel"] == "web"
    assert a["run_id"] == b["run_id"]


def test_tool_call_events_record_outcome(monkeypatch):
    monkeypatch.setattr(handlers, "_handle_web_search", lambda query, count=5: {"hits": []})
    monkeypatch.setattr(handlers, "_handle_close_pr", lambda pr_url: {"error": "not found"})

    handlers.execute_tool("web_search", {"query": "x" * 600})
    handlers.execute_tool("close_pr", {"pr_url": "https://x/pr/1"})
    handlers.execute_tool("nope", {})

    ok, failed, unknown = _events()
    assert ok["event"] == "tool.call" and ok["tool"] == "web_search" and ok["ok"] is True
    assert len(ok["args"]["query"]) == 501
    assert failed["ok"] is False and failed["error"] == "not found"
    assert unknown["ok"] is False and unknown["error"] == "unknown tool"


def test_agent_run_shares_run_id_with_llm_and_tool_events(monkeypatch):
    class _Provider:
        def investigate(self, user_message, context="", thread_history=None):
            emit("llm.call", input_tokens=3)
            handlers.execute_tool("nope", {})
            return "answer"

    agent = core.Agent()
    agent.provider = _Provider()

    assert agent.investigate("q", event_context={"channel": "jira"}) == "answer"

    llm, tool, run = _events()
    assert run["event"] == "run" and run["ok"] is True and run["response_chars"] == 6
    assert llm["run_id"] == tool["run_id"] == run["run_id"]
    assert run["channel"] == "jira"


def test_anthropic_usage_event():
    response = SimpleNamespace(
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=7,
        ),
    )

    anthropic_provider.AnthropicAgentProvider._emit_usage("m", response, 0.0, streamed=True)

    (event,) = _events()
    assert event["event"] == "llm.call" and event["provider"] == "anthropic"
    assert (event["input_tokens"], event["output_tokens"], event["cache_read_input_tokens"]) == (
        10,
        5,
        7,
    )


def test_openai_usage_event():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            input_tokens_details=SimpleNamespace(cached_tokens=4),
            output_tokens_details=SimpleNamespace(reasoning_tokens=2),
        )
    )

    openai_provider.OpenAIAgentProvider._emit_usage("gpt", response, 0.0)

    (event,) = _events()
    assert event["provider"] == "openai" and event["model"] == "gpt"
    assert (event["cached_input_tokens"], event["reasoning_tokens"]) == (4, 2)
