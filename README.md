# onKaul

onKaul is an open-source developer assistant that can investigate issues, analyze code, and provide actionable guidance via Slack, Jira, or a local CLI.

## Status

Production-ready for internal deployments. Designed to be forked and configured for your organization.

## Features

- Smart model selection for deep analysis vs quick investigations
- Slack and Jira integrations with formatted responses
- GitHub code search and file reading via `gh` CLI
- Confluence knowledge base lookups (optional)
- Sentry and Datadog investigation tools (optional)
- Attachment support (OCR, PDF, and text extraction)
- Structured logs for responses and tool usage

## Quickstart (macOS)

```bash
./setup.sh
```

This script checks dependencies, installs missing tools via Homebrew, and helps you create `.env`.

## Installation

### With uv (recommended)

```bash
uv sync
```

### With pip

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

### Required

```bash
# Agent (required)
ANTHROPIC_API_KEY=sk-ant-...

# Enable posting (optional, default: false)
ENABLE_JIRA_POSTING=true
ENABLE_SLACK_POSTING=true
```

### Integrations (optional)

```bash
# GitHub (required for code search)
GITHUB_ORG=your-github-org

# Jira
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=...
JIRA_WEBHOOK_SECRET=your-jira-webhook-secret
ENABLE_JIRA_WEBHOOK_VERIFICATION=true

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_VERIFY_SIGNATURE=true

# Sentry
SENTRY_TOKEN=...
SENTRY_ORG=your-sentry-org

# Datadog
DD_API_KEY=...
DD_APP_KEY=...
DD_SITE=datadoghq.com

# Confluence
CONFLUENCE_EMAIL=your.email@company.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_CLOUD_ID=...
CONFLUENCE_WIKI_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_API_BASE_URL=https://api.atlassian.com/ex/confluence

# Repo configuration
REPO_CONFIG_PATH=./repository_config/repo_config_example.json
```

## Slack Setup

1. Create a Slack app in your workspace.
2. Enable Event Subscriptions and set the Request URL to:
   `https://your-host/webhook/slack`
3. Subscribe to the `app_mention` bot event.
4. Add OAuth scopes (minimum): `chat:write`, `reactions:write`, and a history scope.
5. Install the app to your workspace.
6. Set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` in your `.env`.

## Jira Webhook Secret

Add a custom header to your Jira webhook:
- Header name: `X-Webhook-Secret`
- Header value: your secret

Then set `JIRA_WEBHOOK_SECRET` in your `.env`.
If you need to disable verification (local dev), set `ENABLE_JIRA_WEBHOOK_VERIFICATION=false`.

## Running

### Development Server

```bash
uv run uvicorn main:app --reload --port 8000
```

Server will be available at `http://localhost:8000`.

### Dockerized (API + Workers + Redis)

```bash
docker compose up --build
```

### CLI (Local)

```bash
uv run onkaul
```

Type your request and press Enter. Use `/exit` or `/quit` to leave.

## Testing Webhooks

### Slack

```bash
curl -X POST http://localhost:8000/webhook/slack \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "type": "app_mention",
      "channel": "C123456",
      "ts": "1234567890.123456",
      "thread_ts": "1234567890.123456",
      "text": "@onkaul investigate error in payment flow",
      "user": "U789"
    }
  }'
```

### Jira

```bash
curl -X POST http://localhost:8000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {"key": "B2B-456"},
    "comment": {
      "body": "@onkaul can you investigate this issue?",
      "author": {"displayName": "Sarah"}
    }
  }'
```

## Logs

Responses are logged to:
- Console: real-time structured output
- File: `logs/responses.jsonl` (JSON Lines)

```bash
tail -f logs/responses.jsonl | jq
```

## Code Quality

```bash
uv run ruff format .
uv run ruff check .
```

## Testing

```bash
uv run pytest
```

## Project Structure

```
onKaul/
├── api/
│   └── webhooks.py              # Slack/Jira webhook endpoints
├── agent/
│   ├── core.py                  # Agent loop with tool use
│   └── prompts.py               # System prompt (dynamic from config)
├── clients/
│   ├── sentry.py                # Sentry REST API
│   ├── github.py                # gh CLI wrapper
│   ├── jira.py                  # acli CLI wrapper
│   ├── datadog.py               # Datadog API
│   └── slack.py                 # Slack API
├── tools/
│   ├── schemas.py               # Tool definitions
│   └── handlers.py              # Tool execution
├── utils/
│   ├── logger.py                # Response logger (JSONL)
│   └── slack_formatter.py       # Markdown to mrkdwn
├── worker/
│   └── tasks.py                 # Background investigation handlers
├── repository_config/
│   └── repositories.py          # Repo metadata loader
├── logs/                        # Response logs (gitignored)
├── main.py                      # FastAPI app
├── config.py                    # Environment config
├── pyproject.toml               # Project metadata
└── README.md
```

## Project Policies

- [LICENSE](./LICENSE)
- [CONTRIBUTING](./CONTRIBUTING.md)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Security](./SECURITY.md)
- [Support](./SUPPORT.md)
