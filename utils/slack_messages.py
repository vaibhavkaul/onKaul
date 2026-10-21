"""Turn raw Slack messages into plain text and conversation history.

Alert bots (Sentry, Datadog, PagerDuty, ...) put most of their content —
including the links worth investigating — in Block Kit ``blocks`` or legacy
``attachments``, often with an empty or summary-only ``text``.
"""

from __future__ import annotations


def message_text(msg: dict) -> str:
    """Render a Slack message's text, blocks and attachments as one string."""
    lines: list[str] = []
    _add(lines, msg.get("text", ""))
    for block in msg.get("blocks") or []:
        _render_block(block, lines)
    for att in msg.get("attachments") or []:
        _render_attachment(att, lines)
    return "\n".join(lines)


def thread_to_history(messages: list[dict], own_bot_id: str | None) -> list[dict]:
    """Convert Slack thread messages to ``{role, content}`` turns.

    Only onKaul's own messages become ``assistant``; other bots' messages
    (alerts) are user-side context, labelled with the bot's name.
    """
    history: list[dict] = []
    for msg in messages:
        content = message_text(msg)
        if not content:
            continue
        bot_id = msg.get("bot_id")
        if bot_id and own_bot_id and bot_id == own_bot_id:
            history.append({"role": "assistant", "content": content})
            continue
        if bot_id:
            name = (msg.get("bot_profile") or {}).get("name") or msg.get("username") or "bot"
            content = f"[message from {name}]\n{content}"
        history.append({"role": "user", "content": content})
    return history


def _add(lines: list[str], text: str | None) -> None:
    text = (text or "").strip()
    if text and text not in lines:
        lines.append(text)


def _text_of(obj: dict | None) -> str:
    return (obj or {}).get("text", "") if isinstance(obj, dict) else ""


def _render_block(block: dict, lines: list[str]) -> None:
    kind = block.get("type")
    if kind in ("section", "header"):
        _add(lines, _text_of(block.get("text")))
        for field in block.get("fields") or []:
            _add(lines, _text_of(field))
        _render_element(block.get("accessory") or {}, lines)
    elif kind == "context":
        for element in block.get("elements") or []:
            _add(lines, _text_of(element))
    elif kind == "actions":
        for element in block.get("elements") or []:
            _render_element(element, lines)
    elif kind == "rich_text":
        _add(lines, _rich_text(block.get("elements") or []))


def _render_element(element: dict, lines: list[str]) -> None:
    url = element.get("url")
    if url:
        text = element.get("text")
        label = text if isinstance(text, str) else _text_of(text)
        _add(lines, f"{label}: {url}" if label else url)


def _rich_text(elements: list[dict]) -> str:
    out: list[str] = []
    for el in elements:
        kind = el.get("type")
        if kind == "text":
            out.append(el.get("text", ""))
        elif kind == "link":
            label = el.get("text")
            out.append(f"{label} ({el['url']})" if label else el.get("url", ""))
        elif kind == "user":
            out.append(f"<@{el.get('user_id', '')}>")
        elif kind == "channel":
            out.append(f"<#{el.get('channel_id', '')}>")
        elif kind == "emoji":
            out.append(f":{el.get('name', '')}:")
        elif "elements" in el:
            out.append(_rich_text(el["elements"]))
            if kind in ("rich_text_section", "rich_text_preformatted", "rich_text_quote"):
                out.append("\n")
    return "".join(out).strip()


def _render_attachment(att: dict, lines: list[str]) -> None:
    _add(lines, att.get("pretext"))
    title = att.get("title")
    link = att.get("title_link")
    if title or link:
        _add(lines, f"{title}: {link}" if title and link else title or link)
    _add(lines, att.get("text"))
    for field in att.get("fields") or []:
        _add(lines, f"{field.get('title', '')}: {field.get('value', '')}".strip(": "))
    for action in att.get("actions") or []:
        _render_element(action, lines)
    _add(lines, att.get("from_url"))
    if len(lines) == 0:
        _add(lines, att.get("fallback"))
