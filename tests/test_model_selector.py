from __future__ import annotations

from agent.model_selector import ModelSelector
from config import config


def test_model_selector_uses_configured_anthropic_models(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_MODEL", "anthropic-standard-x")
    monkeypatch.setattr(config, "ANTHROPIC_REASONING_MODEL", "anthropic-deep-x")
    monkeypatch.setattr(config, "OPENAI_MODEL", "openai-standard-x")
    monkeypatch.setattr(config, "OPENAI_REASONING_MODEL", "openai-deep-x")

    selector = ModelSelector()

    standard = selector.select_model("say hi", provider="anthropic")
    deep = selector.select_model("please do a deep dive", provider="anthropic")

    assert standard["id"] == "anthropic-standard-x"
    assert deep["id"] == "anthropic-deep-x"


def test_model_selector_uses_configured_openai_models(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_MODEL", "openai-standard-x")
    monkeypatch.setattr(config, "OPENAI_REASONING_MODEL", "openai-deep-x")

    selector = ModelSelector()

    standard = selector.select_model("say hi", provider="openai")
    deep = selector.select_model("find root cause of intermittent issue", provider="openai")

    assert standard["id"] == "openai-standard-x"
    assert deep["id"] == "openai-deep-x"


def test_default_models_are_current_and_deep_tier_asks_for_high_effort(monkeypatch):
    for key in ("ANTHROPIC_MODEL", "ANTHROPIC_REASONING_MODEL"):
        monkeypatch.setattr(config, key, None)

    selector = ModelSelector()
    standard = selector.select_model("say hi", provider="anthropic")
    deep = selector.select_model("please do a deep dive", provider="anthropic")

    assert (standard["id"], standard["max_tokens"]) == ("claude-sonnet-5-5", 16384)
    assert "effort" not in standard
    assert (deep["id"], deep["max_tokens"], deep["effort"]) == ("claude-opus-5-5", 16384, "high")
