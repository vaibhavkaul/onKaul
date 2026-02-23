# onKaul

onKaul is an open-source developer assistant that can investigate issues, analyze code, and provide actionable guidance via Slack, Jira, or a local CLI.

## Status

🚧 Early release. We’re looking for contributors to help harden this for production deployments.

## What You’ll Build

By following the docs below you can:
- Investigate incidents using Sentry/Datadog
- Search and read code across your repositories
- Ask questions in Slack/Jira and get formatted responses
- Plan fixes and open PRs automatically

## Getting Started (in order)

1. **Overview** — what onKaul does and which mode to use
   - [docs/overview.md](./docs/overview.md)
2. **Quickstart** — get a local CLI working fast (macOS)
   - [docs/quickstart.md](./docs/quickstart.md)
3. **Configuration** — required/optional `.env` values
   - [docs/configuration.md](./docs/configuration.md)
4. **Repository Config** — teach onKaul about your codebases
   - [docs/repository-config.md](./docs/repository-config.md)
5. **Monitoring Config** — add Sentry/Datadog context and routing
   - [docs/monitoring-config.md](./docs/monitoring-config.md)
6. **Integrations** — set up external systems
   - [docs/integrations-slack.md](./docs/integrations-slack.md)
   - [docs/integrations-jira.md](./docs/integrations-jira.md)
   - [docs/integrations-github.md](./docs/integrations-github.md)
   - [docs/integrations-datadog.md](./docs/integrations-datadog.md)
   - [docs/integrations-sentry.md](./docs/integrations-sentry.md)
   - [docs/integrations-confluence.md](./docs/integrations-confluence.md)
7. **Troubleshooting** — common errors and fixes
   - [docs/troubleshooting.md](./docs/troubleshooting.md)

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

## Project Policies

- LICENSE
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md
- SUPPORT.md
