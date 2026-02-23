#!/usr/bin/env bash
set -euo pipefail

say() { printf "%s\n" "$*"; }
ask() {
  local prompt="$1"
  local reply
  read -r -p "$prompt" reply
  reply="$(echo "$reply" | tr '[:upper:]' '[:lower:]')"
  case "$reply" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

install_brew_pkg() {
  local pkg="$1"
  if brew list --formula "$pkg" >/dev/null 2>&1; then
    say "✓ $pkg already installed"
    return 0
  fi
  if ask "Install $pkg with Homebrew? [y/N] "; then
    brew install "$pkg"
  else
    say "Skipping $pkg"
  fi
}

say "onKaul setup (macOS)"

if [[ "$(uname -s)" != "Darwin" ]]; then
  say "This setup.sh currently supports macOS only."
  say "Exiting."
  exit 1
fi

if ! require_cmd brew; then
  say "Homebrew is required."
  say "Install Homebrew from https://brew.sh and re-run this script."
  exit 1
fi

say "Select mode:"
select mode in "CLI" "Webapp"; do
  case "$REPLY" in
    1) MODE="cli"; break ;;
    2) MODE="webapp"; break ;;
    *) say "Please choose 1 or 2." ;;
  esac
done

say ""
say "Checking core dependencies..."
if ! require_cmd python3; then
  say "Python3 not found."
  install_brew_pkg python@3.12
fi

if ! require_cmd uv; then
  say "uv not found."
  install_brew_pkg uv
fi

if ! require_cmd git; then
  say "git not found."
  install_brew_pkg git
fi

if [[ "$MODE" == "webapp" ]]; then
  say "\nWebapp mode selected."
  if ! require_cmd redis-server; then
    say "Redis not found."
    install_brew_pkg redis
    if require_cmd redis-server; then
      say "✓ redis installed"
    fi
  else
    say "✓ redis already installed"
  fi
fi

say ""
say "Optional tools (install if you use these features):"

if require_cmd tesseract; then
  say "✓ tesseract already installed"
else
  if ask "Install tesseract (OCR for attachments)? [y/N] "; then
    install_brew_pkg tesseract
  fi
fi

if require_cmd gh; then
  say "✓ gh already installed"
else
  if ask "Install GitHub CLI (gh)? [y/N] "; then
    install_brew_pkg gh
  fi
fi

if require_cmd acli; then
  say "✓ acli already installed"
else
  if ask "Do you use Atlassian products (Jira/Confluence)? [y/N] "; then
    if ask "Install Atlassian CLI (acli)? [y/N] "; then
      brew install atlassian-cli
    fi
  fi
fi

if [[ ! -f .env ]]; then
  if ask "Create .env from .env.example? [y/N] "; then
    cp .env.example .env
    say "Created .env."
  fi
fi

if [[ -f .env ]]; then
  say ""
  say "Configuring integrations..."

  set_kv() {
    local k="$1"
    local v="$2"
    python3 - <<PY
from pathlib import Path
import re

path = Path(".env")
text = path.read_text()
lines = text.splitlines()
key = "${k}"
val = "${v}"
key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
out = []
found = False
for line in lines:
    m = key_re.match(line)
    if m and m.group(1) == key:
        out.append(f"{key}={val}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{key}={val}")
path.write_text("\\n".join(out) + "\\n")
PY
  }

  say ""
  say "Select integrations to configure:"

  if ask "Configure Sentry? [y/N] "; then
    read -r -p "SENTRY_ORG: " val; set_kv "SENTRY_ORG" "$val"
    read -r -p "SENTRY_TOKEN: " val; set_kv "SENTRY_TOKEN" "$val"
  fi

  if ask "Configure GitHub (gh CLI still required)? [y/N] "; then
    read -r -p "GITHUB_ORG: " val; set_kv "GITHUB_ORG" "$val"
  fi

  if ask "Configure Datadog? [y/N] "; then
    read -r -p "DD_API_KEY: " val; set_kv "DD_API_KEY" "$val"
    read -r -p "DD_APP_KEY: " val; set_kv "DD_APP_KEY" "$val"
    read -r -p "DD_SITE (default datadoghq.com): " val
    if [[ -n "$val" ]]; then set_kv "DD_SITE" "$val"; fi
  fi

  if ask "Configure Confluence? [y/N] "; then
    read -r -p "CONFLUENCE_EMAIL: " val; set_kv "CONFLUENCE_EMAIL" "$val"
    read -r -p "CONFLUENCE_API_TOKEN: " val; set_kv "CONFLUENCE_API_TOKEN" "$val"
    read -r -p "CONFLUENCE_CLOUD_ID: " val; set_kv "CONFLUENCE_CLOUD_ID" "$val"
    read -r -p "CONFLUENCE_WIKI_BASE_URL: " val; set_kv "CONFLUENCE_WIKI_BASE_URL" "$val"
  fi

  if ask "Configure Brave Search? [y/N] "; then
    read -r -p "BRAVE_SEARCH_API_KEY: " val; set_kv "BRAVE_SEARCH_API_KEY" "$val"
  fi

  if [[ "$MODE" == "webapp" ]]; then
    say "\nWebapp mode requires Slack and Jira configuration."

    read -r -p "SLACK_BOT_TOKEN: " val; set_kv "SLACK_BOT_TOKEN" "$val"
    read -r -p "SLACK_SIGNING_SECRET: " val; set_kv "SLACK_SIGNING_SECRET" "$val"
    set_kv "SLACK_VERIFY_SIGNATURE" "true"

    read -r -p "JIRA_BASE_URL: " val; set_kv "JIRA_BASE_URL" "$val"
    read -r -p "JIRA_EMAIL: " val; set_kv "JIRA_EMAIL" "$val"
    read -r -p "JIRA_API_TOKEN: " val; set_kv "JIRA_API_TOKEN" "$val"
    read -r -p "JIRA_WEBHOOK_SECRET: " val; set_kv "JIRA_WEBHOOK_SECRET" "$val"
    set_kv "ENABLE_JIRA_WEBHOOK_VERIFICATION" "true"
  fi

  say "Updated .env with selected integrations."
fi

say ""
say "Setup complete."
if [[ "$MODE" == "cli" ]]; then
  say "Run: uv run onkaul"
else
  say "Run: uv run uvicorn main:app --reload --port 8000"
fi
