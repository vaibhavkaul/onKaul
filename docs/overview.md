# Overview

onKaul is an open-source developer assistant that can investigate issues, analyze code, and provide actionable guidance via Slack, Jira, or a local CLI.

## What You Can Do

- Investigate production issues using Sentry/Datadog data
- Search code across your repositories and read files
- Ask questions in Slack/Jira and receive formatted responses
- Plan fixes and open PRs using headless LLM execution

## Modes

- **Webapp mode**: runs a FastAPI server and listens to Slack/Jira webhooks.
- **CLI mode**: runs locally for private, fast investigations.
