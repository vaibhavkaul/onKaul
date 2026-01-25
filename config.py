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

    # Phase 2.5 - Enable real posting
    ENABLE_JIRA_POSTING = os.getenv("ENABLE_JIRA_POSTING", "false").lower() == "true"
    ENABLE_SLACK_POSTING = os.getenv("ENABLE_SLACK_POSTING", "false").lower() == "true"

    # Paths
    BASE_DIR = Path(__file__).parent
    LOGS_DIR = BASE_DIR / "logs"
    RESPONSE_LOG_FILE = LOGS_DIR / "responses.jsonl"

    # API Keys (Phase 2+)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Slack (Phase 3+)
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

    # Jira (Phase 2+)
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

    # Sentry (Phase 2+)
    SENTRY_TOKEN = os.getenv("SENTRY_TOKEN")
    SENTRY_ORG = os.getenv("SENTRY_ORG")

    # GitHub (Phase 2+)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_ORG = os.getenv("GITHUB_ORG", "taptapsend")

    # Datadog (Phase 2+) - read from DD_ env vars (standard Datadog convention)
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY") or os.getenv("DD_API_KEY")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY") or os.getenv("DD_APP_KEY")
    DATADOG_SITE = os.getenv("DATADOG_SITE") or os.getenv("DD_SITE", "datadoghq.com")

    @classmethod
    def ensure_dirs(cls):
        """Ensure required directories exist."""
        cls.LOGS_DIR.mkdir(exist_ok=True)


# Create config instance
config = Config()
config.ensure_dirs()
