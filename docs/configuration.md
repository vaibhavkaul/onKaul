# Configuration

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

## Required (all modes)

```bash
AGENT_PROVIDER=anthropic  # or openai
ANTHROPIC_API_KEY=sk-ant-...  # required when AGENT_PROVIDER=anthropic
OPENAI_API_KEY=sk-...  # required when AGENT_PROVIDER=openai
OPENAI_STORE=true  # set false to disable server-side response storage
```

## Agent Provider (core investigations)

```bash
# Core investigation provider
AGENT_PROVIDER=anthropic  # or openai

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_REASONING_MODEL=claude-opus-4-5-20251101

# OpenAI
OPENAI_API_KEY=
OPENAI_STORE=true
OPENAI_MODEL=gpt-5-mini
OPENAI_REASONING_MODEL=gpt-5
```

## App Configuration (optional, defaults shown)

```bash
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
PUBLIC_BASE_URL=http://localhost:8000
```

## Webapp Mode (required for Slack/Jira usage)

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

## Code and Repo Configuration

```bash
GITHUB_ORG=your-github-org
GITHUB_TOKEN=...  # Optional if gh CLI is already authenticated
REPO_CONFIG_PATH=./repository_config/repo_config_example.json
MONITORING_CONFIG_PATH=./repository_config/monitoring_config_example.json
```

## Optional Integrations

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

## Storage and Workspaces (optional, defaults shown)

```bash
WORKSPACE_DIR=./workplace
FIX_WORKSPACE_DIR=./fixes
```

## Background Jobs (required for webapp workers)

```bash
# Local host-run (no Docker)
# REDIS_URL=redis://localhost:6379/0

# Docker Compose (default in .env.example)
REDIS_URL=redis://redis:6379/0
REDIS_QUEUE_NAME=onkaul
JOB_TIMEOUT_SECONDS=900
```

## Fix Executor (optional, required for automated PRs)

```bash
FIX_EXECUTOR_ENGINE=codex  # or claude
CODEX_PLAN_CMD=/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never
CODEX_APPLY_CMD=/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never
CODEX_TIMEOUT_SECONDS=1200
CLAUDE_PLAN_CMD=claude -p --allowedTools "Bash,Read" --permission-mode acceptEdits --output-format text
CLAUDE_APPLY_CMD=claude -p --allowedTools "Bash,Read,Edit" --permission-mode acceptEdits --output-format text
CLAUDE_TIMEOUT_SECONDS=1200
```
