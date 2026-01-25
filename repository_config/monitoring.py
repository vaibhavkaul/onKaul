"""Monitoring configuration for TapTap Send - Sentry teams, Datadog tags, service context.

Extracted from appian-server configuration.
"""

# Sentry team ownership mapping
SENTRY_TEAMS = {
    "accounts": {
        "name": "Accounts Team",
        "responsibilities": ["User accounts", "Authentication", "Profile management"],
    },
    "b2b": {
        "name": "B2B Team",
        "responsibilities": [
            "Business-to-business features",
            "Batch payments",
            "Business wallets",
            "KYB",
        ],
    },
    "core": {
        "name": "Core Team",
        "responsibilities": [
            "Core platform logic",
            "KYC verification",
            "Remittance core flows",
            "Default fallback team",
        ],
    },
    "expansion": {
        "name": "Expansion Team",
        "responsibilities": [
            "New corridor integrations",
            "Remittance service providers",
            "Third-party payment integrations",
        ],
    },
    "internal-tools": {
        "name": "Internal Tools Team",
        "responsibilities": ["Admin tools", "Internal dashboards", "Operations tooling"],
    },
    "new-products": {
        "name": "New Products Team",
        "responsibilities": [
            "Debit cards",
            "Payment methods",
            "Checkout flows",
            "New payment products",
        ],
    },
    "platform": {
        "name": "Platform Team",
        "responsibilities": [
            "Infrastructure",
            "Auth system",
            "API gateway",
            "Monitoring/observability",
        ],
    },
}

# Common Datadog service tags (from external integrations)
DATADOG_SERVICES = {
    "payment_processors": [
        "adyen",
        "checkout-dot-com",
        "worldpay",
        "mastercard",
        "visa-direct",
        "stripe",
    ],
    "mobile_money": ["bkash", "mtn", "orange-money", "wave", "airtel-money", "m-pesa"],
    "remittance_providers": ["thunes", "terrapay", "fincra", "dlocal", "interswitch"],
    "banks": ["hdfc", "icici", "equity", "gt-bank", "habib-bank"],
    "kyc_verification": ["jumio", "onfido", "efr", "alloy"],
    "fraud_detection": ["sift", "chainalysis"],
    "notifications": ["twilio", "infobip", "mandrill"],
    "infrastructure": ["aws-s3", "dynamodb", "sqs", "redis"],
}

# Datadog environments
DATADOG_TIERS = {
    "dev": {"name": "Development", "description": "Local development environment"},
    "staging": {"name": "Staging", "description": "Pre-production testing"},
    "prod": {"name": "Production", "description": "Live production environment"},
}

# Common Datadog tags
DATADOG_COMMON_TAGS = [
    "tier",  # dev, staging, prod
    "env",  # Environment
    "service",  # External service name
    "operation",  # Service operation
    "clientPlatform",  # ios, android
    "clientVersion",  # App version
    "container_id",  # ECS container ID
]

# Custom metric prefixes
DATADOG_METRIC_PREFIXES = {
    "custom": "tts.",  # All custom TapTap Send metrics
    "third_party": "tts.3rd_party_api_",  # External API metrics
}

# Queue-to-team mapping (sample - full list has 200+ queues)
QUEUE_TO_TEAM_MAPPING = {
    # New Products team
    "payments": "new-products",
    "adyen": "new-products",
    "checkout-dot-com": "new-products",
    "debit": "new-products",
    "debit-cards": "new-products",
    # Core team
    "kyc": "core",
    "onfido": "core",
    "efr": "core",
    "jumio": "core",
    "namsor": "core",
    # Platform team
    "auth": "platform",
    # Expansion team (most remittance integrations)
    "thunes": "expansion",
    "mastercard": "expansion",
    "interswitch": "expansion",
    "terrapay": "expansion",
    "fincra": "expansion",
}

# Helpful query patterns
DATADOG_QUERY_PATTERNS = {
    "errors_by_service": "status:error @service:{service_name}",
    "errors_in_prod": "status:error @tier:prod",
    "slow_requests": "@latency:>1000 @tier:prod",
    "third_party_errors": "@service:* status:error",
    "mobile_errors": "@clientPlatform:(ios OR android) status:error",
    "recent_deployments": "tags:deployment",
}

SENTRY_QUERY_PATTERNS = {
    "by_team": "assigned:#team-name",
    "unresolved_prod": "is:unresolved environment:prod",
    "recent_errors": "is:unresolved firstSeen:-24h",
}


def get_sentry_team(team_key: str) -> dict:
    """Get Sentry team information."""
    return SENTRY_TEAMS.get(team_key, {})


def get_all_sentry_teams() -> dict:
    """Get all Sentry teams."""
    return SENTRY_TEAMS


def get_datadog_services_by_category(category: str) -> list:
    """Get Datadog services by category."""
    return DATADOG_SERVICES.get(category, [])


def get_datadog_query_pattern(pattern_name: str, **kwargs) -> str:
    """Get a common Datadog query pattern with substitutions."""
    pattern = DATADOG_QUERY_PATTERNS.get(pattern_name, "")
    return pattern.format(**kwargs) if pattern else ""
