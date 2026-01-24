# onKaul

Internal developer assistant agent for TapTap Send.

Tag `@onkaul` in Slack or Jira to investigate issues, analyze code, and get actionable guidance.

## Status

✅ **Phase 1**: Webhook Handlers - Complete
✅ **Phase 2**: Agent Loop + Tools - Complete
🚧 **Phase 3**: External Integrations - Not Started

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

**Required for Phase 2 (Agent Investigation):**
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com/
```

**Optional - for full tool functionality:**
```bash
# GitHub - for code search and file reading
GITHUB_TOKEN=ghp_...           # Get from https://github.com/settings/tokens
GITHUB_ORG=taptapsend

# Sentry - for error investigation
SENTRY_TOKEN=sntrys_...        # Get from Sentry.io settings
SENTRY_ORG=your-org

# Datadog - for log queries
DATADOG_API_KEY=...
DATADOG_APP_KEY=...

# Jira - uses acli CLI (must be installed separately)
JIRA_BASE_URL=https://yourcompany.atlassian.net
```

**Phase 3 only (not needed yet):**
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
```

**Note**: The bot works without API keys but will return helpful setup messages instead of real investigations.

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
│   └── webhooks.py         # Webhook endpoints
├── utils/
│   └── logger.py           # Response logger
├── worker/
│   └── tasks.py            # Background task handlers
├── logs/                   # Response logs (gitignored)
├── main.py                 # FastAPI app
├── config.py               # Configuration
├── pyproject.toml          # Project config (uv)
├── requirements.txt        # Dependencies (pip)
└── README.md
```

## Implementation Phases

- [x] **Phase 1**: Webhook handlers + logging
- [x] **Phase 2**: Agent loop + tool system (current)
- [ ] **Phase 3**: External integrations (Slack/Jira posting, security)

### Phase 2 Features

The agent can now:
- 🔍 **Investigate Sentry errors** - Fetch stacktraces, frequency, affected users
- 📁 **Search GitHub code** - Find relevant files in appian-frontend/appian-server
- 📄 **Read files** - Get full file contents from repos
- 📊 **Query Datadog logs** - Search production logs for issues
- 🎫 **Search Jira** - Find related tickets and context
- 🌐 **Web search** - Look up documentation (placeholder)

The agent uses tools autonomously to investigate issues and provides:
- Investigation breadcrumbs (what it checked)
- Confidence score (🟢 High, 🟡 Medium, 🔴 Low)
- Impact assessment (severity, users affected)
- Root cause analysis with file references
- Claude Code prompts for fixes

See [plan.md](./plan.md) for detailed implementation plan.
