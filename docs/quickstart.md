# Quickstart (macOS)

Status: beta. Linux version coming soon.

```bash
./setup.sh
```

This script checks dependencies, installs missing tools via Homebrew, and helps you create `.env`.

After setup, choose your core provider in `.env`:

```bash
AGENT_PROVIDER=anthropic  # or openai
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
OPENAI_STORE=true
```

## What You’ll Achieve

- Get a working CLI quickly
- Optionally enable webhooks for Slack/Jira
- Create a baseline `.env` for your org
