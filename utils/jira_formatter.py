"""Convert markdown to Jira ADF (Atlassian Document Format)."""

import re


def markdown_to_adf(markdown_text: str) -> dict:
    """
    Convert markdown to Jira ADF format.

    Supports:
    - ## Headers (H2-H6)
    - **bold**
    - `inline code`
    - Numbered lists (1. 2. 3.)
    - Bullet lists (- item)
    - Code blocks (```)

    Args:
        markdown_text: Markdown formatted text

    Returns:
        ADF document dict ready for Jira API
    """
    content = []
    lines = markdown_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Headers (## Text)
        if line.startswith("##"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": min(level, 6)},
                    "content": _parse_inline(text),
                }
            )
            i += 1

        # Numbered list (1. Item)
        elif re.match(r"^\d+\.\s", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                text = re.sub(r"^\d+\.\s+", "", lines[i])
                items.append(
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": _parse_inline(text)}],
                    }
                )
                i += 1
            content.append({"type": "orderedList", "content": items})

        # Bullet list (- Item)
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                text = lines[i][2:]  # Remove "- "
                items.append(
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": _parse_inline(text)}],
                    }
                )
                i += 1
            content.append({"type": "bulletList", "content": items})

        # Code block (```...```)
        elif line.startswith("```"):
            # Extract language if specified (```kotlin)
            lang_match = re.match(r"```(\w+)", line)
            language = lang_match.group(1) if lang_match else None

            code_lines = []
            i += 1  # Skip opening ```
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```

            attrs = {"language": language} if language else {}
            content.append(
                {
                    "type": "codeBlock",
                    "attrs": attrs,
                    "content": [{"type": "text", "text": "\n".join(code_lines)}],
                }
            )

        # Regular paragraph
        else:
            content.append({"type": "paragraph", "content": _parse_inline(line)})
            i += 1

    return {"version": 1, "type": "doc", "content": content}


def _parse_inline(text: str) -> list:
    """
    Parse inline formatting (bold, code) in text.

    Returns list of text nodes with marks.
    """
    nodes = []
    current_pos = 0

    # Pattern for **bold** and `code`
    pattern = r"(\*\*([^*]+)\*\*|`([^`]+)`)"

    for match in re.finditer(pattern, text):
        # Add text before match
        if match.start() > current_pos:
            plain_text = text[current_pos : match.start()]
            if plain_text:
                nodes.append({"type": "text", "text": plain_text})

        # Add formatted text
        if match.group(1).startswith("**"):  # Bold
            nodes.append(
                {"type": "text", "text": match.group(2), "marks": [{"type": "strong"}]}
            )
        elif match.group(1).startswith("`"):  # Code
            nodes.append(
                {"type": "text", "text": match.group(3), "marks": [{"type": "code"}]}
            )

        current_pos = match.end()

    # Add remaining text
    if current_pos < len(text):
        remaining = text[current_pos:]
        if remaining:
            nodes.append({"type": "text", "text": remaining})

    # If no nodes, return single text node
    if not nodes:
        nodes = [{"type": "text", "text": text if text else ""}]

    return nodes
