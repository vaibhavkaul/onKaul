# onKaul

onKaul is an open-source developer assistant with two modes: an **AI investigation & fix agent** that connects to your tooling (Slack, Jira, Sentry, Datadog, GitHub), and a **cloud sandbox** that gives every repo a live preview + Claude Code terminal in the browser — with multiplayer support so two people can code together in the same session.

## Status

🚧 Early release. We’re looking for contributors to help harden this for production deployments.

## What You Can Do

### AI Investigation & Fix Agent
- Investigate incidents using Sentry/Datadog — pull stacktraces, correlate logs, find root causes
- Search and read code across your repositories
- Ask questions in Slack/Jira and get formatted, cited responses
- Plan fixes and open PRs automatically

### Cloud Sandbox (Web UI)
- Spin up a live preview + Claude Code terminal for any repo in one click
- Create new projects from scratch (Static, Vite/React, or Fullstack Vite + FastAPI)
- Claude auto-launches inside the sandbox with full permissions — just start coding
- Upload assets (images, files up to 20MB) directly into the sandbox
- Push changes to a new GitHub branch and open a PR from the UI
- **Share a session** — generate a URL and anyone with the link gets the same live preview + a shared terminal (real-time multiplayer coding via tmux)
- Preview how your app looks on 9 device presets: 4K, 2K, FHD, Desktop, Laptop, iPad, iPhone 15, Pixel 8, Galaxy S24

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
9. **Sandbox** — live preview + Claude Code terminal for repos
   - [docs/sandbox.md](./docs/sandbox.md)

## Features

### AI Agent
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

### Sandbox (Web UI)
- 🖥️ Live preview iframe with hot reload (SSE file watching) + resizable split pane
- 🤖 Claude Code terminal — auto-launches with `bypassPermissions` so Claude can code immediately
- 📁 Three project types: Static HTML, Vite/React, Fullstack (Vite + FastAPI)
- ✨ New project creation from scratch — no repo required to start
- 🔗 Link an existing GitHub repo to any project and push PRs from the UI
- 🗑️ Delete projects directly from the sidebar
- 📤 Asset upload — drag-and-drop files (images, etc.) up to 20 MB, 20 files per sandbox
- 🔄 Reset sandbox to last commit with one click
- 🚀 Push to PR — creates a new branch, commits all changes, pushes, and opens a GitHub PR
- 🔗 Shareable URLs — generate a token link; anyone with it gets the live preview + terminal
- 👥 Multiplayer coding — shared tmux session means both users type and see the same Claude Code terminal in real time
- 📱 Device preview — 9 presets (4K → Galaxy S24); each viewer picks independently

## Project Policies

- LICENSE
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md
- SUPPORT.md
