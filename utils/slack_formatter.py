"""Format markdown text for Slack's mrkdwn format."""

import re

# Fenced code blocks and inline code spans are passed through untouched, so
# things like `**kwargs` or `a ** b` inside code are never rewritten.
_CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def format_for_slack(markdown_text: str) -> str:
    """
    Convert markdown to Slack's mrkdwn format.

    Slack differences from markdown:
    - Bold: *text* (single asterisk, not double **)
    - Headers: No ## support, use *bold text* instead
    - Code blocks: ``` works
    - Lists: - works
    - Links: <url|text> instead of [text](url)

    Args:
        markdown_text: Text in standard markdown format

    Returns:
        Text formatted for Slack mrkdwn
    """
    parts: list[str] = []
    last = 0
    for match in _CODE_RE.finditer(markdown_text):
        parts.append(_format_prose(markdown_text[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_format_prose(markdown_text[last:]))
    return "".join(parts)


def _format_prose(text: str) -> str:
    """Format a stretch of markdown that contains no code."""
    # Headers become bold lines; strip bold markers inside them so
    # "## 🔍 **Summary**" becomes "*🔍 Summary*" rather than nested asterisks.
    text = re.sub(
        r"^#{1,6}\s+(.+?)\s*$",
        lambda m: f"*{m.group(1).replace('**', '').strip()}*",
        text,
        flags=re.MULTILINE,
    )

    # Bold-italic ***text*** -> Slack bold *text*
    text = re.sub(r"\*{3}([^*\n]+?)\*{3}", r"*\1*", text)

    # Bold **text** -> *text*. A single pass: unmatched ** are left as-is.
    text = re.sub(r"\*\*([^*\n]+?)\*\*", r"*\1*", text)

    # Links [text](url) -> <url|text>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)

    # Remove bold wrapper around bare URLs: *https://...* -> https://...
    text = re.sub(r"\*(https?://[^\s*]+)\*", r"\1", text)

    return text
