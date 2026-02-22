"""Configuration management for onKaul."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # App settings
    APP_NAME = "onKaul"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL") or f"http://localhost:{API_PORT}"

    # Enable posting to Slack/Jira
    ENABLE_JIRA_POSTING = os.getenv("ENABLE_JIRA_POSTING", "false").lower() == "true"
    ENABLE_SLACK_POSTING = os.getenv("ENABLE_SLACK_POSTING", "false").lower() == "true"

    # Paths
    BASE_DIR = Path(__file__).parent
    LOGS_DIR = BASE_DIR / "logs"
    RESPONSE_LOG_FILE = LOGS_DIR / "responses.jsonl"
    WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR") or (BASE_DIR / "workplace"))
    FIX_WORKSPACE_DIR = Path(os.getenv("FIX_WORKSPACE_DIR") or (BASE_DIR / "fixes"))

    # AI Agent API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Slack Integration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")  # For webhook signature verification (optional)

    # Jira Integration
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

    # Confluence Integration - Read playbooks and wiki pages
    CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL") or os.getenv("ATLASSIAN_EMAIL")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
    CONFLUENCE_CLOUD_ID = os.getenv("CONFLUENCE_CLOUD_ID")
    CONFLUENCE_API_BASE_URL = os.getenv("CONFLUENCE_API_BASE_URL", "https://api.atlassian.com/ex/confluence")
    CONFLUENCE_WIKI_BASE_URL = os.getenv("CONFLUENCE_WIKI_BASE_URL")

    # Sentry
    SENTRY_TOKEN = os.getenv("SENTRY_TOKEN")
    SENTRY_ORG = os.getenv("SENTRY_ORG")

    # GitHub (uses gh CLI)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_ORG = os.getenv("GITHUB_ORG")

    # Datadog (reads from DD_ env vars - standard Datadog convention)
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY") or os.getenv("DD_API_KEY")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY") or os.getenv("DD_APP_KEY")
    DATADOG_SITE = os.getenv("DATADOG_SITE") or os.getenv("DD_SITE", "datadoghq.com")

    # Brave Search - for web research
    BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

    # Queue
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "onkaul")
    JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "900"))

    # Codex CLI (headless) for fix planning/apply
    CODEX_PLAN_CMD = os.getenv(
        "CODEX_PLAN_CMD",
        "/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never",
    )
    CODEX_APPLY_CMD = os.getenv(
        "CODEX_APPLY_CMD",
        "/Applications/Codex.app/Contents/Resources/codex exec --dangerously-bypass-approvals-and-sandbox --color never",
    )
    CODEX_TIMEOUT_SECONDS = int(os.getenv("CODEX_TIMEOUT_SECONDS", "1200"))

    # Fix executor engine: codex or claude
    FIX_EXECUTOR_ENGINE = os.getenv("FIX_EXECUTOR_ENGINE", "codex").lower()

    # Claude CLI (headless) for fix planning/apply
    CLAUDE_PLAN_CMD = os.getenv(
        "CLAUDE_PLAN_CMD",
        "claude -p --allowedTools \"Bash,Read\" --permission-mode acceptEdits --output-format text",
    )
    CLAUDE_APPLY_CMD = os.getenv(
        "CLAUDE_APPLY_CMD",
        "claude -p --allowedTools \"Bash,Read,Edit\" --permission-mode acceptEdits --output-format text",
    )
    CLAUDE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "1200"))

    @classmethod
    def ensure_dirs(cls):
        """Ensure required directories exist."""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.WORKSPACE_DIR.mkdir(exist_ok=True)
        cls.FIX_WORKSPACE_DIR.mkdir(exist_ok=True)


# Create config instance
config = Config()
config.ensure_dirs()
