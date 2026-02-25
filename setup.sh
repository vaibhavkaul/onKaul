#!/usr/bin/env bash
set -euo pipefail

say() { printf "%s\n" "$*"; }
ask() {
  local prompt="$1"
  local reply
  read -r -p "$prompt" reply
  if [[ -z "$reply" ]]; then
    return 0
  fi
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
  if ask "Install $pkg with Homebrew? [Y/n] "; then
    brew install "$pkg"
  else
    say "Skipping $pkg"
  fi
}

say "onKaul setup (macOS)"

RESET_ENV=0
if [[ "${1:-}" == "--reset" ]]; then
  read -r -p "Type DELETE to reset .env and start fresh: " confirm
  if [[ "$confirm" != "DELETE" ]]; then
    say "Reset cancelled."
    exit 1
  fi
  if [[ -f .env ]]; then
    rm .env
  fi
  RESET_ENV=1
fi

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
else
  say "✓ python3 already installed"
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
  say ""
  say "Webapp mode selected."
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
  if ask "Install tesseract (OCR for attachments)? [Y/n] "; then
    install_brew_pkg tesseract
  fi
fi

if require_cmd gh; then
  say "✓ gh already installed"
else
  if ask "Install GitHub CLI (gh)? [Y/n] "; then
    install_brew_pkg gh
  fi
fi

if require_cmd acli; then
  say "✓ acli already installed"
else
  if ask "Do you use Atlassian products (Jira/Confluence)? [Y/n] "; then
    if ask "Install Atlassian CLI (acli)? [Y/n] "; then
      brew install atlassian-cli
    fi
  fi
fi

if [[ ! -f .env || "$RESET_ENV" -eq 1 ]]; then
  if [[ "$RESET_ENV" -eq 1 ]] || ask "Create .env with defaults? [Y/n] "; then
    {
      echo "# onKaul environment"
      echo ""
      echo "# App configuration"
      echo "DEBUG=true"
      echo "LOG_LEVEL=INFO"
      echo "API_HOST=0.0.0.0"
      echo "API_PORT=8000"
      echo "PUBLIC_BASE_URL=http://localhost:8000"
      echo ""
      echo "# Enable posting (set to true to actually post back)"
      echo "ENABLE_JIRA_POSTING=true"
      echo "ENABLE_SLACK_POSTING=true"
      echo "SLACK_VERIFY_SIGNATURE=true"
      echo "ENABLE_JIRA_WEBHOOK_VERIFICATION=true"
      echo ""
      echo "# Redis"
      echo "REDIS_URL=redis://localhost:6379/0"
      echo "REDIS_QUEUE_NAME=onkaul"
      echo "JOB_TIMEOUT_SECONDS=900"
      echo ""
      echo "# Core agent provider"
      echo "AGENT_PROVIDER=anthropic"
      echo "ANTHROPIC_MODEL=claude-sonnet-4-20250514"
      echo "ANTHROPIC_REASONING_MODEL=claude-opus-4-5-20251101"
      echo "OPENAI_MODEL=gpt-5-mini"
      echo "OPENAI_REASONING_MODEL=gpt-5"
      echo "OPENAI_STORE=true"
      echo ""
      echo "# Headless execution timeouts"
      echo "CODEX_TIMEOUT_SECONDS=1200"
      echo "CLAUDE_TIMEOUT_SECONDS=1200"
      echo ""
      echo "# Repo configuration"
      echo "REPO_CONFIG_PATH=./repository_config/repo_config.json"
      echo ""
      echo "# Workspace paths"
      echo "WORKSPACE_DIR=./workplace"
      echo "FIX_WORKSPACE_DIR=./fixes"
    } > .env
    say "Created .env."
  fi
fi

