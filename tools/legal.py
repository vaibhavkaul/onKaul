"""Legal compliance rules for TapTap Send marketing materials.

These rules are extracted from the tts-legal AI review system.
"""

LEGAL_COMPLIANCE_RULES = {
    "fx_disclaimers": {
        "description": "Foreign Exchange (FX) disclosure requirements",
        "rules": [
            {
                "rule": "FX Rates Disclosure",
                "requirement": "All marketing content must include 'FX rates apply'",
                "severity": "CRITICAL",
            },
            {
                "rule": "Exchange Rate Language - Dynamic",
                "requirement": "Exchange rates as of [date] at [time]. Exchange rates are dynamic and subject to fluctuation",
                "severity": "CRITICAL",
            },
            {
                "rule": "Exchange Rate Language - Illustrative",
                "requirement": "Exchange rates for illustrative purposes only. Exchange rates are dynamic and subject to fluctuation",
                "severity": "CRITICAL",
            },
        ],
    },
    "transfer_claims": {
        "description": "Transfer speed and fee claim requirements",
        "rules": [
            {
                "rule": "Speed Claims",
                "requirement": "X% of transfers to [Country] were delivered in X minutes on [Reference Date]",
                "severity": "CRITICAL",
            },
            {
                "rule": "Fee Disclosure",
                "requirement": "Fee information must disclose that FX rates apply",
                "severity": "CRITICAL",
            },
        ],
    },
    "geographic_disclosures": {
        "description": "Jurisdiction-specific regulatory disclosures",
        "rules": [
            {
                "jurisdiction": "UAE",
                "requirement": "Taptap Send (DIFC) Limited is authorized and regulated by the Dubai Financial Services Authority (DFSA)",
                "severity": "CRITICAL",
            },
            {
                "jurisdiction": "Australia",
                "requirement": "Taptap Send Australia Pty Ltd (ABN 21 675 932 386) Australian Financial Services Licence No. 559468",
                "severity": "CRITICAL",
            },
            {
                "jurisdiction": "USA",
                "requirement": "TapTap Send Payments Co., licensed as a Money Transmitter by the Banking Department of the State of New York. NMLS ID: 2108069",
                "severity": "CRITICAL",
            },
            {
                "jurisdiction": "Rhode Island",
                "requirement": "Licensed as Currency Transmitter",
                "severity": "CRITICAL",
            },
            {
                "jurisdiction": "Massachusetts",
                "requirement": "Licensed as Foreign Transmittal Agency (License FT2108069)",
                "severity": "CRITICAL",
            },
        ],
    },
    "content_type_requirements": {
        "description": "Requirements based on content type",
        "rules": [
            {
                "content_type": "Email Marketing",
                "requirement": "Requires regulatory disclosure with link to full terms",
                "severity": "CRITICAL",
            },
            {
                "content_type": "Influencer/Sponsored Content",
                "requirement": "Must include #ad, #sponsored, or similar disclosure",
                "severity": "CRITICAL",
            },
            {
                "content_type": "Bonus Campaigns/Competitions",
                "requirement": "Must include key T&Cs and link to full T&Cs",
                "severity": "CRITICAL",
            },
            {
                "content_type": "Wallet-to-Wallet Mentions",
                "requirement": "EMI/regulatory disclaimers required",
                "severity": "CRITICAL",
            },
            {
                "content_type": "Philippines Cash Pickup",
                "requirement": "Specific fee and FX disclosure required",
                "severity": "HIGH",
            },
            {
                "content_type": "Morocco Cash Pickup",
                "requirement": "Specific fee and FX disclosure required",
                "severity": "HIGH",
            },
        ],
    },
    "visibility_requirements": {
        "description": "Visibility and presentation requirements",
        "rules": [
            {
                "rule": "Disclaimer Visibility",
                "requirement": "Disclaimers must be clearly visible (not hidden, not covered by UI elements)",
                "severity": "CRITICAL",
            },
        ],
    },
}


def get_compliance_rules(category: str = "all") -> dict:
    """
    Get legal compliance rules for TapTap Send marketing.

    Args:
        category: Category to retrieve (all, fx_disclaimers, geographic_disclosures, content_type_requirements)

    Returns:
        Dict with compliance rules
    """
    if category == "all":
        return {
            "source": "TapTap Send Marketing Compliance (from tts-legal system)",
            "categories": LEGAL_COMPLIANCE_RULES,
        }

    if category in LEGAL_COMPLIANCE_RULES:
        return {
            "category": category,
            "rules": LEGAL_COMPLIANCE_RULES[category],
        }

    return {"error": f"Unknown category: {category}. Available: {list(LEGAL_COMPLIANCE_RULES.keys())}"}
