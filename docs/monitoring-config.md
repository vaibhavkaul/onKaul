# Monitoring Config

The monitoring config adds org-specific observability context for Sentry and Datadog.

## Why This Matters

- Provides team ownership and routing hints
- Improves quality of Sentry and Datadog investigations
- Encodes query patterns and tag conventions

## How to Use Each Section

- `sentry_teams`: team ownership and responsibilities for routing.
- `datadog_services`: categorize third-party services for faster triage.
- `datadog_tiers`: environment definitions used in Datadog queries.
- `datadog_common_tags`: common tags present in logs/metrics.
- `datadog_metric_prefixes`: your custom metric prefixes.
- `queue_to_team_mapping`: map queue/service keys to owning teams.
- `datadog_query_patterns`: reusable query templates.
- `sentry_query_patterns`: common Sentry search patterns.

## Example

```json
{
  "sentry_teams": {
    "payments": {
      "name": "Payments Team",
      "responsibilities": ["Checkout flows", "Payment methods", "Payouts"]
    }
  },
  "datadog_services": {
    "payment_processors": ["stripe", "adyen", "checkout-dot-com"]
  },
  "datadog_tiers": {
    "prod": {"name": "Production", "description": "Live production environment"}
  },
  "datadog_common_tags": ["tier", "service", "operation"],
  "datadog_metric_prefixes": {"custom": "org."},
  "queue_to_team_mapping": {"payments": "payments", "auth": "platform"},
  "datadog_query_patterns": {"errors_in_prod": "status:error @tier:prod"},
  "sentry_query_patterns": {"unresolved_prod": "is:unresolved environment:prod"}
}
```
