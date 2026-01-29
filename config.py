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

    # Enable posting to Slack/Jira
    ENABLE_JIRA_POSTING = os.getenv("ENABLE_JIRA_POSTING", "false").lower() == "true"
    ENABLE_SLACK_POSTING = os.getenv("ENABLE_SLACK_POSTING", "false").lower() == "true"

    # Paths
    BASE_DIR = Path(__file__).parent
    LOGS_DIR = BASE_DIR / "logs"
    RESPONSE_LOG_FILE = LOGS_DIR / "responses.jsonl"

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
    CONFLUENCE_WIKI_BASE_URL = os.getenv("CONFLUENCE_WIKI_BASE_URL", "https://taptapsend.atlassian.net/wiki")

    # Sentry
    SENTRY_TOKEN = os.getenv("SENTRY_TOKEN")
    SENTRY_ORG = os.getenv("SENTRY_ORG")

    # GitHub (uses gh CLI)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_ORG = os.getenv("GITHUB_ORG", "taptapsend")

    # Datadog (reads from DD_ env vars - standard Datadog convention)
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY") or os.getenv("DD_API_KEY")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY") or os.getenv("DD_APP_KEY")
    DATADOG_SITE = os.getenv("DATADOG_SITE") or os.getenv("DD_SITE", "datadoghq.com")

    # Brave Search - for web research
    BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

    @classmethod
    def ensure_dirs(cls):
        """Ensure required directories exist."""
        cls.LOGS_DIR.mkdir(exist_ok=True)


# Create config instance
config = Config()
config.ensure_dirs()
