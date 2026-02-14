"""Format markdown text for Slack's mrkdwn format."""

import re


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
    text = markdown_text

    # First, convert markdown headers (## Header) to bold text
    # ## Text -> *Text*
    # ### Text -> *Text*
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert markdown bold (**text**) to Slack bold (*text*)
    # Do this multiple times to handle nested/adjacent cases
    while '**' in text:
        text = re.sub(r'\*\*([^*]+?)\*\*', r'*\1*', text)

    # Clean up any triple or more asterisks that might have been created
    # *** -> *
    text = re.sub(r'\*{3,}', '*', text)

    # Fix edge case: *emoji *Text** -> *emoji Text*
    # Remove space before closing bold after emoji
    text = re.sub(r'\*([^\*]+?)\s+\*([^\*]+?)\*', r'*\1 \2*', text)

    # Convert markdown links [text](url) to Slack links <url|text>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)

    # Remove bold wrapper around bare URLs: *https://...* -> https://...
    text = re.sub(r'\*(https?://[^\s*]+)\*', r'\1', text)

    # Convert inline code with file:line pattern to preserve backticks
    # `file.kt:123` stays as `file.kt:123`
    # This already works in Slack

    # Code blocks ``` already work in Slack, no change needed

    return text
