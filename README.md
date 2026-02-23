# onKaul

onKaul is an open-source developer assistant that can investigate issues, analyze code, and provide actionable guidance via Slack, Jira, or a local CLI.

## Status

🚧 Early release. We’re looking for contributors to help harden this for production deployments. Designed to be forked and configured for your organization.

## Features

- 🤖 Claude + Codex headless execution for planning and code edits
- 🧵 Slack and Jira integrations with structured, formatted responses
- 🛠️ Fix planning and PR creation workflows (plan → apply → push)
- 🔎 GitHub code search and file reading via `gh` CLI
- 📚 Confluence knowledge base lookups (optional)
- 📈 Sentry investigations (issues, stacktraces, frequency)
- 📊 Datadog investigations (logs, monitors, metrics, incidents, events)
- 📎 Attachments: OCR, PDF, and text extraction
- 🧾 Structured logs for responses and tool usage

## Modes

### 🌐 Webapp Mode

Runs a FastAPI server and listens to Slack and Jira webhooks for @mentions and comments. Best for shared team use and always‑on incident response.

### 🧑‍💻 CLI Mode

Runs locally in your terminal for fast, private investigations. No Slack or Jira required, and great for testing prompts and workflows.

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

### Required (all modes)

```bash
# Agent
ANTHROPIC_API_KEY=sk-ant-...
```

### App Configuration (optional, defaults shown)

```bash
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
PUBLIC_BASE_URL=http://localhost:8000
```

### Webapp Mode (required for Slack/Jira usage)

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_VERIFY_SIGNATURE=true
ENABLE_SLACK_POSTING=true

# Jira
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=...
JIRA_WEBHOOK_SECRET=your-jira-webhook-secret
ENABLE_JIRA_WEBHOOK_VERIFICATION=true
ENABLE_JIRA_POSTING=true
```

### Code and Repo Configuration (required for code search / repo context)

```bash
# GitHub (required for code search)
GITHUB_ORG=your-github-org
GITHUB_TOKEN=...  # Optional if gh CLI is already authenticated

# Repo configuration
REPO_CONFIG_PATH=./repository_config/repo_config_example.json
```

#### Repository Config File

Define your org’s repos, tech stacks, and routing hints in `repository_config/repo_config_example.json`.
onKaul uses this to pick the right repo and add domain context during investigations.

**How to use each section:**
- `repositories`: your repo catalog. Use `tech_stack`, `key_systems`, and `handles` to help the agent select the right codebase and framing.
- `investigation_strategy`: map common issue categories to a default repo.
- `additional_context`: pointers to internal docs (playbooks, runbooks, commands).

**Example:**

```json
{
  "repositories": {
    "merchant-console": {
      "name": "merchant-console",
      "org": "acme",
      "description": "Merchant operations web console",
      "tech_stack": [
        "React 19 + TypeScript",
        "Vite",
        "React Router",
        "Material-UI + TailwindCSS"
      ],
      "key_systems": ["Auth", "Payouts", "Disputes"],
      "handles": ["UI bugs", "Console crashes", "Performance regressions"],
      "context_files": []
    },
    "core-api": {
      "name": "core-api",
      "org": "acme",
      "description": "Core backend API service",
      "tech_stack": [
        "Python/FastAPI",
        "PostgreSQL + SQLModel",
        "Alembic (migrations)"
      ],
      "key_systems": ["API", "Billing", "Webhooks"],
      "handles": ["API errors", "DB issues", "Latency spikes"],
      "context_files": []
    },
    "mobile-app": {
      "name": "mobile-app",
      "org": "acme",
      "description": "React Native mobile application",
      "tech_stack": [
        "React Native",
        "TypeScript/TSX",
        "Redux (state management)",
        "GraphQL (with code generation)",
        "XState (state machines)",
        "Jest (unit tests)",
        "Detox (E2E tests)"
      ],
      "key_systems": ["Wallet", "Onboarding", "Transfers"],
      "handles": ["App crashes", "Mobile UI bugs", "Sync issues"],
      "context_files": []
    }
  },
  "investigation_strategy": {
    "Frontend/UI bugs": "merchant-console",
    "API errors": "core-api",
    "Database issues": "core-api",
    "Mobile crashes": "mobile-app"
  },
  "additional_context": {
    "Sentry Integration": "/path/to/sentry-integration.md",
    "Jira Workflows": "/path/to/jira-commands.md",
    "Confluence Wiki": "/path/to/confluence-wiki.md"
  }
}
```

### Optional Integrations

```bash
# Sentry
SENTRY_TOKEN=...
SENTRY_ORG=your-sentry-org

# Datadog
DD_API_KEY=...   # or DATADOG_API_KEY
DD_APP_KEY=...   # or DATADOG_APP_KEY
DD_SITE=datadoghq.com

# Confluence
CONFLUENCE_EMAIL=your.email@company.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_CLOUD_ID=...
CONFLUENCE_WIKI_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_API_BASE_URL=https://api.atlassian.com/ex/confluence

# Brave Search
BRAVE_SEARCH_API_KEY=...
```

### Storage and Workspaces (optional, defaults shown)

```bash
WORKSPACE_DIR=./workplace
FIX_WORKSPACE_DIR=./fixes
```

### Background Jobs (required for webapp workers)

```bash
REDIS_URL=redis://localhost:6379/0
REDIS_QUEUE_NAME=onkaul
JOB_TIMEOUT_SECONDS=900
```

### Fix Executor (optional, required for automated PRs)

```bash
FIX_EXECUTOR_ENGINE=codex  # or claude
CODEX_PLAN_CMD=/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never
CODEX_APPLY_CMD=/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never
CODEX_TIMEOUT_SECONDS=1200
CLAUDE_PLAN_CMD=claude -p --allowedTools "Bash,Read" --permission-mode acceptEdits --output-format text
CLAUDE_APPLY_CMD=claude -p --allowedTools "Bash,Read,Edit" --permission-mode acceptEdits --output-format text
CLAUDE_TIMEOUT_SECONDS=1200
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

## Quickstart (macOS)

Status: beta. Linux version coming soon.

```bash
./setup.sh
```

This script checks dependencies, installs missing tools via Homebrew, and helps you create `.env`.

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
