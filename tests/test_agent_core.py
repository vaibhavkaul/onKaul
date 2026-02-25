from __future__ import annotations

from agent import core


class _StubProvider:
    def investigate(self, user_message: str, context: str = "", thread_history=None) -> str:
        return f"ok:{user_message}:{context}"

    def investigate_stream(self, user_message: str, context: str = "", thread_history=None):
        yield "a"
        yield "b"


def test_agent_uses_anthropic_provider(monkeypatch):
    monkeypatch.setattr(core.config, "AGENT_PROVIDER", "anthropic")
    monkeypatch.setattr(core, "AnthropicAgentProvider", lambda: _StubProvider())

    agent = core.Agent()

    assert agent.investigate("hello", context="ctx") == "ok:hello:ctx"
    assert "".join(agent.investigate_stream("hello")) == "ab"


def test_agent_uses_openai_provider(monkeypatch):
    monkeypatch.setattr(core.config, "AGENT_PROVIDER", "openai")
    monkeypatch.setattr(core, "OpenAIAgentProvider", lambda: _StubProvider())

    agent = core.Agent()

    assert agent.investigate("hello") == "ok:hello:"


def test_agent_unsupported_provider(monkeypatch):
    monkeypatch.setattr(core.config, "AGENT_PROVIDER", "bogus")

    agent = core.Agent()
    result = agent.investigate("hello")

    assert "Unsupported AGENT_PROVIDER" in result
    assert "bogus" in result
