# Jira Integration

## Setup

1. Create a Jira webhook for issue comments.
2. Add a custom header:
   - Header name: `X-Webhook-Secret`
   - Header value: your secret
3. Set `JIRA_WEBHOOK_SECRET` in `.env`.
4. Set `ENABLE_JIRA_WEBHOOK_VERIFICATION=true`.

## What This Enables

- Jira comment investigations
- ADF formatted responses
- Linking investigations to tickets
