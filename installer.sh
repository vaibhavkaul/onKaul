#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="vaibhavkaul/onKaul"
PROJECT_DIR=""
USE_GUM=0
COLOR=1

supports_color() {
  [[ -t 1 ]] || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  return 0
}

init_ui() {
  if ! supports_color; then
    COLOR=0
  fi
  if require_cmd gum && [[ -r /dev/tty ]] && [[ -w /dev/tty ]]; then
    USE_GUM=1
  fi
}

maybe_install_gum() {
  if [[ "$USE_GUM" -eq 1 ]]; then
    return 0
  fi
  if ! require_cmd brew; then
    return 0
  fi

  if ask_yes_no "Install gum for arrow-key menus and richer prompts?"; then
    brew install gum
    if require_cmd gum; then
      USE_GUM=1
      success "gum installed. Enhanced interactive mode enabled."
    fi
  fi
}

style() {
  local code="$1"
  local text="$2"
  if [[ "$COLOR" -eq 1 ]]; then
    printf "\033[%sm%s\033[0m\n" "$code" "$text"
  else
    printf "%s\n" "$text"
  fi
}

say() { printf "%s\n" "$*"; }
info() { style "36" "$*"; }
success() { style "32" "$*"; }
warn() { style "33" "$*"; }
step() { style "34;1" "$*"; }
die() {
  if [[ "$COLOR" -eq 1 ]]; then
    printf "\033[31;1mERROR:\033[0m %s\n" "$*" >&2
  else
    printf "ERROR: %s\n" "$*" >&2
  fi
  exit 1
}

banner() {
  step "onKaul installer"
}

read_prompt() {
  local prompt="$1"
  local outvar="$2"
  local value=""

  if [[ -r /dev/tty ]]; then
    read -r -p "$prompt" value </dev/tty
  else
    read -r -p "$prompt" value
  fi
  printf -v "$outvar" "%s" "$value"
}

ask_yes_no() {
  local prompt="$1"
  local value=""

  if [[ "$USE_GUM" -eq 1 ]]; then
    say "$prompt"
    value="$(gum choose --cursor.foreground 212 --selected.foreground 212 "Yes" "No" </dev/tty)"
    [[ "$value" == "Yes" ]]
    return
  fi

  read_prompt "$prompt [Y/n] " value
  value="$(printf "%s" "$value" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    ""|y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1
}

require_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    die "This installer currently supports macOS only. Linux support is coming soon."
  fi
}

ensure_gh_setup() {
  require_cmd gh || die "GitHub CLI (gh) is required. Install it with Homebrew: brew install gh"

  if ! gh auth status >/dev/null 2>&1; then
    die "GitHub CLI is not authenticated. Run 'gh auth login' and re-run installer."
  fi
}

ensure_docker_installed() {
  if require_cmd docker; then
    return 0
  fi

  warn "Docker is not installed."
  if ! require_cmd brew; then
    die "Docker Desktop is required. Install Docker Desktop manually, then re-run installer."
  fi

  if ask_yes_no "Install Docker Desktop with Homebrew now?"; then
    brew install --cask docker
  else
    die "Docker Desktop is required for local Docker and local CLI shell modes."
  fi

  require_cmd docker || die "Docker CLI still not found. Open a new terminal and re-run installer."
}

ensure_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    die "Docker Compose v2 is required (docker compose). Update Docker Desktop and re-run."
  fi
}

ensure_docker_engine_running() {
  local i=0
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  warn "Docker engine is not running."
  if ask_yes_no "Open Docker Desktop now?"; then
    open -a Docker >/dev/null 2>&1 || true
  fi

  info "Waiting for Docker engine to become ready..."
  for i in $(seq 1 45); do
    if docker info >/dev/null 2>&1; then
      success "Docker engine is ready."
      return 0
    fi
    sleep 2
  done
  die "Docker engine did not become ready. Start Docker Desktop and re-run installer."
}

ensure_docker_setup() {
  ensure_docker_installed
  ensure_docker_compose
  ensure_docker_engine_running
}

is_repo_root() {
  [[ -f ".env.example" && -f "docker-compose.yml" && -f "README.md" ]]
}

