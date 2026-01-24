# onKaul

Internal developer assistant agent for TapTap Send.

Tag `@onkaul` in Slack or Jira to investigate issues, analyze code, and get actionable guidance.

## Status

✅ **Phase 1**: Webhook Handlers - Complete
✅ **Phase 2**: Agent Loop + Tools - Complete
✅ **Phase 2.5**: Jira + Slack Posting - Complete
🚧 **Phase 3**: Security & Production (rate limiting, auth verification) - Not Started

**Current Features:**
- Real investigations using Claude Sonnet 4
- Posts responses to Jira tickets (optional)
- Posts responses to Slack threads (optional)
- Immediate :onkaul: emoji reactions in Slack
- Formatted responses with mrkdwn for Slack
- Fetches thread context and Jira comments
- Detailed real-time logging of agent activity

See [plan.md](./plan.md) for full implementation details.

## Setup

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

**With uv (recommended):**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

**With pip:**

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

**Required:**
```bash
# Agent (required)
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com/

# Enable posting (optional, default: false)
ENABLE_JIRA_POSTING=true      # Set to true to post comments to Jira
ENABLE_SLACK_POSTING=true     # Set to true to post replies in Slack
```

**Tool Integration (required for investigations):**
```bash
# Sentry - for error investigation (from ~/.sentryclirc)
SENTRY_TOKEN=sntrys_...
SENTRY_ORG=taptapsend

# GitHub - uses gh CLI (must be authenticated: gh auth login)
GITHUB_ORG=taptapsend

# Jira - uses acli CLI (must be installed and configured)
JIRA_BASE_URL=https://taptapsend.atlassian.net

# Slack - for posting responses (get from Slack app settings)
SLACK_BOT_TOKEN=xoxb-...

# Datadog - optional for log queries
DATADOG_API_KEY=...
DATADOG_APP_KEY=...
```

**Prerequisites:**
- `gh` CLI: `brew install gh && gh auth login`
- `acli` CLI: See [Atlassian CLI docs](https://developer.atlassian.com/cloud/acli/)
- Sentry token in `~/.sentryclirc`

**Note**: The bot works without API keys but will return helpful setup messages.

## Running

### Development Server

```bash
# With uv
uv run uvicorn main:app --reload --port 8000

# With pip (after activating venv)
uvicorn main:app --reload --port 8000
```

Server will be available at http://localhost:8000

### Testing Webhooks

**Slack webhook:**

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

**Jira webhook:**

```bash
curl -X POST http://localhost:8000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {"key": "B2B-456"},
    "comment": {
      "body": "@onkaul can you investigate this Sentry issue?",
      "author": {"displayName": "Sarah"}
    }
  }'
```

### Check Logs

Responses are logged to:
- **Console**: Real-time structured output
- **File**: `logs/responses.jsonl` (JSON Lines format)

```bash
# Tail the response log
tail -f logs/responses.jsonl | jq
```

## Development

### Code Quality

```bash
# Format and lint
uv run ruff format .
uv run ruff check .

# Type checking
uv run mypy .
```

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=. --cov-report=html
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
│   ├── schemas.py               # Tool definitions for Claude
│   └── handlers.py              # Tool execution
├── utils/
│   ├── logger.py                # Response logger (JSONL)
│   └── slack_formatter.py       # Markdown → mrkdwn
├── worker/
│   └── tasks.py                 # Background investigation handlers
├── repository_config/
│   └── repositories.py          # TapTap Send repo metadata
├── logs/                        # Response logs (gitignored)
├── main.py                      # FastAPI app
├── config.py                    # Environment config
├── .env                         # API keys (gitignored)
├── pyproject.toml               # uv config
└── README.md
```

## Features

### Investigation Tools
- 🔍 **Sentry** - Fetch error details, stacktraces, frequency, affected users
- 📁 **GitHub** - Search code in appian-frontend/appian-server (via `gh` CLI)
- 📄 **Read Files** - Get full file contents from repos
- 📊 **Datadog** - Query production logs (if configured)
- 🎫 **Jira** - Fetch issue details + comments (via `acli` CLI)

### Response Capabilities
- **Slack**: Posts formatted responses in threads with :onkaul: reaction
- **Jira**: Posts formatted comments to tickets
- **Logging**: All responses logged to console + `logs/responses.jsonl`
- **Real-time**: Detailed logging shows each tool use as it happens

### Response Format
Investigations include:
- 🔍 **Investigation Path** - What the agent checked
- 📊 **Confidence Score** - 🟢 High / 🟡 Medium / 🔴 Low
- ⚠️ **Impact Assessment** - Severity, users affected, related issues
- 📝 **Findings** - Root cause with file:line references
- 💻 **Claude Code Prompt** - (Only when user asks for fix)

### Configuration
- **Max Iterations**: 100 (allows very thorough investigations)
- **Max Output**: 8,192 tokens (comprehensive responses)
- **Thread Context**: Reads Slack thread history and Jira comments
- **Smart Routing**: Uses correct repo based on error type

## Implementation Status

- [x] **Phase 1**: Webhook handlers + logging
- [x] **Phase 2**: Agent loop + tool system
- [x] **Phase 2.5**: Jira + Slack posting with formatting
- [ ] **Phase 3**: Security (rate limiting, signature verification, allowlists)

See [plan.md](./plan.md) for detailed implementation plan.
