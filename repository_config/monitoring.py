"""Monitoring configuration template - Sentry teams, Datadog tags, service context."""

# Sentry team ownership mapping
SENTRY_TEAMS = {
    "accounts": {
        "name": "Accounts Team",
        "responsibilities": ["User accounts", "Authentication", "Profile management"],
    },
    "payments": {
        "name": "Payments Team",
        "responsibilities": ["Checkout flows", "Payment methods", "Payouts"],
    },
    "core": {
        "name": "Core Platform Team",
        "responsibilities": ["Core APIs", "Data models", "Shared services"],
    },
    "growth": {
        "name": "Growth Team",
        "responsibilities": ["Onboarding", "Activation", "Conversion funnels"],
    },
    "internal-tools": {
        "name": "Internal Tools Team",
        "responsibilities": ["Admin tools", "Internal dashboards", "Operations tooling"],
    },
    "platform": {
        "name": "Platform Team",
        "responsibilities": ["Infrastructure", "Auth system", "Observability"],
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
    "custom": "org.",  # Custom metrics prefix
    "third_party": "org.3rd_party_api_",  # External API metrics
}

# Queue-to-team mapping (sample - full list has 200+ queues)
QUEUE_TO_TEAM_MAPPING = {
    "payments": "payments",
    "checkout": "payments",
    "payouts": "payments",
    "kyc": "core",
    "fraud": "core",
    "auth": "platform",
    "ops": "internal-tools",
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
