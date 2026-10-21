from __future__ import annotations

from utils.slack_messages import message_text, thread_to_history

SENTRY_ALERT = {
    "bot_id": "B_SENTRY",
    "bot_profile": {"name": "Sentry"},
    "text": "",
    "blocks": [
        {"type": "header", "text": {"type": "plain_text", "text": "TypeError in checkout"}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "<https://sentry.io/issues/123|View issue>"},
            "fields": [{"type": "mrkdwn", "text": "*Env:* prod"}],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open trace"},
                    "url": "https://sentry.io/trace/abc",
                }
            ],
        },
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {"type": "text", "text": "Runbook: "},
                        {"type": "link", "url": "https://wiki.dev/runbook"},
                    ],
                }
            ],
        },
    ],
}


def test_message_text_renders_blocks_and_their_urls():
    text = message_text(SENTRY_ALERT)

    assert "TypeError in checkout" in text
    assert "<https://sentry.io/issues/123|View issue>" in text
    assert "*Env:* prod" in text
    assert "Open trace: https://sentry.io/trace/abc" in text
    assert "Runbook: https://wiki.dev/runbook" in text


def test_message_text_renders_legacy_attachments():
    msg = {
        "text": "Monitor alert",
        "attachments": [
            {
                "title": "High error rate",
                "title_link": "https://app.datadoghq.com/monitors/9",
                "text": "errors > 5%",
                "fields": [{"title": "Service", "value": "api"}],
                "actions": [{"type": "button", "text": "Ack", "url": "https://pd.dev/ack"}],
            }
        ],
    }

    assert message_text(msg) == "\n".join(
        [
            "Monitor alert",
            "High error rate: https://app.datadoghq.com/monitors/9",
            "errors > 5%",
            "Service: api",
            "Ack: https://pd.dev/ack",
        ]
    )


def test_message_text_skips_text_duplicated_by_blocks():
    msg = {
        "text": "hello",
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "hello"}}],
    }

    assert message_text(msg) == "hello"


def test_thread_to_history_only_own_bot_is_assistant():
    thread = [
        SENTRY_ALERT,
        {"user": "U1", "text": "<@UONKAUL> what broke?"},
        {"bot_id": "B_ONKAUL", "text": "The checkout handler."},
        {"user": "U1", "text": ""},
    ]

    history = thread_to_history(thread, own_bot_id="B_ONKAUL")

    assert [turn["role"] for turn in history] == ["user", "user", "assistant"]
    assert history[0]["content"].startswith("[message from Sentry]\nTypeError in checkout")
    assert history[2]["content"] == "The checkout handler."


def test_thread_to_history_without_own_bot_id_treats_bots_as_user():
    history = thread_to_history([{"bot_id": "B1", "text": "hi"}], own_bot_id=None)

    assert history == [{"role": "user", "content": "[message from bot]\nhi"}]


def test_people_are_labelled_with_their_slack_mention():
    history = thread_to_history(
        [{"user": "U1", "text": "it broke"}, {"user": "U2", "text": "same here"}], "B_ONKAUL"
    )

    assert history == [
        {"role": "user", "content": "<@U1>: it broke"},
        {"role": "user", "content": "<@U2>: same here"},
    ]
