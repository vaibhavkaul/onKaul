"""Provider-neutral conversation history.

Every channel hands providers *prior* turns only — the current message is
passed separately. Providers call ``build_messages`` to get a clean,
alternating ``[{"role", "content"}, ...]`` list ending with the current turn.
"""

from __future__ import annotations


def normalize_history(history: list[dict] | None) -> list[dict]:
    """Reduce raw history to ``{role, content}`` turns that alternate, starting with user.

    Accepts web-chat messages (``role``/``content`` plus extra fields such as
    timestamps) and raw Slack messages (``user``/``text``, bots have ``bot_id``).
    """
    turns: list[dict] = []
    for msg in history or []:
        if "role" in msg:
            role = msg["role"]
            content = msg.get("content", "")
        else:
            role = "assistant" if msg.get("bot_id") else "user"
            content = msg.get("text", "")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content:
            continue
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"] += "\n\n" + content
        else:
            turns.append({"role": role, "content": content})

    if turns and turns[0]["role"] != "user":
        turns.insert(0, {"role": "user", "content": "(thread started by the bot)"})
    return turns


def build_messages(history: list[dict] | None, current_message: str) -> list[dict]:
    """Return normalized prior turns followed by the current user message."""
    return normalize_history([*(history or []), {"role": "user", "content": current_message}])
