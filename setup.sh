#!/usr/bin/env bash
set -euo pipefail

say() { printf "%s\n" "$*"; }
ask() {
  local prompt="$1"
  local reply
  read -r -p "$prompt" reply
  case "${reply,,}" in
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

say "\nChecking core dependencies..."
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
  fi
fi

say "\nOptional tools (install if you use these features):"
if ! require_cmd tesseract; then
  if ask "Install tesseract (OCR for attachments)? [y/N] "; then
    install_brew_pkg tesseract
  fi
else
  say "✓ tesseract already installed"
fi

if ! require_cmd gh; then
  if ask "Install GitHub CLI (gh)? [y/N] "; then
    install_brew_pkg gh
  fi
else
  say "✓ gh already installed"
fi

if ! require_cmd acli; then
  if ask "Install Atlassian CLI (acli)? [y/N] "; then
    brew install atlassian-cli
  fi
else
  say "✓ acli already installed"
fi

if [[ ! -f .env ]]; then
  if ask "Create .env from .env.example? [y/N] "; then
    cp .env.example .env
    say "Created .env. Please fill in required values."
  fi
fi

say "\nSetup complete."
if [[ "$MODE" == "cli" ]]; then
  say "Run: uv run onkaul"
else
  say "Run: uv run uvicorn main:app --reload --port 8000"
fi
