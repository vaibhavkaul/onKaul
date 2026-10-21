from __future__ import annotations

from agent.history import build_messages, normalize_history


def test_normalize_strips_extra_fields_from_web_messages():
    history = [
        {"role": "user", "content": "q1", "timestamp": "2026-01-01T00:00:00Z"},
        {"role": "assistant", "content": "a1", "timestamp": "2026-01-01T00:00:01Z"},
    ]

    assert normalize_history(history) == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]


def test_normalize_converts_slack_messages_and_merges_same_role():
    history = [
        {"user": "U1", "text": "first"},
        {"user": "U2", "text": "second"},
        {"user": "UBOT", "bot_id": "B1", "text": "answer"},
        {"user": "U1", "text": ""},
    ]

    assert normalize_history(history) == [
        {"role": "user", "content": "first\n\nsecond"},
        {"role": "assistant", "content": "answer"},
    ]


def test_normalize_prepends_user_turn_when_bot_speaks_first():
    turns = normalize_history([{"bot_id": "B1", "text": "hello"}])

    assert turns[0]["role"] == "user"
    assert turns[1] == {"role": "assistant", "content": "hello"}


def test_normalize_does_not_mutate_input():
    history = [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]

    normalize_history(history)

    assert history[0]["content"] == "a"


def test_build_messages_keeps_last_prior_turn_and_appends_current():
    history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]

    assert build_messages(history, "q2") == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]


def test_build_messages_without_history():
    assert build_messages(None, "hi") == [{"role": "user", "content": "hi"}]