dir_has_only_installer_artifacts() {
  local dir="$1"
  local entry=""
  local base=""
  local entries=()

  shopt -s nullglob dotglob
  entries=("$dir"/*)
  shopt -u nullglob dotglob

  if [[ ${#entries[@]} -eq 0 ]]; then
    return 1
  fi

  for entry in "${entries[@]}"; do
    base="$(basename "$entry")"
    case "$base" in
      installer.sh|install.sh|.DS_Store) ;;
      *) return 1 ;;
    esac
  done
  return 0
}

choose_install_dir() {
  local target=""
  local default_dir

  default_dir="$(pwd)"
  if [[ "$USE_GUM" -eq 1 ]]; then
    target="$(gum input --prompt "Install directory: " --value "$default_dir" </dev/tty)"
  else
    read_prompt "Install directory [$default_dir]: " target
    if [[ -z "$target" ]]; then
      target="$default_dir"
    fi
  fi
  printf "%s\n" "$target"
}

resolve_project_dir() {
  local target=""
  local nested_target=""

  if is_repo_root; then
    PROJECT_DIR="$(pwd)"
    success "Using existing repository at $PROJECT_DIR"
    return 0
  fi

  target="$(choose_install_dir)"
  if [[ -d "$target/.git" ]]; then
    PROJECT_DIR="$target"
    success "Using existing clone at $PROJECT_DIR"
    return 0
  fi

  if [[ -d "$target" ]]; then
    if [[ -z "$(ls -A "$target")" ]]; then
      info "Cloning $REPO_SLUG into empty directory $target ..."
      gh repo clone "$REPO_SLUG" "$target"
      PROJECT_DIR="$target"
      return 0
    fi

    if dir_has_only_installer_artifacts "$target"; then
      info "Directory contains only installer artifact(s); cloning into $target ..."
      rm -f "$target/installer.sh" "$target/install.sh" "$target/.DS_Store"
      gh repo clone "$REPO_SLUG" "$target"
      PROJECT_DIR="$target"
      return 0
    fi

    nested_target="$target/onKaul"
    if ask_yes_no "Directory is not an onKaul clone. Clone into '$nested_target' instead?"; then
      if [[ -e "$nested_target" ]]; then
        if [[ -d "$nested_target/.git" ]]; then
          PROJECT_DIR="$nested_target"
          success "Using existing clone at $PROJECT_DIR"
          return 0
        fi
        die "Path already exists and is not an onKaul git clone: $nested_target"
      fi
      info "Cloning $REPO_SLUG into $nested_target ..."
      gh repo clone "$REPO_SLUG" "$nested_target"
      PROJECT_DIR="$nested_target"
      return 0
    fi

    die "Install directory exists and is not an onKaul git clone: $target"
  fi

  if [[ -e "$target" ]]; then
    die "Install path exists and is not a directory: $target"
  fi

  info "Cloning $REPO_SLUG into $target ..."
  gh repo clone "$REPO_SLUG" "$target"
  PROJECT_DIR="$target"
}

update_existing_clone() {
  if [[ ! -d "$PROJECT_DIR/.git" ]]; then
    return 0
  fi

  if [[ -n "$(git -C "$PROJECT_DIR" status --porcelain)" ]]; then
    warn "Local changes detected in $PROJECT_DIR; skipping auto-update."
    return 0
  fi

  info "Updating existing clone (git pull --ff-only)..."
  if ! git -C "$PROJECT_DIR" pull --ff-only; then
    warn "Auto-update failed; continuing with local clone."
  fi
}

upsert_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp_file

  tmp_file="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { found = 0 }
    $0 ~ "^[[:space:]]*" k "=" {
      print k "=" v
      found = 1
      next
    }
    { print }
    END {
      if (!found) {
        print k "=" v
      }
    }
  ' "$file" > "$tmp_file"
  mv "$tmp_file" "$file"
}

get_env_value() {
  local key="$1"
  local file="$2"
  awk -F'=' -v k="$key" '
    $1 == k {
      print substr($0, index($0, "=") + 1)
      exit
    }
  ' "$file"
}

ensure_local_config_paths() {
  local repo_path=""
  local mon_path=""
  local default_repo="./repository_config/repo_config_example.json"
  local default_mon="./repository_config/monitoring_config_example.json"

  repo_path="$(get_env_value "REPO_CONFIG_PATH" ".env" || true)"
  mon_path="$(get_env_value "MONITORING_CONFIG_PATH" ".env" || true)"

  if [[ -z "$repo_path" || ! -f "$repo_path" ]]; then
    upsert_env_value "REPO_CONFIG_PATH" "$default_repo" ".env"
    success "Set REPO_CONFIG_PATH=$default_repo"
  fi

  if [[ -z "$mon_path" || ! -f "$mon_path" ]]; then
    upsert_env_value "MONITORING_CONFIG_PATH" "$default_mon" ".env"
    success "Set MONITORING_CONFIG_PATH=$default_mon"
  fi
}

initialize_env() {
  local key=""
  local provider=""

  if [[ -f ".env" ]]; then
    success ".env already exists; leaving it as-is"
    return 0
  fi

  cp .env.example .env
  success "Created .env from .env.example"

  if [[ "$USE_GUM" -eq 1 ]]; then
    provider="$(gum choose --cursor.foreground 212 --selected.foreground 212 "anthropic" "openai" </dev/tty)"
  else
    say "Select core provider:"
    say "1) anthropic"
    say "2) openai"
    while true; do
      read_prompt "Choose 1-2: " provider
      case "$provider" in
        1) provider="anthropic"; break ;;
        2) provider="openai"; break ;;
        anthropic|openai) break ;;
        *) warn "Please enter 1, 2, anthropic, or openai." ;;
      esac
    done
  fi
  upsert_env_value "AGENT_PROVIDER" "$provider" ".env"

  if [[ "$provider" == "openai" ]]; then
    while true; do
      read_prompt "Enter OPENAI_API_KEY (required): " key
      if [[ -n "$key" ]]; then
        break
      fi
      warn "OPENAI_API_KEY is required when AGENT_PROVIDER=openai."
    done
    upsert_env_value "OPENAI_API_KEY" "$key" ".env"
    upsert_env_value "OPENAI_STORE" "true" ".env"
    success "Saved AGENT_PROVIDER=openai and OPENAI_API_KEY in .env"
  else
    while true; do
      read_prompt "Enter ANTHROPIC_API_KEY (required): " key
      if [[ -n "$key" ]]; then
        break
      fi
      warn "ANTHROPIC_API_KEY is required when AGENT_PROVIDER=anthropic."
    done
    upsert_env_value "ANTHROPIC_API_KEY" "$key" ".env"
    success "Saved AGENT_PROVIDER=anthropic and ANTHROPIC_API_KEY in .env"
  fi
}

is_stack_running() {
  local running_services=""
  running_services="$(docker compose ps --services --status running 2>/dev/null || true)"
  [[ "$running_services" == *"api"* ]] && [[ "$running_services" == *"bee-worker"* ]] && [[ "$running_services" == *"redis"* ]]
}

start_local_stack_detached() {
  step "Starting local stack (detached)"
  docker compose up --build -d

  info "Recent startup logs:"
  docker compose logs --tail=80 || true

  info "Service status:"
  docker compose ps || true

  info "To stop services later:"
  say "  docker compose down"
}

run_local_docker_setup() {
  step "Selected: Local Docker webapp mode"
  ensure_docker_setup

  initialize_env
  ensure_local_config_paths

  info "Local default for PUBLIC_BASE_URL should be: http://localhost:8000"

  if ask_yes_no "Start the Docker stack now?"; then
    start_local_stack_detached
    if ask_yes_no "Start interactive shell now (uv run onkaul)?"; then
      uv run onkaul
    fi
    return 0
  fi

  info "Run manually when ready:"
  say "  docker compose up --build -d"
  say "  docker compose logs --tail=80"
  say "  uv run onkaul"
  say "  docker compose down"
}

run_local_cli_setup() {
  step "Selected: Local CLI shell mode"
  info "This mode uses the local API server, so Docker services must be running."

  ensure_docker_setup
  initialize_env
  ensure_local_config_paths

  if ! is_stack_running; then
    warn "Local stack is not running."
    if ask_yes_no "Start local stack now?"; then
      start_local_stack_detached
    else
      info "Start services manually:"
      say "  docker compose up --build -d"
      info "Then run shell:"
      say "  uv run onkaul"
      return 0
    fi
  else
    success "Local stack appears to be running."
    docker compose ps || true
  fi

  info "Then launch the shell:"
  say "  uv run onkaul"
  info "To stop services:"
  say "  docker compose down"

  if ask_yes_no "Run 'uv run onkaul' now?"; then
    uv run onkaul
  fi
}

choose_mode() {
  local selection=""
  step "How do you want to run onKaul?"

  if [[ "$USE_GUM" -eq 1 ]]; then
    selection="$(gum choose \
      --cursor.foreground 212 \
      --selected.foreground 212 \
      "1) Local Docker webapp mode" \
      "2) Local CLI shell mode (requires local server)" \
      "3) AWS EC2 (coming soon)" \
      "4) AWS ECS (coming soon)" </dev/tty)"
    selection="${selection%%)*}"
  else
    say "1) Local Docker webapp mode"
    say "2) Local CLI shell mode (requires local server)"
    say "3) AWS EC2 (coming soon)"
    say "4) AWS ECS (coming soon)"
    say ""
    read_prompt "Choose 1-4: " selection
  fi

  case "$selection" in
    1) run_local_docker_setup ;;
    2) run_local_cli_setup ;;
    3) die "AWS EC2 installer is coming soon." ;;
    4) die "AWS ECS installer is coming soon." ;;
    *) die "Invalid selection: $selection" ;;
  esac
}

main() {
  init_ui
  banner
  maybe_install_gum
  [[ "$USE_GUM" -eq 1 ]] || warn "Tip: install gum for arrow-key menus and richer prompts (brew install gum)"
  require_macos
  ensure_gh_setup
  resolve_project_dir
  update_existing_clone
  cd "$PROJECT_DIR"
  is_repo_root || die "Repository clone is missing expected files (.env.example, docker-compose.yml, README.md)."
  choose_mode
}

main "$@"
