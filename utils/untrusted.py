"""Mark external content as data so the model does not follow instructions in it.

Tool results, fetched pages, ticket text, logs and attachments can all contain
text written by someone other than the user (prompt injection). Everything from
outside is wrapped in a tag the system prompt tells the model to treat as data.
"""

from __future__ import annotations

import re

TAG = "untrusted_content"

# The content must not be able to close (or open) the wrapper itself.
_TAG_RE = re.compile(rf"<(/?)\s*{TAG}", re.IGNORECASE)


def wrap_untrusted(source: str, content: str) -> str:
    """Wrap ``content`` from ``source`` (a tool name, "attachment: x.pdf", ...)."""
    safe_source = re.sub(r'["<>\n]', "", source)
    safe_content = _TAG_RE.sub(lambda m: f"&lt;{m.group(1)}{TAG}", content)
    return f'<{TAG} source="{safe_source}">\n{safe_content}\n</{TAG}>'