if [[ -f .env ]]; then
  say ""
  say "Configuring integrations..."

  get_current() {
    local k="$1"
    python3 - <<PY
from pathlib import Path
import re
key = "${k}"
path = Path(".env")
key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
text = path.read_text()
# Repair a file that was mistakenly written with literal "\n" sequences.
if "\n" not in text and "\\n" in text:
    text = text.replace("\\n", "\n")
text = text.replace("\r\n", "\n").replace("\r", "\n")
for line in text.split("\n"):
    m = key_re.match(line)
    if m and m.group(1) == key:
        print(m.group(2))
        break
PY
  }

  set_kv() {
    local k="$1"
    local v="$2"
    KEY="$k" VAL="$v" python3 - <<'PY'
from pathlib import Path
import re
import os

path = Path(".env")
text = path.read_text()
# Repair a file that was mistakenly written with literal "\n" sequences.
if "\n" not in text and "\\n" in text:
    text = text.replace("\\n", "\n")
text = text.replace("\r\n", "\n").replace("\r", "\n")
lines = text.split("\n")
key = os.environ["KEY"]
val = os.environ["VAL"]
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
path.write_text("\n".join(out) + "\n")
PY
  }

  prompt_kv() {
    local k="$1"
    local prompt="$2"
    local current
    current="$(get_current "$k")"
    if [[ -n "$current" ]]; then
      read -r -p "${prompt} (Enter to keep current): " val
      if [[ -z "$val" ]]; then
        return 0
      fi
    else
      read -r -p "${prompt}: " val
    fi
    if [[ -n "$val" ]]; then
      val="${val//$'\r'/}"
      set_kv "$k" "$val"
    fi
  }

  # Ensure default keys exist even if user skips prompts
  if [[ -z "$(get_current "DEBUG")" ]]; then set_kv "DEBUG" "true"; fi
  if [[ -z "$(get_current "LOG_LEVEL")" ]]; then set_kv "LOG_LEVEL" "INFO"; fi
  if [[ -z "$(get_current "API_HOST")" ]]; then set_kv "API_HOST" "0.0.0.0"; fi
  if [[ -z "$(get_current "API_PORT")" ]]; then set_kv "API_PORT" "8000"; fi
  if [[ -z "$(get_current "PUBLIC_BASE_URL")" ]]; then set_kv "PUBLIC_BASE_URL" "http://localhost:8000"; fi
  if [[ -z "$(get_current "AGENT_PROVIDER")" ]]; then set_kv "AGENT_PROVIDER" "anthropic"; fi
  if [[ -z "$(get_current "ANTHROPIC_MODEL")" ]]; then set_kv "ANTHROPIC_MODEL" "claude-sonnet-4-20250514"; fi
  if [[ -z "$(get_current "ANTHROPIC_REASONING_MODEL")" ]]; then set_kv "ANTHROPIC_REASONING_MODEL" "claude-opus-4-5-20251101"; fi
  if [[ -z "$(get_current "OPENAI_MODEL")" ]]; then set_kv "OPENAI_MODEL" "gpt-5-mini"; fi
  if [[ -z "$(get_current "OPENAI_REASONING_MODEL")" ]]; then set_kv "OPENAI_REASONING_MODEL" "gpt-5"; fi
  if [[ -z "$(get_current "OPENAI_STORE")" ]]; then set_kv "OPENAI_STORE" "true"; fi
  if [[ -z "$(get_current "CODEX_TIMEOUT_SECONDS")" ]]; then set_kv "CODEX_TIMEOUT_SECONDS" "1200"; fi
  if [[ -z "$(get_current "CLAUDE_TIMEOUT_SECONDS")" ]]; then set_kv "CLAUDE_TIMEOUT_SECONDS" "1200"; fi
  if [[ -z "$(get_current "REDIS_URL")" ]]; then set_kv "REDIS_URL" "redis://localhost:6379/0"; fi
  if [[ -z "$(get_current "REDIS_QUEUE_NAME")" ]]; then set_kv "REDIS_QUEUE_NAME" "onkaul"; fi
  if [[ -z "$(get_current "JOB_TIMEOUT_SECONDS")" ]]; then set_kv "JOB_TIMEOUT_SECONDS" "900"; fi
  if [[ -z "$(get_current "REPO_CONFIG_PATH")" ]]; then set_kv "REPO_CONFIG_PATH" "./repository_config/repo_config.json"; fi
  if [[ -z "$(get_current "WORKSPACE_DIR")" ]]; then set_kv "WORKSPACE_DIR" "./workplace"; fi
  if [[ -z "$(get_current "FIX_WORKSPACE_DIR")" ]]; then set_kv "FIX_WORKSPACE_DIR" "./fixes"; fi

  say ""
  say "Select integrations to configure:"

  say ""
  say "Select core agent provider:"
  select provider in "Anthropic" "OpenAI"; do
    case "$REPLY" in
      1) set_kv "AGENT_PROVIDER" "anthropic"; break ;;
      2) set_kv "AGENT_PROVIDER" "openai"; break ;;
      *) say "Please choose 1 or 2." ;;
    esac
  done

  current_provider="$(get_current "AGENT_PROVIDER")"
  if [[ "$current_provider" == "openai" ]]; then
    prompt_kv "OPENAI_API_KEY" "OPENAI_API_KEY"
    prompt_kv "OPENAI_STORE" "OPENAI_STORE (true/false, default true)"
  else
    prompt_kv "ANTHROPIC_API_KEY" "ANTHROPIC_API_KEY"
  fi

  if ask "Configure Sentry? [Y/n] "; then
    prompt_kv "SENTRY_ORG" "SENTRY_ORG"
    prompt_kv "SENTRY_TOKEN" "SENTRY_TOKEN"
  fi

  if ask "Configure GitHub (gh CLI still required)? [Y/n] "; then
    prompt_kv "GITHUB_ORG" "GITHUB_ORG"
  fi

  if ask "Configure Datadog? [Y/n] "; then
    prompt_kv "DD_API_KEY" "DD_API_KEY"
    prompt_kv "DD_APP_KEY" "DD_APP_KEY"
    prompt_kv "DD_SITE" "DD_SITE (default datadoghq.com)"
  fi

  if ask "Configure Confluence? [Y/n] "; then
    prompt_kv "CONFLUENCE_EMAIL" "CONFLUENCE_EMAIL"
    prompt_kv "CONFLUENCE_API_TOKEN" "CONFLUENCE_API_TOKEN"
    prompt_kv "CONFLUENCE_CLOUD_ID" "CONFLUENCE_CLOUD_ID"
    prompt_kv "CONFLUENCE_WIKI_BASE_URL" "CONFLUENCE_WIKI_BASE_URL"
    prompt_kv "CONFLUENCE_API_BASE_URL" "CONFLUENCE_API_BASE_URL (default https://api.atlassian.com/ex/confluence)"
  fi

  if ask "Configure Brave Search? [Y/n] "; then
    prompt_kv "BRAVE_SEARCH_API_KEY" "BRAVE_SEARCH_API_KEY"
  fi

  if [[ "$MODE" == "webapp" ]]; then
    say ""
    say "Webapp mode requires Slack and Jira configuration."

    prompt_kv "SLACK_BOT_TOKEN" "SLACK_BOT_TOKEN"
    prompt_kv "SLACK_SIGNING_SECRET" "SLACK_SIGNING_SECRET"
    set_kv "SLACK_VERIFY_SIGNATURE" "true"

    prompt_kv "JIRA_BASE_URL" "JIRA_BASE_URL"
    prompt_kv "JIRA_EMAIL" "JIRA_EMAIL"
    prompt_kv "JIRA_API_TOKEN" "JIRA_API_TOKEN"
    prompt_kv "JIRA_WEBHOOK_SECRET" "JIRA_WEBHOOK_SECRET"
    set_kv "ENABLE_JIRA_WEBHOOK_VERIFICATION" "true"

    if ask "Enable Slack webhook verification? [Y/n] "; then
      set_kv "SLACK_VERIFY_SIGNATURE" "true"
    else
      set_kv "SLACK_VERIFY_SIGNATURE" "false"
    fi

    if ask "Enable Jira webhook verification? [Y/n] "; then
      set_kv "ENABLE_JIRA_WEBHOOK_VERIFICATION" "true"
    else
      set_kv "ENABLE_JIRA_WEBHOOK_VERIFICATION" "false"
    fi
  fi

  if ask "Configure local workspace paths? [Y/n] "; then
    prompt_kv "WORKSPACE_DIR" "WORKSPACE_DIR (default ./workplace)"
    prompt_kv "FIX_WORKSPACE_DIR" "FIX_WORKSPACE_DIR (default ./fixes)"
  else
    set_kv "WORKSPACE_DIR" "./workplace"
    set_kv "FIX_WORKSPACE_DIR" "./fixes"
  fi

  if ask "Configure fix executor engine (codex or claude)? [Y/n] "; then
    prompt_kv "FIX_EXECUTOR_ENGINE" "FIX_EXECUTOR_ENGINE (codex/claude)"
  fi

  if ask "Configure Codex CLI path? [Y/n] "; then
    current_codex_plan="$(get_current "CODEX_PLAN_CMD")"
    if [[ -n "$current_codex_plan" ]]; then
      read -r -p "CODEX_CLI_PATH (e.g., /Applications/Codex.app/Contents/Resources/codex) (Enter to keep current): " codex_path
      codex_path="${codex_path//$'\r'/}"
    else
      read -r -p "CODEX_CLI_PATH (e.g., /Applications/Codex.app/Contents/Resources/codex): " codex_path
      codex_path="${codex_path//$'\r'/}"
    fi
    if [[ -n "$codex_path" ]]; then
      set_kv "CODEX_PLAN_CMD" "$codex_path exec --dangerously-bypass-approvals-and-sandbox --color never"
      set_kv "CODEX_APPLY_CMD" "$codex_path exec --dangerously-bypass-approvals-and-sandbox --color never"
    fi
  fi

  if ask "Configure Claude CLI path? [Y/n] "; then
    current_claude_plan="$(get_current "CLAUDE_PLAN_CMD")"
    if [[ -n "$current_claude_plan" ]]; then
      read -r -p "CLAUDE_CLI_PATH (e.g., claude) (Enter to keep current): " claude_path
      claude_path="${claude_path//$'\r'/}"
    else
      read -r -p "CLAUDE_CLI_PATH (e.g., claude): " claude_path
      claude_path="${claude_path//$'\r'/}"
    fi
    if [[ -n "$claude_path" ]]; then
      set_kv "CLAUDE_PLAN_CMD" "$claude_path -p --allowedTools \"Bash,Read\" --permission-mode acceptEdits --output-format text"
      set_kv "CLAUDE_APPLY_CMD" "$claude_path -p --allowedTools \"Bash,Read,Edit\" --permission-mode acceptEdits --output-format text"
    fi
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
