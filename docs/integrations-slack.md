# Slack Integration

## Setup

1. Create a Slack app in your workspace.
2. Enable Event Subscriptions and set the Request URL to:
   `https://your-host/webhook/slack`
3. Subscribe to the `app_mention` bot event.
4. Add OAuth scopes (minimum): `chat:write`, `reactions:write`, and a history scope.
5. Install the app to your workspace.
6. Set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` in your `.env`.

## What This Enables

- Slack @mention investigations
- Structured, formatted responses with reactions
- Thread context gathering
