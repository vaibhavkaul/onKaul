"""Regulatory publication extraction tool."""

import re


def is_regulatory_request(text: str) -> bool:
    """
    Check if message is requesting regulatory publication extraction.

    Args:
        text: Message text

    Returns:
        True if this is a regulatory publication request
    """
    text_lower = text.lower()
    has_regulatory = "regulatory" in text_lower or "regulation" in text_lower
    has_url = bool(re.search(r"https?://", text))

    return has_regulatory and has_url


def extract_regulatory_url(text: str) -> str | None:
    """
    Extract regulatory publication URL from text.

    Supports: FCA, SEC, FinCEN, DFSA, MAS, etc.

    Args:
        text: Message text

    Returns:
        URL if found, None otherwise
    """
    # Match common regulatory domains
    regulatory_domains = [
        r"fca\.org\.uk",
        r"sec\.gov",
        r"fincen\.gov",
        r"dfsa\.ae",
        r"mas\.gov\.sg",
        r"treasury\.gov",
        r"consumerfinance\.gov",  # CFPB
        r"federalreserve\.gov",
        r"occ\.gov",
        r"fdic\.gov",
    ]

    pattern = rf"(https?://(?:www\.)?(?:{'|'.join(regulatory_domains)})[^\s<>]+)"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(1)

    # Fallback: any HTTPS URL if "regulatory" keyword present
    if "regulatory" in text.lower() or "regulation" in text.lower():
        match = re.search(r"(https?://[^\s<>]+)", text)
        if match:
            return match.group(1)

    return None


def format_regulatory_summary(data: dict) -> str:
    """
    Format regulatory publication data for Slack/Jira.

    Args:
        data: Dict with jurisdiction, date, summary, calls_to_action, url

    Returns:
        Formatted markdown summary
    """
    jurisdiction = data.get("jurisdiction", "Unknown")
    date = data.get("date_of_implementation", "Not specified")
    summary = data.get("summary", "")
    calls_to_action = data.get("calls_to_action", [])
    url = data.get("url", "")

    # Build output
    output = f"""📋 **Regulatory Publication Summary**

**Jurisdiction:** {jurisdiction}

**Date of Implementation:** {date}

**Summary:**
{summary}

**Calls to Action:**
"""

    for i, call in enumerate(calls_to_action, 1):
        output += f"{i}. {call}\n"

    output += f"\n🔗 Source: {url}"

    return output
