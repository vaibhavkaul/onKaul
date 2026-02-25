# onKaul

onKaul is an open-source developer assistant that can investigate issues, analyze code, and provide actionable guidance via Slack, Jira, or a local CLI.

## Status

🚧 Early release. We’re looking for contributors to help harden this for production deployments.

## What You Can Do

- Investigate incidents using Sentry/Datadog
- Search and read code across your repositories
- Ask questions in Slack/Jira and get formatted responses
- Plan fixes and open PRs automatically

## Start Here

Pick one path:

1. Local on Docker (webapp mode: API + worker + Redis)
2. Local CLI quickstart (macOS)

## Local on Docker (Webapp Mode)

Use this path if you want to run webhook endpoints locally and test end-to-end behavior.

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)

### Setup

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```bash
AGENT_PROVIDER=anthropic  # or openai
ANTHROPIC_API_KEY=sk-ant-...  # required for anthropic
OPENAI_API_KEY=sk-...  # required for openai
OPENAI_STORE=true
PUBLIC_BASE_URL=http://localhost:8000
```

For local webhook smoke tests (without Slack/Jira signature headers), set:

```bash
SLACK_VERIFY_SIGNATURE=false
ENABLE_JIRA_WEBHOOK_VERIFICATION=false
```

Start services:

```bash
docker compose up --build
```

### Verify

Health endpoint:

```bash
curl http://localhost:8000/health
```

Slack webhook smoke test:

```bash
curl -X POST http://localhost:8000/webhook/slack \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "type": "app_mention",
      "channel": "C123",
      "ts": "123.456",
      "text": "@onkaul test from local docker",
      "user": "U123"
    }
  }'
```

Jira webhook smoke test:

```bash
curl -X POST http://localhost:8000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {"key": "TEST-123"},
    "comment": {
      "body": "@onkaul test from local docker",
      "author": {"displayName": "Local Tester"}
    }
  }'
```

Check logs:

```bash
docker compose logs api bee-worker --tail=100
```

Use local shell (no Slack/Jira required for testing):

```bash
uv run onkaul
```

Stop services:

```bash
docker compose down
```

Notes:

- You may see `/health` being called every ~15 seconds. This is expected from Docker Compose healthchecks.
- Re-enable signature verification before exposing this outside localhost.

## Docs Map

1. **Overview** — what onKaul does and which mode to use
   - [docs/overview.md](./docs/overview.md)
2. **CLI Quickstart (macOS)** — get a local CLI working fast
   - [docs/quickstart.md](./docs/quickstart.md)
3. **Configuration** — required/optional `.env` values
   - [docs/configuration.md](./docs/configuration.md)
4. **Webapp Deploy (Docker, EC2, ECS)** — deployment-focused guide
   - [docs/deploy-webapp-aws.md](./docs/deploy-webapp-aws.md)
5. **Repository Config** — teach onKaul about your codebases
   - [docs/repository-config.md](./docs/repository-config.md)
6. **Monitoring Config** — add Sentry/Datadog context and routing
   - [docs/monitoring-config.md](./docs/monitoring-config.md)
7. **Integrations** — set up external systems
   - [docs/integrations-slack.md](./docs/integrations-slack.md)
   - [docs/integrations-jira.md](./docs/integrations-jira.md)
   - [docs/integrations-github.md](./docs/integrations-github.md)
   - [docs/integrations-datadog.md](./docs/integrations-datadog.md)
   - [docs/integrations-sentry.md](./docs/integrations-sentry.md)
   - [docs/integrations-confluence.md](./docs/integrations-confluence.md)
8. **Troubleshooting** — common errors and fixes
   - [docs/troubleshooting.md](./docs/troubleshooting.md)

## Features

- 🤖 Anthropic or OpenAI for core investigations (configurable)
- 🧠 Codex/Claude headless execution for planning and code edits
- 🧵 Slack and Jira integrations with structured, formatted responses
- 🛠️ Fix planning and PR creation workflows (plan → apply → push)
- 🔎 GitHub code search and file reading via `gh` CLI
- 📚 Confluence knowledge base lookups (optional)
- 📈 Sentry investigations (issues, stacktraces, frequency)
- 📊 Datadog investigations (logs, monitors, metrics, incidents, events)
- 📎 Attachments: OCR, PDF, and text extraction
- 🧾 Structured logs for responses and tool usage

## Project Policies

- LICENSE
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md
- SUPPORT.md
